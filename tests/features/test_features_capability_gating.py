"""Tests for feature gating across tiers.

Verifies that capabilities are correctly available/unavailable based on tier:
- Community: Basic features only
- Pro: Extended features
- Enterprise: All features including governance

[20260124_TEST] Created feature gating tests for all tools.
"""

from __future__ import annotations


from code_scalpel.licensing.features import get_tool_capabilities, has_capability


class TestSecurityScanFeatureGating:
    """Test security_scan capability gating across tiers."""

    def test_security_scan_community_basic_features(self, community_tier):
        """Community tier should have only basic vulnerability detection."""
        caps = get_tool_capabilities("security_scan", "community")
        capabilities = set(caps.get("capabilities", []))

        expected = {
            "basic_vulnerabilities",
            "owasp_top_10",
            "sql_injection_detection",
            "xss_detection",
        }
        assert expected.issubset(
            capabilities
        ), f"Community security_scan missing basic features: {expected - capabilities}"

    def test_security_scan_community_lacks_advanced_features(self, community_tier):
        """Community should not have advanced analysis features."""
        assert not has_capability(
            "security_scan", "context_aware_scanning", "community"
        )
        assert not has_capability("security_scan", "sanitizer_recognition", "community")

    def test_security_scan_pro_has_extended_features(self, pro_tier):
        """Pro tier should have context-aware scanning."""
        assert has_capability("security_scan", "context_aware_scanning", "pro")
        assert has_capability("security_scan", "sanitizer_recognition", "pro")

    def test_security_scan_enterprise_has_all_features(self, enterprise_tier):
        """Enterprise should have all features including custom policies."""
        assert has_capability("security_scan", "context_aware_scanning", "enterprise")
        assert has_capability("security_scan", "custom_policy_engine", "enterprise")
        assert has_capability(
            "security_scan", "priority_finding_ordering", "enterprise"
        )


class TestAnalyzeCodeLanguageGating:
    """Test language support gating across tiers."""

    def test_analyze_code_community_languages(self, community_tier):
        """Community should support Python, JavaScript, TypeScript, Java."""
        caps = get_tool_capabilities("analyze_code", "community")
        limits = caps.get("limits", {})
        languages = limits.get("languages", [])

        expected = {"python", "javascript", "typescript", "java"}
        assert expected.issubset(
            set(languages)
        ), f"Community missing languages: {expected - set(languages)}"

    def test_analyze_code_community_has_rust(self, community_tier):
        """Community should have Rust support (implemented in v2.1.0)."""
        # [20260305_FEATURE] Rust implemented — assertion updated
        caps = get_tool_capabilities("analyze_code", "community")
        limits = caps.get("limits", {})
        languages = limits.get("languages", [])
        lower = [lang.lower() for lang in languages]

        # Go is now implemented (v2.1.0) and should be present
        assert "go" in lower, "Go should be in Community tier (implemented in v2.1.0)"

        # Rust is now implemented (v2.1.0)
        assert "rust" in lower, "Rust should be in Community tier (implemented in v2.1.0)"

    def test_analyze_code_pro_extended_languages(self, pro_tier):
        """Pro tier may extend language support beyond Community."""
        caps = get_tool_capabilities("analyze_code", "pro")
        limits = caps.get("limits", {})
        languages = limits.get("languages", [])

        # Pro should have at least Community languages
        expected = {"python", "javascript", "typescript", "java"}
        assert expected.issubset(
            set(languages)
        ), f"Pro missing languages: {expected - set(languages)}"

    def test_analyze_code_enterprise_unlimited_languages(self, enterprise_tier):
        """Enterprise tier should support all languages (omitted = unlimited)."""
        caps = get_tool_capabilities("analyze_code", "enterprise")
        limits = caps.get("limits", {})

        # Omitted languages key in enterprise means all languages supported
        languages = limits.get("languages")
        # If omitted (None), it means unlimited
        assert languages is None or isinstance(
            languages, (list, set)
        ), "Enterprise analyze_code should have unlimited language support"


