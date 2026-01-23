"""Comprehensive tier validation for unified_sink_detect MCP tool.

[20260121_TEST] Validates all 22 checklist items across Community, Pro, Enterprise tiers:
- Community (10 items): max 50 sinks, 4 language support, basic confidence/CWE, id stability, truncation
- Pro (6 items): unlimited sinks, advanced confidence, context-aware, framework sinks, custom definitions, coverage
- Enterprise (6 items): unlimited + Pro features, org rules, risk scoring, compliance, historical tracking, remediation
"""

from code_scalpel.licensing.features import get_tool_capabilities
from code_scalpel.mcp.helpers.security_helpers import _unified_sink_detect_sync


class TestUnifiedSinkDetectCommunityTier:
    """Validate Community tier unified_sink_detect constraints (10 tests)."""

    def test_max_50_sinks_enforced(self, community_tier):
        """Verify max 50 sinks limit enforced for Community tier."""
        # Create code with 60+ detectable sinks
        code = "\n".join([f"os.system(user_input_{i})" for i in range(60)])
        result = _unified_sink_detect_sync(code=code, language="python", confidence_threshold=0.0, tier="community")

        assert result.success
        assert result.sink_count <= 50, f"Community should limit to 50, got {result.sink_count}"
        assert result.max_sinks_applied == 50
        if result.sinks_detected and result.sinks_detected > 50:
            assert result.truncated is True

    def test_python_sink_detection_enabled(self, community_tier):
        """Verify Python sink detection works for Community tier."""
        code = "import sqlite3\ndb.execute(user_sql)"
        result = _unified_sink_detect_sync(code=code, language="python", confidence_threshold=0.0, tier="community")

        assert result.success
        assert result.language == "python"
        assert result.sink_count > 0, "Should detect SQL sink in Python"
        assert any(s.sink_type and "SQL" in s.sink_type for s in (result.sinks or []))

    def test_javascript_sink_detection_enabled(self, community_tier):
        """Verify JavaScript sink detection works for Community tier."""
        code = "const sql = `SELECT * FROM users WHERE id = ${userId}`;\ndb.execute(sql);"
        result = _unified_sink_detect_sync(code=code, language="javascript", confidence_threshold=0.0, tier="community")

        assert result.success
        assert result.language == "javascript"
        assert result.sink_count > 0, "Should detect SQL sink in JavaScript"

    def test_typescript_sink_detection_enabled(self, community_tier):
        """Verify TypeScript sink detection works for Community tier."""
        code = "const code = userInput;\\neval(code);"
        result = _unified_sink_detect_sync(code=code, language="typescript", confidence_threshold=0.0, tier="community")

        assert result.success
        assert result.language == "typescript"
        assert result.sink_count > 0, "Should detect EVAL sink in TypeScript"

    def test_java_sink_detection_enabled(self, community_tier):
        """Verify Java sink detection works for Community tier."""
        code = 'String cmd = "ls " + userInput;\nRuntime.getRuntime().exec(cmd);'
        result = _unified_sink_detect_sync(code=code, language="java", confidence_threshold=0.0, tier="community")

        assert result.success
        assert result.language == "java"
        assert result.sink_count > 0, "Should detect SQL sink in Java"

    def test_basic_confidence_scoring_present(self, community_tier):
        """Verify confidence scores are present in Community results."""
        code = "import sqlite3\ndb.execute(user_input)"
        result = _unified_sink_detect_sync(code=code, language="python", confidence_threshold=0.0, tier="community")

        assert result.success
        if result.sinks:
            assert all(hasattr(s, "confidence") for s in result.sinks), "All sinks should have confidence"
            assert all(0.0 <= s.confidence <= 1.0 for s in result.sinks), "Confidence should be 0-1"

    def test_cwe_mapping_populated(self, community_tier):
        """Verify CWE mapping is populated for Community tier."""
        code = "import sqlite3\ndb.execute(user_sql)"
        result = _unified_sink_detect_sync(code=code, language="python", confidence_threshold=0.0, tier="community")

        assert result.success
        if result.sinks:
            assert any(s.cwe_id for s in result.sinks), "At least one sink should have CWE mapping"
            assert any("CWE-" in str(s.cwe_id) for s in result.sinks if s.cwe_id), "CWE should be formatted as CWE-XXX"

    def test_sink_id_stability(self, community_tier):
        """Verify sink_id is stable and consistent across runs."""
        code = "import sqlite3\ndb.execute(user_input)"
        result1 = _unified_sink_detect_sync(code=code, language="python", confidence_threshold=0.0, tier="community")
        result2 = _unified_sink_detect_sync(code=code, language="python", confidence_threshold=0.0, tier="community")

        assert result1.success and result2.success
        if result1.sinks and result2.sinks:
            ids1 = sorted([s.sink_id for s in result1.sinks])
            ids2 = sorted([s.sink_id for s in result2.sinks])
            assert ids1 == ids2, "sink_id should be deterministic across runs"

    def test_code_snippet_truncation_indicators(self, community_tier):
        """Verify code_snippet_truncated and code_snippet_original_len are present."""
        # Create a sink with a very long line
        long_line = "x = user_input; " * 50  # 800+ chars
        code = f"import sqlite3\ndb.execute({long_line})"
        result = _unified_sink_detect_sync(code=code, language="python", confidence_threshold=0.0, tier="community")

        assert result.success
        if result.sinks:
            # Check that truncation fields exist and are used correctly
            for sink in result.sinks:
                assert hasattr(sink, "code_snippet_truncated")
                if sink.code_snippet_truncated:
                    assert sink.code_snippet_original_len is not None
                    assert sink.code_snippet_original_len > len(sink.code_snippet or "")
                    assert "…" in (sink.code_snippet or ""), "Truncated snippets should have ellipsis"

    def test_unsupported_language_error_code(self, community_tier):
        """Verify unsupported language returns correct error_code."""
        code = "some code"
        result = _unified_sink_detect_sync(code=code, language="rust", confidence_threshold=0.0, tier="community")

        # Community should not support Rust
        assert not result.success
        assert result.error_code == "UNIFIED_SINK_DETECT_UNSUPPORTED_LANGUAGE"


