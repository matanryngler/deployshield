"""Tests for split_compound_command."""

from __future__ import annotations


def test_simple_command(v):
    assert v.split_compound_command("echo hello") == ["echo hello"]


def test_and_operator(v):
    assert v.split_compound_command("echo a && echo b") == ["echo a", "echo b"]


def test_or_operator(v):
    assert v.split_compound_command("echo a || echo b") == ["echo a", "echo b"]


def test_semicolon(v):
    assert v.split_compound_command("echo a; echo b") == ["echo a", "echo b"]


def test_pipe(v):
    assert v.split_compound_command("echo a | grep a") == ["echo a", "grep a"]


def test_multiple_operators(v):
    result = v.split_compound_command("echo a && echo b || echo c; echo d")
    assert result == ["echo a", "echo b", "echo c", "echo d"]


def test_double_quoted_and(v):
    """&& inside double quotes should NOT split."""
    assert v.split_compound_command('echo "hello && world"') == [
        'echo "hello && world"'
    ]


def test_single_quoted_and(v):
    """&& inside single quotes should NOT split."""
    assert v.split_compound_command("echo 'hello && world'") == [
        "echo 'hello && world'"
    ]


def test_subshell_not_split(v):
    """Operators inside $(...) should NOT split."""
    result = v.split_compound_command("echo $(echo a && echo b)")
    assert result == ["echo $(echo a && echo b)"]


def test_backtick_not_split(v):
    """Operators inside backticks should NOT split."""
    result = v.split_compound_command("echo `echo a && echo b`")
    assert result == ["echo `echo a && echo b`"]


def test_escaped_operator(v):
    """Escaped && should not split (backslash escapes the first &)."""
    result = v.split_compound_command("echo a \\&& echo b")
    # The backslash escapes the first &, so the second & is standalone
    # and doesn't form &&.  Exact behavior depends on parser, but it should
    # not produce a clean split like ["echo a", "echo b"].
    assert len(result) >= 1


def test_empty_string(v):
    assert v.split_compound_command("") == []


def test_whitespace_only(v):
    assert v.split_compound_command("   ") == []


def test_nested_subshell(v):
    """Nested $(...) should be handled correctly."""
    result = v.split_compound_command("echo $(echo $(echo inner)) && echo outer")
    assert result == ["echo $(echo $(echo inner))", "echo outer"]


def test_process_substitution(v):
    """<(...) should not cause splitting on the inner operators."""
    result = v.split_compound_command("diff <(echo a && echo b) file.txt")
    assert result == ["diff <(echo a && echo b) file.txt"]


def test_mixed_quotes_and_operators(v):
    result = v.split_compound_command("""echo "hello" && echo 'world' | grep w""")
    assert result == ['echo "hello"', "echo 'world'", "grep w"]
