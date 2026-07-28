"""Test fixtures for osint gen_commands module."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def gen_commands_module():
    """Load gen_commands.py as a module for unit tests."""
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "gen_commands.py"
    spec = importlib.util.spec_from_file_location("gen_commands", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load gen_commands.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
