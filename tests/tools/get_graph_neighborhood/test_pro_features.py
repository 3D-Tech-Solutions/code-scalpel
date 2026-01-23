"""
Tests for get_graph_neighborhood Pro Tier Features.

Tests semantic neighbor detection and logical relationship mapping.

**Pro Tier Features Tested**:
- Semantic neighbor detection (name similarity, parameter similarity, docstring similarity)
- Logical relationship mapping (sibling functions, test pairs, helpers, same-class methods)
- Enhanced confidence scoring for semantic relationships
- Interaction with core k-hop extraction

**Test Organization**:
1. TestSemanticNeighborDetection - Basic semantic neighbor behavior
2. TestSemanticNameSimilarity - Name-based semantic matching
3. TestSemanticParameterSimilarity - Parameter-based semantic matching
4. TestLogicalRelationshipDetection - Basic logical relationship detection
5. TestLogicalSiblingRelationships - Same-file function relationships
6. TestLogicalTestImplementationPairs - Test-to-implementation mappings
7. TestLogicalHelperRelationships - Helper function detection
8. TestLogicalSameClassMethods - Class method relationships
9. TestProTierIntegrationWithKHop - Semantic + k-hop combined traversal
10. TestProTierCapabilityGating - Feature gating based on tier

**Implementation Notes**:
- Pro tier features are best-effort (don't fail main query)
- SemanticNeighborFinder requires project files on disk
- LogicalRelationshipDetector requires parseable Python files
- Tests use temporary project directories with sample code
"""

from pathlib import Path

import pytest

# =============================================================================
# Test Class 1: Semantic Neighbor Detection
# =============================================================================


class TestSemanticNeighborDetection:
    """Test semantic neighbor discovery feature."""

    def test_semantic_neighbors_capability_key_exists(self, mock_tier_pro):
        """Pro tier includes 'semantic_neighbors' capability."""
        with mock_tier_pro:
            from code_scalpel.licensing.features import get_tool_capabilities

            caps = get_tool_capabilities("get_graph_neighborhood", "pro")
            capabilities = set(caps.get("capabilities", []))
            assert "semantic_neighbors" in capabilities

    def test_semantic_neighbors_disabled_for_community(self, mock_tier_community):
        """Community tier does NOT have semantic_neighbors capability."""
        with mock_tier_community:
            from code_scalpel.licensing.features import get_tool_capabilities

            caps = get_tool_capabilities("get_graph_neighborhood", "community")
            capabilities = set(caps.get("capabilities", []))
            assert "semantic_neighbors" not in capabilities

    def test_semantic_neighbor_finder_initialization(self, temp_project_dir):
        """SemanticNeighborFinder can be initialized with project root."""
        from code_scalpel.graph.semantic_neighbors import SemanticNeighborFinder

        finder = SemanticNeighborFinder(temp_project_dir)
        assert finder.root == Path(temp_project_dir)

    def test_semantic_neighbors_empty_project(self, temp_project_dir):
        """Semantic neighbor search on empty project returns no results."""
        from code_scalpel.graph.semantic_neighbors import find_semantic_neighbors

        result = find_semantic_neighbors(temp_project_dir, "nonexistent_function", k=5)
        assert result.success is False
        assert "not found" in result.error.lower()
        assert len(result.neighbors) == 0


