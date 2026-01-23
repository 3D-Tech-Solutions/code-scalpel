"""
Community tier tests for get_file_context.

Community tier provides:
- Function and class extraction
- Import detection
- Line counting and complexity calculation
- Security issue detection (eval, exec, pickle, os.system, bare except)
- 500-line limit
- NO code quality metrics (code_smells, doc_coverage, maintainability_index)
- NO Enterprise metadata (custom_metadata, compliance_flags, owners, technical_debt_score)

These tests validate that:
1. Basic extraction works correctly
2. 500-line limit is enforced
3. Code quality fields are EMPTY for Community tier
4. Enterprise fields are EMPTY for Community tier
"""


class TestCommunityTierBasicExtraction:
    """Test Community tier basic code element extraction."""

    def test_extracts_functions_from_python_file(self, temp_python_project):
        """Community tier should extract function definitions."""
        good_code_path = temp_python_project / "good_code.py"

        # Import the tool function
        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        # Call with Community tier capabilities (empty list)
        result = _get_file_context_sync(
            str(good_code_path),
            capabilities=[],  # Community tier - no advanced features
        )

        # Should extract functions
        assert result.functions is not None
        assert len(result.functions) > 0
        assert any(f.name == "calculate_sum" for f in result.functions)

    def test_extracts_classes_from_python_file(self, temp_python_project):
        """Community tier should extract class definitions."""
        good_code_path = temp_python_project / "good_code.py"

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        result = _get_file_context_sync(
            str(good_code_path),
            capabilities=[],
        )

        # Should extract classes
        assert result.classes is not None
        assert len(result.classes) > 0
        assert any(c.name == "DataProcessor" for c in result.classes)

    def test_extracts_imports_from_python_file(self, temp_python_project):
        """Community tier should extract import statements."""
        good_code_path = temp_python_project / "good_code.py"

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        result = _get_file_context_sync(
            str(good_code_path),
            capabilities=[],
        )

        # Should have imports field
        assert result.imports is not None


class TestCommunityTierLineLimits:
    """Test Community tier enforces 500-line limit."""

    def test_enforces_500_line_limit_community(self, temp_python_project):
        """Community tier should limit context to 500 lines."""
        good_code_path = temp_python_project / "good_code.py"

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        result = _get_file_context_sync(
            str(good_code_path),
            capabilities=[],
        )

        # Should not exceed 500 lines in context
        if result.expanded_context:
            lines = result.expanded_context.count("\n")
            assert lines <= 500, f"Community tier exceeded 500-line limit: {lines} lines"


class TestCommunityTierSecurityIssues:
    """Test Community tier detects security issues (world-class base feature)."""

    def test_detects_bare_except_clause(self, temp_python_project):
        """Community tier should detect bare except clauses."""
        smelly_code_path = temp_python_project / "smelly_code.py"

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        result = _get_file_context_sync(
            str(smelly_code_path),
            capabilities=[],
        )

        # Should detect has_security_issues
        assert hasattr(result, "has_security_issues")
        assert result.has_security_issues is True, "Should detect bare except clause"

    def test_returns_security_issue_flag(self, temp_python_project):
        """Community tier should return has_security_issues boolean."""
        good_code_path = temp_python_project / "good_code.py"

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        result = _get_file_context_sync(
            str(good_code_path),
            capabilities=[],
        )

        # Should have security flag
        assert hasattr(result, "has_security_issues")
        assert isinstance(result.has_security_issues, bool)


class TestCommunityTierNoProFeatures:
    """Test Community tier does NOT include Pro-only features."""

    def test_code_smells_empty_for_community(self, temp_python_project):
        """Community tier should NOT include code_smells (Pro feature)."""
        smelly_code_path = temp_python_project / "smelly_code.py"

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        result = _get_file_context_sync(
            str(smelly_code_path),
            capabilities=[],  # Community tier - no code smell detection
        )

        # Community tier should have empty or no code_smells
        assert not result.code_smells or result.code_smells == [], "Community tier should not return code_smells"

    def test_doc_coverage_empty_for_community(self, temp_python_project):
        """Community tier should NOT include doc_coverage (Pro feature)."""
        undocumented_path = temp_python_project / "undocumented.py"

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        result = _get_file_context_sync(
            str(undocumented_path),
            capabilities=[],
        )

        # Community tier should not have doc_coverage
        assert result.doc_coverage is None, "Community tier should not return doc_coverage"

    def test_maintainability_index_empty_for_community(self, temp_python_project):
        """Community tier should NOT include maintainability_index (Pro feature)."""
        good_code_path = temp_python_project / "good_code.py"

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        result = _get_file_context_sync(
            str(good_code_path),
            capabilities=[],
        )

        # Community tier should not have maintainability_index
        assert result.maintainability_index is None, "Community tier should not return maintainability_index"


class TestCommunityTierNoEnterpriseFeatures:
    """Test Community tier does NOT include Enterprise-only features."""

    def test_custom_metadata_empty_for_community(self, temp_python_project):
        """Community tier should NOT include custom_metadata (Enterprise feature)."""
        good_code_path = temp_python_project / "good_code.py"

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        result = _get_file_context_sync(
            str(good_code_path),
            capabilities=[],
        )

        # Community tier should have empty custom_metadata
        assert (
            not result.custom_metadata or result.custom_metadata == {}
        ), "Community tier should not return custom_metadata"

    def test_compliance_flags_empty_for_community(self, temp_python_project):
        """Community tier should NOT include compliance_flags (Enterprise feature)."""
        good_code_path = temp_python_project / "good_code.py"

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        result = _get_file_context_sync(
            str(good_code_path),
            capabilities=[],
        )

        # Community tier should have empty compliance_flags
        assert (
            not result.compliance_flags or result.compliance_flags == []
        ), "Community tier should not return compliance_flags"

    def test_owners_empty_for_community(self, temp_python_project):
        """Community tier should NOT include owners (Enterprise feature)."""
        good_code_path = temp_python_project / "good_code.py"

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        result = _get_file_context_sync(
            str(good_code_path),
            capabilities=[],
        )

        # Community tier should have empty owners
        assert not result.owners or result.owners == [], "Community tier should not return owners"

    def test_technical_debt_score_empty_for_community(self, temp_python_project):
        """Community tier should NOT include technical_debt_score (Enterprise feature)."""
        good_code_path = temp_python_project / "good_code.py"

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        result = _get_file_context_sync(
            str(good_code_path),
            capabilities=[],
        )

        # Community tier should not have technical_debt_score
        assert result.technical_debt_score is None, "Community tier should not return technical_debt_score"


class TestCommunityTierErrorHandling:
    """Test Community tier error handling."""

    def test_handles_file_not_found(self):
        """Community tier should handle missing files gracefully."""
        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        result = _get_file_context_sync(
            "/nonexistent/path/file.py",
            capabilities=[],
        )

        # Should return error result
        assert hasattr(result, "error") or result is None or result.functions is None

    def test_handles_syntax_errors(self, tmpdir):
        """Community tier should handle files with syntax errors."""
        bad_file = tmpdir.join("bad.py")
        bad_file.write("def broken(: pass")

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        # Should not crash on syntax error
        result = _get_file_context_sync(
            str(bad_file),
            capabilities=[],
        )

        # Should handle gracefully
        assert result is not None or result is not None
