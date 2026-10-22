"""Tests for roadmaps validate_roadmap module."""

from __future__ import annotations

import pytest


class TestValidateRoadmapValid:
    def test_valid_roadmap_no_errors(self, validate_roadmap_module, valid_roadmap):
        errors = validate_roadmap_module.validate_roadmap(str(valid_roadmap))
        assert errors == []

    def test_valid_roadmap_returns_list(self, validate_roadmap_module, valid_roadmap):
        errors = validate_roadmap_module.validate_roadmap(str(valid_roadmap))
        assert isinstance(errors, list)


class TestValidateRoadmapMissingHeader:
    def test_missing_roadmap_header(self, validate_roadmap_module, tmp_path):
        content = """## Metadata
- Owner: Test

## Steps

### Step 1: Setup
- **Type**: linear
- **Status**: completed
"""
        path = tmp_path / "bad.md"
        path.write_text(content, encoding="utf-8")
        errors = validate_roadmap_module.validate_roadmap(str(path))
        assert any("Roadmap:" in e for e in errors)


class TestValidateRoadmapMissingMetadata:
    def test_missing_metadata_section(self, validate_roadmap_module, tmp_path):
        content = """# Roadmap: My Project

## Steps

### Step 1: Setup
- **Type**: linear
- **Status**: completed
"""
        path = tmp_path / "no_meta.md"
        path.write_text(content, encoding="utf-8")
        errors = validate_roadmap_module.validate_roadmap(str(path))
        assert any("Metadata" in e for e in errors)


class TestValidateRoadmapMissingSteps:
    def test_missing_steps_section(self, validate_roadmap_module, tmp_path):
        content = """# Roadmap: My Project

## Metadata
- Owner: Test
"""
        path = tmp_path / "no_steps.md"
        path.write_text(content, encoding="utf-8")
        errors = validate_roadmap_module.validate_roadmap(str(path))
        assert any("Steps" in e for e in errors)


class TestValidateRoadmapStepNumbering:
    def test_no_steps_found(self, validate_roadmap_module, tmp_path):
        content = """# Roadmap: My Project

## Metadata
- Owner: Test

## Steps

Some text without proper step headers.
"""
        path = tmp_path / "no_step_headers.md"
        path.write_text(content, encoding="utf-8")
        errors = validate_roadmap_module.validate_roadmap(str(path))
        assert any("No steps found" in e for e in errors)

    def test_step_numbering_gap(self, validate_roadmap_module, tmp_path):
        content = """# Roadmap: My Project

## Metadata
- Owner: Test

## Steps

### Step 1: Setup
- **Type**: linear
- **Status**: completed

### Step 3: Deploy
- **Type**: linear
- **Status**: pending
"""
        path = tmp_path / "gap.md"
        path.write_text(content, encoding="utf-8")
        errors = validate_roadmap_module.validate_roadmap(str(path))
        assert any("Step numbering gap" in e and "2" in e for e in errors)

    def test_wrong_first_step_number(self, validate_roadmap_module, tmp_path):
        content = """# Roadmap: My Project

## Metadata
- Owner: Test

## Steps

### Step 2: Setup
- **Type**: linear
- **Status**: completed
"""
        path = tmp_path / "wrong_start.md"
        path.write_text(content, encoding="utf-8")
        errors = validate_roadmap_module.validate_roadmap(str(path))
        assert any("Step numbering gap" in e for e in errors)


class TestValidateRoadmapStepFields:
    def test_missing_type_field(self, validate_roadmap_module, tmp_path):
        content = """# Roadmap: My Project

## Metadata
- Owner: Test

## Steps

### Step 1: Setup
- **Status**: completed
"""
        path = tmp_path / "no_type.md"
        path.write_text(content, encoding="utf-8")
        errors = validate_roadmap_module.validate_roadmap(str(path))
        assert any("missing '- **Type**:'" in e for e in errors)

    def test_missing_status_field(self, validate_roadmap_module, tmp_path):
        content = """# Roadmap: My Project

## Metadata
- Owner: Test

## Steps

### Step 1: Setup
- **Type**: linear
"""
        path = tmp_path / "no_status.md"
        path.write_text(content, encoding="utf-8")
        errors = validate_roadmap_module.validate_roadmap(str(path))
        assert any("missing '- **Status**:'" in e for e in errors)


class TestValidateRoadmapInvalidType:
    def test_invalid_step_type(self, validate_roadmap_module, tmp_path):
        content = """# Roadmap: My Project

## Metadata
- Owner: Test

## Steps

### Step 1: Setup
- **Type**: invalid_type
- **Status**: completed
"""
        path = tmp_path / "bad_type.md"
        path.write_text(content, encoding="utf-8")
        errors = validate_roadmap_module.validate_roadmap(str(path))
        assert any("invalid type" in e for e in errors)

    @pytest.mark.parametrize("valid_type", ["linear", "decision", "loop", "parallel", "milestone"])
    def test_valid_step_types_accepted(self, validate_roadmap_module, tmp_path, valid_type):
        decision_extra = ""
        if valid_type == "decision":
            decision_extra = "\n- **Decision**: Do it?\n- **If yes**: Go\n- **If no**: Stop"
        if valid_type == "loop":
            decision_extra = "\n- **Loop condition**: while true\n- **Loop back to**: Step 1"
        content = f"""# Roadmap: My Project

## Metadata
- Owner: Test

## Steps

### Step 1: Thing
- **Type**: {valid_type}
- **Status**: pending{decision_extra}
"""
        path = tmp_path / f"type_{valid_type}.md"
        path.write_text(content, encoding="utf-8")
        errors = validate_roadmap_module.validate_roadmap(str(path))
        assert not any("invalid type" in e for e in errors)


