#!/usr/bin/env python3
"""DeployShield: Validates cloud CLI commands before execution.

Blocks write/mutating operations; allows read-only commands.
Reads PreToolUse hook JSON from stdin.
"""

import json
import sys


# ──────────────────────────────────────────────────────────────────
# Command splitting – respects quoting, subshells, escapes
# ──────────────────────────────────────────────────────────────────

def split_compound_command(cmd: str) -> list[str]:
    """Split a shell command on &&, ||, ;, | while respecting quoting."""
    segments: list[str] = []
    current: list[str] = []
    i = 0
    n = len(cmd)

    # Nesting depth for $(...) subshells
    paren_depth = 0
    # Nesting depth for <(...) and >(...) process substitutions
    in_single_quote = False
    in_double_quote = False
    in_backtick = False

    while i < n:
        c = cmd[i]

        # ── Escape handling ──────────────────────────────────
        if c == '\\' and not in_single_quote:
            current.append(c)
            if i + 1 < n:
                current.append(cmd[i + 1])
                i += 2
            else:
                i += 1
            continue

        # ── Single-quote context ─────────────────────────────
        if in_single_quote:
            current.append(c)
            if c == "'":
                in_single_quote = False
            i += 1
            continue

        # ── Backtick context ─────────────────────────────────
        if in_backtick:
            current.append(c)
            if c == '`':
                in_backtick = False
            i += 1
            continue

        # ── Quote openers ────────────────────────────────────
        if c == "'" and not in_double_quote:
            in_single_quote = True
            current.append(c)
            i += 1
            continue

        if c == '`' and not in_double_quote:
            in_backtick = True
            current.append(c)
            i += 1
            continue

        if c == '"':
            in_double_quote = not in_double_quote
            current.append(c)
            i += 1
            continue

        # ── Subshell / process substitution tracking ─────────
        if c == '$' and i + 1 < n and cmd[i + 1] == '(':
            paren_depth += 1
            current.append(c)
            current.append('(')
            i += 2
            continue

        if c in '<>' and i + 1 < n and cmd[i + 1] == '(':
            paren_depth += 1
            current.append(c)
            current.append('(')
            i += 2
            continue

        if c == '(' and paren_depth > 0:
            paren_depth += 1
            current.append(c)
            i += 1
            continue

        if c == ')' and paren_depth > 0:
            paren_depth -= 1
            current.append(c)
            i += 1
            continue

        # ── Only split when we're at the top level ───────────
        if paren_depth == 0 and not in_double_quote:
            # Check for && and ||
            if c in '&|' and i + 1 < n and cmd[i + 1] == c:
                seg = ''.join(current).strip()
                if seg:
                    segments.append(seg)
                current = []
                i += 2
                continue

            # Check for ;
            if c == ';':
                seg = ''.join(current).strip()
                if seg:
                    segments.append(seg)
                current = []
                i += 1
                continue

            # Check for single | (but not ||, already handled)
            if c == '|':
                seg = ''.join(current).strip()
                if seg:
                    segments.append(seg)
                current = []
                i += 1
                continue

        current.append(c)
        i += 1

    seg = ''.join(current).strip()
    if seg:
        segments.append(seg)

    return segments


# ──────────────────────────────────────────────────────────────────
# Normalize a single command segment
# ──────────────────────────────────────────────────────────────────

def normalize_segment(seg: str) -> tuple[str, list[str]]:
    """Strip env-var prefixes and full paths, return (binary, arg_tokens)."""
    import shlex
    try:
        tokens = shlex.split(seg)
    except ValueError:
        # Malformed quoting — fall back to naive split
        tokens = seg.split()

    if not tokens:
        return ('', [])

    # Strip env-var prefixes (KEY=VALUE ...)
    idx = 0
    while idx < len(tokens):
        tok = tokens[idx]
        if '=' in tok:
            key = tok.split('=', 1)[0]
            if key.isidentifier():
                idx += 1
                continue
        break

    if idx >= len(tokens):
        return ('', [])

    binary = tokens[idx]
    # Strip path: /usr/local/bin/aws -> aws
    if '/' in binary:
        binary = binary.rsplit('/', 1)[-1]

    args = tokens[idx + 1:]
    return (binary, args)


# ──────────────────────────────────────────────────────────────────
# Per-provider safe-list checks
# ──────────────────────────────────────────────────────────────────

