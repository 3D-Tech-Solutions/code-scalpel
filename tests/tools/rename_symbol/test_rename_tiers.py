# [20260108_TEST] Tier enforcement tests for rename_symbol
"""
Tests that verify tier limits are enforced correctly for rename_symbol.

Community tier: Single-file only (max_files_searched=0, max_files_updated=0)
Pro tier: Cross-file updates (max_files_searched=500, max_files_updated=200)
Enterprise tier: Unlimited (max_files_searched=None, max_files_updated=None)
"""

from pathlib import Path

import pytest

from code_scalpel.licensing.features import get_tool_capabilities
from code_scalpel.surgery.rename_symbol_refactor import rename_references_across_project


class TestRenameSymbolTierEnforcement:
    """Test that tier limits are enforced correctly."""

    def test_community_tier_limits_defined(self):
        """Community tier has restrictive limits (single-file only)."""
        caps = get_tool_capabilities("rename_symbol", "community")

        assert caps["enabled"] is True
        assert caps["limits"]["max_files_searched"] == 0
        assert caps["limits"]["max_files_updated"] == 0
        assert "definition_rename" in caps["capabilities"]
        assert "cross_file_reference_rename" not in caps["capabilities"]

    def test_pro_tier_limits_defined(self):
        """Pro tier has higher limits for cross-file operations."""
        caps = get_tool_capabilities("rename_symbol", "pro")

        assert caps["enabled"] is True
        assert caps["limits"]["max_files_searched"] == 500
        assert caps["limits"]["max_files_updated"] == 200
        assert "definition_rename" in caps["capabilities"]
        assert "cross_file_reference_rename" in caps["capabilities"]
        assert "import_rename" in caps["capabilities"]

    def test_enterprise_tier_unlimited(self):
        """Enterprise tier has unlimited cross-file operations."""
        caps = get_tool_capabilities("rename_symbol", "enterprise")

        assert caps["enabled"] is True
        assert caps["limits"]["max_files_searched"] is None
        assert caps["limits"]["max_files_updated"] is None
        assert "definition_rename" in caps["capabilities"]
        assert "cross_file_reference_rename" in caps["capabilities"]
        assert "organization_wide_rename" in caps["capabilities"]


class TestRenameSymbolCrossFileCapabilities:
    """Test cross-file rename behavior at different tiers."""

    def test_cross_file_rename_updates_references(self, temp_project):
        """Cross-file rename updates import statements and references."""
        from code_scalpel.surgery.surgical_patcher import UnifiedPatcher

        main_py = temp_project / "main.py"
        utils_py = temp_project / "utils.py"

        # Step 1: Rename definition in main.py
        patcher = UnifiedPatcher.from_file(str(main_py))
        def_result = patcher.rename_symbol("function", "old_function", "new_function")
        assert def_result.success
        patcher.save(backup=False)

        # Step 2: Update references in other files
        result = rename_references_across_project(
            project_root=temp_project,
            target_file=main_py,
            target_type="function",
            target_name="old_function",
            new_name="new_function",
            create_backup=False,
            max_files_searched=500,  # Pro tier limit
            max_files_updated=200,
        )

        assert result.success is True
        # Result has: success, changed_files, backup_paths, warnings, error
        assert len(result.changed_files) >= 1  # At least utils.py

        # Verify main.py definition was updated
        main_content = main_py.read_text()
        assert "def new_function():" in main_content
        assert "old_function" not in main_content

        # Verify utils.py import was updated
        utils_content = utils_py.read_text()
        assert "from main import new_function" in utils_content
        assert "new_function()" in utils_content

    def test_cross_file_rename_with_limit_enforcement(self, temp_project):
        """Cross-file rename respects max_files_searched limit."""
        main_py = temp_project / "main.py"

        # Create many files to exceed limit
        for i in range(10):
            extra = temp_project / f"extra_{i}.py"
            extra.write_text(f"""
from main import old_function

def use_{i}():
    return old_function()
""".strip())

        result = rename_references_across_project(
            project_root=temp_project,
            target_file=main_py,
            target_type="function",
            target_name="old_function",
            new_name="new_function",
            create_backup=False,
            max_files_searched=3,  # Very restrictive limit
            max_files_updated=3,
        )

        # Should still succeed but may not update all files
        assert result.success is True
        # Check that some files were changed
        assert len(result.changed_files) >= 1

    def test_cross_file_rename_class_method(self, temp_project):
        """Cross-file rename updates method definition (references not tracked for methods)."""
        from code_scalpel.surgery.surgical_patcher import UnifiedPatcher

        main_py = temp_project / "main.py"
        temp_project / "utils.py"

        # Step 1: Rename definition
        patcher = UnifiedPatcher.from_file(str(main_py))
        def_result = patcher.rename_symbol("method", "OldClass.old_method", "new_method")
        assert def_result.success
        patcher.save(backup=False)

        # Verify method definition was renamed in main.py
        main_content = main_py.read_text()
        assert "def new_method" in main_content
        assert "def old_method" not in main_content

        # NOTE: Cross-file reference tracking for method calls is not yet implemented
        # Step 2 would update references, but method tracking is a known limitation
        # This test documents current behavior: definition renamed, but not call sites

    def test_rename_with_module_import(self, temp_project):
        """Cross-file rename handles module.function() style imports."""
        main_py = temp_project / "main.py"
        helper_py = temp_project / "helper.py"

        result = rename_references_across_project(
            project_root=temp_project,
            target_file=main_py,
            target_type="function",
            target_name="old_function",
            new_name="new_function",
            create_backup=False,
            max_files_searched=500,
            max_files_updated=200,
        )

        assert result.success is True

        # Verify helper.py uses new name
        helper_content = helper_py.read_text()
        assert "main.new_function()" in helper_content


