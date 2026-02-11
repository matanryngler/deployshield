"""Tests for normalize_segment and skip_flags."""

from __future__ import annotations


class TestNormalizeSegment:
    def test_simple_command(self, v):
        binary, args = v.normalize_segment("aws s3 ls")
        assert binary == "aws"
        assert args == ["s3", "ls"]

    def test_env_var_prefix(self, v):
        binary, args = v.normalize_segment("AWS_PROFILE=prod aws s3 ls")
        assert binary == "aws"
        assert args == ["s3", "ls"]

    def test_multiple_env_vars(self, v):
        binary, args = v.normalize_segment("FOO=bar BAZ=qux kubectl get pods")
        assert binary == "kubectl"
        assert args == ["get", "pods"]

    def test_full_path_stripped(self, v):
        binary, args = v.normalize_segment("/usr/local/bin/aws ec2 describe-instances")
        assert binary == "aws"
        assert args == ["ec2", "describe-instances"]

    def test_empty_input(self, v):
        binary, args = v.normalize_segment("")
        assert binary == ""
        assert args == []

    def test_whitespace_input(self, v):
        binary, args = v.normalize_segment("   ")
        assert binary == ""
        assert args == []

    def test_env_var_only(self, v):
        """Only env vars, no actual command."""
        binary, args = v.normalize_segment("FOO=bar")
        assert binary == ""
        assert args == []

    def test_quoted_args(self, v):
        binary, args = v.normalize_segment('psql -c "SELECT * FROM users"')
        assert binary == "psql"
        assert "-c" in args
        assert "SELECT * FROM users" in args

    def test_shlex_fallback_on_malformed_quotes(self, v):
        """Malformed quoting should fall back to naive split."""
        binary, args = v.normalize_segment('echo "unterminated')
        assert binary == "echo"


class TestSkipFlags:
    def test_no_flags(self, v):
        result = v.skip_flags(["get", "pods"], set(), set())
        assert result == ["get", "pods"]

    def test_flags_with_value(self, v):
        result = v.skip_flags(
            ["--namespace", "default", "get", "pods"],
            flags_with_value={"--namespace"},
            flags_no_value=set(),
        )
        assert result == ["get", "pods"]

    def test_flags_no_value(self, v):
        result = v.skip_flags(
            ["--debug", "get", "pods"],
            flags_with_value=set(),
            flags_no_value={"--debug"},
        )
        assert result == ["get", "pods"]

    def test_unknown_flag_skipped(self, v):
        result = v.skip_flags(
            ["--unknown", "get", "pods"],
            flags_with_value=set(),
            flags_no_value=set(),
        )
        assert result == ["get", "pods"]

    def test_empty_args(self, v):
        result = v.skip_flags([], set(), set())
        assert result == []