class TestValidateRoadmapInvalidStatus:
    def test_invalid_step_status(self, validate_roadmap_module, tmp_path):
        content = """# Roadmap: My Project

## Metadata
- Owner: Test

## Steps

### Step 1: Setup
- **Type**: linear
- **Status**: banana
"""
        path = tmp_path / "bad_status.md"
        path.write_text(content, encoding="utf-8")
        errors = validate_roadmap_module.validate_roadmap(str(path))
        assert any("invalid status" in e for e in errors)

    @pytest.mark.parametrize("valid_status", ["pending", "in_progress", "completed", "skipped", "blocked"])
    def test_valid_statuses_accepted(self, validate_roadmap_module, tmp_path, valid_status):
        content = f"""# Roadmap: My Project

## Metadata
- Owner: Test

## Steps

### Step 1: Setup
- **Type**: linear
- **Status**: {valid_status}
"""
        path = tmp_path / f"status_{valid_status}.md"
        path.write_text(content, encoding="utf-8")
        errors = validate_roadmap_module.validate_roadmap(str(path))
        assert not any("invalid status" in e for e in errors)


class TestValidateRoadmapDecisionStep:
    def test_decision_missing_decision_field(self, validate_roadmap_module, tmp_path):
        content = """# Roadmap: My Project

## Metadata
- Owner: Test

## Steps

### Step 1: Decision
- **Type**: decision
- **Status**: pending
- **If yes**: Go
- **If no**: Stop
"""
        path = tmp_path / "no_decision.md"
        path.write_text(content, encoding="utf-8")
        errors = validate_roadmap_module.validate_roadmap(str(path))
        assert any("missing '- **Decision**:'" in e for e in errors)

    def test_decision_missing_if_yes(self, validate_roadmap_module, tmp_path):
        content = """# Roadmap: My Project

## Metadata
- Owner: Test

## Steps

### Step 1: Decision
- **Type**: decision
- **Status**: pending
- **Decision**: Should we?
- **If no**: Stop
"""
        path = tmp_path / "no_yes.md"
        path.write_text(content, encoding="utf-8")
        errors = validate_roadmap_module.validate_roadmap(str(path))
        assert any("missing '- **If yes**:'" in e for e in errors)

    def test_decision_missing_if_no(self, validate_roadmap_module, tmp_path):
        content = """# Roadmap: My Project

## Metadata
- Owner: Test

## Steps

### Step 1: Decision
- **Type**: decision
- **Status**: pending
- **Decision**: Should we?
- **If yes**: Go
"""
        path = tmp_path / "no_no.md"
        path.write_text(content, encoding="utf-8")
        errors = validate_roadmap_module.validate_roadmap(str(path))
        assert any("missing '- **If no**:'" in e for e in errors)


class TestValidateRoadmapLoopStep:
    def test_loop_missing_condition(self, validate_roadmap_module, tmp_path):
        content = """# Roadmap: My Project

## Metadata
- Owner: Test

## Steps

### Step 1: Loop
- **Type**: loop
- **Status**: pending
- **Loop back to**: Step 1
"""
        path = tmp_path / "no_loop_cond.md"
        path.write_text(content, encoding="utf-8")
        errors = validate_roadmap_module.validate_roadmap(str(path))
        assert any("missing '- **Loop condition**:'" in e for e in errors)

    def test_loop_missing_loop_back(self, validate_roadmap_module, tmp_path):
        content = """# Roadmap: My Project

## Metadata
- Owner: Test

## Steps

### Step 1: Loop
- **Type**: loop
- **Status**: pending
- **Loop condition**: while not done
"""
        path = tmp_path / "no_loop_back.md"
        path.write_text(content, encoding="utf-8")
        errors = validate_roadmap_module.validate_roadmap(str(path))
        assert any("missing '- **Loop back to**:'" in e for e in errors)


class TestValidateRoadmapMultipleErrors:
    def test_accumulates_all_errors(self, validate_roadmap_module, tmp_path):
        content = """Some random text without proper headers.
"""
        path = tmp_path / "multi_err.md"
        path.write_text(content, encoding="utf-8")
        errors = validate_roadmap_module.validate_roadmap(str(path))
        assert len(errors) >= 2


class TestValidateRoadmapEmptyFile:
    def test_empty_file(self, validate_roadmap_module, tmp_path):
        path = tmp_path / "empty.md"
        path.write_text("", encoding="utf-8")
        errors = validate_roadmap_module.validate_roadmap(str(path))
        assert len(errors) >= 2


class TestValidateRoadmapSubSteps:
    def test_substep_numbering_detected_as_gap(self, validate_roadmap_module, tmp_path):
        content = """# Roadmap: My Project

## Metadata
- Owner: Test

## Steps

### Step 1.1: Substep
- **Type**: linear
- **Status**: completed
"""
        path = tmp_path / "substep.md"
        path.write_text(content, encoding="utf-8")
        errors = validate_roadmap_module.validate_roadmap(str(path))
        assert any("Step numbering gap" in e and "1.1" in e for e in errors)

    def test_substep_after_main_step(self, validate_roadmap_module, tmp_path):
        content = """# Roadmap: My Project

## Metadata
- Owner: Test

## Steps

### Step 1: Main Step
- **Type**: linear
- **Status**: completed

### Step 1.1: Substep
- **Type**: linear
- **Status**: completed
"""
        path = tmp_path / "substep_after.md"
        path.write_text(content, encoding="utf-8")
        errors = validate_roadmap_module.validate_roadmap(str(path))
        assert any("Step numbering gap" in e and "2" in e for e in errors)
