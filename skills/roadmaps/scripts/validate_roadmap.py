import re
import sys
from pathlib import Path


def validate_roadmap(filepath):
    content = Path(filepath).read_text(encoding="utf-8")
    errors = []
    warnings = []

    if not content.startswith("# Roadmap:"):
        errors.append("Must start with '# Roadmap: <Project Name>'")

    if "## Metadata" not in content:
        errors.append("Missing ## Metadata section")

    if "## Steps" not in content:
        errors.append("Missing ## Steps section")
        return errors

    # Steps moved to "## Completed" are archived and intentionally no longer
    # sequentially numbered; exclude that section from numbering/field checks
    # so the skill's "move completed prefix steps" flow validates cleanly.
    active_content = content.split("## Completed", 1)[0]

    step_pattern = r"### Step (\d+(?:\.\d+)?):"
    step_nums = re.findall(step_pattern, active_content)
    if not step_nums:
        errors.append("No steps found (must use '### Step N: <name>' format)")
    else:
        for i, num in enumerate(step_nums):
            expected = i + 1
            if float(num) != expected:
                errors.append(f"Step numbering gap: expected {expected}, found {num}")

    step_blocks = re.split(r"### Step \d+(?:\.\d+)?:", active_content)[1:]
    for i, block in enumerate(step_blocks):
        if "- **Type**:" not in block:
            errors.append(f"Step {i+1}: missing '- **Type**:' field")
        if "- **Status**:" not in block:
            errors.append(f"Step {i+1}: missing '- **Status**:' field")

        step_type = re.search(r"- \*\*Type\*\*:\s*(\w+)", block)
        if step_type and step_type.group(1) not in ("linear", "decision", "loop", "parallel", "milestone"):
            errors.append(f"Step {i+1}: invalid type '{step_type.group(1)}'")

        status = re.search(r"- \*\*Status\*\*:\s*(\w+)", block)
        if status and status.group(1) not in ("pending", "in_progress", "completed", "skipped", "blocked"):
            errors.append(f"Step {i+1}: invalid status '{status.group(1)}'")

        if step_type and step_type.group(1) == "decision":
            if "- **Decision**:" not in block:
                errors.append(f"Step {i+1}: decision step missing '- **Decision**:' field")
            if "- **If yes**:" not in block:
                errors.append(f"Step {i+1}: decision step missing '- **If yes**:' field")
            if "- **If no**:" not in block:
                errors.append(f"Step {i+1}: decision step missing '- **If no**:' field")

        if step_type and step_type.group(1) == "loop":
            if "- **Loop condition**:" not in block:
                errors.append(f"Step {i+1}: loop step missing '- **Loop condition**:' field")
            if "- **Loop back to**:" not in block:
                errors.append(f"Step {i+1}: loop step missing '- **Loop back to**:' field")

        if step_type and step_type.group(1) == "parallel":
            if "- **Sub-steps**:" not in block:
                errors.append(f"Step {i+1}: parallel step missing '- **Sub-steps**:' field")

        if step_type and step_type.group(1) == "milestone":
            if "- **Criteria**:" not in block:
                errors.append(f"Step {i+1}: milestone step missing '- **Criteria**:' field")

        if "- **Next**:" not in block and (not step_type or step_type.group(1) != "milestone"):
            warnings.append(f"Step {i+1}: missing '- **Next**:' field (use '-' if final step)")

    if not errors and not warnings:
        print(f"[OK] {filepath} -- valid roadmap ({len(step_nums)} active steps)")
    elif not errors:
        print(f"[WARN] {filepath} -- valid with {len(warnings)} warning(s):")
        for w in warnings:
            print(f"  - {w}")
    else:
        print(f"[FAIL] {filepath} -- {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        if warnings:
            print(f"  Warnings ({len(warnings)}):")
            for w in warnings:
                print(f"    - {w}")

    return errors


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "roadmap.md"
    errors = validate_roadmap(path)
    sys.exit(1 if errors else 0)
