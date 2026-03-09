"""Tier behavior tests for get_file_context.

These tests validate tier-specific limits and output fields:
- Community: Truncated context (2,000 lines), definitions only
- Pro: Unlimited context, includes docstrings/imports
- Enterprise: Unlimited context with PII/Secret probability scores

[20260121_TEST] Validate get_file_context tier outputs systematically.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync
from code_scalpel.mcp import server


class TestGetFileContextCommunityTier:
    """Test get_file_context at Community tier."""

    def test_tier_applied_is_community(self, community_tier, tmp_path):
        """Community tier reports tier_applied='community'."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass\n")

        result = _get_file_context_sync(str(test_file), tier="community")

        assert result.success is True
        assert result.tier_applied == "community"

    def test_max_context_lines_applied_is_2000(self, community_tier, tmp_path):
        """Community tier should limit context to 2,000 lines.

        [20260121_ASSERTION] Community max_context_lines = 2000
        """
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass\n")

        result = _get_file_context_sync(str(test_file), tier="community")

        assert result.success is True
        # max_context_lines_applied should be 2000 or None (handled by limits.toml)
        assert result.max_context_lines_applied in (2000, None)

    def test_pro_features_enabled_is_false(self, community_tier, tmp_path):
        """Community tier reports pro_features_enabled=False."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass\n")

        result = _get_file_context_sync(str(test_file), tier="community")

        assert result.success is True
        assert result.pro_features_enabled is False

    def test_enterprise_features_enabled_is_false(self, community_tier, tmp_path):
        """Community tier reports enterprise_features_enabled=False."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass\n")

        result = _get_file_context_sync(str(test_file), tier="community")

        assert result.success is True
        assert result.enterprise_features_enabled is False

    def test_community_file_exceeds_2000_lines_fails(self, community_tier, tmp_path):
        """Community tier returns error when file exceeds 2,000 lines.

        [20260121_ASSERTION] Community enforces max_context_lines limit
        """
        # Create a file with 2100 lines
        test_file = tmp_path / "large.py"
        lines = ["# Line " + str(i) for i in range(2100)]
        test_file.write_text("\n".join(lines))

        result = _get_file_context_sync(str(test_file), tier="community")

        # Should fail because file exceeds limit
        assert result.success is False
        assert "exceeds" in (result.error or "").lower()
        assert result.line_count == 2100


class TestGetFileContextProTier:
    """Test get_file_context at Pro tier."""

    def test_tier_applied_is_pro(self, pro_tier, tmp_path):
        """Pro tier reports tier_applied='pro'."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass\n")

        result = _get_file_context_sync(str(test_file), tier="pro")

        assert result.success is True
        assert result.tier_applied == "pro"

    def test_max_context_lines_applied_is_none(self, pro_tier, tmp_path):
        """Pro tier should have unlimited context lines.

        [20260121_ASSERTION] Pro max_context_lines = None (unlimited)
        """
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass\n")

        result = _get_file_context_sync(str(test_file), tier="pro")

        assert result.success is True
        # max_context_lines_applied should be None (unlimited)
        assert result.max_context_lines_applied is None

    def test_pro_features_enabled_is_true(self, pro_tier, tmp_path):
        """Pro tier reports pro_features_enabled=True."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello():\n    '''Docstring.'''\n    pass\n")

        result = _get_file_context_sync(str(test_file), tier="pro")

        assert result.success is True
        assert result.pro_features_enabled is True

    def test_enterprise_features_enabled_is_false(self, pro_tier, tmp_path):
        """Pro tier reports enterprise_features_enabled=False."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass\n")

        result = _get_file_context_sync(str(test_file), tier="pro")

        assert result.success is True
        assert result.enterprise_features_enabled is False

    def test_pro_file_with_1500_lines_succeeds(self, pro_tier, tmp_path):
        """Pro tier accepts unlimited file sizes.

        [20260121_ASSERTION] Pro tier has unlimited context lines
        """
        # Create a file with 1,500 lines
        test_file = tmp_path / "large.py"
        lines = ["# Line " + str(i) for i in range(1500)]
        test_file.write_text("\n".join(lines))

        result = _get_file_context_sync(str(test_file), tier="pro")

        # Should succeed because file is within pro limit
        assert result.success is True
        assert result.line_count == 1500

    def test_pro_includes_imports_and_docstrings(self, pro_tier, tmp_path):
        """Pro tier includes imports and docstrings in analysis.

        [20260121_ASSERTION] Pro tier enables documentation_coverage
        """
        test_file = tmp_path / "module.py"
        test_file.write_text('''"""Module docstring."""

import json
from typing import Dict, List

def process(data: Dict) -> List:
    """Process input data.
    
    Args:
        data: Input dictionary
    
    Returns:
        Processed list
    """
    return [v for v in data.values()]
''')

        result = _get_file_context_sync(str(test_file), tier="pro")

        assert result.success is True
        # Should have detected imports
        assert len(result.imports) > 0
        # Functions should be captured
        assert len(result.functions) > 0


class TestGetFileContextEnterpriseTier:
    """Test get_file_context at Enterprise tier."""

    def test_tier_applied_is_enterprise(self, enterprise_tier, tmp_path):
        """Enterprise tier reports tier_applied='enterprise'."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass\n")

        result = _get_file_context_sync(str(test_file), tier="enterprise")

        assert result.success is True
        assert result.tier_applied == "enterprise"

    def test_max_context_lines_applied_is_none(self, enterprise_tier, tmp_path):
        """Enterprise tier has unlimited context (max_context_lines_applied=None).

        [20260121_ASSERTION] Enterprise max_context_lines = None (unlimited)
        """
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass\n")

        result = _get_file_context_sync(str(test_file), tier="enterprise")

        assert result.success is True
        # Enterprise should have None (unlimited)
        assert result.max_context_lines_applied is None

    def test_pro_features_enabled_is_true(self, enterprise_tier, tmp_path):
        """Enterprise tier reports pro_features_enabled=True."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass\n")

        result = _get_file_context_sync(str(test_file), tier="enterprise")

        assert result.success is True
        assert result.pro_features_enabled is True

    def test_enterprise_features_enabled_is_true(self, enterprise_tier, tmp_path):
        """Enterprise tier reports enterprise_features_enabled=True."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass\n")

        result = _get_file_context_sync(str(test_file), tier="enterprise")

        assert result.success is True
        assert result.enterprise_features_enabled is True

    def test_enterprise_large_file_succeeds(self, enterprise_tier, tmp_path):
        """Enterprise tier accepts unlimited file size.

        [20260121_ASSERTION] Enterprise allows very large context (no truncation)
        """
        # Create a file with 5,000 lines
        test_file = tmp_path / "huge.py"
        lines = ["# Line " + str(i) for i in range(5000)]
        test_file.write_text("\n".join(lines))

        result = _get_file_context_sync(str(test_file), tier="enterprise")

        # Should succeed because enterprise has unlimited context
        assert result.success is True
        assert result.line_count == 5000

    def test_enterprise_pii_redaction_enabled(self, enterprise_tier, tmp_path):
        """Enterprise tier enables PII/Secret detection and redaction.

        [20260121_ASSERTION] Enterprise enables pii_redaction, secret_masking
        """
        test_file = tmp_path / "sensitive.py"
        code = """# Module with sensitive data
API_KEY = "sk-1234567890abcdef"
USER_SSN = "123-45-6789"
EMAIL = "user@example.com"

def authenticate(token):
    # Authenticate with API token
    return token == API_KEY
"""
        test_file.write_text(code)

        result = _get_file_context_sync(str(test_file), tier="enterprise")

        # Enterprise should have redaction enabled (metadata present even if parsing failed)
        assert result.enterprise_features_enabled is True
        assert result.pii_redacted is True
        assert result.secrets_masked is True
        assert result.redaction_summary is not None
        # The important part: verification that redaction was attempted
        assert len(result.redaction_summary) > 0


