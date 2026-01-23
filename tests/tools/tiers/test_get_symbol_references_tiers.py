"""
Output metadata field tests for get_symbol_references.

Tests tier transparency fields and feature enablement:
- tier_applied: The tier that was applied to the request
- max_files_applied: The max_files limit applied
- max_references_applied: The max_references limit applied
- category_counts: Populated when Pro tier enables usage categorization (Pro+)
- risk_score, blast_radius: Populated when Enterprise enables impact analysis

[20260121_TEST] v3.3.0 - Output metadata field validation for AI agent transparency
"""

import tempfile
from pathlib import Path

import pytest

from code_scalpel.mcp.helpers.context_helpers import _get_symbol_references_sync


@pytest.fixture
def temp_project_with_symbol():
    """Create a temporary project with a symbol that has multiple references."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Create main.py with definition
        (root / "main.py").write_text("""
def process_data(x):
    '''Process the data.'''
    return x * 2

result = process_data(5)
""")

        # Create handler.py with multiple calls
        (root / "handler.py").write_text("""
from main import process_data

def handle_request(data):
    '''Handle incoming request.'''
    processed = process_data(data)
    return {"result": processed}

def handle_batch(items):
    '''Handle batch.'''
    return [process_data(item) for item in items]
""")

        # Create test file with references
        (root / "test_main.py").write_text("""
import unittest
from main import process_data

class TestProcessData(unittest.TestCase):
    def test_with_positive(self):
        result = process_data(10)
        self.assertEqual(result, 20)

    def test_with_negative(self):
        assert process_data(-5) == -10
""")

        # Create utils.py with additional call
        (root / "utils.py").write_text("""
from main import process_data

def transform(value):
    '''Transform value using process_data.'''
    return process_data(value) + 1
""")

        yield root


class TestGetSymbolReferencesCommunityTier:
    """Community tier: 10 files searched, 50 references max, no categorization."""

    def test_tier_applied_is_community(self, community_tier, temp_project_with_symbol):
        """Community tier should be applied."""
        result = _get_symbol_references_sync(
            "process_data",
            str(temp_project_with_symbol),
            max_files=10,
            max_references=50,
            tier="community",
        )

        assert result.tier_applied == "community"

    def test_max_files_limit_applied(self, community_tier, temp_project_with_symbol):
        """Community tier max_files=10 should be applied."""
        result = _get_symbol_references_sync(
            "process_data",
            str(temp_project_with_symbol),
            max_files=10,
            max_references=50,
            tier="community",
        )

        assert result.max_files_applied == 10

    def test_max_references_limit_applied(self, community_tier, temp_project_with_symbol):
        """Community tier max_references=50 should be applied."""
        result = _get_symbol_references_sync(
            "process_data",
            str(temp_project_with_symbol),
            max_files=10,
            max_references=50,
            tier="community",
        )

        assert result.max_references_applied == 50

    def test_no_category_counts(self, community_tier, temp_project_with_symbol):
        """Community tier does NOT populate category_counts (Pro+ feature)."""
        result = _get_symbol_references_sync(
            "process_data",
            str(temp_project_with_symbol),
            max_files=10,
            max_references=50,
            enable_categorization=False,
            tier="community",
        )

        # Community tier without categorization should not have category_counts
        assert result.category_counts is None

    def test_no_risk_metadata(self, community_tier, temp_project_with_symbol):
        """Community tier does NOT populate risk_score or blast_radius (Enterprise feature)."""
        result = _get_symbol_references_sync(
            "process_data",
            str(temp_project_with_symbol),
            max_files=10,
            max_references=50,
            enable_impact_analysis=False,
            tier="community",
        )

        # Community tier without impact analysis should not have risk metadata
        assert result.risk_score is None
        assert result.blast_radius is None


class TestGetSymbolReferencesProTier:
    """Pro tier: Unlimited files/references, usage categorization enabled, scope filtering works."""

    def test_tier_applied_is_pro(self, pro_tier, temp_project_with_symbol):
        """Pro tier should be applied."""
        result = _get_symbol_references_sync(
            "process_data",
            str(temp_project_with_symbol),
            max_files=None,
            max_references=None,
            enable_categorization=True,
            tier="pro",
        )

        assert result.tier_applied == "pro"

    def test_max_files_unlimited(self, pro_tier, temp_project_with_symbol):
        """Pro tier has unlimited file search (max_files=None)."""
        result = _get_symbol_references_sync(
            "process_data",
            str(temp_project_with_symbol),
            max_files=None,
            max_references=None,
            enable_categorization=True,
            tier="pro",
        )

        assert result.max_files_applied is None

    def test_max_references_unlimited(self, pro_tier, temp_project_with_symbol):
        """Pro tier has unlimited references (max_references=None)."""
        result = _get_symbol_references_sync(
            "process_data",
            str(temp_project_with_symbol),
            max_files=None,
            max_references=None,
            enable_categorization=True,
            tier="pro",
        )

        assert result.max_references_applied is None

    def test_category_counts_populated(self, pro_tier, temp_project_with_symbol):
        """Pro tier with categorization populates category_counts."""
        result = _get_symbol_references_sync(
            "process_data",
            str(temp_project_with_symbol),
            max_files=None,
            max_references=None,
            enable_categorization=True,
            tier="pro",
        )

        # Pro tier with categorization should populate category_counts
        assert result.category_counts is not None
        assert isinstance(result.category_counts, dict)
        # Should have reference types
        assert len(result.category_counts) > 0

    def test_no_risk_metadata_pro(self, pro_tier, temp_project_with_symbol):
        """Pro tier does NOT enable impact analysis (Enterprise feature)."""
        result = _get_symbol_references_sync(
            "process_data",
            str(temp_project_with_symbol),
            max_files=None,
            max_references=None,
            enable_categorization=True,
            enable_impact_analysis=False,
            tier="pro",
        )

        # Pro tier without impact analysis should not have risk metadata
        assert result.risk_score is None
        assert result.blast_radius is None


class TestGetSymbolReferencesEnterpriseTier:
    """Enterprise tier: Unlimited files/references, risk scoring, CODEOWNERS integration."""

    def test_tier_applied_is_enterprise(self, enterprise_tier, temp_project_with_symbol):
        """Enterprise tier should be applied."""
        result = _get_symbol_references_sync(
            "process_data",
            str(temp_project_with_symbol),
            max_files=None,
            max_references=None,
            enable_categorization=True,
            enable_codeowners=True,
            enable_impact_analysis=True,
            tier="enterprise",
        )

        assert result.tier_applied == "enterprise"

    def test_max_files_unlimited_enterprise(self, enterprise_tier, temp_project_with_symbol):
        """Enterprise tier has unlimited file search."""
        result = _get_symbol_references_sync(
            "process_data",
            str(temp_project_with_symbol),
            max_files=None,
            max_references=None,
            enable_categorization=True,
            enable_codeowners=True,
            enable_impact_analysis=True,
            tier="enterprise",
        )

        assert result.max_files_applied is None

    def test_max_references_unlimited_enterprise(self, enterprise_tier, temp_project_with_symbol):
        """Enterprise tier has unlimited references."""
        result = _get_symbol_references_sync(
            "process_data",
            str(temp_project_with_symbol),
            max_files=None,
            max_references=None,
            enable_categorization=True,
            enable_codeowners=True,
            enable_impact_analysis=True,
            tier="enterprise",
        )

        assert result.max_references_applied is None

    def test_category_counts_enterprise(self, enterprise_tier, temp_project_with_symbol):
        """Enterprise tier inherits Pro features including categorization."""
        result = _get_symbol_references_sync(
            "process_data",
            str(temp_project_with_symbol),
            max_files=None,
            max_references=None,
            enable_categorization=True,
            enable_codeowners=True,
            enable_impact_analysis=True,
            tier="enterprise",
        )

        # Enterprise tier should have categorization (Pro+ feature)
        assert result.category_counts is not None
        assert isinstance(result.category_counts, dict)

    def test_risk_metadata_populated(self, enterprise_tier, temp_project_with_symbol):
        """Enterprise tier with impact analysis populates risk_score and blast_radius."""
        result = _get_symbol_references_sync(
            "process_data",
            str(temp_project_with_symbol),
            max_files=None,
            max_references=None,
            enable_categorization=True,
            enable_codeowners=True,
            enable_impact_analysis=True,
            tier="enterprise",
        )

        # Enterprise tier with impact analysis should populate risk metadata
        assert result.risk_score is not None
        assert isinstance(result.risk_score, int)
        assert result.blast_radius is not None
        assert isinstance(result.blast_radius, int)

    def test_codeowners_support(self, enterprise_tier, temp_project_with_symbol):
        """Enterprise tier supports CODEOWNERS-based ownership attribution."""
        # Create CODEOWNERS file
        codeowners_path = temp_project_with_symbol / ".github"
        codeowners_path.mkdir(exist_ok=True)
        (codeowners_path / "CODEOWNERS").write_text("""# Code ownership
