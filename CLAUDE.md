# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

DeployShield is a Claude Code plugin that blocks write/mutating CLI commands while allowing read-only ones. It works as a PreToolUse hook on Bash commands — every command Claude tries to run goes through the validator, which default-denies any recognized CLI action that isn't on the safe-list. Unrecognized CLIs pass through untouched.

## Commands

```bash
# Run tests (uses uv, no venv activation needed)
uv run --with pytest pytest -v

# Run a single test file or class
uv run --with pytest pytest tests/test_cloud_providers.py -v
uv run --with pytest pytest tests/test_cloud_providers.py::TestAWS -v

# Lint
uv run --with ruff ruff check hooks/scripts/ tests/
uv run --with ruff ruff format --check hooks/scripts/ tests/

# Format
uv run --with ruff ruff format hooks/scripts/ tests/

# Manual smoke test (pipe JSON to stdin, exit 0 = allow, JSON output = deny)
echo '{"tool_input":{"command":"kubectl get pods"}}' | ./hooks/scripts/validate-cloud-command.py
echo '{"tool_input":{"command":"terraform apply"}}' | ./hooks/scripts/validate-cloud-command.py
```

## Architecture

The entire validation engine is a single Python script (`hooks/scripts/validate-cloud-command.py`) with no dependencies beyond the stdlib. The hook system wires it up:

- **hooks/hooks.json** — Registers the PreToolUse hook (runs the validator on every Bash command) and a SessionStart hook (tells Claude that DeployShield is active).
- **hooks/scripts/validate-cloud-command.py** — Core logic. Flow: read JSON from stdin → `split_compound_command` (state-machine shell parser respecting quotes/subshells) → `normalize_segment` (strip env prefixes and paths via shlex) → dispatch to per-provider `check_*` function → `deny()` if unsafe.
- **skills/deployshield/SKILL.md** — Context injected into Claude when working with infra files (glob-matched). Lists safe commands and suggests dry-run alternatives.
- **.claude-plugin/plugin.json** — Plugin manifest (name, version, metadata). Version is bumped automatically by release-please.

### Adding a New Provider

1. Write a `check_newcli(args: list[str]) -> bool` function (True = safe, False = block)
2. Add it to the `PROVIDERS` dict at the bottom of the validator
3. Add tests in `tests/test_*.py` using the `v` fixture (which imports the validator as a module)
4. Update `SKILL.md` and `README.md` tables

### Context-Aware Blocking

Optional `.deployshield.json` config allows blocking writes only in specific contexts (e.g. prod kube context, production AWS profile). Config keys are CLI binary names, values are fnmatch glob patterns. See README.md for full schema. Key functions: `load_config()`, `detect_context()`, `context_is_blocked()`. Config is loaded lazily and cached per invocation.

### Key Design Decisions

- **Default-deny for guarded CLIs**: if the binary is in `PROVIDERS` but the subcommand isn't explicitly safe-listed, it's blocked.
- **Default-allow for unknown CLIs**: commands not in `PROVIDERS` (e.g., `git`, `make`) pass through.
- **Context-aware is opt-in**: without a config file, behavior is identical to before. Undetectable context defaults to blocked (secure).
- **No external dependencies**: the validator runs on any Python 3.8+ with just stdlib. This matters because it executes on every Bash command.

## Test Structure

Tests import the validator script as a module via `conftest.py` (uses `importlib.util`). The `v` fixture exposes all functions. Tests are organized by provider category: `test_cloud_providers.py`, `test_databases.py`, `test_iac_tools.py`, `test_other_providers.py`, `test_command_splitting.py`, `test_normalization.py`, `test_integration.py`.

## CI

- Python 3.9–3.14 test matrix + ruff lint on PRs to main
- PR titles must follow conventional commits (enforced by `amannn/action-semantic-pull-request`)
- Releases via `release-please` in manifest mode — bumps version in `plugin.json` and `marketplace.json`