def skip_flags(args: list[str], flags_with_value: set[str], flags_no_value: set[str]) -> list[str]:
    """Skip leading flags, return remaining positional args."""
    result = []
    i = 0
    while i < len(args):
        tok = args[i]
        if tok in flags_with_value and i + 1 < len(args):
            i += 2
            continue
        if tok in flags_no_value:
            i += 1
            continue
        if tok.startswith('-'):
            # Unknown flag — skip it alone (conservative)
            i += 1
            continue
        # Not a flag — rest is positional
        result = args[i:]
        break
    return result


def check_aws(args: list[str]) -> bool:
    positional = skip_flags(
        args,
        flags_with_value={'--profile', '--region', '--output', '--endpoint-url',
                          '--cli-input-json', '--cli-input-yaml'},
        flags_no_value={'--no-paginate', '--no-sign-request', '--no-verify-ssl', '--debug'},
    )

    if not positional:
        return True  # just `aws` or `aws --help`

    service = positional[0]
    action = positional[1] if len(positional) > 1 else ''
    rest = positional[2:]

    # Help is always safe
    if service == 'help' or action == 'help':
        return True

    # Safe single-word actions
    if action.startswith(('describe', 'get', 'list')) or action in ('wait', 'help'):
        return True

    # Safe compound patterns
    compound = f"{service} {action}"
    if compound.startswith('sts get-'):
        return True
    if compound == 's3 ls':
        return True
    if compound == 's3 cp':
        # Allow download only: src must be s3://, dst must NOT be s3://
        src, dst = '', ''
        for tok in rest:
            if tok.startswith('-'):
                continue
            if not src:
                src = tok
            elif not dst:
                dst = tok
                break
        if src.startswith('s3://') and not dst.startswith('s3://'):
            return True
        return False
    if compound == 'configure list':
        return True
    if compound == 'sso login':
        return True

    return False


def check_gcloud(args: list[str]) -> bool:
    positional = skip_flags(
        args,
        flags_with_value={'--project', '--account', '--format', '--configuration', '--verbosity'},
        flags_no_value={'--quiet', '--no-user-output-enabled'},
    )

    if not positional:
        return True

    joined = ' '.join(positional)

    # Safe action words anywhere in the subcommand chain
    safe_actions = ('describe', 'list', 'info', 'help')
    for tok in positional:
        if tok in safe_actions:
            return True

    # Safe compound patterns
    if joined.startswith(('config list', 'config get-value',
                          'auth list', 'auth print-')):
        return True

    return False


def check_az(args: list[str]) -> bool:
    positional = skip_flags(
        args,
        flags_with_value={'--output', '-o', '--subscription', '--resource-group', '-g', '--query'},
        flags_no_value={'--verbose', '--debug'},
    )

    if not positional:
        return True

    joined = ' '.join(positional)

    # Safe action words
    safe_actions = ('show', 'list', 'get', 'help')
    for tok in positional:
        if tok in safe_actions:
            return True

    # Safe compound patterns
    if joined.startswith(('account show', 'account list', 'ad signed-in-user show')):
        return True

    return False


def check_kubectl(args: list[str]) -> bool:
    # Allow --dry-run=client or --dry-run=server (but NOT --dry-run=none)
    for tok in args:
        if tok in ('--dry-run=client', '--dry-run=server', '--dry-run'):
            return True

    positional = skip_flags(
        args,
        flags_with_value={'--context', '--cluster', '--namespace', '-n',
                          '--kubeconfig', '-s', '--server', '--token', '--user'},
        flags_no_value=set(),
    )

    if not positional:
        return True

    subcmd = positional[0]
    subaction = positional[1] if len(positional) > 1 else ''

    safe_single = {'get', 'describe', 'logs', 'explain', 'api-resources',
                   'api-versions', 'cluster-info', 'version', 'diff', 'top', 'wait'}
    if subcmd in safe_single:
        return True

    if subcmd == 'config' and subaction in ('view', 'current-context') or \
       subcmd == 'config' and subaction.startswith('get-'):
        return True

    if subcmd == 'auth' and subaction == 'can-i':
        return True

    return False