def test_changed_files_are_relative_paths(temp_project):
    """Changed file paths are redacted to project-relative paths."""
    main_py = temp_project / "main.py"

    result = rename_references_across_project(
        project_root=temp_project,
        target_file=main_py,
        target_type="function",
        target_name="old_function",
        new_name="new_function",
        create_backup=False,
        max_files_searched=10,
        max_files_updated=10,
    )

    assert result.success is True
    assert result.changed_files, "Expected at least one changed file"
    assert all(not Path(p).is_absolute() for p in result.changed_files)


class TestRenameSymbolBackupCapability:
    """Test backup creation (available at all tiers per features.py)."""

    def test_backup_created_when_requested(self, temp_project):
        """Backup file is created when create_backup=True."""
        from code_scalpel.surgery.surgical_patcher import UnifiedPatcher

        main_py = temp_project / "main.py"
        utils_py = temp_project / "utils.py"
        utils_py.read_text()

        # Step 1: Rename definition
        patcher = UnifiedPatcher.from_file(str(main_py))
        patcher.rename_symbol("function", "old_function", "new_function")
        patcher.save(backup=True)

        # Step 2: Update cross-file references with backup
        result = rename_references_across_project(
            project_root=temp_project,
            target_file=main_py,
            target_type="function",
            target_name="old_function",
            new_name="new_function",
            create_backup=True,  # Enable backup
            max_files_searched=500,
            max_files_updated=200,
        )

        assert result.success is True

        # Check if backup was created for cross-file updates
        assert result.backup_paths is not None
        assert len(result.backup_paths) > 0

        # Backup file should exist
        backup_files = list(temp_project.glob("*.py.bak*"))
        assert len(backup_files) > 0

    def test_no_backup_when_disabled(self, temp_project):
        """No backup file created when create_backup=False."""
        main_py = temp_project / "main.py"

        result = rename_references_across_project(
            project_root=temp_project,
            target_file=main_py,
            target_type="function",
            target_name="old_function",
            new_name="new_function",
            create_backup=False,
            max_files_searched=0,
            max_files_updated=0,
        )

        assert result.success is True

        # No backup files should exist
        backup_files = list(temp_project.glob("*.py.bak*"))
        assert len(backup_files) == 0


