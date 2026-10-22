"""Test fixtures for skill-creator scripts."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def quick_validate_module():
    """Load quick_validate.py as a module."""
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "quick_validate.py"
    spec = importlib.util.spec_from_file_location("quick_validate", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load quick_validate.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def aggregate_benchmark_module():
    """Load aggregate_benchmark.py as a module."""
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "aggregate_benchmark.py"
    spec = importlib.util.spec_from_file_location("aggregate_benchmark", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load aggregate_benchmark.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
