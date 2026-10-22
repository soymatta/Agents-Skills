"""Test fixtures for content-humanizer detect_ai module."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def detect_ai_module():
    """Load detect_ai.py as a module for unit tests."""
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "detect_ai.py"
    spec = importlib.util.spec_from_file_location("detect_ai", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load detect_ai.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
