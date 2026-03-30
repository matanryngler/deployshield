# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

DeployShield is a production safety guardrail for **Claude Code** and **Gemini CLI**. It blocks write/mutating CLI commands while allowing read-only ones. It works as a hook on shell commands — every command the AI tries to run goes through the validator, which default-denies any recognized CLI action that isn't on the safe-list. Unrecognized CLIs pass through untouched.

## Commands

```bash
# Run tests
uv run pytest -v

# Run a single test file or class
uv run pytest tests/test_integration.py -v
uv run pytest tests/test_cloud_providers.py -v

# Lint
uv run ruff check hooks/scripts/ tests/
uv run ruff format --check hooks/scripts/ tests/

# Pre-commit (runs automatically on commit after install)
uv run pre-commit install
uv run pre-commit run --all-files

# Manual smoke test (pipe JSON to stdin, exit 0 = allow, JSON output = deny)
echo '{"hook_event_name": "PreToolUse", "tool_input":{"command":"kubectl get pods"}}' | ./hooks/scripts/validate-cloud-command.py
echo '{"hook_event_name": "BeforeTool", "tool_input":{"command":"terraform apply"}}' | ./hooks/scripts/validate-cloud-command.py

# Test session start message
python3 hooks/scripts/validate-cloud-command.py --session-start claude
python3 hooks/scripts/validate-cloud-command.py --session-start gemini
```

## Architecture

The entire validation engine is a single Python script (`hooks/scripts/validate-cloud-command.py`) with no dependencies beyond the stdlib.

- **hooks/hooks.json** — Primary hook file for Gemini CLI (uses `BeforeTool` event).
- **hooks/claude-hooks.json** — Dedicated hook file for Claude Code (uses `PreToolUse` event).
- **.claude-plugin/plugin.json** — Plugin manifest. Points to `hooks/claude-hooks.json`.
- **hooks/scripts/validate-cloud-command.py** — Core logic. Flow: read JSON from stdin → detect platform from `hook_event_name` → `split_compound_command` (state-machine shell parser) → `normalize_segment` (unwraps `sudo`, `env`, `xargs`) → dispatch to per-provider `check_*` function → `deny()` with platform-specific JSON output if unsafe.
- **skills/deployshield/SKILL.md** — Context injected into Claude when working with infra files.
- **skills/gemini/SKILL.md** — Context injected into Gemini CLI.

### Adding a New Provider

1. Write a `check_newcli(args: list[str]) -> bool` function (True = safe, False = block)
2. Add it to the `PROVIDERS` dict at the bottom of the validator
3. Add tests in `tests/test_*.py`
4. Update `SKILL.md` (both Claude and Gemini) and `README.md` tables

### Context-Aware Blocking

Optional `.deployshield.json` config allows blocking writes only in specific contexts (e.g. prod kube context, production AWS profile). See README.md for full schema.

### Key Design Decisions

- **Dual-Hook Architecture**: Separate hook files for Gemini and Claude to avoid "Invalid hook event name" warnings in Gemini CLI.
- **Default-deny for guarded CLIs**: If the binary is in `PROVIDERS` but the subcommand isn't explicitly safe-listed, it's blocked.
- **Recursive Safety**: Scans subshells, backticks, `sudo`, `env`, `xargs`, and `bash -c`.
- **Command Sanitization**: Blocked commands are sanitized and truncated in rejection messages to prevent secret leaks or terminal injection.
- **No external dependencies**: The validator runs on any Python 3.8+ with just stdlib.

## Test Structure

Tests use `importlib.util` to import the validator as a module. `test_integration.py` verifies the full JSON I/O for both Claude and Gemini formats. Other tests focus on provider logic, command splitting, and normalization.

## CI

- PR titles must follow conventional commits.
- Releases via `release-please` in manifest mode — bumps version in manifests automatically.
