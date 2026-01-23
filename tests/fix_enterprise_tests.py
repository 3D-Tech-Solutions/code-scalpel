#!/usr/bin/env python3
"""Fix enterprise feature tests to use hasattr instead of model_dump()."""

import re
from pathlib import Path


def fix_test_file(filepath):
    """Fix a single test file."""
    content = Path(filepath).read_text()
    original = content

    # Pattern 1: result_dict = result.model_dump() ... assert "field" in result_dict
    # Replace with: assert hasattr(result, "field")
    pattern1 = r'result_dict = result\.model_dump\(\) if hasattr\(result, "model_dump"\) else vars\(result\)\s+assert \(\s+"(\w+)" in result_dict\s+\), f"([^"]+)\. Available: \{list\(result_dict\.keys\(\)\)\}"'

    def replacement1(match):
        field = match.group(1)
        message = match.group(2)
        return f'# [20260122_BUGFIX] Use hasattr() which works with __getattr__ forwarding\n        assert hasattr(result, "{field}"), f"{message}"\n        assert result.{field} is not None'

    content = re.sub(pattern1, replacement1, content)

    # Pattern 2: simpler version without line breaks
    pattern2 = r'result_dict = result\.model_dump\(\) if hasattr\(result, "model_dump"\) else vars\(result\)\s+assert "(\w+)" in result_dict, f"([^"]+)\. Available: \{list\(result_dict\.keys\(\)\)\}"'

    def replacement2(match):
        field = match.group(1)
        message = match.group(2)
        return f'# [20260122_BUGFIX] Use hasattr() which works with __getattr__ forwarding\n        assert hasattr(result, "{field}"), f"{message}"\n        assert result.{field} is not None'

    content = re.sub(pattern2, replacement2, content)

    # Pattern 3: checking if field exists and value
    pattern3 = r'result_dict = result\.model_dump\(\) if hasattr\(result, "model_dump"\) else vars\(result\)\s+if "(\w+)" in result_dict:\s+value = result_dict\["\1"\]'

    def replacement3(match):
        field = match.group(1)
        return f'# [20260122_BUGFIX] Check if field is accessible\n        if hasattr(result, "{field}"):\n            value = result.{field}'

    content = re.sub(pattern3, replacement3, content)

    # Pattern 4: historical trends special case
    pattern4 = r'result_dict = result\.model_dump\(\) if hasattr\(result, "model_dump"\) else vars\(result\)\s+# May be named historical_trends or historical_architecture_trends\s+has_trends = "historical_trends" in result_dict or "historical_architecture_trends" in result_dict\s+assert has_trends, f"([^"]+)\. Available: \{list\(result_dict\.keys\(\)\)\}"'

    def replacement4(match):
        message = match.group(1)
        return f'# [20260122_BUGFIX] Use hasattr() which works with __getattr__ forwarding\n        # May be named historical_trends or historical_architecture_trends\n        has_trends = hasattr(result, "historical_trends") or hasattr(result, "historical_architecture_trends")\n        assert has_trends, f"{message}"'

    content = re.sub(pattern4, replacement4, content, flags=re.MULTILINE)

    if content != original:
        Path(filepath).write_text(content)
        print(f"✓ Fixed {filepath}")
        return True
    else:
        print(f"- No changes needed for {filepath}")
        return False


if __name__ == "__main__":
    test_files = [
        "tests/tools/get_project_map/test_enterprise_features.py",
        "tests/tools/get_project_map/test_enterprise_tier.py",
        "tests/tools/get_project_map/test_tier_enforcement.py",
    ]

    fixed_count = 0
    for test_file in test_files:
        if fix_test_file(test_file):
            fixed_count += 1

    print(f"\nFixed {fixed_count} test files")
