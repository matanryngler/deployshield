# Gemini CLI Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable DeployShield to work with Gemini CLI by supporting its specific hook names and JSON formats.

**Architecture:** Update the hook registration and the validation script to be polyglot, detecting the platform from the input JSON and responding with the appropriate format.

**Tech Stack:** Python (stdlib), JSON, Shell.

---

### Task 1: Update Hook Registration

**Files:**
- Modify: `hooks/hooks.json`

- [ ] **Step 1: Add BeforeTool hook and update SessionStart**

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
            "command": "python3 \"${extensionPath}/hooks/scripts/validate-cloud-command.py\""
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
            "command": "echo '{\"hookSpecificOutput\":{\"hookEventName\":\"SessionStart\",\"contextForAgent\":\"DeployShield is active...\"},\"additionalContext\":\"DeployShield is active. Write/mutating operations are blocked for cloud, DB, and IaC tools. Use read-only commands.\"}'"
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add hooks/hooks.json
git commit -m "feat: add Gemini-compatible BeforeTool hook and update SessionStart"
```

### Task 2: Polyglot Validator Logic

**Files:**
- Modify: `hooks/scripts/validate-cloud-command.py`

- [ ] **Step 1: Update `deny` and `main` to handle Gemini formats**

```python
def deny(provider: str, cmd: str, platform: str = "claude") -> None:
    reason = (
        f"DeployShield: Blocked {provider} write operation "
        f"'{cmd.strip()}'. Only read-only commands are allowed in this context. "
        "This is an intentional safety guardrail to prevent accidental modifications "
        "to production or sensitive environments. If you need to perform this action, "
        "please verify your current context (e.g., kubeconfig, AWS profile) or use a "
        "read-only alternative like 'plan' or '--dry-run' if supported."
    )

    if platform == "gemini":
        result = {
            "decision": "deny",
            "reason": reason,
            "systemMessage": f"🔒 DeployShield: Blocked {provider} write operation"
        }
    else:
        result = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }

    json.dump(result, sys.stdout, indent=2)
    print()
    sys.exit(0)

# In check_segment, pass platform
def check_segment(segment: str, platform: str = "claude") -> None:
    # ... nested checks ...
    if binary in PROVIDERS:
        # ... context checks ...
        provider_name, checker = PROVIDERS[binary]
        if not checker(args):
            deny(provider_name, segment, platform)

def main() -> None:
    # ... read raw ...
    data = json.loads(raw)

    # Detect platform
    event = data.get("hook_event_name", "")
    platform = "gemini" if event == "BeforeTool" else "claude"

    command = data.get("tool_input", {}).get("command", "")
    # ...
    for seg in segments:
        check_segment(seg, platform)
```

- [ ] **Step 2: Commit**

```bash
git add hooks/scripts/validate-cloud-command.py
git commit -m "feat: support Gemini-style deny response and platform detection"
```

### Task 3: Integration Testing for Gemini

**Files:**
- Modify: `tests/test_integration.py`

- [ ] **Step 1: Add Gemini-specific integration tests**

```python
def run_validator_gemini(command: str) -> tuple[int, str]:
    """Pipe a command through the validator simulating Gemini and return (exit_code, stdout)."""
    payload = json.dumps({
        "hook_event_name": "BeforeTool",
        "tool_input": {"command": command}
    })
    result = subprocess.run(
        [sys.executable, SCRIPT],
        input=payload,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout

class TestGeminiCompatibility:
    def test_gemini_block_format(self):
        code, out = run_validator_gemini("terraform apply")
        assert code == 0
        result = json.loads(out)
        assert result["decision"] == "deny"
        assert "reason" in result
        assert "systemMessage" in result

    def test_gemini_allow_format(self):
        code, out = run_validator_gemini("terraform plan")
        assert code == 0
        assert out.strip() == ""
```

- [ ] **Step 2: Run tests**

Run: `uv run pytest tests/test_integration.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add Gemini compatibility integration tests"
```

### Task 4: Documentation Update

**Files:**
- Modify: `skills/gemini/SKILL.md`

- [ ] **Step 1: Update SKILL.md with correct Gemini details**

```markdown
## Integration
This skill uses the core DeployShield validator via a **BeforeTool** hook on the **run_shell_command** tool.
```

- [ ] **Step 2: Commit**

```bash
git add skills/gemini/SKILL.md
git commit -m "docs: update Gemini skill to reflect BeforeTool hook"
```