def check_helm(args: list[str]) -> bool:
    # Allow --dry-run for any helm command
    if '--dry-run' in args:
        return True

    positional = skip_flags(
        args,
        flags_with_value={'--kube-context', '--kubeconfig', '-n', '--namespace'},
        flags_no_value={'--debug'},
    )

    if not positional:
        return True

    subcmd = positional[0]
    subaction = positional[1] if len(positional) > 1 else ''

    safe_single = {'list', 'ls', 'get', 'show', 'status', 'history',
                   'search', 'template', 'lint', 'verify', 'version', 'env'}
    if subcmd in safe_single:
        return True

    if subcmd == 'repo' and subaction == 'list':
        return True

    return False


def check_terraform(args: list[str]) -> bool:
    positional = skip_flags(
        args,
        flags_with_value={'-chdir'},
        flags_no_value=set(),
    )

    if not positional:
        return True

    subcmd = positional[0]
    subaction = positional[1] if len(positional) > 1 else ''

    safe_single = {'plan', 'show', 'output', 'validate', 'fmt',
                   'providers', 'version', 'graph', 'init'}
    if subcmd in safe_single:
        return True

    if subcmd == 'state' and subaction in ('list', 'show', 'pull'):
        return True

    if subcmd == 'workspace' and subaction in ('list', 'show'):
        return True

    return False


def check_pulumi(args: list[str]) -> bool:
    positional = skip_flags(
        args,
        flags_with_value={'--cwd', '-C', '--stack', '-s'},
        flags_no_value={'--verbose', '-v', '--debug'},
    )

    if not positional:
        return True

    subcmd = positional[0]
    subaction = positional[1] if len(positional) > 1 else ''

    safe_single = {'preview', 'whoami', 'version', 'about'}
    if subcmd in safe_single:
        return True

    if subcmd == 'stack' and subaction in ('ls', 'select'):
        return True

    if subcmd == 'config' and subaction == 'get':
        return True

    return False


# ──────────────────────────────────────────────────────────────────
# Database CLIs
# ──────────────────────────────────────────────────────────────────

# SQL keywords that are safe (read-only)
_SAFE_SQL_PREFIXES = (
    'select ', 'show ', 'describe ', 'explain ', 'desc ',
    '\\d', '\\l', '\\dt', '\\dn', '\\di', '\\ds', '\\dv', '\\du',
    '\\sf', '\\sv', '\\pset', '\\timing', '\\conninfo', '\\encoding',
)

_UNSAFE_SQL_PREFIXES = (
    'drop ', 'delete ', 'truncate ', 'alter ', 'update ', 'insert ',
    'create ', 'grant ', 'revoke ', 'replace ', 'merge ',
)


def _check_sql_safe(sql: str) -> bool:
    """Check if a SQL statement is read-only."""
    s = sql.strip().lower()
    if not s:
        return True
    # Psql backslash commands that are safe
    if s.startswith('\\'):
        # Block \! (shell escape), \copy, \i (file exec), \o (output to file)
        unsafe_backslash = ('\\!', '\\copy', '\\i ', '\\ir ', '\\o ')
        for prefix in unsafe_backslash:
            if s.startswith(prefix):
                return False
        return True
    for prefix in _SAFE_SQL_PREFIXES:
        if s.startswith(prefix):
            return True
    for prefix in _UNSAFE_SQL_PREFIXES:
        if s.startswith(prefix):
            return False
    # Unknown SQL — default-deny for safety
    return False


def check_psql(args: list[str]) -> bool:
    # Allow --help, --version
    if not args or '--help' in args or '--version' in args:
        return True

    # -l (list databases) is safe
    if '-l' in args or '--list' in args:
        return True

    # Check -c (command) flag for SQL content
    for i, tok in enumerate(args):
        if tok == '-c' and i + 1 < len(args):
            if not _check_sql_safe(args[i + 1]):
                return False
        elif tok.startswith('-c') and len(tok) > 2:
            if not _check_sql_safe(tok[2:]):
                return False

    # -f (file execution) — we can't verify file contents, block it
    if '-f' in args or '--file' in args:
        return False

    # If no -c and no -f, it's either a connection-only command or interactive.
    # Allow it — Claude can't interact with an interactive session.
    # But check for positional SQL after dbname (shouldn't happen with psql).
    return True