* @default-owner
main.py @main-owner
handler.py @handler-owner
""")

        result = _get_symbol_references_sync(
            "process_data",
            str(temp_project_with_symbol),
            max_files=None,
            max_references=None,
            enable_categorization=True,
            enable_codeowners=True,
            enable_impact_analysis=True,
            tier="enterprise",
        )

        # Enterprise tier with CODEOWNERS should populate owner_counts
        assert result.owner_counts is not None
        assert isinstance(result.owner_counts, dict)
        # Should have at least one owner
        assert len(result.owner_counts) > 0

    def test_references_have_owners(self, enterprise_tier, temp_project_with_symbol):
        """Enterprise references should include owner information from CODEOWNERS."""
        # Create CODEOWNERS file
        codeowners_path = temp_project_with_symbol / ".github"
        codeowners_path.mkdir(exist_ok=True)
        (codeowners_path / "CODEOWNERS").write_text("""# Code ownership
* @default-owner
main.py @main-owner
""")

        result = _get_symbol_references_sync(
            "process_data",
            str(temp_project_with_symbol),
            max_files=None,
            max_references=None,
            enable_categorization=True,
            enable_codeowners=True,
            enable_impact_analysis=True,
            tier="enterprise",
        )

        # Enterprise with CODEOWNERS should populate owners field in references
        if result.success and result.references:
            # At least some references should have owners populated
            with_owners = [ref for ref in result.references if ref.owners]
            assert len(with_owners) > 0


class TestGetSymbolReferencesAsyncInterface:
    """Test async interface for get_symbol_references."""

    @pytest.mark.asyncio
    async def test_async_interface_works(self, pro_tier, temp_project_with_symbol):
        """Async interface should work and return results."""
        from code_scalpel.mcp.helpers.context_helpers import (
            get_symbol_references,
        )

        result = await get_symbol_references("process_data", str(temp_project_with_symbol))

        # Verify we got a result with expected structure
        assert result is not None
        assert result.symbol_name == "process_data"
        assert result.tier_applied is not None
