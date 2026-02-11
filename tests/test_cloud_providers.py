"""Tests for AWS, GCP, Azure, kubectl, and helm checkers."""

from __future__ import annotations


class TestAWS:
    def test_describe_safe(self, v):
        assert v.check_aws(["ec2", "describe-instances"]) is True

    def test_get_safe(self, v):
        assert v.check_aws(["s3api", "get-object"]) is True

    def test_list_safe(self, v):
        assert v.check_aws(["ec2", "list-snapshots"]) is True

    def test_help_safe(self, v):
        assert v.check_aws(["help"]) is True

    def test_service_help_safe(self, v):
        assert v.check_aws(["ec2", "help"]) is True

    def test_s3_ls_safe(self, v):
        assert v.check_aws(["s3", "ls"]) is True

    def test_s3_cp_download_safe(self, v):
        assert v.check_aws(["s3", "cp", "s3://bucket/key", "/tmp/local"]) is True

    def test_s3_cp_upload_blocked(self, v):
        assert v.check_aws(["s3", "cp", "/tmp/local", "s3://bucket/key"]) is False

    def test_s3_rm_blocked(self, v):
        assert v.check_aws(["s3", "rm", "s3://bucket/key"]) is False

    def test_run_instances_blocked(self, v):
        assert v.check_aws(["ec2", "run-instances"]) is False

    def test_sts_get_safe(self, v):
        assert v.check_aws(["sts", "get-caller-identity"]) is True

    def test_configure_list_safe(self, v):
        assert v.check_aws(["configure", "list"]) is True

    def test_sso_login_safe(self, v):
        assert v.check_aws(["sso", "login"]) is True

    def test_empty_args_safe(self, v):
        assert v.check_aws([]) is True

    def test_profile_flag_skipped(self, v):
        assert v.check_aws(["--profile", "prod", "ec2", "describe-instances"]) is True

    def test_wait_safe(self, v):
        assert v.check_aws(["ec2", "wait", "instance-running"]) is True

    def test_terminate_blocked(self, v):
        assert v.check_aws(["ec2", "terminate-instances"]) is False


class TestGCloud:
    def test_describe_safe(self, v):
        assert v.check_gcloud(["compute", "instances", "describe", "my-vm"]) is True

    def test_list_safe(self, v):
        assert v.check_gcloud(["compute", "instances", "list"]) is True

    def test_config_list_safe(self, v):
        assert v.check_gcloud(["config", "list"]) is True

    def test_auth_list_safe(self, v):
        assert v.check_gcloud(["auth", "list"]) is True

    def test_auth_print_safe(self, v):
        assert v.check_gcloud(["auth", "print-access-token"]) is True

    def test_create_blocked(self, v):
        assert v.check_gcloud(["compute", "instances", "create", "my-vm"]) is False

    def test_delete_blocked(self, v):
        assert v.check_gcloud(["compute", "instances", "delete", "my-vm"]) is False

    def test_empty_args_safe(self, v):
        assert v.check_gcloud([]) is True


class TestAzure:
    def test_show_safe(self, v):
        assert v.check_az(["vm", "show", "--name", "my-vm"]) is True

    def test_list_safe(self, v):
        assert v.check_az(["vm", "list"]) is True

    def test_account_show_safe(self, v):
        assert v.check_az(["account", "show"]) is True

    def test_account_list_safe(self, v):
        assert v.check_az(["account", "list"]) is True

    def test_create_blocked(self, v):
        assert v.check_az(["vm", "create"]) is False

    def test_delete_blocked(self, v):
        assert v.check_az(["vm", "delete"]) is False

    def test_empty_args_safe(self, v):
        assert v.check_az([]) is True


class TestKubectl:
    def test_get_safe(self, v):
        assert v.check_kubectl(["get", "pods"]) is True

    def test_describe_safe(self, v):
        assert v.check_kubectl(["describe", "pod", "my-pod"]) is True

    def test_logs_safe(self, v):
        assert v.check_kubectl(["logs", "my-pod"]) is True

    def test_apply_blocked(self, v):
        assert v.check_kubectl(["apply", "-f", "deploy.yaml"]) is False

    def test_delete_blocked(self, v):
        assert v.check_kubectl(["delete", "pod", "my-pod"]) is False

    def test_dry_run_client_safe(self, v):
        assert (
            v.check_kubectl(["apply", "-f", "deploy.yaml", "--dry-run=client"]) is True
        )

    def test_dry_run_server_safe(self, v):
        assert (
            v.check_kubectl(["apply", "-f", "deploy.yaml", "--dry-run=server"]) is True
        )

    def test_dry_run_none_blocked(self, v):
        """--dry-run=none is NOT safe, it actually applies."""
        assert (
            v.check_kubectl(["apply", "-f", "deploy.yaml", "--dry-run=none"]) is False
        )

    def test_config_view_safe(self, v):
        assert v.check_kubectl(["config", "view"]) is True

    def test_config_current_context_safe(self, v):
        assert v.check_kubectl(["config", "current-context"]) is True

    def test_config_get_contexts_safe(self, v):
        assert v.check_kubectl(["config", "get-contexts"]) is True

    def test_auth_can_i_safe(self, v):
        assert v.check_kubectl(["auth", "can-i", "get", "pods"]) is True

    def test_diff_safe(self, v):
        assert v.check_kubectl(["diff", "-f", "deploy.yaml"]) is True

    def test_top_safe(self, v):
        assert v.check_kubectl(["top", "nodes"]) is True

    def test_namespace_flag_skipped(self, v):
        assert v.check_kubectl(["-n", "default", "get", "pods"]) is True

    def test_scale_blocked(self, v):
        assert v.check_kubectl(["scale", "--replicas=3", "deployment/app"]) is False

    def test_empty_args_safe(self, v):
        assert v.check_kubectl([]) is True


class TestHelm:
    def test_list_safe(self, v):
        assert v.check_helm(["list"]) is True

    def test_ls_safe(self, v):
        assert v.check_helm(["ls"]) is True

    def test_get_safe(self, v):
        assert v.check_helm(["get", "values", "my-release"]) is True

    def test_show_safe(self, v):
        assert v.check_helm(["show", "chart", "my-chart"]) is True

    def test_status_safe(self, v):
        assert v.check_helm(["status", "my-release"]) is True

    def test_template_safe(self, v):
        assert v.check_helm(["template", "my-release", "my-chart"]) is True

    def test_install_blocked(self, v):
        assert v.check_helm(["install", "my-release", "my-chart"]) is False

    def test_upgrade_blocked(self, v):
        assert v.check_helm(["upgrade", "my-release", "my-chart"]) is False

    def test_uninstall_blocked(self, v):
        assert v.check_helm(["uninstall", "my-release"]) is False

    def test_dry_run_safe(self, v):
        assert v.check_helm(["install", "my-release", "my-chart", "--dry-run"]) is True

    def test_repo_list_safe(self, v):
        assert v.check_helm(["repo", "list"]) is True

    def test_repo_add_blocked(self, v):
        assert v.check_helm(["repo", "add", "stable", "https://example.com"]) is False

    def test_empty_args_safe(self, v):
        assert v.check_helm([]) is True