def check_mysql(args: list[str]) -> bool:
    if not args or '--help' in args or '--version' in args:
        return True

    # Check -e (execute) flag for SQL content
    for i, tok in enumerate(args):
        if tok == '-e' and i + 1 < len(args):
            if not _check_sql_safe(args[i + 1]):
                return False
        elif tok.startswith('-e') and len(tok) > 2:
            if not _check_sql_safe(tok[2:]):
                return False
        elif tok == '--execute' and i + 1 < len(args):
            if not _check_sql_safe(args[i + 1]):
                return False

    # Source/execute file — block
    if '--init-command' in args:
        return False
    for tok in args:
        if tok.startswith('--init-command='):
            return False

    return True


def check_mongosh(args: list[str]) -> bool:
    if not args or '--help' in args or '--version' in args:
        return True

    # Check --eval flag for JavaScript content
    for i, tok in enumerate(args):
        if tok == '--eval' and i + 1 < len(args):
            js = args[i + 1].lower()
            # Safe patterns
            if any(p in js for p in ('.find(', '.findone(', '.count(', 'show ',
                                      '.getstatus(', '.stats(', '.explain(',
                                      '.aggregate(', 'db.getnames', '.listdatabases',
                                      'printjson', 'db.version')):
                return True
            # Unsafe patterns
            if any(p in js for p in ('.drop(', '.delete', '.remove(', '.update(',
                                      '.insert(', '.replaceone(', '.createsindex',
                                      '.dropcollection', '.dropdatabase',
                                      'db.createcollection', 'db.createuser')):
                return False
            # Unknown JS — default-deny
            return False

    # --file / script file — block
    if '--file' in args or '-f' in args:
        return False

    return True


def check_redis_cli(args: list[str]) -> bool:
    if not args or '--help' in args or '--version' in args:
        return True

    # Skip connection flags to get to the command
    positional = skip_flags(
        args,
        flags_with_value={'-h', '--host', '-p', '--port', '-a', '--pass',
                          '-n', '--db', '-u', '--uri', '--user'},
        flags_no_value={'--tls', '--insecure', '--no-auth-warning', '-c', '--cluster'},
    )

    if not positional:
        return True

    cmd = positional[0].upper()
    safe_commands = {
        'GET', 'MGET', 'KEYS', 'SCAN', 'EXISTS', 'TYPE', 'TTL', 'PTTL',
        'STRLEN', 'LLEN', 'LRANGE', 'LINDEX', 'SCARD', 'SMEMBERS',
        'SISMEMBER', 'HGET', 'HGETALL', 'HKEYS', 'HVALS', 'HLEN',
        'ZCARD', 'ZRANGE', 'ZRANGEBYSCORE', 'ZSCORE', 'ZRANK',
        'INFO', 'PING', 'ECHO', 'DBSIZE', 'LASTSAVE', 'TIME',
        'CONFIG', 'SLOWLOG', 'CLIENT', 'CLUSTER', 'MEMORY',
        'OBJECT', 'DEBUG', 'XLEN', 'XRANGE', 'XINFO',
    }

    if cmd in safe_commands:
        # Extra check: CONFIG SET is not safe, CONFIG GET is
        if cmd == 'CONFIG' and len(positional) > 1:
            subcmd = positional[1].upper()
            if subcmd not in ('GET', 'RESETSTAT'):
                return False
        return True

    return False


# ──────────────────────────────────────────────────────────────────
# IaC deployment tools
# ──────────────────────────────────────────────────────────────────

def check_cdk(args: list[str]) -> bool:
    if not args or '--help' in args or '--version' in args:
        return True

    positional = skip_flags(
        args,
        flags_with_value={'--app', '-a', '--context', '-c', '--profile', '--output', '-o'},
        flags_no_value={'--verbose', '-v', '--debug', '--json', '--long'},
    )

    if not positional:
        return True

    subcmd = positional[0]
    safe = {'diff', 'synth', 'synthesize', 'list', 'ls', 'doctor', 'context',
            'metadata', 'version', 'docs'}
    return subcmd in safe


def check_sam(args: list[str]) -> bool:
    if not args or '--help' in args or '--version' in args:
        return True

    positional = skip_flags(
        args,
        flags_with_value={'--template', '-t', '--config-file', '--config-env',
                          '--profile', '--region'},
        flags_no_value={'--debug', '--verbose'},
    )

    if not positional:
        return True

    subcmd = positional[0]
    safe = {'validate', 'build', 'local', 'logs', 'list', 'traces', 'version'}
    return subcmd in safe


