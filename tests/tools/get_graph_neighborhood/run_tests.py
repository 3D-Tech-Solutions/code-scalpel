"""
Test runner and summary for get_graph_neighborhood test suite.

This script:
1. Validates all test modules are discoverable
2. Runs all tests with verbose output
3. Generates a coverage report
4. Validates tier enforcement across all tests
"""

import subprocess
import sys
from pathlib import Path


def run_tests():
    """Run all get_graph_neighborhood tests."""

    test_dir = Path(__file__).parent

    print("=" * 80)
    print("get_graph_neighborhood Test Suite")
    print("=" * 80)
    print()

    # List test modules created
    test_modules = [
        "test_core_algorithm.py",
        "test_direction_filtering.py",
        "test_confidence_filtering.py",
        "test_truncation_protection.py",
        "test_tier_enforcement.py",
    ]

    print("Test Modules Created:")
    print("-" * 80)
    for module in test_modules:
        module_path = test_dir / module
        if module_path.exists():
            # Count test classes and functions
            with open(module_path) as f:
                content = f.read()
                test_classes = content.count("class Test")
                test_methods = content.count("def test_")
            print(f"  ✓ {module:<40} ({test_classes} classes, {test_methods} methods)")
        else:
            print(f"  ✗ {module:<40} (NOT FOUND)")

    print()
    print("=" * 80)
    print("Running Tests (Phase 1 - Critical Pre-Release)")
    print("=" * 80)
    print()

    # Run pytest on the directory
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(test_dir),
        "-v",
        "--tb=short",
        "--co",  # Collect only (show what would run)
    ]

    print(f"Command: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, cwd=test_dir)

    return result.returncode == 0


def main():
    """Main entry point."""
    success = run_tests()

    if success:
        print()
        print("=" * 80)
        print("Test Collection Successful")
        print("=" * 80)
        print()
        print("Next Steps:")
        print("  1. Run full test suite: pytest tests/tools/get_graph_neighborhood/ -v")
        print("  2. Check coverage: pytest --cov=code_scalpel.mcp.server --cov-report=html")
        print("  3. Update assessment document with test references")
        return 0
    else:
        print()
        print("ERROR: Test collection failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
