#!/usr/bin/env python
"""v1.5.x Python Regression Tests

[20251215_TEST] v2.0.0 - Verify no breaking changes from previous version.

Note:
This script is executed directly in CI. It must be able to import `code_scalpel`
even if the package hasn't been installed (e.g., missing `pip install -e .`).
"""

import asyncio


def _ensure_repo_src_on_path() -> None:
    try:
        import code_scalpel  # noqa: F401

        return
    except Exception:
        pass

    import sys
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[1]
    src_root = repo_root / "src"
    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))


_ensure_repo_src_on_path()

from code_scalpel.mcp.server import (  # noqa: E402
    analyze_code,
    extract_code,
    security_scan,
)


def test_python_extraction():
    """Test Python extraction still works."""
    test_code = """
def calculate_tax(amount, rate=0.1):
    return amount * rate

class Calculator:
    def add(self, a, b):
        return a + b
"""

    # Extract function
    result = asyncio.run(
        extract_code(
            code=test_code,
            target_type="function",
            target_name="calculate_tax",
            include_context=False,
        )
    )
    assert result.success, f"Function extraction failed: {result.error}"
    assert "calculate_tax" in result.target_code, "Function extraction failed"
    print("✓ Python function extraction works")

    # Extract class
    result2 = asyncio.run(
        extract_code(
            code=test_code,
            target_type="class",
            target_name="Calculator",
            include_context=False,
        )
    )
    assert result2.success, f"Class extraction failed: {result2.error}"
    assert "Calculator" in result2.target_code, "Class extraction failed"
    print("✓ Python class extraction works")


def test_security_scan():
    """Test security scan still detects vulnerabilities."""
    vuln_code = """
import sqlite3
def get_user(user_id):
    conn = sqlite3.connect('db.sqlite')
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM users WHERE id={user_id}")
    return cursor.fetchone()
"""

    scan_result = asyncio.run(security_scan(code=vuln_code))
    assert scan_result.vulnerability_count > 0, "Security scan failed to detect SQL injection"
    print("✓ Python security scan works")


def test_code_analysis():
    """Test code analysis still works."""
    test_code = """
def calculate_tax(amount, rate=0.1):
    return amount * rate

class Calculator:
    def add(self, a, b):
        return a + b
"""

    analysis = asyncio.run(analyze_code(code=test_code))
    assert analysis.functions, "Code analysis failed"
    print("✓ Python code analysis works")


def main():
    print("=" * 60)
    print("v1.5.x Python Regression Tests")
    print("=" * 60)
    print()

    test_python_extraction()
    test_security_scan()
    test_code_analysis()

    print()
    print("All v1.5.x Python regression tests passed!")


if __name__ == "__main__":
    main()