def check_serverless(args: list[str]) -> bool:
    if not args or '--help' in args or '--version' in args:
        return True

    positional = skip_flags(
        args,
        flags_with_value={'--stage', '-s', '--region', '-r', '--config', '-c',
                          '--aws-profile'},
        flags_no_value={'--verbose', '-v', '--debug'},
    )

    if not positional:
        return True

    subcmd = positional[0]
    safe = {'info', 'print', 'package', 'version', 'doctor', 'help'}
    if subcmd in safe:
        return True

    # invoke local is safe, invoke (remote) is not
    if subcmd == 'invoke' and 'local' in positional:
        return True

    return False


def check_ansible_playbook(args: list[str]) -> bool:
    if not args or '--help' in args or '--version' in args:
        return True

    # Only safe with --check (dry run) or --diff (show changes) or --list-hosts/--list-tasks
    if '--check' in args or '-C' in args:
        return True
    if '--list-hosts' in args or '--list-tasks' in args or '--list-tags' in args:
        return True
    if '--syntax-check' in args:
        return True

    return False


# ──────────────────────────────────────────────────────────────────
# Secrets / Vault
# ──────────────────────────────────────────────────────────────────

def check_vault(args: list[str]) -> bool:
    if not args or '--help' in args or '-h' in args or '--version' in args:
        return True

    positional = skip_flags(
        args,
        flags_with_value={'--address', '-address', '--namespace', '-namespace',
                          '--format', '-format'},
        flags_no_value={'--no-color', '-no-color'},
    )

    if not positional:
        return True

    subcmd = positional[0]
    safe = {'read', 'list', 'status', 'version', 'login', 'print', 'path-help',
            'audit', 'debug'}

    if subcmd in safe:
        return True

    if subcmd == 'token' and len(positional) > 1:
        return positional[1] in ('lookup', 'capabilities')

    if subcmd == 'kv' and len(positional) > 1:
        return positional[1] in ('get', 'list', 'metadata')

    if subcmd == 'secrets' and len(positional) > 1:
        return positional[1] == 'list'

    if subcmd == 'policy' and len(positional) > 1:
        return positional[1] in ('read', 'list', 'fmt')

    return False


# ──────────────────────────────────────────────────────────────────
# GitHub CLI
# ──────────────────────────────────────────────────────────────────

def check_gh(args: list[str]) -> bool:
    if not args or '--help' in args or '--version' in args:
        return True

    subcmd = args[0]
    subaction = args[1] if len(args) > 1 else ''

    # Always safe top-level commands
    if subcmd in ('auth', 'status', 'version', 'help', 'config', 'alias',
                  'completion', 'browse', 'search', 'extension', 'label'):
        return True

    # Per-resource safe actions
    read_actions = {'view', 'list', 'status', 'diff', 'checks', 'comment'}
    if subcmd in ('pr', 'issue', 'run', 'release', 'project'):
        if subaction in read_actions:
            return True

    # gh api — allow GET, block other methods
    if subcmd == 'api':
        # Check for explicit method flag
        for i, tok in enumerate(args):
            if tok in ('-X', '--method') and i + 1 < len(args):
                return args[i + 1].upper() == 'GET'
        # Default method for gh api is GET
        return True

    # gh repo — only view/list/clone/fork(read) are safe
    if subcmd == 'repo':
        return subaction in ('view', 'list', 'clone')

    # gh gist — only view/list
    if subcmd == 'gist':
        return subaction in ('view', 'list')

    return False


# ──────────────────────────────────────────────────────────────────
# Container runtimes
# ──────────────────────────────────────────────────────────────────

def check_docker(args: list[str]) -> bool:
    if not args or '--help' in args or '--version' in args:
        return True

    positional = skip_flags(
        args,
        flags_with_value={'-H', '--host', '--context', '-c', '--log-level', '-l'},
        flags_no_value={'--debug', '-D'},
    )

    if not positional:
        return True

    subcmd = positional[0]
    subaction = positional[1] if len(positional) > 1 else ''

    # Safe top-level commands
    safe_single = {'ps', 'images', 'info', 'version', 'inspect', 'logs',
                   'stats', 'top', 'port', 'events', 'diff', 'history',
                   'search', 'login', 'logout'}
    if subcmd in safe_single:
        return True

    # Management commands with safe subactions
    if subcmd in ('container', 'image', 'volume', 'network', 'node',
                  'service', 'stack', 'secret', 'config', 'plugin',
                  'system', 'context', 'manifest', 'trust', 'buildx',
                  'compose'):
        read_subs = {'ls', 'list', 'inspect', 'logs', 'top', 'stats',
                     'diff', 'history', 'events', 'info', 'version',
                     'show', 'ps', 'config'}
        if subaction in read_subs:
            return True
        # docker system df is safe
        if subcmd == 'system' and subaction == 'df':
            return True
        # docker compose ps/logs/config/version
        if subcmd == 'compose' and subaction in ('ps', 'logs', 'config',
                                                  'version', 'images', 'top'):
            return True
        return False

    # docker build is explicitly NOT safe (creates images, can push)
    return False


