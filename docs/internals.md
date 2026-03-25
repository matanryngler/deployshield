# DeployShield Internals

This document explains how DeployShield works under the hood, from command interception to validation.

## 1. Command Interception (Hooks)

DeployShield uses the **`PreToolUse`** hook event in Claude Code and Gemini CLI.

- **Trigger**: Every time the AI attempts to execute a `Bash` command.
- **Payload**: The CLI sends a JSON object containing the command string to DeployShield's validator script.
- **Response**: The validator must return a JSON response with a `permissionDecision` of either `"allow"` or `"deny"`.

## 2. Command Parsing (The State Machine)

Shell commands can be complex (nested quotes, subshells, compound operators). DeployShield uses a custom state machine in `hooks/scripts/validate-cloud-command.py` to correctly tokenize these commands.

### Compound Commands
The `split_compound_command` function splits a raw string into individual segments based on operators: `&&`, `||`, `;`, and `|`. It correctly ignores these operators if they are inside quotes or subshells.

### Recursive Validation
DeployShield is **recursive-by-design**. The `check_segment` function performs the following steps:

1.  **Extract Nested Commands**: It scans for `$(...)`, `` `...` ``, `<(...)`, and `>(...)`.
2.  **Recurse**: Each nested command is itself treated as a raw command string and passed back through the entire validation pipeline (splitting → normalization → checking).
3.  **Unwrap Wrappers**: It identifies administrative wrappers like `sudo` and `env`, strips their flags, and recursively validates the *actual* command being invoked.
4.  **Handle Shell Wrappers**: For `bash -c "..."` or `sh -c "..."`, it extracts the string argument and recursively validates its contents.

## 3. Normalization

The `normalize_segment` function simplifies a command token into a canonical binary name:
- **Env Prefix**: Strips `AWS_PROFILE=prod ...`
- **Full Paths**: Converts `/usr/local/bin/aws` to `aws`.
- **Wrappers**: Unwraps `sudo` and `env`.

## 4. Provider Registry

Guarded CLIs are defined in the `PROVIDERS` dictionary. Each entry maps a binary name to a **Checker Function**.

### Adding a New Provider
To add support for a new CLI:
1.  Implement a `check_<provider>` function that takes a list of arguments.
2.  Identify the "subcommand" (usually the first non-flag argument).
3.  Check it against a list of known read-only commands.
4.  Register the function in the `PROVIDERS` dictionary.

Example:
```python
def check_mycli(args):
    # Skip global flags
    subcmd = find_subcommand(args)
    return subcmd in ("get", "list", "show")

PROVIDERS = {
    "mycli": ("My CLI Provider", check_mycli),
}
```

## 5. Context-Aware Logic

Before a checker function is called, DeployShield attempts to detect the environment context.

- **Secure Default**: If no config is found, or if context detection fails, DeployShield assumes the context is "Sensitive" and blocks any non-read-only operation.
- **Glob Matching**: Users can use patterns like `prod-*` in their `.deployshield.json` to block wide ranges of environments at once.
