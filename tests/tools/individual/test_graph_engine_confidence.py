"""
Tests for confidence scoring engine.

[20251216_FEATURE] v2.1.0 - Test confidence scoring for graph edges
"""

from code_scalpel.graph_engine.confidence import (
    CONFIDENCE_RULES,
    ConfidenceEngine,
    ConfidenceEvidence,
    ConfidenceLevel,
    EdgeType,
)


class TestConfidenceRules:
    """Tests for CONFIDENCE_RULES constant."""

    def test_definite_relationships_have_score_1_0(self):
        """Test that definite relationships have maximum confidence."""
        assert CONFIDENCE_RULES[EdgeType.IMPORT_STATEMENT] == 1.0
        assert CONFIDENCE_RULES[EdgeType.TYPE_ANNOTATION] == 1.0
        assert CONFIDENCE_RULES[EdgeType.INHERITANCE] == 1.0

    def test_high_confidence_relationships(self):
        """Test high confidence relationships."""
        assert 0.8 <= CONFIDENCE_RULES[EdgeType.ROUTE_EXACT_MATCH] <= 1.0
        assert 0.8 <= CONFIDENCE_RULES[EdgeType.ROUTE_PATTERN_MATCH] <= 1.0

    def test_medium_confidence_relationships(self):
        """Test medium confidence relationships."""
        assert 0.5 <= CONFIDENCE_RULES[EdgeType.STRING_LITERAL_MATCH] < 0.8

    def test_low_confidence_relationships(self):
        """Test low confidence relationships."""
        assert 0.3 <= CONFIDENCE_RULES[EdgeType.DYNAMIC_ROUTE] < 0.8


class TestConfidenceLevel:
    """Tests for ConfidenceLevel enum."""

    def test_all_levels_defined(self):
        """Test all confidence levels are defined."""
        levels = [
            ConfidenceLevel.DEFINITE,
            ConfidenceLevel.HIGH,
            ConfidenceLevel.MEDIUM,
            ConfidenceLevel.LOW,
            ConfidenceLevel.UNCERTAIN,
        ]

        assert all(isinstance(level, ConfidenceLevel) for level in levels)


class TestConfidenceEngine:
    """Tests for ConfidenceEngine class."""

    def test_init_default_threshold(self):
        """Test initialization with default threshold."""
        engine = ConfidenceEngine()
        assert engine.min_threshold == 0.8

    def test_init_custom_threshold(self):
        """Test initialization with custom threshold."""
        engine = ConfidenceEngine(min_threshold=0.6)
        assert engine.min_threshold == 0.6

    def test_score_import_statement(self):
        """Test scoring an import statement (definite)."""
        engine = ConfidenceEngine()
        evidence = engine.score_edge(EdgeType.IMPORT_STATEMENT, {})

        assert evidence.final_score == 1.0
        assert evidence.edge_type == EdgeType.IMPORT_STATEMENT
        assert isinstance(evidence.explanation, str)

    def test_score_type_annotation(self):
        """Test scoring a type annotation (definite)."""
        engine = ConfidenceEngine()
        evidence = engine.score_edge(EdgeType.TYPE_ANNOTATION, {})

        assert evidence.final_score == 1.0

    def test_score_route_exact_match(self):
        """Test scoring an exact route match."""
        engine = ConfidenceEngine()
        context = {"route_match": "exact"}
        evidence = engine.score_edge(EdgeType.HTTP_CALL, context)

        # Should be high confidence with exact match adjustment
        assert evidence.final_score >= 0.9
        assert "exact_route_match" in evidence.adjustments

    def test_score_route_pattern_match(self):
        """Test scoring a pattern route match."""
        engine = ConfidenceEngine()
        context = {"route_match": "pattern"}
        evidence = engine.score_edge(EdgeType.HTTP_CALL, context)

        # Should be high confidence but less than exact
        assert 0.7 <= evidence.final_score <= 0.95

    def test_score_dynamic_route(self):
        """Test scoring a dynamic route."""
        engine = ConfidenceEngine()
        context = {"route_match": "dynamic"}
        evidence = engine.score_edge(EdgeType.HTTP_CALL, context)

        # Should be medium confidence
        assert evidence.final_score < 0.8

    def test_score_with_typed_client(self):
        """Test that typed clients increase confidence."""
        engine = ConfidenceEngine()
        context = {"route_match": "exact", "typed_client": True}
        evidence = engine.score_edge(EdgeType.HTTP_CALL, context)

        # Should have typed_client adjustment
        assert "typed_client" in evidence.adjustments
        assert evidence.adjustments["typed_client"] > 0

    def test_score_string_match_with_long_string(self):
        """Test that longer strings increase confidence."""
        engine = ConfidenceEngine()
        context = {"string_length": 30}
        evidence = engine.score_edge(EdgeType.STRING_LITERAL_MATCH, context)

        # Should have long_string adjustment
        assert "long_string" in evidence.adjustments

    def test_score_string_match_with_url_pattern(self):
        """Test that URL patterns increase confidence."""
        engine = ConfidenceEngine()
        context = {"is_url_pattern": True}
        evidence = engine.score_edge(EdgeType.STRING_LITERAL_MATCH, context)

        # Should have url_pattern adjustment
        assert "url_pattern" in evidence.adjustments

    def test_score_clamped_to_valid_range(self):
        """Test that scores are clamped to [0.0, 1.0]."""
        engine = ConfidenceEngine()

        # Try to push score above 1.0
        context = {"route_match": "exact", "typed_client": True}
        evidence = engine.score_edge(EdgeType.HTTP_CALL, context)

        assert 0.0 <= evidence.final_score <= 1.0

    def test_get_confidence_level_definite(self):
        """Test getting DEFINITE level."""
        engine = ConfidenceEngine()
        level = engine.get_confidence_level(1.0)
        assert level == ConfidenceLevel.DEFINITE

    def test_get_confidence_level_high(self):
        """Test getting HIGH level."""
        engine = ConfidenceEngine()
        level = engine.get_confidence_level(0.85)
        assert level == ConfidenceLevel.HIGH

    def test_get_confidence_level_medium(self):
        """Test getting MEDIUM level."""
        engine = ConfidenceEngine()
        level = engine.get_confidence_level(0.65)
        assert level == ConfidenceLevel.MEDIUM

    def test_get_confidence_level_low(self):
        """Test getting LOW level."""
        engine = ConfidenceEngine()
        level = engine.get_confidence_level(0.4)
        assert level == ConfidenceLevel.LOW

    def test_get_confidence_level_uncertain(self):
        """Test getting UNCERTAIN level."""
        engine = ConfidenceEngine()
        level = engine.get_confidence_level(0.2)
        assert level == ConfidenceLevel.UNCERTAIN

    def test_requires_human_approval_below_threshold(self):
        """Test that scores below threshold require approval."""
        engine = ConfidenceEngine(min_threshold=0.8)
        assert engine.requires_human_approval(0.7) is True

    def test_requires_human_approval_above_threshold(self):
        """Test that scores above threshold don't require approval."""
        engine = ConfidenceEngine(min_threshold=0.8)
        assert engine.requires_human_approval(0.9) is False

    def test_requires_human_approval_at_threshold(self):
        """Test that scores at threshold don't require approval."""
        engine = ConfidenceEngine(min_threshold=0.8)
        assert engine.requires_human_approval(0.8) is False


