"""Test keyword validation atomicity for rename_symbol.

[20260121_TEST] Critical: Verify that keyword/identifier validation happens BEFORE
any file modifications, preventing partial-apply atomicity bugs.

Regression test for: "If I rename 'process' to 'yield', the tool might break the
local file syntax and then fail the cross-file check, leaving the repo in a
broken, half-edited state."
"""

from pathlib import Path

import pytest


@pytest.mark.asyncio
async def test_keyword_validation_before_file_modification(tmp_path):
    """Verify keyword validation prevents ANY file modification."""
    from code_scalpel.mcp.helpers.extraction_helpers import rename_symbol

    # Create a test file
    test_file = tmp_path / "test_module.py"
    original_code = '''def process_data(x):
    """Process data."""
    return x * 2

def helper():
    result = process_data(5)
    return result
'''
    test_file.write_text(original_code)

    # Attempt to rename to a reserved keyword
    result = await rename_symbol(
        file_path=str(test_file),
        target_type="function",
        target_name="process_data",
        new_name="yield",  # Reserved keyword
        create_backup=True,
    )

    # Verify the operation failed
    assert result.success is False
    assert "Invalid Python identifier" in result.error
    assert "reserved keyword" in result.error.lower()

    # CRITICAL: Verify the file was NOT modified
    current_content = test_file.read_text()
    assert current_content == original_code, "File should not be modified when validation fails"

    # Verify no backup was created (since no modification occurred)
    backup_file = Path(str(test_file) + ".bak")
    assert not backup_file.exists(), "Backup should not exist when validation fails early"


@pytest.mark.asyncio
async def test_invalid_identifier_validation_before_file_modification(tmp_path):
    """Verify invalid identifier validation prevents ANY file modification."""
    from code_scalpel.mcp.helpers.extraction_helpers import rename_symbol

    test_file = tmp_path / "test_module.py"
    original_code = '''def calculate(x):
    """Calculate value."""
    return x + 1
'''
    test_file.write_text(original_code)

    # Attempt to rename to an invalid identifier (starts with digit)
    result = await rename_symbol(
        file_path=str(test_file),
        target_type="function",
        target_name="calculate",
        new_name="123invalid",  # Invalid: starts with digit
        create_backup=True,
    )

    # Verify the operation failed
    assert result.success is False
    assert "Invalid Python identifier" in result.error

    # CRITICAL: Verify the file was NOT modified
    current_content = test_file.read_text()
    assert current_content == original_code, "File should not be modified when validation fails"


@pytest.mark.asyncio
async def test_empty_name_validation_before_file_modification(tmp_path):
    """Verify empty name validation prevents ANY file modification."""
    from code_scalpel.mcp.helpers.extraction_helpers import rename_symbol

    test_file = tmp_path / "test_module.py"
    original_code = """def process(x):
    return x
"""
    test_file.write_text(original_code)

    # Attempt to rename to empty string
    result = await rename_symbol(
        file_path=str(test_file),
        target_type="function",
        target_name="process",
        new_name="",  # Empty
        create_backup=True,
    )

    # Verify the operation failed
    assert result.success is False
    assert "Invalid Python identifier" in result.error

    # CRITICAL: Verify the file was NOT modified
    current_content = test_file.read_text()
    assert current_content == original_code


@pytest.mark.asyncio
async def test_all_python_keywords_rejected_early(tmp_path):
    """Verify all Python reserved keywords are rejected before file modification."""
    from code_scalpel.mcp.helpers.extraction_helpers import rename_symbol

    test_file = tmp_path / "test_module.py"
    original_code = """def original_name(x):
    return x
"""
    test_file.write_text(original_code)

    # Test a representative sample of Python keywords
    keywords_to_test = [
        "class",
        "def",
        "return",
        "if",
        "else",
        "for",
        "while",
        "import",
        "from",
        "as",
        "try",
        "except",
        "finally",
        "raise",
        "with",
        "yield",
        "lambda",
        "pass",
        "break",
        "continue",
        "assert",
        "global",
        "nonlocal",
    ]

    for kw in keywords_to_test:
        # Reset file content
        test_file.write_text(original_code)

        result = await rename_symbol(
            file_path=str(test_file),
            target_type="function",
            target_name="original_name",
            new_name=kw,
            create_backup=True,
        )

        # Verify rejection
        assert result.success is False, f"Keyword '{kw}' should be rejected"
        assert "Invalid Python identifier" in result.error
        assert "reserved keyword" in result.error.lower()

        # Verify file unchanged
        assert test_file.read_text() == original_code, f"File should be unchanged after rejecting '{kw}'"


@pytest.mark.asyncio
async def test_valid_rename_still_works():
    """Verify valid renames still work correctly after adding validation."""
    import tempfile

    from code_scalpel.mcp.helpers.extraction_helpers import rename_symbol

    # Use a temp file in the current working directory (within project)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, dir=".") as tmp:
        original_code = '''def process_data(x):
    """Process data."""
    return x * 2
'''
        tmp.write(original_code)
        tmp.flush()
        test_file = Path(tmp.name)

    try:
        # Valid rename
        result = await rename_symbol(
            file_path=str(test_file),
            target_type="function",
            target_name="process_data",
            new_name="transform_data",  # Valid identifier
            create_backup=True,
        )

        # Verify success
        assert result.success is True, f"Rename failed: {result.error}"
        assert result.error is None

        # Verify file was modified correctly
        new_content = test_file.read_text()
        assert "def transform_data(x):" in new_content
        assert "process_data" not in new_content

        # Verify backup was created
        backup_file = Path(str(test_file) + ".bak")
        assert backup_file.exists()
        assert backup_file.read_text() == original_code
    finally:
        # Cleanup
        if test_file.exists():
            test_file.unlink()
        backup_file = Path(str(test_file) + ".bak")
        if backup_file.exists():
            backup_file.unlink()
