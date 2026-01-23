#!/usr/bin/env python3
"""Fix test assertion patterns to work with ToolResponseEnvelope __getattr__ forwarding.

The issue: Tests call result.model_dump() which only shows envelope fields,
then check if data fields exist. They should use hasattr(result, "field") instead.

Pattern replacements:
1. result_dict = result.model_dump() ... assert "field" in result_dict
   → assert hasattr(result, "field")

2. result_dict = result.model_dump() if hasattr(result, "model_dump") else vars(result)
   assert "field" in result_dict
   → assert hasattr(result, "field")
"""

import re
from pathlib import Path


def fix_test_file(filepath: Path) -> tuple[int, list[str]]:
    """Fix assertion patterns in a test file.

    Returns:
        (num_fixes, list_of_changes)
    """
    content = filepath.read_text()
    original_content = content
    changes = []

    # Pattern 1: Direct model_dump() followed by "field" in result_dict
    # Example: result_dict = result.model_dump()
    #          assert "packages" in result_dict

    # Pattern 2: Conditional model_dump() with fallback
    # result_dict = result.model_dump() if hasattr(result, "model_dump") else vars(result)
    # assert "field" in result_dict

    # Find all instances where we assign to result_dict from model_dump
    lines = content.split("\n")
    fixed_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check if this line assigns result_dict from model_dump
        if re.search(r"result_dict\s*=\s*result\.model_dump\(\)", line):
            # This line needs to be removed or commented
            # Look ahead for assertions that use result_dict
            j = i + 1
            assertions_to_fix = []

            while j < len(lines):
                next_line = lines[j]

                # Stop if we hit a blank line, new test, or unrelated code
                if (
                    not next_line.strip()
                    or next_line.strip().startswith("def ")
                    or next_line.strip().startswith("async def ")
                    or next_line.strip().startswith("class ")
                ):
                    break

                # Check if this is an assertion using result_dict
                if "result_dict" in next_line and "in result_dict" in next_line:
                    # Extract field name from pattern like: assert "field" in result_dict
                    match = re.search(r'["\'](\w+)["\'] in result_dict', next_line)
                    if match:
                        field_name = match.group(1)
                        assertions_to_fix.append((j, field_name, next_line))

                j += 1

            if assertions_to_fix:
                # Comment out the result_dict assignment
                fixed_lines.append("        # [20260122_BUGFIX] Removed model_dump() - use hasattr() instead")
                fixed_lines.append(f"        # {line}")
                changes.append(f"Line {i+1}: Commented out result_dict assignment")

                # Skip to assertions and fix them
                for k in range(i + 1, assertions_to_fix[0][0]):
                    if k < len(lines):
                        fixed_lines.append(lines[k])

                # Fix assertions
                for assert_line_idx, field_name, assert_line in assertions_to_fix:
                    indent = len(assert_line) - len(assert_line.lstrip())
                    # Extract any assertion message
                    msg_match = re.search(r',\s*f?"([^"]+)"', assert_line)
                    if msg_match:
                        msg = msg_match.group(1)
                        new_line = f"{' ' * indent}assert hasattr(result, \"{field_name}\"), f\"{msg}\""
                    else:
                        new_line = f"{' ' * indent}assert hasattr(result, \"{field_name}\")"

                    fixed_lines.append(new_line)
                    changes.append(
                        f"Line {assert_line_idx+1}: Changed '{field_name} in result_dict' to 'hasattr(result, \"{field_name}\")'"
                    )

                # Skip past the lines we've already processed
                i = assertions_to_fix[-1][0] + 1
                continue

        # Keep line as-is if not part of a pattern we're fixing
        fixed_lines.append(line)
        i += 1

    new_content = "\n".join(fixed_lines)

    if new_content != original_content:
        filepath.write_text(new_content)
        return len(changes), changes

    return 0, []


if __name__ == "__main__":
    test_files = [
        Path("tests/tools/get_project_map/test_enterprise_features.py"),
        Path("tests/tools/get_project_map/test_enterprise_tier.py"),
        Path("tests/tools/get_project_map/test_tier_enforcement.py"),
    ]

    total_fixes = 0
    for test_file in test_files:
        print(f"\n{'='*80}")
        print(f"Processing: {test_file}")
        print("=" * 80)

        num_fixes, changes = fix_test_file(test_file)
        total_fixes += num_fixes

        if changes:
            for change in changes:
                print(f"  ✓ {change}")
        else:
            print("  No changes needed")

    print(f"\n{'='*80}")
    print(f"Total fixes applied: {total_fixes}")
    print("=" * 80)
