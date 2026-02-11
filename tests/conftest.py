"""Shared fixtures for DeployShield tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

# Import the validation script as a module so individual functions can be tested.
_SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "hooks"
    / "scripts"
    / "validate-cloud-command.py"
)
_spec = importlib.util.spec_from_file_location("validator", str(_SCRIPT))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


@pytest.fixture
def v():
    """Expose every function in validate-cloud-command.py."""
    return _mod
