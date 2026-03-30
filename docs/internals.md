# DeployShield Internals

This document explains how DeployShield works under the hood, from command interception to validation.

## 1. Command Interception (Hooks)

DeployShield uses the **`PreToolUse`** (Claude Code) and **`BeforeTool`** (Gemini CLI) hook events.

- **Trigger**: Every time the AI attempts to execute a shell command (e.g., `Bash` in Claude or `run_shell_command` in Gemini).
- **Dual-Platform Architecture**:
    - **`hooks/hooks.json`**: Primary hook file for Gemini CLI. Contains only Gemini-supported events to avoid "Invalid hook event name" warnings.
    - **`hooks/claude-hooks.json`**: Dedicated hook file for Claude Code.
    - **`.claude-plugin/plugin.json`**: Configured with `"hooks": "./hooks/claude-hooks.json"` to direct Claude to the correct file.
- **Payload**: The CLI sends a JSON object containing the command string to DeployShield's validator script.
- **Response**: The validator returns a JSON response:
    - **Claude**: Uses `hookSpecificOutput.permissionDecision` (`"allow"` or `"deny"`).
    - **Gemini**: Uses `decision` (`"allow"` or `"deny"`) and `systemMessage` for colorful terminal output.

## 2. Command Parsing (The State Machine)

Shell commands can be complex (nested quotes, subshells, compound operators). DeployShield uses a custom state machine in `hooks/scripts/validate-cloud-command.py` to correctly tokenize these commands.

### Compound Commands
The `split_compound_command` function splits a raw string into individual segments based on operators: `&&`, `||`, `;`, and `|`. It correctly ignores these operators if they are inside quotes or subshells.

### Recursive Validation
DeployShield is **recursive-by-design**. The `check_segment` function performs the following steps:

1.  **Extract Nested Commands**: It scans for `$(...)`, `` `...` ``, `<(...)`, and `>(...)`.
2.  **Recurse**: Each nested command is itself treated as a raw command string and passed back through the entire validation pipeline (splitting → normalization → checking).
3.  **Unwrap Wrappers**: It identifies administrative and execution wrappers like `sudo`, `env`, and `xargs`, strips their flags, and recursively validates the *actual* command being invoked.
4.  **Handle Shell Wrappers**: For `bash -c "..."` or `sh -c "..."`, it extracts the string argument and recursively validates its contents.

## 3. Normalization

The `normalize_segment` function simplifies a command token into a canonical binary name:
- **Env Prefix**: Strips `AWS_PROFILE=prod ...`
- **Full Paths**: Converts `/usr/local/bin/aws` to `aws`.
- **Wrappers**: Unwraps `sudo`, `env`, and `xargs`.

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

## 5. Session Initialization (Onboarding)

DeployShield uses a centralized `SessionStart` logic to ensure consistency between the validator rules and the documentation shown to the AI agent.

- **Logic**: The `validate-cloud-command.py` script has a `--session-start <platform>` flag.
- **Dynamic Message**: It generates an onboarding message that automatically lists all currently guarded providers from the `PROVIDERS` registry.
- **Injection**: This message is injected into the agent's initial context to inform it that DeployShield is active and explain its rules.

## 6. Security and Sanitization

When a command is blocked, DeployShield provides a descriptive reason to both the user and the agent.
- **Explicit Platform Validation**: The validator explicitly validates the `hook_event_name` to ensure it only responds to supported events.
- **Command Sanitization**: Blocked commands are sanitized (stripped of newlines/control characters and truncated) before being included in the rejection message to prevent terminal injection or secret leakage.
- **Fail-Safe**: If an unknown or malformed JSON payload is received, DeployShield exits cleanly with code 0 (Allow) to avoid breaking the user's terminal session, unless it's an unsupported hook event in which case it fails fast.