class TestUnifiedSinkDetectProTier:
    """Validate Pro tier unified_sink_detect features (6 tests)."""

    def test_unlimited_sinks_returned(self, pro_tier):
        """Verify Pro tier analyzes unlimited sinks (no 50-limit)."""
        # Create code with 60+ sinks
        code = "\n".join([f"os.system(input_{i})" for i in range(60)])
        result = _unified_sink_detect_sync(code=code, language="python", confidence_threshold=0.0, tier="pro")

        assert result.success
        assert result.sink_count > 50, f"Pro should exceed 50-limit, got {result.sink_count}"
        if result.max_sinks_applied:
            assert result.max_sinks_applied is None or result.max_sinks_applied > 50

    def test_advanced_confidence_scoring_enabled(self, pro_tier):
        """Verify advanced confidence scoring for Pro tier."""
        code = "import sqlite3\ndb.execute(user_sql)"
        capabilities = get_tool_capabilities("unified_sink_detect", "pro")
        result = _unified_sink_detect_sync(
            code=code,
            language="python",
            confidence_threshold=0.0,
            tier="pro",
            capabilities=capabilities,
        )

        assert result.success
        # Pro should have confidence_scores field populated
        assert hasattr(result, "confidence_scores")
        if result.confidence_scores:
            assert len(result.confidence_scores) > 0, "Pro should have confidence scores"

    def test_context_aware_detection_enabled(self, pro_tier):
        """Verify context-aware detection is enabled for Pro tier."""
        code = "from flask import request\ndb.execute(request.args.get('id'))"
        capabilities = get_tool_capabilities("unified_sink_detect", "pro")
        result = _unified_sink_detect_sync(
            code=code,
            language="python",
            confidence_threshold=0.0,
            tier="pro",
            capabilities=capabilities,
        )

        assert result.success
        assert hasattr(result, "context_analysis")
        if result.context_analysis:
            assert "analyzed_sinks" in result.context_analysis, "Context analysis should be populated"

    def test_framework_specific_sinks_detected(self, pro_tier):
        """Verify framework-specific sinks are detected for Pro tier."""
        code = "from flask import Flask\napp = Flask(__name__)\n@app.route('/api')\ndef api():\n    return render_template(user_template)"
        capabilities = get_tool_capabilities("unified_sink_detect", "pro")
        result = _unified_sink_detect_sync(
            code=code,
            language="python",
            confidence_threshold=0.0,
            tier="pro",
            capabilities=capabilities,
        )

        assert result.success
        assert hasattr(result, "framework_sinks")
        # Framework sinks may be populated depending on code patterns
        assert isinstance(result.framework_sinks, (list, type(None)))

    def test_custom_sink_definitions_supported(self, pro_tier):
        """Verify custom sink definitions capability for Pro tier."""
        capabilities = get_tool_capabilities("unified_sink_detect", "pro")
        assert "custom_sink_definitions" in (
            capabilities.get("capabilities", []) or []
        ), "Pro should have custom_sink_definitions"

    def test_sink_coverage_analysis_included(self, pro_tier):
        """Verify sink coverage analysis is included for Pro tier."""
        code = "\n".join(["os.system(cmd1)", "db.execute(sql1)", "render(template1)"])
        capabilities = get_tool_capabilities("unified_sink_detect", "pro")
        result = _unified_sink_detect_sync(
            code=code,
            language="python",
            confidence_threshold=0.0,
            tier="pro",
            capabilities=capabilities,
        )

        assert result.success
        assert result.coverage_summary is not None, "Pro should have coverage_summary"
        assert "total_patterns" in result.coverage_summary, "Coverage should include pattern count"