class TestCodePolicyCheckComplianceGating:
    """Test compliance framework availability across tiers."""

    def test_code_policy_check_community_basic_only(self, community_tier):
        """Community should only have basic compliance checks."""
        caps = get_tool_capabilities("code_policy_check", "community")
        set(caps.get("capabilities", []))

        assert has_capability("code_policy_check", "basic_compliance", "community")

    def test_code_policy_check_community_no_hipaa_soc2(self, community_tier):
        """Community should not have HIPAA/SOC2 compliance."""
        assert not has_capability("code_policy_check", "hipaa_compliance", "community")
        assert not has_capability("code_policy_check", "soc2_compliance", "community")
        assert not has_capability("code_policy_check", "gdpr_compliance", "community")
        assert not has_capability(
            "code_policy_check", "pci_dss_compliance", "community"
        )

    def test_code_policy_check_pro_extended_compliance(self, pro_tier):
        """Pro should have extended compliance frameworks."""
        assert has_capability("code_policy_check", "extended_compliance", "pro")
        # May have additional frameworks beyond community

    def test_code_policy_check_enterprise_all_compliance(self, enterprise_tier):
        """Enterprise should have all compliance frameworks."""
        frameworks = [
            "basic_compliance",
            "hipaa_compliance",
            "soc2_compliance",
            "gdpr_compliance",
            "pci_dss_compliance",
        ]

        for framework in frameworks:
            assert has_capability(
                "code_policy_check", framework, "enterprise"
            ), f"Enterprise should have {framework}"


class TestSymbolicExecutionGating:
    """Test symbolic execution features across tiers."""

    def test_symbolic_execute_community_basic(self, community_tier):
        """Community should have basic symbolic execution."""
        caps = get_tool_capabilities("symbolic_execute", "community")
        limits = caps.get("limits", {})

        # [20260212_TEST] Updated to match rebalanced limits.toml
        # Community has strict path and depth limits
        assert limits.get("max_paths") == 100
        assert limits.get("max_depth") == 10

    def test_symbolic_execute_community_no_advanced(self, community_tier):
        """Community should not have advanced constraint solving."""
        assert not has_capability(
            "symbolic_execute", "advanced_constraint_solving", "community"
        )

    def test_symbolic_execute_pro_unlimited_paths(self, pro_tier):
        """Pro should allow unlimited paths."""
        caps = get_tool_capabilities("symbolic_execute", "pro")
        limits = caps.get("limits", {})

        assert limits.get("max_paths") is None, "Pro should have unlimited paths"

    def test_symbolic_execute_enterprise_advanced_features(self, enterprise_tier):
        """Enterprise should have advanced constraint solving."""
        assert has_capability(
            "symbolic_execute", "advanced_constraint_solving", "enterprise"
        )


class TestGenerateUnitTestsGating:
    """Test test generation features across tiers."""

    def test_generate_unit_tests_community_pytest(self, community_tier):
        """Community should have pytest support."""
        assert has_capability("generate_unit_tests", "pytest_support", "community")

    def test_generate_unit_tests_community_limited_cases(self, community_tier):
        """Community should limit test case generation."""
        caps = get_tool_capabilities("generate_unit_tests", "community")
        limits = caps.get("limits", {})

        # [20260212_TEST] Updated to match rebalanced limits.toml
        assert (
            limits.get("max_test_cases") == 10
        ), "Community should generate max 10 test cases"

    def test_generate_unit_tests_community_no_data_driven(self, community_tier):
        """Community should not have data-driven test generation."""
        assert not has_capability(
            "generate_unit_tests", "data_driven_tests", "community"
        )

    def test_generate_unit_tests_pro_multiple_frameworks(self, pro_tier):
        """Pro should support multiple test frameworks."""
        frameworks = ["pytest_support", "unittest_support", "jest_support"]
        for framework in frameworks:
            assert has_capability(
                "generate_unit_tests", framework, "pro"
            ), f"Pro should have {framework}"

    def test_generate_unit_tests_pro_data_driven(self, pro_tier):
        """Pro should have data-driven test generation."""
        assert has_capability("generate_unit_tests", "data_driven_tests", "pro")

    def test_generate_unit_tests_enterprise_all_features(self, enterprise_tier):
        """Enterprise should have all test generation features."""
        features = [
            "pytest_support",
            "unittest_support",
            "jest_support",
            "mocha_support",
            "data_driven_tests",
            "coverage_analysis",
        ]

        for feature in features:
            assert has_capability(
                "generate_unit_tests", feature, "enterprise"
            ), f"Enterprise should have {feature}"


class TestTypeEvaporationGating:
    """Test type safety checking across tiers."""

    def test_type_evaporation_community_frontend_only(self, community_tier):
        """Community should check frontend types only."""
        caps = get_tool_capabilities("type_evaporation_scan", "community")
        limits = caps.get("limits", {})

        # Community is frontend-only
        assert limits.get("frontend_only") is True

    def test_type_evaporation_pro_bidirectional(self, pro_tier):
        """Pro should have bidirectional type checking."""
        caps = get_tool_capabilities("type_evaporation_scan", "pro")
        limits = caps.get("limits", {})

        # Pro removes frontend-only restriction
        assert limits.get("frontend_only") is False

    def test_type_evaporation_enterprise_schema_gen(self, enterprise_tier):
        """Enterprise should generate type schemas."""
        assert has_capability(
            "type_evaporation_scan", "schema_generation", "enterprise"
        )
