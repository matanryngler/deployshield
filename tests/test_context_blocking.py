"""Tests for context-aware conditional blocking."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = str(
    Path(__file__).resolve().parent.parent
    / "hooks"
    / "scripts"
    / "validate-cloud-command.py"
)


@pytest.fixture(autouse=True)
def reset_config_cache(v):
    """Reset config cache between tests."""
    v._config_cache = None
    yield
    v._config_cache = None


# ──────────────────────────────────────────────────────────────────
# Config loading
# ──────────────────────────────────────────────────────────────────


class TestLoadConfig:
    def test_no_config_returns_none(self, v, monkeypatch, tmp_path):
        monkeypatch.delenv("DEPLOYSHIELD_CONFIG", raising=False)
        monkeypatch.chdir(tmp_path)
        # Ensure no ~/.deployshield.json
        monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
        assert v.load_config() is None

    def test_env_var_override(self, v, monkeypatch, tmp_path):
        config = {"kubectl": ["prod"]}
        config_file = tmp_path / "custom.json"
        config_file.write_text(json.dumps(config))
        monkeypatch.setenv("DEPLOYSHIELD_CONFIG", str(config_file))
        assert v.load_config() == config

    def test_cwd_config(self, v, monkeypatch, tmp_path):
        config = {"aws": ["production"]}
        (tmp_path / ".deployshield.json").write_text(json.dumps(config))
        monkeypatch.delenv("DEPLOYSHIELD_CONFIG", raising=False)
        monkeypatch.chdir(tmp_path)
        assert v.load_config() == config

    def test_home_config(self, v, monkeypatch, tmp_path):
        config = {"terraform": ["default"]}
        home = tmp_path / "home"
        home.mkdir()
        (home / ".deployshield.json").write_text(json.dumps(config))
        monkeypatch.delenv("DEPLOYSHIELD_CONFIG", raising=False)
        monkeypatch.chdir(tmp_path)  # No .deployshield.json in CWD
        monkeypatch.setenv("HOME", str(home))
        assert v.load_config() == config

    def test_env_var_takes_priority_over_cwd(self, v, monkeypatch, tmp_path):
        env_config = {"kubectl": ["staging"]}
        cwd_config = {"kubectl": ["prod"]}
        env_file = tmp_path / "env.json"
        env_file.write_text(json.dumps(env_config))
        (tmp_path / ".deployshield.json").write_text(json.dumps(cwd_config))
        monkeypatch.setenv("DEPLOYSHIELD_CONFIG", str(env_file))
        monkeypatch.chdir(tmp_path)
        assert v.load_config() == env_config

    def test_invalid_json_returns_none(self, v, monkeypatch, tmp_path):
        (tmp_path / ".deployshield.json").write_text("not json{{{")
        monkeypatch.delenv("DEPLOYSHIELD_CONFIG", raising=False)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
        assert v.load_config() is None

    def test_non_dict_json_returns_none(self, v, monkeypatch, tmp_path):
        (tmp_path / ".deployshield.json").write_text('["a list"]')
        monkeypatch.delenv("DEPLOYSHIELD_CONFIG", raising=False)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
        assert v.load_config() is None

    def test_config_is_cached(self, v, monkeypatch, tmp_path):
        config = {"kubectl": ["prod"]}
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))
        monkeypatch.setenv("DEPLOYSHIELD_CONFIG", str(config_file))
        result1 = v.load_config()
        # Delete the file — cached value should still be returned
        config_file.unlink()
        result2 = v.load_config()
        assert result1 == result2 == config

    def test_empty_dict_is_valid_config(self, v, monkeypatch, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text("{}")
        monkeypatch.setenv("DEPLOYSHIELD_CONFIG", str(config_file))
        assert v.load_config() == {}


# ──────────────────────────────────────────────────────────────────
# Flag extraction
# ──────────────────────────────────────────────────────────────────


class TestExtractFlagValue:
    def test_flag_with_space(self, v):
        assert (
            v.extract_flag_value(["--context", "prod", "get", "pods"], "--context")
            == "prod"
        )

    def test_flag_with_equals(self, v):
        assert (
            v.extract_flag_value(["--context=prod", "get", "pods"], "--context")
            == "prod"
        )

    def test_missing_flag(self, v):
        assert v.extract_flag_value(["get", "pods"], "--context") is None

    def test_flag_at_end_no_value(self, v):
        assert v.extract_flag_value(["get", "--context"], "--context") is None

    def test_multiple_flag_names(self, v):
        assert v.extract_flag_value(["--stack", "dev"], "--stack", "-s") == "dev"
        assert v.extract_flag_value(["-s", "dev"], "--stack", "-s") == "dev"

    def test_first_match_wins(self, v):
        assert (
            v.extract_flag_value(
                ["--context", "first", "--context", "second"], "--context"
            )
            == "first"
        )

    def test_equals_empty_value(self, v):
        assert v.extract_flag_value(["--context="], "--context") == ""


# ──────────────────────────────────────────────────────────────────
# Env prefix extraction
# ──────────────────────────────────────────────────────────────────


class TestExtractEnvPrefix:
    def test_simple_prefix(self, v):
        assert (
            v.extract_env_prefix("AWS_PROFILE=prod aws s3 ls", "AWS_PROFILE") == "prod"
        )

    def test_no_prefix(self, v):
        assert v.extract_env_prefix("aws s3 ls", "AWS_PROFILE") is None

    def test_wrong_var_name(self, v):
        assert (
            v.extract_env_prefix("AWS_REGION=us-east-1 aws s3 ls", "AWS_PROFILE")
            is None
        )

    def test_multiple_prefixes(self, v):
        assert (
            v.extract_env_prefix(
                "AWS_REGION=us-east-1 AWS_PROFILE=prod aws s3 ls", "AWS_PROFILE"
            )
            == "prod"
        )

    def test_prefix_with_path_value(self, v):
        assert (
            v.extract_env_prefix(
                "KUBECONFIG=/tmp/config kubectl get pods", "KUBECONFIG"
            )
            == "/tmp/config"
        )


# ──────────────────────────────────────────────────────────────────
# Context detection — kubectl / helm
# ──────────────────────────────────────────────────────────────────


class TestDetectKubeContext:
    def test_context_flag(self, v):
        assert (
            v._detect_kube_context(["--context", "prod", "get", "pods"], "--context")
            == "prod"
        )

    def test_context_flag_equals(self, v):
        assert (
            v._detect_kube_context(["--context=prod", "get", "pods"], "--context")
            == "prod"
        )

    def test_kubeconfig_file(self, v, monkeypatch, tmp_path):
        kubeconfig = tmp_path / "config"
        kubeconfig.write_text(
            "apiVersion: v1\nclusters: []\ncurrent-context: my-prod-cluster\nkind: Config\n"
        )
        monkeypatch.setenv("KUBECONFIG", str(kubeconfig))
        assert v._detect_kube_context(["get", "pods"], "--context") == "my-prod-cluster"

    def test_kubeconfig_colon_separated(self, v, monkeypatch, tmp_path):
        first = tmp_path / "config1"
        first.write_text("current-context: first-ctx\n")
        second = tmp_path / "config2"
        second.write_text("current-context: second-ctx\n")
        monkeypatch.setenv("KUBECONFIG", f"{first}{os.pathsep}{second}")
        assert v._detect_kube_context(["get", "pods"], "--context") == "first-ctx"

    def test_kubeconfig_quoted_context(self, v, monkeypatch, tmp_path):
        kubeconfig = tmp_path / "config"
        kubeconfig.write_text('current-context: "my-context"\n')
        monkeypatch.setenv("KUBECONFIG", str(kubeconfig))
        assert v._detect_kube_context(["get", "pods"], "--context") == "my-context"

    def test_no_context_available(self, v, monkeypatch, tmp_path):
        monkeypatch.delenv("KUBECONFIG", raising=False)
        monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
        assert v._detect_kube_context(["get", "pods"], "--context") is None

    def test_helm_kube_context_flag(self, v):
        assert (
            v._detect_kube_context(
                ["--kube-context", "staging", "list"], "--kube-context"
            )
            == "staging"
        )


# ──────────────────────────────────────────────────────────────────
# Context detection — AWS
# ──────────────────────────────────────────────────────────────────


class TestDetectAWSProfile:
    def test_profile_flag(self, v, monkeypatch):
        monkeypatch.delenv("AWS_PROFILE", raising=False)
        assert (
            v._detect_aws_profile("aws ec2 list", ["--profile", "prod", "ec2", "list"])
            == "prod"
        )

    def test_env_prefix(self, v, monkeypatch):
        monkeypatch.delenv("AWS_PROFILE", raising=False)
        assert (
            v._detect_aws_profile("AWS_PROFILE=staging aws ec2 list", ["ec2", "list"])
            == "staging"
        )

    def test_env_var(self, v, monkeypatch):
        monkeypatch.setenv("AWS_PROFILE", "from-env")
        assert v._detect_aws_profile("aws ec2 list", ["ec2", "list"]) == "from-env"

    def test_default(self, v, monkeypatch):
        monkeypatch.delenv("AWS_PROFILE", raising=False)
        assert v._detect_aws_profile("aws ec2 list", ["ec2", "list"]) == "default"

    def test_flag_priority_over_env(self, v, monkeypatch):
        monkeypatch.setenv("AWS_PROFILE", "from-env")
        assert (
            v._detect_aws_profile(
                "aws ec2 list", ["--profile", "from-flag", "ec2", "list"]
            )
            == "from-flag"
        )

    def test_env_prefix_priority_over_env_var(self, v, monkeypatch):
        monkeypatch.setenv("AWS_PROFILE", "from-env")
        assert (
            v._detect_aws_profile(
                "AWS_PROFILE=from-prefix aws ec2 list", ["ec2", "list"]
            )
            == "from-prefix"
        )


# ──────────────────────────────────────────────────────────────────
# Context detection — Terraform
# ──────────────────────────────────────────────────────────────────


class TestDetectTerraformWorkspace:
    def test_env_var(self, v, monkeypatch):
        monkeypatch.setenv("TF_WORKSPACE", "staging")
        assert v._detect_terraform_workspace(["plan"]) == "staging"

    def test_environment_file(self, v, monkeypatch, tmp_path):
        monkeypatch.delenv("TF_WORKSPACE", raising=False)
        monkeypatch.chdir(tmp_path)
        tf_dir = tmp_path / ".terraform"
        tf_dir.mkdir()
        (tf_dir / "environment").write_text("production\n")
        assert v._detect_terraform_workspace(["plan"]) == "production"

    def test_chdir_flag(self, v, monkeypatch, tmp_path):
        monkeypatch.delenv("TF_WORKSPACE", raising=False)
        other_dir = tmp_path / "other"
        other_dir.mkdir()
        tf_dir = other_dir / ".terraform"
        tf_dir.mkdir()
        (tf_dir / "environment").write_text("prod-ws\n")
        assert (
            v._detect_terraform_workspace(["-chdir", str(other_dir), "plan"])
            == "prod-ws"
        )

    def test_chdir_equals(self, v, monkeypatch, tmp_path):
        monkeypatch.delenv("TF_WORKSPACE", raising=False)
        other_dir = tmp_path / "other"
        other_dir.mkdir()
        tf_dir = other_dir / ".terraform"
        tf_dir.mkdir()
        (tf_dir / "environment").write_text("prod-ws\n")
        assert (
            v._detect_terraform_workspace([f"-chdir={other_dir}", "plan"]) == "prod-ws"
        )

    def test_default(self, v, monkeypatch, tmp_path):
        monkeypatch.delenv("TF_WORKSPACE", raising=False)
        monkeypatch.chdir(tmp_path)
        assert v._detect_terraform_workspace(["plan"]) == "default"

    def test_env_var_priority_over_file(self, v, monkeypatch, tmp_path):
        monkeypatch.setenv("TF_WORKSPACE", "from-env")
        monkeypatch.chdir(tmp_path)
        tf_dir = tmp_path / ".terraform"
        tf_dir.mkdir()
        (tf_dir / "environment").write_text("from-file\n")
        assert v._detect_terraform_workspace(["plan"]) == "from-env"


# ──────────────────────────────────────────────────────────────────
# Context detection — GCloud, Azure, Pulumi
# ──────────────────────────────────────────────────────────────────


class TestDetectGCloudProject:
    def test_project_flag(self, v, monkeypatch):
        monkeypatch.delenv("CLOUDSDK_CORE_PROJECT", raising=False)
        assert (
            v._detect_gcloud_project(["--project", "my-prod", "compute", "list"])
            == "my-prod"
        )

    def test_project_flag_equals(self, v):
        assert (
            v._detect_gcloud_project(["--project=my-prod", "compute", "list"])
            == "my-prod"
        )

    def test_env_var(self, v, monkeypatch):
        monkeypatch.setenv("CLOUDSDK_CORE_PROJECT", "env-project")
        assert v._detect_gcloud_project(["compute", "list"]) == "env-project"

    def test_none(self, v, monkeypatch):
        monkeypatch.delenv("CLOUDSDK_CORE_PROJECT", raising=False)
        assert v._detect_gcloud_project(["compute", "list"]) is None


class TestDetectAzSubscription:
    def test_subscription_flag(self, v, monkeypatch):
        monkeypatch.delenv("AZURE_SUBSCRIPTION_ID", raising=False)
        assert (
            v._detect_az_subscription(["--subscription", "prod-sub", "vm", "list"])
            == "prod-sub"
        )

    def test_env_var(self, v, monkeypatch):
        monkeypatch.setenv("AZURE_SUBSCRIPTION_ID", "env-sub")
        assert v._detect_az_subscription(["vm", "list"]) == "env-sub"

    def test_none(self, v, monkeypatch):
        monkeypatch.delenv("AZURE_SUBSCRIPTION_ID", raising=False)
        assert v._detect_az_subscription(["vm", "list"]) is None


class TestDetectPulumiStack:
    def test_stack_flag(self, v):
        assert v._detect_pulumi_stack(["--stack", "prod", "up"]) == "prod"

    def test_short_flag(self, v):
        assert v._detect_pulumi_stack(["-s", "dev", "preview"]) == "dev"

    def test_none(self, v):
        assert v._detect_pulumi_stack(["preview"]) is None


# ──────────────────────────────────────────────────────────────────
# detect_context dispatch
# ──────────────────────────────────────────────────────────────────


class TestDetectContext:
    def test_kubectl(self, v):
        assert (
            v.detect_context(
                "kubectl",
                "kubectl --context=prod get pods",
                ["--context=prod", "get", "pods"],
            )
            == "prod"
        )

    def test_helm(self, v):
        assert (
            v.detect_context(
                "helm",
                "helm --kube-context=staging list",
                ["--kube-context=staging", "list"],
            )
            == "staging"
        )

    def test_aws(self, v, monkeypatch):
        monkeypatch.delenv("AWS_PROFILE", raising=False)
        assert (
            v.detect_context(
                "aws", "aws --profile prod s3 ls", ["--profile", "prod", "s3", "ls"]
            )
            == "prod"
        )

    def test_alias_podman_to_docker(self, v, monkeypatch):
        """podman uses docker's context detector (not in CONTEXT_DETECTORS, falls to None)."""
        # podman maps to docker, but docker has no detector → returns None
        assert v.detect_context("podman", "podman ps", ["ps"]) is None

    def test_unknown_binary(self, v):
        assert (
            v.detect_context("vault", "vault read secret/foo", ["read", "secret/foo"])
            is None
        )