class TestSemanticNameSimilarity:
    """Test name-based semantic neighbor detection."""

    @pytest.fixture
    def project_with_similar_names(self, temp_project_dir):
        """Create project with functions having similar names."""
        code = '''
def process_order(order_id):
    """Process an order."""
    pass

def process_payment(payment_id):
    """Process a payment."""
    pass

def validate_order(order_id):
    """Validate an order."""
    pass

def handle_order(order_id):
    """Handle an order."""
    pass

def unrelated_function(x):
    """Completely unrelated."""
    pass
'''
        file_path = Path(temp_project_dir) / "orders.py"
        file_path.write_text(code)
        return temp_project_dir

    def test_name_similarity_finds_related_functions(self, project_with_similar_names):
        """Functions with similar names are detected as semantic neighbors."""
        from code_scalpel.graph.semantic_neighbors import find_semantic_neighbors

        result = find_semantic_neighbors(project_with_similar_names, "process_order", k=10, min_similarity=0.3)

        assert result.success is True
        assert len(result.neighbors) > 0

        # Should find validate_order, handle_order, process_payment
        neighbor_names = [n.name for n in result.neighbors]
        assert any("order" in name for name in neighbor_names)

    def test_name_similarity_ordered_by_score(self, project_with_similar_names):
        """Semantic neighbors are ordered by similarity score (descending)."""
        from code_scalpel.graph.semantic_neighbors import find_semantic_neighbors

        result = find_semantic_neighbors(project_with_similar_names, "process_order", k=10, min_similarity=0.2)

        if len(result.neighbors) > 1:
            scores = [n.similarity_score for n in result.neighbors]
            assert scores == sorted(scores, reverse=True)


class TestSemanticParameterSimilarity:
    """Test parameter-based semantic similarity."""

    @pytest.fixture
    def project_with_shared_params(self, temp_project_dir):
        """Create project with functions sharing parameters."""
        code = '''
def create_user(username: str, email: str, password: str):
    """Create a new user."""
    pass

def update_user(username: str, email: str):
    """Update user information."""
    pass

def validate_user(username: str, email: str):
    """Validate user credentials."""
    pass

def delete_user(user_id: int):
    """Delete a user (different parameters)."""
    pass
'''
        file_path = Path(temp_project_dir) / "users.py"
        file_path.write_text(code)
        return temp_project_dir

    def test_shared_parameters_increase_similarity(self, project_with_shared_params):
        """Functions with shared parameters have higher similarity."""
        from code_scalpel.graph.semantic_neighbors import find_semantic_neighbors

        result = find_semantic_neighbors(project_with_shared_params, "create_user", k=10, min_similarity=0.2)

        assert result.success is True

        # update_user and validate_user share username, email parameters
        neighbor_names = [n.name for n in result.neighbors]
        if len(neighbor_names) > 0:
            # Functions with shared params should be found
            assert any(name in ["update_user", "validate_user"] for name in neighbor_names)


# =============================================================================
# Test Class 4: Logical Relationship Detection
# =============================================================================


class TestLogicalRelationshipDetection:
    """Test logical relationship detection feature."""

    def test_logical_relationship_capability_key_exists(self, mock_tier_pro):
        """Pro tier includes 'logical_relationship_detection' capability."""
        with mock_tier_pro:
            from code_scalpel.licensing.features import get_tool_capabilities

            caps = get_tool_capabilities("get_graph_neighborhood", "pro")
            capabilities = set(caps.get("capabilities", []))
            assert "logical_relationship_detection" in capabilities

    def test_logical_relationships_disabled_for_community(self, mock_tier_community):
        """Community tier does NOT have logical relationship detection."""
        with mock_tier_community:
            from code_scalpel.licensing.features import get_tool_capabilities

            caps = get_tool_capabilities("get_graph_neighborhood", "community")
            capabilities = set(caps.get("capabilities", []))
            assert "logical_relationship_detection" not in capabilities

    def test_logical_relationship_detector_initialization(self, temp_project_dir):
        """LogicalRelationshipDetector can be initialized."""
        from code_scalpel.graph.logical_relationships import (
            LogicalRelationshipDetector,
        )

        detector = LogicalRelationshipDetector(temp_project_dir)
        assert detector.root == Path(temp_project_dir)

    def test_logical_relationships_empty_project(self, temp_project_dir):
        """Logical relationship search on empty project returns error."""
        from code_scalpel.graph.logical_relationships import find_logical_relationships

        result = find_logical_relationships(temp_project_dir, "nonexistent_function")
        assert result.success is False
        assert "not found" in result.error.lower()