# ──────────────────────────────────────────────────────────────────
# Package publishing
# ──────────────────────────────────────────────────────────────────

def check_npm_publish(binary: str, args: list[str]) -> bool | None:
    """Check npm/yarn/pnpm for publish commands. Returns None if not relevant."""
    if binary not in ('npm', 'yarn', 'pnpm'):
        return None

    if not args:
        return True

    subcmd = args[0]
    # Block publish/unpublish, allow everything else
    if subcmd in ('publish', 'unpublish'):
        return False
    return True


def check_twine(args: list[str]) -> bool:
    if not args or '--help' in args:
        return True
    subcmd = args[0]
    return subcmd != 'upload'


def check_gem(args: list[str]) -> bool:
    if not args or '--help' in args or '--version' in args:
        return True
    subcmd = args[0]
    return subcmd not in ('push', 'yank')


def check_cargo(args: list[str]) -> bool:
    if not args or '--help' in args or '--version' in args:
        return True
    subcmd = args[0]
    return subcmd != 'publish'


# ──────────────────────────────────────────────────────────────────
# Provider dispatch
# ──────────────────────────────────────────────────────────────────

PROVIDERS = {
    # Cloud CLIs
    'aws':       ('AWS',        check_aws),
    'gcloud':    ('GCP',        check_gcloud),
    'az':        ('Azure',      check_az),
    'kubectl':   ('Kubernetes', check_kubectl),
    'helm':      ('Helm',       check_helm),
    'terraform': ('Terraform',  check_terraform),
    'pulumi':    ('Pulumi',     check_pulumi),
    # Database CLIs
    'psql':      ('PostgreSQL',  check_psql),
    'mysql':     ('MySQL',       check_mysql),
    'mongosh':   ('MongoDB',     check_mongosh),
    'mongo':     ('MongoDB',     check_mongosh),
    'redis-cli': ('Redis',       check_redis_cli),
    # IaC deployment tools
    'cdk':       ('CDK',         check_cdk),
    'sam':       ('SAM',         check_sam),
    'serverless': ('Serverless', check_serverless),
    'sls':       ('Serverless',  check_serverless),
    'ansible-playbook': ('Ansible', check_ansible_playbook),
    # Secrets
    'vault':     ('Vault',       check_vault),
    # GitHub CLI
    'gh':        ('GitHub CLI',  check_gh),
    # Container runtimes
    'docker':    ('Docker',      check_docker),
    'podman':    ('Podman',      check_docker),
    # Package publishing
    'twine':     ('PyPI',        check_twine),
    'gem':       ('RubyGems',    check_gem),
    'cargo':     ('Cargo',       check_cargo),
}


def deny(provider: str, cmd: str) -> None:
    result = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                f"DeployShield: Blocked {provider} write operation "
                f"'{cmd.strip()}'. Only read-only commands are allowed."
            ),
        }
    }
    json.dump(result, sys.stdout, indent=2)
    print()
    sys.exit(0)


def check_segment(segment: str) -> None:
    binary, args = normalize_segment(segment)
    if not binary:
        return

    # Special case: npm/yarn/pnpm — only block publish subcommand
    pub_result = check_npm_publish(binary, args)
    if pub_result is not None:
        if not pub_result:
            deny('npm', segment)
        return

    if binary in PROVIDERS:
        provider_name, checker = PROVIDERS[binary]
        if not checker(args):
            deny(provider_name, segment)


# ──────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────

def main() -> None:
    raw = sys.stdin.read()
    if not raw.strip():
        sys.exit(0)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        sys.exit(0)

    command = data.get('tool_input', {}).get('command', '')
    if not command:
        sys.exit(0)

    segments = split_compound_command(command)
    for seg in segments:
        check_segment(seg)

    # All segments passed
    sys.exit(0)


if __name__ == '__main__':
    main()
