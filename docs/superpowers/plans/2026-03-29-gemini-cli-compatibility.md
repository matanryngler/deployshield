# Gemini CLI Compatibility Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix DeployShield's integration with Gemini CLI by updating hook names, matchers, and extension manifest structure.

**Architecture:** Add parallel support for Gemini CLI specific hook events (`BeforeTool`) and tool names (`run_shell_command`) alongside existing Claude Code hooks. Normalize the extension manifest and command definitions for Gemini discovery.

**Tech Stack:** JSON, TOML, Python (existing validator).

---

### Task 1: Update Extension Manifest

**Files:**
- Modify: `gemini-extension.json`

- [ ] **Step 1: Update `gemini-extension.json` to include `contextFileName` and remove unsupported keys**

```json
{
  "name": "deployshield",
  "version": "1.4.0",
  "description": "Production safety guardrails that block write/mutating operations on cloud, database, IaC, and deployment CLIs.",
  "author": "Matan Ryngler",
  "repository": "https://github.com/matanryngler/deployshield",
  "license": "MIT",
  "main": "hooks/hooks.json",
  "contextFileName": "GEMINI.md"
}
```

- [ ] **Step 2: Verify JSON validity**

Run: `python3 -m json.tool gemini-extension.json`
Expected: Valid JSON output

- [ ] **Step 3: Commit**

```bash
git add gemini-extension.json
git commit -m "fix: update extension manifest for Gemini CLI compatibility"
```

### Task 2: Add Gemini-Compatible Hooks

**Files:**
- Modify: `hooks/hooks.json`

- [ ] **Step 1: Add `BeforeTool` event with `run_shell_command` matcher**

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"${extensionPath:-$CLAUDE_PLUGIN_ROOT}/hooks/scripts/validate-cloud-command.py\""
          }
        ]
      }
    ],
    "BeforeTool": [
      {
        "matcher": "run_shell_command",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"${extensionPath:-$CLAUDE_PLUGIN_ROOT}/hooks/scripts/validate-cloud-command.py\""
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "echo '{\"hookSpecificOutput\":{\"hookEventName\":\"SessionStart\",\"contextForAgent\":\"DeployShield is active. Write/mutating operations are blocked for guarded CLIs. Only read-only commands are allowed.\"}}'"
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 2: Verify JSON validity**

Run: `python3 -m json.tool hooks/hooks.json`
Expected: Valid JSON output

- [ ] **Step 3: Commit**

```bash
git add hooks/hooks.json
git commit -m "fix: add BeforeTool hook for Gemini CLI compatibility"
```

### Task 3: Create Gemini Command Definition

**Files:**
- Create: `commands/deployshield-status.toml`

- [ ] **Step 1: Create the TOML command definition**

```toml
name = "deployshield-status"
description = "Show DeployShield protection status and guarded CLIs"

[[actions]]
type = "read_file"
file_path = "commands/deployshield-status.md"
```

- [ ] **Step 2: Commit**

```bash
git add commands/deployshield-status.toml
git commit -m "fix: add TOML definition for deployshield-status command"
```

### Task 4: Final Verification

- [ ] **Step 1: Run existing tests to ensure no regressions**

Run: `uv run pytest`
Expected: All tests PASS

- [ ] **Step 2: Verify file existence**

Run: `ls -l gemini-extension.json hooks/hooks.json commands/deployshield-status.toml`
Expected: All files exist