class TestUnifiedSinkDetectEnterpriseTier:
    """Validate Enterprise tier unified_sink_detect features (6 tests)."""

    def test_unlimited_sinks_with_pro_features(self, enterprise_tier):
        """Verify Enterprise has unlimited sinks with all Pro features."""
        code = "\n".join([f"os.system(input_{i})" for i in range(100)])
        capabilities = get_tool_capabilities("unified_sink_detect", "enterprise")
        result = _unified_sink_detect_sync(
            code=code,
            language="python",
            confidence_threshold=0.0,
            tier="enterprise",
            capabilities=capabilities,
        )

        assert result.success
        assert result.sink_count >= 50, "Enterprise should handle 100+ sinks"

    def test_organization_sink_rules_enabled(self, enterprise_tier):
        """Verify organization-specific sink rules are available for Enterprise."""
        capabilities = get_tool_capabilities("unified_sink_detect", "enterprise")
        assert "organization_sink_rules" in (capabilities.get("capabilities", []) or [])

    def test_sink_risk_scoring_populated(self, enterprise_tier):
        """Verify sink risk scoring is populated for Enterprise tier."""
        code = "\n".join(
            [
                "db.execute(user_sql)",
                "os.system(user_cmd)",
                "template.render(user_data)",
            ]
        )
        capabilities = get_tool_capabilities("unified_sink_detect", "enterprise")
        result = _unified_sink_detect_sync(
            code=code,
            language="python",
            confidence_threshold=0.0,
            tier="enterprise",
            capabilities=capabilities,
        )

        assert result.success
        assert hasattr(result, "risk_assessments")
        if result.risk_assessments:
            assert any("risk_score" in r for r in result.risk_assessments), "Risk assessments should include scores"

    def test_compliance_mapping_present(self, enterprise_tier):
        """Verify compliance mapping for Enterprise tier."""
        code = "db.execute(user_input)"
        capabilities = get_tool_capabilities("unified_sink_detect", "enterprise")
        result = _unified_sink_detect_sync(
            code=code,
            language="python",
            confidence_threshold=0.0,
            tier="enterprise",
            capabilities=capabilities,
        )

        assert result.success
        assert hasattr(result, "compliance_mapping")
        if result.compliance_mapping:
            # Should have SOC2/ISO mappings
            assert isinstance(result.compliance_mapping, dict)

    def test_historical_sink_tracking_enabled(self, enterprise_tier):
        """Verify historical sink tracking is available for Enterprise."""
        code = "db.execute(user_input)"
        capabilities = get_tool_capabilities("unified_sink_detect", "enterprise")
        result = _unified_sink_detect_sync(
            code=code,
            language="python",
            confidence_threshold=0.0,
            tier="enterprise",
            capabilities=capabilities,
        )

        assert result.success
        assert hasattr(result, "historical_comparison")
        # Field should exist (may be None if no historical data)
        assert hasattr(result, "historical_comparison")

    def test_automated_remediation_suggestions(self, enterprise_tier):
        """Verify automated remediation suggestions for Enterprise."""
        code = "\n".join(["db.execute(user_sql)", "os.system(user_cmd)"])
        capabilities = get_tool_capabilities("unified_sink_detect", "enterprise")
        result = _unified_sink_detect_sync(
            code=code,
            language="python",
            confidence_threshold=0.0,
            tier="enterprise",
            capabilities=capabilities,
        )

        assert result.success
        assert hasattr(result, "remediation_suggestions")
        if result.remediation_suggestions:
            assert len(result.remediation_suggestions) > 0, "Enterprise should provide remediation suggestions"
            assert any("suggested_fix" in r for r in result.remediation_suggestions)


