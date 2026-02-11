"""Tests for Terraform, Pulumi, CDK, SAM, Serverless, and Ansible checkers."""

from __future__ import annotations


class TestTerraform:
    def test_plan_safe(self, v):
        assert v.check_terraform(["plan"]) is True

    def test_show_safe(self, v):
        assert v.check_terraform(["show"]) is True

    def test_output_safe(self, v):
        assert v.check_terraform(["output"]) is True

    def test_validate_safe(self, v):
        assert v.check_terraform(["validate"]) is True

    def test_fmt_safe(self, v):
        assert v.check_terraform(["fmt"]) is True

    def test_init_safe(self, v):
        assert v.check_terraform(["init"]) is True

    def test_version_safe(self, v):
        assert v.check_terraform(["version"]) is True

    def test_state_list_safe(self, v):
        assert v.check_terraform(["state", "list"]) is True

    def test_state_show_safe(self, v):
        assert v.check_terraform(["state", "show", "aws_instance.example"]) is True

    def test_state_pull_safe(self, v):
        assert v.check_terraform(["state", "pull"]) is True

    def test_workspace_list_safe(self, v):
        assert v.check_terraform(["workspace", "list"]) is True

    def test_workspace_show_safe(self, v):
        assert v.check_terraform(["workspace", "show"]) is True

    def test_apply_blocked(self, v):
        assert v.check_terraform(["apply"]) is False

    def test_destroy_blocked(self, v):
        assert v.check_terraform(["destroy"]) is False

    def test_import_blocked(self, v):
        assert v.check_terraform(["import", "aws_instance.foo", "i-12345"]) is False

    def test_state_rm_blocked(self, v):
        assert v.check_terraform(["state", "rm", "aws_instance.foo"]) is False

    def test_workspace_new_blocked(self, v):
        assert v.check_terraform(["workspace", "new", "staging"]) is False

    def test_chdir_flag_skipped(self, v):
        assert v.check_terraform(["-chdir=/infra", "plan"]) is True

    def test_empty_args_safe(self, v):
        assert v.check_terraform([]) is True


class TestPulumi:
    def test_preview_safe(self, v):
        assert v.check_pulumi(["preview"]) is True

    def test_whoami_safe(self, v):
        assert v.check_pulumi(["whoami"]) is True

    def test_version_safe(self, v):
        assert v.check_pulumi(["version"]) is True

    def test_stack_ls_safe(self, v):
        assert v.check_pulumi(["stack", "ls"]) is True

    def test_stack_select_safe(self, v):
        assert v.check_pulumi(["stack", "select", "dev"]) is True

    def test_config_get_safe(self, v):
        assert v.check_pulumi(["config", "get", "aws:region"]) is True

    def test_up_blocked(self, v):
        assert v.check_pulumi(["up"]) is False

    def test_destroy_blocked(self, v):
        assert v.check_pulumi(["destroy"]) is False

    def test_empty_args_safe(self, v):
        assert v.check_pulumi([]) is True


class TestCDK:
    def test_diff_safe(self, v):
        assert v.check_cdk(["diff"]) is True

    def test_synth_safe(self, v):
        assert v.check_cdk(["synth"]) is True

    def test_synthesize_safe(self, v):
        assert v.check_cdk(["synthesize"]) is True

    def test_list_safe(self, v):
        assert v.check_cdk(["list"]) is True

    def test_ls_safe(self, v):
        assert v.check_cdk(["ls"]) is True

    def test_doctor_safe(self, v):
        assert v.check_cdk(["doctor"]) is True

    def test_deploy_blocked(self, v):
        assert v.check_cdk(["deploy"]) is False

    def test_destroy_blocked(self, v):
        assert v.check_cdk(["destroy"]) is False

    def test_bootstrap_blocked(self, v):
        assert v.check_cdk(["bootstrap"]) is False

    def test_empty_args_safe(self, v):
        assert v.check_cdk([]) is True


class TestSAM:
    def test_validate_safe(self, v):
        assert v.check_sam(["validate"]) is True

    def test_build_safe(self, v):
        assert v.check_sam(["build"]) is True

    def test_local_safe(self, v):
        assert v.check_sam(["local", "invoke"]) is True

    def test_logs_safe(self, v):
        assert v.check_sam(["logs"]) is True

    def test_deploy_blocked(self, v):
        assert v.check_sam(["deploy"]) is False

    def test_delete_blocked(self, v):
        assert v.check_sam(["delete"]) is False

    def test_empty_args_safe(self, v):
        assert v.check_sam([]) is True


class TestServerless:
    def test_info_safe(self, v):
        assert v.check_serverless(["info"]) is True

    def test_print_safe(self, v):
        assert v.check_serverless(["print"]) is True

    def test_package_safe(self, v):
        assert v.check_serverless(["package"]) is True

    def test_invoke_local_safe(self, v):
        assert v.check_serverless(["invoke", "local", "-f", "myFunc"]) is True

    def test_invoke_remote_blocked(self, v):
        assert v.check_serverless(["invoke", "-f", "myFunc"]) is False

    def test_deploy_blocked(self, v):
        assert v.check_serverless(["deploy"]) is False

    def test_remove_blocked(self, v):
        assert v.check_serverless(["remove"]) is False

    def test_empty_args_safe(self, v):
        assert v.check_serverless([]) is True


class TestAnsiblePlaybook:
    def test_check_mode_safe(self, v):
        assert v.check_ansible_playbook(["site.yml", "--check"]) is True

    def test_short_check_safe(self, v):
        assert v.check_ansible_playbook(["site.yml", "-C"]) is True

    def test_syntax_check_safe(self, v):
        assert v.check_ansible_playbook(["site.yml", "--syntax-check"]) is True

    def test_list_hosts_safe(self, v):
        assert v.check_ansible_playbook(["site.yml", "--list-hosts"]) is True

    def test_list_tasks_safe(self, v):
        assert v.check_ansible_playbook(["site.yml", "--list-tasks"]) is True

    def test_list_tags_safe(self, v):
        assert v.check_ansible_playbook(["site.yml", "--list-tags"]) is True

    def test_plain_run_blocked(self, v):
        assert v.check_ansible_playbook(["site.yml"]) is False

    def test_empty_args_safe(self, v):
        assert v.check_ansible_playbook([]) is True