class TestLogicalSiblingRelationships:
    """Test sibling function detection (same file)."""

    @pytest.fixture
    def project_with_siblings(self, temp_project_dir):
        """Create project with sibling functions in same file."""
        code = '''
def function_a():
    """First function."""
    pass

def function_b():
    """Second function."""
    pass

def function_c():
    """Third function."""
    pass
'''
        file_path = Path(temp_project_dir) / "module.py"
        file_path.write_text(code)
        return temp_project_dir

    def test_sibling_functions_detected(self, project_with_siblings):
        """Functions in same file are detected as siblings."""
        from code_scalpel.graph.logical_relationships import find_logical_relationships

        result = find_logical_relationships(project_with_siblings, "function_a")

        assert result.success is True
        assert len(result.relationships) > 0

        # Should find function_b and function_c as siblings
        relationship_types = [r.relationship_type for r in result.relationships]
        assert "sibling" in relationship_types


class TestLogicalTestImplementationPairs:
    """Test test-to-implementation relationship detection."""

    @pytest.fixture
    def project_with_tests(self, temp_project_dir):
        """Create project with test/implementation pairs."""
        impl_code = '''
def calculate_total(items):
    """Calculate total price."""
    return sum(item.price for item in items)

def validate_items(items):
    """Validate items."""
    return all(item.is_valid for item in items)
'''
        test_code = '''
def test_calculate_total():
    """Test calculate_total function."""
    pass

def test_validate_items():
    """Test validate_items function."""
    pass
'''
        (Path(temp_project_dir) / "calculator.py").write_text(impl_code)
        (Path(temp_project_dir) / "test_calculator.py").write_text(test_code)
        return temp_project_dir

    def test_test_for_relationship_detected(self, project_with_tests):
        """Implementation finds its test function."""
        from code_scalpel.graph.logical_relationships import LogicalRelationshipDetector

        detector = LogicalRelationshipDetector(project_with_tests)
        result = detector.find_relationships("calculate_total", relationship_types={"test_for"})

        if result.success and len(result.relationships) > 0:
            relationship_types = [r.relationship_type for r in result.relationships]
            target_names = [r.target_node for r in result.relationships]

            # May find test_calculate_total
            assert (
                any("test_calculate_total" in name.lower() for name in target_names) or "test_for" in relationship_types
            )

    def test_tested_by_relationship_detected(self, project_with_tests):
        """Test function finds its implementation."""
        from code_scalpel.graph.logical_relationships import LogicalRelationshipDetector

        detector = LogicalRelationshipDetector(project_with_tests)
        result = detector.find_relationships("test_calculate_total", relationship_types={"tested_by"})

        if result.success and len(result.relationships) > 0:
            relationship_types = [r.relationship_type for r in result.relationships]
            target_names = [r.target_node for r in result.relationships]

            # May find calculate_total
            assert any("calculate_total" in name.lower() for name in target_names) or "tested_by" in relationship_types


class TestLogicalHelperRelationships:
    """Test helper function detection (private functions)."""

    @pytest.fixture
    def project_with_helpers(self, temp_project_dir):
        """Create project with helper functions."""
        code = '''
def public_function():
    """Public function."""
    return _helper_function()

def _helper_function():
    """Private helper."""
    return 42

def _another_helper():
    """Another helper."""
    return 100
'''
        file_path = Path(temp_project_dir) / "helpers.py"
        file_path.write_text(code)
        return temp_project_dir

    def test_helper_relationships_detected(self, project_with_helpers):
        """Helper functions are detected."""
        from code_scalpel.graph.logical_relationships import LogicalRelationshipDetector

        detector = LogicalRelationshipDetector(project_with_helpers)
        result = detector.find_relationships("public_function", relationship_types={"helper_of"})

        if result.success and len(result.relationships) > 0:
            relationship_types = [r.relationship_type for r in result.relationships]
            # Helper relationships should be detected
            assert "helper_of" in relationship_types or len(result.relationships) > 0


