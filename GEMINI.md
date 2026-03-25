# DeployShield

DeployShield is a Claude Code plugin that acts as a production safety guardrail. It intercepts Bash commands before execution and blocks dangerous operations (writes, deletes, etc.) while allowing read-only commands to pass through.

## Project Overview

- **Purpose:** Prevent accidental or malicious mutating operations on production environments by Claude.
- **Main Technologies:** Python 3.8+ (validation logic), Shell/Bash (intercepted commands), JSON (configuration).
- **Architecture:**
    - **Hook System:** Uses Claude Code's `PreToolUse` hook to intercept every Bash command.
    - **Recursive Validation:** Deeply scans commands for nested subshells (`$(...)`), backticks (`` `...` ``), administrative wrappers (`sudo`, `env`), and shell wrappers (`bash -c`).
    - **Validation Engine:** A Python script (`hooks/scripts/validate-cloud-command.py`) that handles compound commands (`&&`, `||`, `;`) and checks against provider-specific safe-lists.
    - **Plugin Manifest:** `.claude-plugin/plugin.json` and `hooks/hooks.json`.

## Building and Running

### Development Tools
This project uses **`uv`** for dependency management and tool execution.

### Installation
For local development:
```bash
git clone https://github.com/matanryngler/deployshield.git
claude --plugin-dir ./deployshield
```

### Testing
Tests are written in Python using `pytest`.
```bash
uv run --with pytest pytest -v
```

### Linting & Formatting
We use **`ruff`** for linting and formatting, managed via **`pre-commit`**.
```bash
# Install hooks (run once)
uv run pre-commit install

# Run manually
uv run pre-commit run --all-files
```

## Development Conventions

- **Safe-list Approach**: Every guarded CLI (e.g., `aws`, `kubectl`, `terraform`) must have an explicit safe-list of read-only subcommands.
- **Context-Aware Blocking**: Optional `.deployshield.json` config allows blocking writes only in specific contexts (e.g., prod kube contexts). Undetectable context defaults to **Blocked**.
- **Recursive Safety**: The validator must recurse into any subshells or wrappers to ensure dangerous commands aren't hidden.
- **No Dependencies**: The core validator script MUST NOT have any external dependencies beyond the Python standard library.

## Key Files

- `hooks/scripts/validate-cloud-command.py`: Core validation logic and recursive safety engine.
- `hooks/hooks.json`: Hook registration and session start message.
- `.claude-plugin/plugin.json`: Plugin metadata.
- `.deployshield.json`: (Optional) User configuration for context-aware blocking.
- `.pre-commit-config.yaml`: Pre-commit hook configuration.
- `skills/deployshield/SKILL.md`: Context for the agent about safe operations.
- `docs/superpowers/specs/`: Design documents for major features.
- `tests/`: Comprehensive test suite for various CLIs and edge cases.