# ──────────────────────────────────────────────────────────────────
# context_is_blocked
# ──────────────────────────────────────────────────────────────────


class TestContextIsBlocked:
    def test_none_context_is_blocked(self, v):
        assert v.context_is_blocked(None, ["prod"]) is True

    def test_exact_match(self, v):
        assert v.context_is_blocked("prod", ["prod", "staging"]) is True

    def test_glob_match(self, v):
        assert v.context_is_blocked("prod-us-east", ["prod-*"]) is True

    def test_no_match(self, v):
        assert v.context_is_blocked("dev", ["prod", "staging"]) is False

    def test_empty_patterns(self, v):
        assert v.context_is_blocked("prod", []) is False

    def test_case_sensitive(self, v):
        assert v.context_is_blocked("Prod", ["prod"]) is False
        assert v.context_is_blocked("prod", ["Prod"]) is False

    def test_wildcard_matches_all(self, v):
        assert v.context_is_blocked("anything", ["*"]) is True

    def test_question_mark_glob(self, v):
        assert v.context_is_blocked("prod1", ["prod?"]) is True
        assert v.context_is_blocked("prod12", ["prod?"]) is False


# ──────────────────────────────────────────────────────────────────
# Integration: check_segment with config + context
# ──────────────────────────────────────────────────────────────────