class TestConfidenceEvidence:
    """Tests for ConfidenceEvidence dataclass."""

    def test_to_dict(self):
        """Test converting evidence to dictionary."""
        evidence = ConfidenceEvidence(
            edge_type=EdgeType.IMPORT_STATEMENT,
            base_score=1.0,
            adjustments={},
            final_score=1.0,
            explanation="Base: import_statement | Level: definite",
        )

        d = evidence.to_dict()
        assert d["edge_type"] == "import_statement"
        assert d["base_score"] == 1.0
        assert d["final_score"] == 1.0
        assert "explanation" in d


class TestRouteMatchScoring:
    """Tests for route matching confidence scoring."""

    def test_exact_route_match_increases_confidence(self):
        """Test that exact route matches get high confidence."""
        engine = ConfidenceEngine()
        context = {"exact_match": True}
        evidence = engine.score_edge(EdgeType.ROUTE_PATTERN_MATCH, context)

        # Should have adjustment for exact match
        assert "exact_string" in evidence.adjustments
        assert evidence.final_score > 0.8

    def test_multiple_matches_decrease_confidence(self):
        """Test that multiple matches decrease confidence."""
        engine = ConfidenceEngine()
        context = {"match_count": 3}
        evidence = engine.score_edge(EdgeType.ROUTE_PATTERN_MATCH, context)

        # Should have negative adjustment for multiple matches
        assert "multiple_matches" in evidence.adjustments
        assert evidence.adjustments["multiple_matches"] < 0

    def test_single_match_no_penalty(self):
        """Test that single match has no penalty."""
        engine = ConfidenceEngine()
        context = {"match_count": 1}
        evidence = engine.score_edge(EdgeType.ROUTE_PATTERN_MATCH, context)

        # Should not have multiple_matches adjustment
        assert "multiple_matches" not in evidence.adjustments


class TestExplanationBuilding:
    """Tests for explanation string building."""

    def test_explanation_includes_edge_type(self):
        """Test that explanation includes edge type."""
        engine = ConfidenceEngine()
        evidence = engine.score_edge(EdgeType.IMPORT_STATEMENT, {})

        assert "import_statement" in evidence.explanation

    def test_explanation_includes_level(self):
        """Test that explanation includes confidence level."""
        engine = ConfidenceEngine()
        evidence = engine.score_edge(EdgeType.IMPORT_STATEMENT, {})

        assert "definite" in evidence.explanation.lower()

    def test_explanation_includes_adjustments(self):
        """Test that explanation includes adjustments when present."""
        engine = ConfidenceEngine()
        context = {"route_match": "exact"}
        evidence = engine.score_edge(EdgeType.HTTP_CALL, context)

        # Should mention adjustments
        assert "Adjustments" in evidence.explanation or "exact_route_match" in str(evidence.adjustments)