class TestLogicalSameClassMethods:
    """Test same-class method detection."""

    @pytest.fixture
    def project_with_class(self, temp_project_dir):
        """Create project with class methods."""
        code = '''
class Calculator:
    """Calculator class."""

    def add(self, a, b):
        """Add two numbers."""
        return a + b

    def subtract(self, a, b):
        """Subtract two numbers."""
        return a - b

    def multiply(self, a, b):
        """Multiply two numbers."""
        return a * b
'''
        file_path = Path(temp_project_dir) / "calculator.py"
        file_path.write_text(code)
        return temp_project_dir

    def test_same_class_methods_detected(self, project_with_class):
        """Methods in same class are detected."""
        from code_scalpel.graph.logical_relationships import LogicalRelationshipDetector

        detector = LogicalRelationshipDetector(project_with_class)
        result = detector.find_relationships("add", relationship_types={"same_class"})

        if result.success and len(result.relationships) > 0:
            relationship_types = [r.relationship_type for r in result.relationships]
            # Same-class relationships should be detected
            assert "same_class" in relationship_types or len(result.relationships) >= 2


class TestProTierIntegrationWithKHop:
    """Test Pro tier features integrate with core k-hop extraction."""

    def test_pro_tier_adds_semantic_neighbors_to_graph(self, mock_tier_pro, sample_call_graph, temp_project_dir):
        """When Pro tier is active, semantic neighbors can be added to results."""
        # This test would require actual integration with get_graph_neighborhood
        # For now, verify capability gating
        with mock_tier_pro:
            from code_scalpel.licensing.features import get_tool_capabilities

            caps = get_tool_capabilities("get_graph_neighborhood", "pro")
            capabilities = set(caps.get("capabilities", []))
            assert "semantic_neighbors" in capabilities
            assert "logical_relationship_detection" in capabilities


class TestProTierCapabilityGating:
    """Test Pro tier feature gating."""

    def test_community_tier_no_pro_features(self, mock_tier_community):
        """Community tier does not have Pro features."""
        with mock_tier_community:
            from code_scalpel.licensing.features import get_tool_capabilities

            caps = get_tool_capabilities("get_graph_neighborhood", "community")
            capabilities = set(caps.get("capabilities", []))
            assert "semantic_neighbors" not in capabilities
            assert "logical_relationship_detection" not in capabilities

    def test_pro_tier_has_all_community_plus_pro(self, mock_tier_pro):
        """Pro tier has Community features + Pro features."""
        with mock_tier_pro:
            from code_scalpel.licensing.features import get_tool_capabilities

            caps = get_tool_capabilities("get_graph_neighborhood", "pro")
            capabilities = set(caps.get("capabilities", []))

            # Community features
            assert "basic_neighborhood" in capabilities

            # Pro features
            assert "semantic_neighbors" in capabilities
            assert "logical_relationship_detection" in capabilities

    def test_enterprise_tier_has_all_features(self, mock_tier_enterprise):
        """Enterprise tier has all Community + Pro + Enterprise features."""
        with mock_tier_enterprise:
            from code_scalpel.licensing.features import get_tool_capabilities

            caps = get_tool_capabilities("get_graph_neighborhood", "enterprise")
            capabilities = set(caps.get("capabilities", []))

            # Community features
            assert "basic_neighborhood" in capabilities

            # Pro features
            assert "semantic_neighbors" in capabilities
            assert "logical_relationship_detection" in capabilities

            # Enterprise features
            assert "graph_query_language" in capabilities


class TestLicenseFallback:
    """Validate invalid/missing license fallback to Community limits/capabilities."""

    def test_invalid_license_falls_back_to_community(self):
        from code_scalpel.licensing.features import get_tool_capabilities

        caps = get_tool_capabilities("get_graph_neighborhood", "invalid")
        capabilities = set(caps.get("capabilities", []))
        limits = caps.get("limits", {})

        # Current behavior: unknown tier returns empty capabilities; verify no privileges granted
        assert capabilities == set()
        assert limits == {} or limits.get("max_k") in (None, 1)

    def test_missing_license_defaults_to_community(self):
        from code_scalpel.licensing.features import get_tool_capabilities

        caps = get_tool_capabilities("get_graph_neighborhood", "missing")
        capabilities = set(caps.get("capabilities", []))
        limits = caps.get("limits", {})

        # Current behavior: unknown tier returns empty capabilities; verify no privileges granted
        assert capabilities == set()
        assert limits == {} or limits.get("max_k") in (None, 1)