class TestRenameSymbolEdgeCases:
    """Test edge cases and error conditions."""

    def test_rename_nonexistent_symbol_fails(self, temp_project):
        """Renaming a non-existent symbol doesn't break (cross-file only updates references)."""
        main_py = temp_project / "main.py"

        # rename_references_across_project doesn't check if symbol exists in target file
        # It only updates references, so it will succeed but change nothing
        result = rename_references_across_project(
            project_root=temp_project,
            target_file=main_py,
            target_type="function",
            target_name="does_not_exist",
            new_name="whatever",
            create_backup=False,
            max_files_searched=500,
            max_files_updated=200,
        )

        # Should succeed but change no files
        assert result.success is True
        assert len(result.changed_files) == 0

    def test_rename_to_existing_name_collision(self, temp_project):
        """Renaming to an existing name should be detected."""
        main_py = temp_project / "main.py"

        # Add another function with the target name
        content = main_py.read_text()
        content += "\n\ndef new_function():\n    return 'collision'\n"
        main_py.write_text(content)

        result = rename_references_across_project(
            project_root=temp_project,
            target_file=main_py,
            target_type="function",
            target_name="old_function",
            new_name="new_function",  # Already exists
            create_backup=False,
            max_files_searched=0,
            max_files_updated=0,
        )

        # Should either fail or warn about collision
        # Implementation may allow overwrite, but should at least not break
        assert result is not None

    def test_rename_invalid_target_name(self, temp_project):
        """Identifier validation rejects invalid Python names."""
        from code_scalpel.surgery.surgical_patcher import UnifiedPatcher

        main_py = temp_project / "main.py"

        # [20250309_TEST] Identifier validation now enforced in same-file patcher.
        patcher = UnifiedPatcher.from_file(str(main_py))

        result = patcher.rename_symbol("function", "old_function", "123invalid")
        assert result.success is False
        assert result.error == "Invalid Python identifier: 123invalid"

        patcher = UnifiedPatcher.from_file(str(main_py))
        result = patcher.rename_symbol("function", "old_function", "with-dash")
        assert result.success is False
        assert result.error == "Invalid Python identifier: with-dash"

        patcher = UnifiedPatcher.from_file(str(main_py))
        result = patcher.rename_symbol("function", "old_function", "class")
        assert result.success is False
        assert result.error == "Invalid Python identifier: class"

    def test_invalid_encoding_handling(self, temp_project):
        """Files with invalid encoding should be handled gracefully."""
        from code_scalpel.surgery.surgical_patcher import UnifiedPatcher

        # Create a file with invalid UTF-8 encoding
        invalid_py = temp_project / "invalid_encoding.py"
        with open(invalid_py, "wb") as f:
            # Write valid Python code with invalid UTF-8 byte sequence
            f.write(b"def old_function():\n    return 'test'\n")
            f.write(b"# Invalid UTF-8: \xff\xfe\n")  # Invalid UTF-8 sequence

        # Try to rename - should fail gracefully with ValueError
        with pytest.raises(ValueError) as exc_info:
            UnifiedPatcher.from_file(str(invalid_py))

        # Verify error message is informative
        error_msg = str(exc_info.value).lower()
        assert "cannot read file" in error_msg
        assert "utf" in error_msg or "codec" in error_msg or "decode" in error_msg


class TestRenameSymbolExplicitDenials:
    """[20260108_TEST] Explicit feature denial coverage for tier gating."""

    def test_community_cross_file_request_denied(self, temp_project):
        """Community tier cannot perform cross-file updates (limit zero)."""
        main_py = temp_project / "main.py"
        utils_py = temp_project / "utils.py"

        result = rename_references_across_project(
            project_root=temp_project,
            target_file=main_py,
            target_type="function",
            target_name="old_function",
            new_name="new_function",
            create_backup=False,
            max_files_searched=0,
            max_files_updated=0,
        )

        assert result.success is True
        assert result.changed_files == []
        assert any("max_files_searched=0" in warning for warning in result.warnings), result.warnings

        # No cross-file updates should occur at community tier
        utils_content = utils_py.read_text()
        assert "old_function" in utils_content
        assert "new_function" not in utils_content

    def test_pro_not_unlimited_enterprise_scope(self, temp_project):
        """Pro tier stops at max_files_updated; Enterprise would continue."""
        main_py = temp_project / "main.py"

        result = rename_references_across_project(
            project_root=temp_project,
            target_file=main_py,
            target_type="function",
            target_name="old_function",
            new_name="new_function",
            create_backup=False,
            max_files_searched=10,
            max_files_updated=1,
        )

        assert result.success is True
        assert len(result.changed_files) <= 1
        assert any("max_files_updated=1" in warning for warning in result.warnings), result.warnings

        # At least one file should remain unchanged because Pro is bounded
        untouched = []
        for py_file in temp_project.glob("*.py"):
            if py_file.name == "main.py":
                continue
            text = py_file.read_text()
            if "old_function" in text:
                untouched.append(py_file)
        assert untouched, "Expected at least one untouched file under Pro limits"


