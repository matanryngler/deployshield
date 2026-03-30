"""End-to-end integration tests: pipe JSON to the script, check stdout/exit code."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = str(
    Path(__file__).resolve().parent.parent
    / "hooks"
    / "scripts"
    / "validate-cloud-command.py"
)


def run_validator(command: str) -> tuple[int, str]:
    """Pipe a command through the validator and return (exit_code, stdout)."""
    payload = json.dumps(
        {
            "tool_input": {"command": command},
            "hook_event_name": "PreToolUse",
        }
    )
    result = subprocess.run(
        [sys.executable, SCRIPT],
        input=payload,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout


class TestAllowed:
    def test_aws_describe(self):
        code, out = run_validator("aws ec2 describe-instances")
        assert code == 0
        assert out.strip() == ""

    def test_kubectl_get(self):
        code, out = run_validator("kubectl get pods")
        assert code == 0
        assert out.strip() == ""

    def test_terraform_plan(self):
        code, out = run_validator("terraform plan")
        assert code == 0
        assert out.strip() == ""

    def test_non_cloud_command(self):
        """Non-guarded commands should always pass through."""
        code, out = run_validator("git push origin main")
        assert code == 0
        assert out.strip() == ""

    def test_npm_test(self):
        code, out = run_validator("npm test")
        assert code == 0
        assert out.strip() == ""

    def test_compound_allowed(self):
        code, out = run_validator("aws s3 ls && kubectl get pods")
        assert code == 0
        assert out.strip() == ""


class TestBlocked:
    def test_terraform_apply(self):
        code, out = run_validator("terraform apply")
        assert code == 0
        result = json.loads(out)
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_kubectl_apply(self):
        code, out = run_validator("kubectl apply -f deploy.yaml")
        assert code == 0
        result = json.loads(out)
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_npm_publish(self):
        code, out = run_validator("npm publish")
        assert code == 0
        result = json.loads(out)
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_compound_blocks_on_second(self):
        """First segment is allowed but second is blocked."""
        code, out = run_validator("echo ok && terraform apply")
        assert code == 0
        result = json.loads(out)
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"


class TestEdgeCases:
    def test_empty_command(self):
        code, out = run_validator("")
        assert code == 0
        assert out.strip() == ""

    def test_empty_json(self):
        """Empty stdin should exit cleanly."""
        result = subprocess.run(
            [sys.executable, SCRIPT],
            input="",
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    def test_invalid_json(self):
        """Malformed JSON should exit cleanly."""
        result = subprocess.run(
            [sys.executable, SCRIPT],
            input="not json",
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    def test_invalid_hook_event(self):
        """Unsupported hook_event_name should fail fast with exit 1."""
        payload = json.dumps(
            {
                "tool_input": {"command": "ls"},
                "hook_event_name": "UnknownHook",
            }
        )
        result = subprocess.run(
            [sys.executable, SCRIPT],
            input=payload,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "Unsupported hook_event_name" in result.stderr

    def test_env_var_prefix(self):
        """Env vars before a dangerous command should still block."""
        code, out = run_validator("AWS_PROFILE=prod aws ec2 run-instances")
        assert code == 0
        result = json.loads(out)
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_full_path_binary(self):
        """/usr/local/bin/terraform apply should be blocked."""
        code, out = run_validator("/usr/local/bin/terraform apply")
        assert code == 0
        result = json.loads(out)
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"


class TestShellWrappers:
    def test_bash_c_blocking(self):
        code, out = run_validator('bash -c "terraform apply"')
        assert code == 0
        result = json.loads(out)
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_sudo_bash_c_blocking(self):
        code, out = run_validator('sudo bash -c "kubectl delete pods --all"')
        assert code == 0
        result = json.loads(out)
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_deeply_wrapped_bypass(self):
        # sudo -> bash -c -> $(dangerous)
        code, out = run_validator('sudo bash -c "echo $(terraform destroy)"')
        assert code == 0
        result = json.loads(out)
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_xargs_blocking(self):
        """xargs terraform apply should be blocked."""
        code, out = run_validator("echo id | xargs terraform apply")
        assert code == 0
        result = json.loads(out)
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"


def run_validator_gemini(command: str) -> tuple[int, str]:
    """Simulate a Gemini request by including "hook_event_name": "BeforeTool"."""
    payload = json.dumps(
        {
            "tool_input": {"command": command},
            "hook_event_name": "BeforeTool",
        }
    )
    result = subprocess.run(
        [sys.executable, SCRIPT],
        input=payload,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout


class TestGeminiCompatibility:
    def test_gemini_block_format(self):
        """Verify that a blocked command returns Gemini-specific JSON format."""
        code, out = run_validator_gemini("terraform apply")
        assert code == 0
        result = json.loads(out)
        assert "decision" in result
        assert "reason" in result
        assert "systemMessage" in result
        assert result["decision"] == "deny"

    def test_gemini_allow_format(self):
        """Verify that an allowed command exits with 0 and no output for Gemini."""
        code, out = run_validator_gemini("terraform plan")
        assert code == 0
        assert out.strip() == ""
