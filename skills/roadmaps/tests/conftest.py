"""Test fixtures for roadmaps validate_roadmap module."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def validate_roadmap_module():
    """Load validate_roadmap.py as a module for unit tests."""
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "validate_roadmap.py"
    spec = importlib.util.spec_from_file_location("validate_roadmap", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load validate_roadmap.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def valid_roadmap(tmp_path):
    """Create a valid roadmap file and return its path."""
    content = """# Roadmap: Test Project

## Metadata
- Owner: Test User
- Status: active

## Steps

### Step 1: Setup
- **Type**: linear
- **Status**: completed

### Step 2: Decision Point
- **Type**: decision
- **Status**: pending
- **Decision**: Should we use React or Vue?
- **If yes**: Use React
- **If no**: Use Vue

### Step 3: Implementation
- **Type**: linear
- **Status**: in_progress
"""
    path = tmp_path / "roadmap.md"
    path.write_text(content, encoding="utf-8")
    return path
