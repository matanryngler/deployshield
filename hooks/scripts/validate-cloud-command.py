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
# Provider dispatch
# ──────────────────────────────────────────────────────────────────

PROVIDERS = {
    'aws':       ('AWS',        check_aws),
    'gcloud':    ('GCP',        check_gcloud),
    'az':        ('Azure',      check_az),
    'kubectl':   ('Kubernetes', check_kubectl),
    'helm':      ('Helm',       check_helm),
    'terraform': ('Terraform',  check_terraform),
    'pulumi':    ('Pulumi',     check_pulumi),
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
