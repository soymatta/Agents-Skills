"""Test fixtures for jobfinder scoring module."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture(scope="module")
def score_match_module():
    """Load score_match.py as a module for unit tests.

    The module replaces sys.stdout/sys.stderr on win32 at import time,
    which breaks pytest capture. We neutralize the platform check during import.
    """
    saved_stdout = sys.stdout
    saved_stderr = sys.stderr
    try:
        with patch.object(sys, "platform", "linux"):
            spec = importlib.util.spec_from_file_location(
                "score_match",
                Path(__file__).resolve().parents[1] / "scripts" / "score_match.py",
            )
            if spec is None or spec.loader is None:
                raise RuntimeError("Failed to load score_match.py")
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            return module
    finally:
        sys.stdout = saved_stdout
        sys.stderr = saved_stderr


@pytest.fixture(scope="module")
def parse_cv_module():
    """Load parse_cv.py as a module for unit tests."""
    spec = importlib.util.spec_from_file_location(
        "parse_cv",
        Path(__file__).resolve().parents[1] / "scripts" / "parse_cv.py",
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load parse_cv.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
