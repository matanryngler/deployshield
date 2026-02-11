# Security Policy

## Scope

DeployShield is a safety-guardrail plugin for Claude Code. Security reports in the following areas are welcome:

- **Parser bypasses** — shell quoting, escaping, or compound-command tricks that evade the validator
- **Checker logic flaws** — cases where a mutating command is incorrectly classified as safe
- **Safe-list gaps** — missing dangerous subcommands for a guarded CLI

## Reporting a Vulnerability

**Public issues:** For non-sensitive bugs (e.g., a missing subcommand in a safe-list), open a [GitHub issue](https://github.com/matanryngler/deployshield/issues).

**Sensitive disclosures:** For parser bypasses or logic flaws that could allow destructive commands to pass through undetected, please email **matan.ryngler@gmail.com** with:

1. A description of the vulnerability
2. A minimal reproducing command (the JSON payload you would pipe to the validator)
3. Expected vs. actual behavior

You will receive an acknowledgment within 48 hours and a fix or mitigation plan within 7 days.

## Known Limitations

DeployShield is a **defense-in-depth layer**, not a sandbox:

- It relies on CLI binary-name detection — renamed or aliased binaries are not caught.
- It does not inspect file contents (e.g., a SQL file passed with `psql -f`).
- It only guards the specific CLIs listed in the provider table; other tools pass through.
- Shell built-ins and functions are not intercepted.
- It operates at the command-string level and does not execute or sandbox commands.

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.x     | Yes       |