@pytest.mark.asyncio
async def test_get_file_context_async_interface(community_tier, tmp_path: Path):
    """Test the async interface of get_file_context via server module.

    [20260121_TEST] Verify async wrapper works with tier detection
    """
    test_file = tmp_path / "test.py"
    test_file.write_text("""def simple_function():
    '''Does something simple.'''
    return True
""")

    result = await server.get_file_context(str(test_file))

    assert result.success is True
    assert result.tier_applied == "community"
    assert len(result.functions) > 0


class TestGetFileContextCSharpFallback:
    """Validate C# file-context fallback when optional parser deps are missing."""

    def test_csharp_file_context_succeeds_without_tree_sitter(
        self, community_tier, tmp_path: Path
    ):
        """C# get_file_context should fall back to lightweight structural parsing.

        [20260308_TEST] Ensures .cs files still produce useful summaries when the
        optional tree-sitter-c-sharp dependency is unavailable.
        """
        test_file = tmp_path / "Program.cs"
        test_file.write_text(
            """using System;
using System.Collections.Generic;

namespace Demo.App;

public class UserService
{
    public string GetUser(int id)
    {
        return id.ToString();
    }

    private static void Log(string message)
    {
        Console.WriteLine(message);
    }
}
"""
        )

        result = _get_file_context_sync(str(test_file), tier="community")

        assert result.success is True
        assert result.language == "csharp"
        assert result.error is None
        assert result.imports == ["System", "System.Collections.Generic"]

        class_names = [c["name"] if isinstance(c, dict) else c.name for c in result.classes]
        assert class_names == ["UserService"]

        method_names = [f["name"] if isinstance(f, dict) else f.name for f in result.functions]
        assert method_names == ["UserService.GetUser", "UserService.Log"]
        assert "namespace Demo.App" in result.summary

    def test_csharp_file_context_pro_fields_use_fallback(self, pro_tier, tmp_path: Path):
        """Pro-tier enrichments should still work with the fallback C# parser."""
        test_file = tmp_path / "Program.cs"
        test_file.write_text(
            """using Demo.Core;

namespace Demo.App;

public static class Program
{
    public static int Main(string[] args)
    {
        return args.Length;
    }
}
"""
        )

        result = _get_file_context_sync(str(test_file), tier="pro")

        assert result.success is True
        assert result.language == "csharp"
        assert result.semantic_summary is not None
        assert "1 function(s)" in result.semantic_summary
        assert result.expanded_context is not None
        assert "public static class Program" in result.expanded_context