class TestContextAwareCheckSegment:
    def test_no_config_blocks_as_usual(self, v, monkeypatch, tmp_path):
        """Without config, mutating commands are still blocked."""
        monkeypatch.delenv("DEPLOYSHIELD_CONFIG", raising=False)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
        # check_segment calls sys.exit(0) and writes JSON on deny — test via subprocess
        # Instead, test check_kubectl directly to verify no regression
        assert v.check_kubectl(["apply", "-f", "deploy.yaml"]) is False
        assert v.check_kubectl(["get", "pods"]) is True

    def test_config_with_matching_context_still_blocks_writes(
        self, v, monkeypatch, tmp_path
    ):
        """When context matches a blocked pattern, writes are still blocked."""
        config = {"kubectl": ["prod"]}
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))
        monkeypatch.setenv("DEPLOYSHIELD_CONFIG", str(config_file))
        # kubectl --context=prod apply → context matches "prod" → falls through to safe-list check → blocked
        # We can't easily test check_segment because it calls deny() which calls sys.exit()
        # Instead, test the logic components
        assert v.context_is_blocked("prod", ["prod"]) is True

    def test_config_with_non_matching_context_allows_writes(
        self, v, monkeypatch, tmp_path
    ):
        """When context doesn't match any pattern, ALL commands are allowed."""
        config = {"kubectl": ["prod"]}
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))
        monkeypatch.setenv("DEPLOYSHIELD_CONFIG", str(config_file))
        assert v.context_is_blocked("dev", ["prod"]) is False

    def test_config_empty_list_never_blocks(self, v, monkeypatch, tmp_path):
        """Empty patterns list = disabled for that CLI."""
        config = {"kubectl": []}
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))
        monkeypatch.setenv("DEPLOYSHIELD_CONFIG", str(config_file))
        result = v.load_config()
        assert result == config
        # Empty list → never blocked
        assert result["kubectl"] == []

    def test_provider_not_in_config_blocks_as_usual(self, v, monkeypatch, tmp_path):
        """Provider not in config → normal blocking (current behavior)."""
        config = {"kubectl": ["prod"]}  # Only kubectl configured
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))
        monkeypatch.setenv("DEPLOYSHIELD_CONFIG", str(config_file))
        v.load_config()
        # terraform is NOT in config → should still block writes
        assert v.check_terraform(["apply"]) is False

    def test_safe_command_still_allowed_in_blocked_context(
        self, v, monkeypatch, tmp_path
    ):
        """Even when context matches, read-only commands still pass the safe-list."""
        config = {"kubectl": ["prod"]}
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))
        monkeypatch.setenv("DEPLOYSHIELD_CONFIG", str(config_file))
        # "kubectl get pods" is safe even in prod context
        assert v.check_kubectl(["get", "pods"]) is True


