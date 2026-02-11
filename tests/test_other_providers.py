"""Tests for Vault, gh, Docker, npm publish, twine, gem, and cargo checkers."""

from __future__ import annotations


class TestVault:
    def test_read_safe(self, v):
        assert v.check_vault(["read", "secret/data/myapp"]) is True

    def test_list_safe(self, v):
        assert v.check_vault(["list", "secret/"]) is True

    def test_status_safe(self, v):
        assert v.check_vault(["status"]) is True

    def test_login_safe(self, v):
        assert v.check_vault(["login"]) is True

    def test_kv_get_safe(self, v):
        assert v.check_vault(["kv", "get", "secret/myapp"]) is True

    def test_kv_list_safe(self, v):
        assert v.check_vault(["kv", "list", "secret/"]) is True

    def test_kv_metadata_safe(self, v):
        assert v.check_vault(["kv", "metadata", "get", "secret/myapp"]) is True

    def test_write_blocked(self, v):
        assert v.check_vault(["write", "secret/data/myapp", "key=val"]) is False

    def test_delete_blocked(self, v):
        assert v.check_vault(["delete", "secret/data/myapp"]) is False

    def test_kv_put_blocked(self, v):
        assert v.check_vault(["kv", "put", "secret/myapp", "key=val"]) is False

    def test_seal_blocked(self, v):
        assert v.check_vault(["seal"]) is False

    def test_token_lookup_safe(self, v):
        assert v.check_vault(["token", "lookup"]) is True

    def test_token_revoke_blocked(self, v):
        assert v.check_vault(["token", "revoke"]) is False

    def test_policy_read_safe(self, v):
        assert v.check_vault(["policy", "read", "default"]) is True

    def test_policy_write_blocked(self, v):
        assert v.check_vault(["policy", "write", "mypolicy", "policy.hcl"]) is False

    def test_secrets_list_safe(self, v):
        assert v.check_vault(["secrets", "list"]) is True

    def test_secrets_enable_blocked(self, v):
        assert v.check_vault(["secrets", "enable", "kv"]) is False

    def test_empty_args_safe(self, v):
        assert v.check_vault([]) is True


class TestGH:
    def test_pr_view_safe(self, v):
        assert v.check_gh(["pr", "view", "123"]) is True

    def test_pr_list_safe(self, v):
        assert v.check_gh(["pr", "list"]) is True

    def test_pr_merge_blocked(self, v):
        assert v.check_gh(["pr", "merge", "123"]) is False

    def test_pr_close_blocked(self, v):
        assert v.check_gh(["pr", "close", "123"]) is False

    def test_issue_view_safe(self, v):
        assert v.check_gh(["issue", "view", "456"]) is True

    def test_issue_list_safe(self, v):
        assert v.check_gh(["issue", "list"]) is True

    def test_issue_close_blocked(self, v):
        assert v.check_gh(["issue", "close", "456"]) is False

    def test_api_get_safe(self, v):
        assert v.check_gh(["api", "repos/owner/repo"]) is True

    def test_api_get_explicit_safe(self, v):
        assert v.check_gh(["api", "-X", "GET", "repos/owner/repo"]) is True

    def test_api_put_blocked(self, v):
        assert v.check_gh(["api", "-X", "PUT", "repos/owner/repo"]) is False

    def test_auth_safe(self, v):
        assert v.check_gh(["auth", "status"]) is True

    def test_repo_view_safe(self, v):
        assert v.check_gh(["repo", "view"]) is True

    def test_repo_clone_safe(self, v):
        assert v.check_gh(["repo", "clone", "owner/repo"]) is True

    def test_repo_delete_blocked(self, v):
        assert v.check_gh(["repo", "delete", "owner/repo"]) is False

    def test_release_create_blocked(self, v):
        assert v.check_gh(["release", "create", "v1.0"]) is False

    def test_search_safe(self, v):
        assert v.check_gh(["search", "repos", "query"]) is True

    def test_empty_args_safe(self, v):
        assert v.check_gh([]) is True


class TestDocker:
    def test_ps_safe(self, v):
        assert v.check_docker(["ps"]) is True

    def test_images_safe(self, v):
        assert v.check_docker(["images"]) is True

    def test_logs_safe(self, v):
        assert v.check_docker(["logs", "my-container"]) is True

    def test_inspect_safe(self, v):
        assert v.check_docker(["inspect", "my-container"]) is True

    def test_info_safe(self, v):
        assert v.check_docker(["info"]) is True

    def test_version_safe(self, v):
        assert v.check_docker(["version"]) is True

    def test_rm_blocked(self, v):
        assert v.check_docker(["rm", "my-container"]) is False

    def test_rmi_blocked(self, v):
        assert v.check_docker(["rmi", "my-image"]) is False

    def test_system_prune_blocked(self, v):
        assert v.check_docker(["system", "prune"]) is False

    def test_system_df_safe(self, v):
        assert v.check_docker(["system", "df"]) is True

    def test_compose_ps_safe(self, v):
        assert v.check_docker(["compose", "ps"]) is True

    def test_compose_logs_safe(self, v):
        assert v.check_docker(["compose", "logs"]) is True

    def test_compose_up_blocked(self, v):
        assert v.check_docker(["compose", "up"]) is False

    def test_container_ls_safe(self, v):
        assert v.check_docker(["container", "ls"]) is True

    def test_container_rm_blocked(self, v):
        assert v.check_docker(["container", "rm", "abc"]) is False

    def test_build_blocked(self, v):
        assert v.check_docker(["build", "."]) is False

    def test_empty_args_safe(self, v):
        assert v.check_docker([]) is True


class TestNpmPublish:
    def test_npm_publish_blocked(self, v):
        assert v.check_npm_publish("npm", ["publish"]) is False

    def test_npm_unpublish_blocked(self, v):
        assert v.check_npm_publish("npm", ["unpublish"]) is False

    def test_npm_test_safe(self, v):
        assert v.check_npm_publish("npm", ["test"]) is True

    def test_npm_install_safe(self, v):
        assert v.check_npm_publish("npm", ["install"]) is True

    def test_yarn_publish_blocked(self, v):
        assert v.check_npm_publish("yarn", ["publish"]) is False

    def test_pnpm_publish_blocked(self, v):
        assert v.check_npm_publish("pnpm", ["publish"]) is False

    def test_not_npm_returns_none(self, v):
        assert v.check_npm_publish("pip", ["install"]) is None

    def test_empty_args_safe(self, v):
        assert v.check_npm_publish("npm", []) is True


class TestTwine:
    def test_upload_blocked(self, v):
        assert v.check_twine(["upload", "dist/*"]) is False

    def test_check_safe(self, v):
        assert v.check_twine(["check", "dist/*"]) is True

    def test_empty_safe(self, v):
        assert v.check_twine([]) is True


class TestGem:
    def test_push_blocked(self, v):
        assert v.check_gem(["push", "mygem-1.0.gem"]) is False

    def test_yank_blocked(self, v):
        assert v.check_gem(["yank", "mygem"]) is False

    def test_list_safe(self, v):
        assert v.check_gem(["list"]) is True

    def test_empty_safe(self, v):
        assert v.check_gem([]) is True


class TestCargo:
    def test_publish_blocked(self, v):
        assert v.check_cargo(["publish"]) is False

    def test_build_safe(self, v):
        assert v.check_cargo(["build"]) is True

    def test_test_safe(self, v):
        assert v.check_cargo(["test"]) is True

    def test_empty_safe(self, v):
        assert v.check_cargo([]) is True