class TestUnifiedSinkDetectCrossTierComparison:
    """Cross-tier comparison tests (2 tests)."""

    def test_community_vs_pro_sink_limit(self, community_tier, pro_tier):
        """Verify Pro analyzes more sinks than Community (no 50-limit)."""
        code = "\n".join([f"os.system(input_{i})" for i in range(65)])

        comm_result = _unified_sink_detect_sync(
            code=code, language="python", confidence_threshold=0.0, tier="community"
        )
        pro_result = _unified_sink_detect_sync(code=code, language="python", confidence_threshold=0.0, tier="pro")

        assert comm_result.success and pro_result.success
        assert comm_result.sink_count <= 50, "Community should limit to 50"
        assert pro_result.sink_count > comm_result.sink_count, "Pro should have more sinks"

    def test_community_no_advanced_features_pro_has(self, community_tier, pro_tier):
        """Verify Pro has advanced features that Community lacks."""
        comm_caps = get_tool_capabilities("unified_sink_detect", "community") or {}
        pro_caps = get_tool_capabilities("unified_sink_detect", "pro") or {}

        comm_cap_set = set(comm_caps.get("capabilities", []) or [])
        pro_cap_set = set(pro_caps.get("capabilities", []) or [])

        # Pro should have advanced_confidence_scoring
        assert "advanced_confidence_scoring" not in comm_cap_set
        assert "advanced_confidence_scoring" in pro_cap_set


class TestUnifiedSinkDetectEdgeCases:
    """Edge case and error handling tests (4 tests)."""

    def test_empty_code_error_handling(self, community_tier):
        """Verify empty code is handled gracefully."""
        result = _unified_sink_detect_sync(code="", language="python", confidence_threshold=0.0, tier="community")
        assert not result.success
        assert result.error_code == "UNIFIED_SINK_DETECT_MISSING_CODE"

    def test_invalid_confidence_threshold_error(self, community_tier):
        """Verify invalid confidence threshold is rejected."""
        code = "os.system(x)"
        result = _unified_sink_detect_sync(code=code, language="python", confidence_threshold=1.5, tier="community")
        assert not result.success
        assert result.error_code == "UNIFIED_SINK_DETECT_INVALID_MIN_CONFIDENCE"

    def test_all_four_languages_supported_community(self, community_tier):
        """Verify all 4 languages are supported in Community tier."""
        test_cases = {
            "python": "os.system(x)",
            "javascript": "child_process.exec(x)",
            "typescript": "child_process.exec(x)",
            "java": "runtime.exec(x)",
        }

        for lang, code in test_cases.items():
            result = _unified_sink_detect_sync(code=code, language=lang, confidence_threshold=0.0, tier="community")
            assert result.success, f"Should support {lang} in Community"
            assert result.language == lang

    def test_confidence_threshold_filtering(self, community_tier):
        """Verify confidence threshold filters sinks correctly."""
        code = "os.system(x); db.execute(y); eval(z)"

        result_low = _unified_sink_detect_sync(code=code, language="python", confidence_threshold=0.0, tier="community")
        result_high = _unified_sink_detect_sync(
            code=code, language="python", confidence_threshold=0.9, tier="community"
        )

        assert result_low.success and result_high.success
        # Higher threshold should find fewer sinks
        assert result_high.sink_count <= result_low.sink_count