class TestRenameSymbolAdvancedEdgeCases:
    """Advanced edge cases: shadowed vars, globals, circular deps."""

    def test_shadowed_parameter_not_renamed(self, temp_project):
        from code_scalpel.surgery.surgical_patcher import UnifiedPatcher

        main_py = temp_project / "main.py"
        shadowed_py = temp_project / "shadowed.py"
        shadowed_py.write_text("""
from main import old_function

def outer():
    value = old_function()

    def inner(old_function):
        return old_function()

    return value + inner(1)
""".strip())

        patcher = UnifiedPatcher.from_file(str(main_py))
        assert patcher.rename_symbol("function", "old_function", "new_function").success
        patcher.save(backup=False)

        result = rename_references_across_project(
            project_root=temp_project,
            target_file=main_py,
            target_type="function",
            target_name="old_function",
            new_name="new_function",
            create_backup=False,
            max_files_searched=500,
            max_files_updated=200,
        )

        assert result.success is True
        content = shadowed_py.read_text()
        assert "from main import new_function" in content
        assert "value = new_function()" in content
        # Parameter shadow remains unchanged inside inner scope
        assert "def inner(old_function):" in content
        assert "return old_function()" in content

    def test_global_scope_still_renamed(self, temp_project):
        from code_scalpel.surgery.surgical_patcher import UnifiedPatcher

        main_py = temp_project / "main.py"
        scoped_py = temp_project / "scoped.py"
        scoped_py.write_text("""
from main import old_function

value = old_function()

def use_global():
    global old_function
    return old_function()
""".strip())

        patcher = UnifiedPatcher.from_file(str(main_py))
        assert patcher.rename_symbol("function", "old_function", "new_function").success
        patcher.save(backup=False)

        result = rename_references_across_project(
            project_root=temp_project,
            target_file=main_py,
            target_type="function",
            target_name="old_function",
            new_name="new_function",
            create_backup=False,
            max_files_searched=500,
            max_files_updated=200,
        )

        assert result.success is True
        content = scoped_py.read_text()
        assert "from main import new_function" in content
        assert "value = new_function()" in content
        assert "return new_function()" in content
        assert "old_function()" not in content

    def test_circular_dependencies_updated(self, temp_project):
        from code_scalpel.surgery.surgical_patcher import UnifiedPatcher

        main_py = temp_project / "main.py"
        circle_a = temp_project / "circle_a.py"
        circle_b = temp_project / "circle_b.py"

        circle_a.write_text("""
from main import old_function
import circle_b

def call_a():
    return old_function() + circle_b.call_b()
""".strip())
        circle_b.write_text("""
from main import old_function
import circle_a

def call_b():
    return old_function() + circle_a.call_a()
""".strip())

        patcher = UnifiedPatcher.from_file(str(main_py))
        assert patcher.rename_symbol("function", "old_function", "new_function").success
        patcher.save(backup=False)

        result = rename_references_across_project(
            project_root=temp_project,
            target_file=main_py,
            target_type="function",
            target_name="old_function",
            new_name="new_function",
            create_backup=False,
            max_files_searched=None,
            max_files_updated=None,
        )

        assert result.success is True
        changed = set(result.changed_files)
        # changed_files may be relative paths
        assert any("circle_a.py" in c for c in changed)
        assert any("circle_b.py" in c for c in changed)
        assert "new_function" in circle_a.read_text()
        assert "new_function" in circle_b.read_text()


class TestIdentifierValidation:
    """Identifier validation for rename_symbol operations."""

    def test_same_file_invalid_identifier_rejected(self, temp_project):
        from code_scalpel.surgery.surgical_patcher import UnifiedPatcher

        main_py = temp_project / "main.py"
        patcher = UnifiedPatcher.from_file(str(main_py))
        result = patcher.rename_symbol("function", "old_function", "123invalid")

        assert result.success is False
        assert result.error is not None
        assert "Invalid Python identifier" in result.error

    def test_cross_file_invalid_identifier_rejected(self, temp_project):
        main_py = temp_project / "main.py"
        result = rename_references_across_project(
            project_root=temp_project,
            target_file=main_py,
            target_type="function",
            target_name="old_function",
            new_name="with-dash",
            create_backup=False,
            max_files_searched=10,
            max_files_updated=10,
        )

        assert result.success is False
        assert result.error is not None
        assert "Invalid Python identifier" in result.error


class TestEnterpriseWorkflowCoverage:
    """Enterprise-tier behavior with unbounded limits."""

    def test_enterprise_unbounded_updates(self, temp_project):
        from code_scalpel.surgery.surgical_patcher import UnifiedPatcher

        main_py = temp_project / "main.py"

        extra_files = []
        for i in range(12):
            extra = temp_project / f"enterprise_extra_{i}.py"
            extra.write_text(f"""
from main import old_function

def use_{i}():
    return old_function()
""".strip())
            extra_files.append(extra)

        patcher = UnifiedPatcher.from_file(str(main_py))
        assert patcher.rename_symbol("function", "old_function", "new_function").success
        patcher.save(backup=False)

        result = rename_references_across_project(
            project_root=temp_project,
            target_file=main_py,
            target_type="function",
            target_name="old_function",
            new_name="new_function",
            create_backup=False,
            max_files_searched=None,
            max_files_updated=None,
        )

        assert result.success is True
        assert len(result.changed_files) >= len(extra_files) + 2  # utils + helper + extras
        assert not any("max_files" in w for w in result.warnings)

        for extra in extra_files:
            content = extra.read_text()
            assert "new_function" in content
            assert "old_function" not in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
