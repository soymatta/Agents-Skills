"""Test fixtures for citation-formatter references module."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def references():
    """Load references.py as a module for unit tests."""
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "references.py"
    spec = importlib.util.spec_from_file_location("references", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load references.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def generate_outputs_module():
    """Load generate_outputs.py as a module for unit tests."""
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "generate_outputs.py"
    spec = importlib.util.spec_from_file_location("generate_outputs", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load generate_outputs.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module