class TestContextAwareIntegration:
    """End-to-end subprocess tests with config."""

    def _run(self, command: str, env_extra: dict | None = None) -> tuple[int, str]:
        env = os.environ.copy()
        if env_extra:
            env.update(env_extra)
        payload = json.dumps({"tool_input": {"command": command}})
        result = subprocess.run(
            [sys.executable, SCRIPT],
            input=payload,
            capture_output=True,
            text=True,
            env=env,
        )
        return result.returncode, result.stdout

    def test_blocked_context_blocks_write(self, tmp_path):
        config = {"kubectl": ["prod"]}
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))
        code, out = self._run(
            "kubectl --context=prod apply -f deploy.yaml",
            {"DEPLOYSHIELD_CONFIG": str(config_file)},
        )
        assert code == 0
        result = json.loads(out)
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_non_blocked_context_allows_write(self, tmp_path):
        config = {"kubectl": ["prod"]}
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))
        code, out = self._run(
            "kubectl --context=dev apply -f deploy.yaml",
            {"DEPLOYSHIELD_CONFIG": str(config_file)},
        )
        assert code == 0
        assert out.strip() == ""

    def test_safe_command_allowed_in_blocked_context(self, tmp_path):
        config = {"kubectl": ["prod"]}
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))
        code, out = self._run(
            "kubectl --context=prod get pods",
            {"DEPLOYSHIELD_CONFIG": str(config_file)},
        )
        assert code == 0
        assert out.strip() == ""

    def test_empty_list_allows_everything(self, tmp_path):
        config = {"kubectl": []}
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))
        code, out = self._run(
            "kubectl apply -f deploy.yaml",
            {"DEPLOYSHIELD_CONFIG": str(config_file)},
        )
        assert code == 0
        assert out.strip() == ""

    def test_unconfigured_provider_still_blocked(self, tmp_path):
        config = {"kubectl": ["prod"]}  # Only kubectl — terraform not listed
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))
        code, out = self._run(
            "terraform apply",
            {"DEPLOYSHIELD_CONFIG": str(config_file)},
        )
        assert code == 0
        result = json.loads(out)
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_no_config_blocks_as_usual(self, tmp_path):
        code, out = self._run(
            "terraform apply",
            {"DEPLOYSHIELD_CONFIG": str(tmp_path / "nonexistent.json")},
        )
        assert code == 0
        result = json.loads(out)
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_glob_pattern_matching(self, tmp_path):
        config = {"kubectl": ["prod-*"]}
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))
        # prod-us matches glob → blocked context
        code, out = self._run(
            "kubectl --context=prod-us apply -f x.yaml",
            {"DEPLOYSHIELD_CONFIG": str(config_file)},
        )
        assert code == 0
        result = json.loads(out)
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

        # dev doesn't match → allowed
        code, out = self._run(
            "kubectl --context=dev apply -f x.yaml",
            {"DEPLOYSHIELD_CONFIG": str(config_file)},
        )
        assert code == 0
        assert out.strip() == ""

    def test_alias_podman_uses_docker_config(self, tmp_path):
        config = {"docker": []}  # Never block docker/podman
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))
        code, out = self._run(
            "podman system prune",
            {"DEPLOYSHIELD_CONFIG": str(config_file)},
        )
        assert code == 0
        assert out.strip() == ""

    def test_alias_sls_uses_serverless_config(self, tmp_path):
        config = {"serverless": []}  # Never block serverless/sls
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))
        code, out = self._run(
            "sls deploy",
            {"DEPLOYSHIELD_CONFIG": str(config_file)},
        )
        assert code == 0
        assert out.strip() == ""

    def test_aws_profile_env_prefix(self, tmp_path):
        config = {"aws": ["production"]}
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))
        # AWS_PROFILE=production in command → matches → blocked
        code, out = self._run(
            "AWS_PROFILE=production aws ec2 run-instances",
            {"DEPLOYSHIELD_CONFIG": str(config_file)},
        )
        assert code == 0
        result = json.loads(out)
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

        # AWS_PROFILE=dev → doesn't match → allowed
        code, out = self._run(
            "AWS_PROFILE=dev aws ec2 run-instances",
            {"DEPLOYSHIELD_CONFIG": str(config_file)},
        )
        assert code == 0
        assert out.strip() == ""

    def test_terraform_workspace_from_env(self, tmp_path):
        config = {"terraform": ["production"]}
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))
        code, out = self._run(
            "terraform apply",
            {"DEPLOYSHIELD_CONFIG": str(config_file), "TF_WORKSPACE": "production"},
        )
        assert code == 0
        result = json.loads(out)
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

        code, out = self._run(
            "terraform apply",
            {"DEPLOYSHIELD_CONFIG": str(config_file), "TF_WORKSPACE": "dev"},
        )
        assert code == 0
        assert out.strip() == ""

    def test_compound_command_with_config(self, tmp_path):
        config = {"kubectl": ["prod"]}
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))
        # First segment allowed (non-blocked context), second still blocked
        code, out = self._run(
            "kubectl --context=dev apply -f x.yaml && kubectl --context=prod apply -f y.yaml",
            {"DEPLOYSHIELD_CONFIG": str(config_file)},
        )
        assert code == 0
        result = json.loads(out)
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_none_context_still_blocks(self, tmp_path):
        """When context can't be detected, default to blocking."""
        config = {"kubectl": ["prod"]}
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))
        # No --context flag and no kubeconfig → context is None → blocked
        code, out = self._run(
            "kubectl apply -f deploy.yaml",
            {
                "DEPLOYSHIELD_CONFIG": str(config_file),
                "HOME": str(tmp_path / "fakehome"),
            },
        )
        assert code == 0
        result = json.loads(out)
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
