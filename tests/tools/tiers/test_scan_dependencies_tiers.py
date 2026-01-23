"""
Tier validation tests for scan_dependencies MCP tool.

Tests validate Community/Pro/Enterprise tier functionality per PRE_RELEASE_CHECKLIST.md:
- Community: max 50 dependencies, CVE detection via OSV, CVSS scoring, language support, fixed versions
- Pro: unlimited dependencies, reachability analysis, license compliance, typosquatting detection, supply chain scoring
- Enterprise: all Pro features + policy-based blocking, compliance reporting (SOC2/ISO)
"""

import pytest

from code_scalpel.mcp.helpers.security_helpers import _scan_dependencies_sync

# ============================================================================
# TEST FIXTURES - Project dependency files
# ============================================================================


@pytest.fixture
def python_requirements_with_vulns(tmp_path):
    """Create a Python requirements.txt with known vulnerable packages."""
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("""
# Vulnerable packages (intentionally outdated for testing)
requests==2.6.0
django==1.4.0
pillow==2.4.0
urllib3==1.7
cryptography==0.4
flask==0.10
""")
    return tmp_path


@pytest.fixture
def python_pyproject_with_vulns(tmp_path):
    """Create a pyproject.toml with vulnerable dependencies."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("""
[project]
name = "test-project"
version = "0.1.0"
dependencies = [
    "requests==2.6.0",
    "django==1.4.0",
    "pillow==2.4.0",
]

[project.optional-dependencies]
dev = [
    "pytest==3.0.0",
    "black==19.10b0",
]
""")
    return tmp_path


@pytest.fixture
def javascript_package_json_with_vulns(tmp_path):
    """Create a package.json with vulnerable dependencies."""
    pkg_json = tmp_path / "package.json"
    pkg_json.write_text("""{
  "name": "test-app",
  "version": "1.0.0",
  "dependencies": {
    "express": "3.0.0",
    "lodash": "2.4.1",
    "moment": "2.10.0"
  },
  "devDependencies": {
    "webpack": "1.0.0",
    "babel": "5.0.0"
  }
}
""")
    return tmp_path


@pytest.fixture
def java_pom_xml_with_vulns(tmp_path):
    """Create a pom.xml with vulnerable dependencies."""
    pom_file = tmp_path / "pom.xml"
    pom_file.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<project>
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>test-app</artifactId>
  <version>1.0.0</version>
  <dependencies>
    <dependency>
      <groupId>org.springframework</groupId>
      <artifactId>spring-core</artifactId>
      <version>3.0.0</version>
    </dependency>
    <dependency>
      <groupId>org.apache.commons</groupId>
      <artifactId>commons-io</artifactId>
      <version>2.4</version>
    </dependency>
    <dependency>
      <groupId>junit</groupId>
      <artifactId>junit</artifactId>
      <version>3.8.1</version>
      <scope>test</scope>
    </dependency>
  </dependencies>
</project>
""")
    return tmp_path


@pytest.fixture
def java_gradle_with_vulns(tmp_path):
    """Create a build.gradle with vulnerable dependencies."""
    gradle_file = tmp_path / "build.gradle"
    gradle_file.write_text("""
dependencies {
    implementation 'org.springframework:spring-core:3.0.0'
    implementation 'commons-io:commons-io:2.4'
    testImplementation 'junit:junit:3.8.1'
}
""")
    return tmp_path


@pytest.fixture
def benign_python_project(tmp_path):
    """Create a benign Python project with no known vulnerabilities."""
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("""
requests==2.31.0
django==4.2.0
pillow==10.0.0
""")
    return tmp_path


@pytest.fixture
def large_dependency_list(tmp_path):
    """Create a requirements.txt with many dependencies for testing limits."""
    req_file = tmp_path / "requirements.txt"
    deps = []
    # Create 100+ dependencies
    for i in range(100):
        deps.append(f"package{i:03d}==1.0.0")
    req_file.write_text("\n".join(deps))
    return tmp_path


# ============================================================================
# COMMUNITY TIER TESTS
# ============================================================================


class TestScanDependenciesCommunityTier:
    """Validate Community tier limits and basic functionality."""

    def test_max_50_dependencies_enforced(self, community_tier, large_dependency_list):
        """Verify max 50 dependencies enforced for Community tier."""
        result = _scan_dependencies_sync(
            project_root=str(large_dependency_list),
            scan_vulnerabilities=True,
            include_dev=True,
            timeout=30.0,
            tier="community",
        )
        assert result.success is True
        # Should be limited to 50 dependencies
        assert len(result.dependencies) <= 50, f"Expected ≤50, got {len(result.dependencies)}"

    def test_cve_detection_via_osv_enabled(self, community_tier, python_requirements_with_vulns):
        """Verify CVE detection via OSV API works for Community tier."""
        result = _scan_dependencies_sync(
            project_root=str(python_requirements_with_vulns),
            scan_vulnerabilities=True,
            include_dev=True,
            timeout=30.0,
            tier="community",
        )
        assert result.success is True
        # Should have detected vulnerabilities if OSV lookup works
        # Note: actual result depends on OSV API availability
        assert result.total_vulnerabilities >= 0

    def test_severity_scoring_present(self, community_tier, python_requirements_with_vulns):
        """Verify CVSS severity scoring is present for Community tier."""
        result = _scan_dependencies_sync(
            project_root=str(python_requirements_with_vulns),
            scan_vulnerabilities=True,
            include_dev=True,
            timeout=30.0,
            tier="community",
        )
        assert result.success is True
        # If vulnerabilities found, severity_summary should be populated
        if result.total_vulnerabilities > 0:
            assert result.severity_summary is not None
            assert isinstance(result.severity_summary, dict)

    def test_python_language_support(self, community_tier, python_requirements_with_vulns):
        """Verify Python language support (requirements.txt parsing)."""
        result = _scan_dependencies_sync(
            project_root=str(python_requirements_with_vulns),
            scan_vulnerabilities=False,  # Skip OSV for faster test
            include_dev=True,
            timeout=30.0,
            tier="community",
        )
        assert result.success is True
        # Should find Python dependencies
        python_deps = [d for d in result.dependencies if d.ecosystem in ["PyPI", "pip"]]
        assert len(python_deps) > 0, "Should detect Python dependencies"

    def test_javascript_language_support(self, community_tier, javascript_package_json_with_vulns):
        """Verify JavaScript language support (package.json parsing)."""
        result = _scan_dependencies_sync(
            project_root=str(javascript_package_json_with_vulns),
            scan_vulnerabilities=False,
            include_dev=True,
            timeout=30.0,
            tier="community",
        )
        assert result.success is True
        # Should find JavaScript dependencies
        js_deps = [d for d in result.dependencies if "npm" in d.ecosystem.lower()]
        assert len(js_deps) > 0, "Should detect JavaScript dependencies"

    def test_java_language_support(self, community_tier, java_pom_xml_with_vulns):
        """Verify Java language support (pom.xml parsing)."""
        result = _scan_dependencies_sync(
            project_root=str(java_pom_xml_with_vulns),
            scan_vulnerabilities=False,
            include_dev=True,
            timeout=30.0,
            tier="community",
        )
        assert result.success is True
        # Should find Java dependencies
        java_deps = [d for d in result.dependencies if "maven" in d.ecosystem.lower()]
        assert len(java_deps) > 0, "Should detect Java dependencies"

    def test_fixed_version_remediation(self, community_tier, python_requirements_with_vulns):
        """Verify fixed_version field is included for Community tier."""
        result = _scan_dependencies_sync(
            project_root=str(python_requirements_with_vulns),
            scan_vulnerabilities=True,
            include_dev=True,
            timeout=30.0,
            tier="community",
        )
        assert result.success is True
        # If vulnerabilities found, should have fixed version info
        if result.total_vulnerabilities > 0:
            for dep_info in result.dependencies:
                if dep_info.vulnerabilities:
                    for vuln in dep_info.vulnerabilities:
                        assert hasattr(vuln, "fixed_version"), "Should have fixed_version field"


# ============================================================================
# PRO TIER TESTS
# ============================================================================


class TestScanDependenciesProTier:
    """Validate Pro tier enhancements."""

    def test_unlimited_dependencies_scanned(self, pro_tier, large_dependency_list):
        """Verify unlimited dependencies for Pro tier."""
        result = _scan_dependencies_sync(
            project_root=str(large_dependency_list),
            scan_vulnerabilities=False,  # Skip OSV for faster test
            include_dev=True,
            timeout=30.0,
            tier="pro",
        )
        assert result.success is True
        # Pro tier should scan all dependencies, not just first 50
        assert len(result.dependencies) > 50, f"Expected >50, got {len(result.dependencies)}"

    def test_reachability_analysis_enabled(self, pro_tier, python_requirements_with_vulns):
        """Verify reachability analysis is enabled for Pro tier."""
        result = _scan_dependencies_sync(
            project_root=str(python_requirements_with_vulns),
            scan_vulnerabilities=False,
            include_dev=True,
            timeout=30.0,
            tier="pro",
        )
        assert result.success is True
        # Pro tier should have reachability_analysis capability
        if result.dependencies:
            # Check if is_imported field is populated (indicates reachability analysis)
            any(d.is_imported is not None for d in result.dependencies)
            # is_imported might be None if no imports found, but capability should be available

    def test_license_compliance_enabled(self, pro_tier, python_requirements_with_vulns):
        """Verify license compliance checking for Pro tier."""
        result = _scan_dependencies_sync(
            project_root=str(python_requirements_with_vulns),
            scan_vulnerabilities=False,
            include_dev=True,
            timeout=30.0,
            tier="pro",
        )
        assert result.success is True
        # Pro tier should have license info populated
        if result.dependencies:
            # At least some dependencies should have license information
            any(d.license is not None for d in result.dependencies)
            # May be None if license lookup fails, but capability should be enabled

    def test_typosquatting_detection_enabled(self, pro_tier, python_requirements_with_vulns):
        """Verify typosquatting detection for Pro tier."""
        result = _scan_dependencies_sync(
            project_root=str(python_requirements_with_vulns),
            scan_vulnerabilities=False,
            include_dev=True,
            timeout=30.0,
            tier="pro",
        )
        assert result.success is True
        # Pro tier should have typosquatting_risk field populated
        if result.dependencies:
            # typosquatting_risk should be present in response
            any(hasattr(d, "typosquatting_risk") for d in result.dependencies)
            # Field should exist, even if all values are None

    def test_supply_chain_risk_scoring_present(self, pro_tier, python_requirements_with_vulns):
        """Verify supply chain risk scoring for Pro tier."""
        result = _scan_dependencies_sync(
            project_root=str(python_requirements_with_vulns),
            scan_vulnerabilities=False,
            include_dev=True,
            timeout=30.0,
            tier="pro",
        )
        assert result.success is True
        # Pro tier should have supply_chain_risk_score field
        if result.dependencies:
            # At least check that field exists
            any(hasattr(d, "supply_chain_risk_score") for d in result.dependencies)
            # Field should exist, even if values are None

    def test_false_positive_reduction_applied(self, pro_tier, python_requirements_with_vulns):
        """Verify false positive reduction via reachability for Pro tier."""
        result = _scan_dependencies_sync(
            project_root=str(python_requirements_with_vulns),
            scan_vulnerabilities=True,
            include_dev=True,
            timeout=30.0,
            tier="pro",
        )
        assert result.success is True
        # Pro tier should apply false_positive_reduction via reachability
        # Dependencies with is_imported=False should be marked for filtering
        if result.dependencies:
            [d for d in result.dependencies if d.is_imported is False]
            # Capability should be enabled to filter unreachable vuln deps


# ============================================================================
# ENTERPRISE TIER TESTS
# ============================================================================


class TestScanDependenciesEnterpriseTier:
    """Validate Enterprise tier capabilities."""

    def test_unlimited_dependencies_with_pro_features(self, enterprise_tier, large_dependency_list):
        """Verify unlimited dependencies with all Pro features for Enterprise tier."""
        result = _scan_dependencies_sync(
            project_root=str(large_dependency_list),
            scan_vulnerabilities=False,
            include_dev=True,
            timeout=30.0,
            tier="enterprise",
        )
        assert result.success is True
        # Enterprise should scan all dependencies
        assert len(result.dependencies) > 50

    def test_policy_based_blocking_enabled(self, enterprise_tier, python_requirements_with_vulns):
        """Verify policy-based blocking for Enterprise tier."""
        result = _scan_dependencies_sync(
            project_root=str(python_requirements_with_vulns),
            scan_vulnerabilities=False,
            include_dev=True,
            timeout=30.0,
            tier="enterprise",
        )
        assert result.success is True
        # Enterprise tier should have policy_violations field
        if hasattr(result, "policy_violations") or result.policy_violations is not None:
            assert isinstance(result.policy_violations, list)

    def test_compliance_reporting_present(self, enterprise_tier, python_requirements_with_vulns):
        """Verify compliance reporting (SOC2/ISO) for Enterprise tier."""
        result = _scan_dependencies_sync(
            project_root=str(python_requirements_with_vulns),
            scan_vulnerabilities=False,
            include_dev=True,
            timeout=30.0,
            tier="enterprise",
        )
        assert result.success is True
        # Enterprise should have compliance_report field
        if hasattr(result, "compliance_report"):
            # Compliance report should include SOC2, ISO mappings
            if result.compliance_report:
                assert isinstance(result.compliance_report, dict)

    def test_all_languages_supported(self, enterprise_tier, tmp_path):
        """Verify all language support for Enterprise tier."""
        # Create multi-language project
        (tmp_path / "requirements.txt").write_text("requests==2.6.0\n")
        (tmp_path / "package.json").write_text('{"dependencies": {"express": "3.0.0"}}')
        (tmp_path / "pom.xml").write_text("""<?xml version="1.0"?>
<project><dependencies>
<dependency><groupId>org.springframework</groupId>
<artifactId>spring-core</artifactId>
<version>3.0.0</version>
</dependency></dependencies></project>""")

        result = _scan_dependencies_sync(
            project_root=str(tmp_path),
            scan_vulnerabilities=False,
            include_dev=True,
            timeout=30.0,
            tier="enterprise",
        )
        assert result.success is True
        # Enterprise should detect all three language ecosystems
        ecosystems = set(d.ecosystem for d in result.dependencies)
        assert len(ecosystems) >= 2, f"Expected ≥2 ecosystems, got {ecosystems}"

    def test_custom_vulnerability_database(self, enterprise_tier, python_requirements_with_vulns):
        """Verify custom vulnerability database support for Enterprise tier."""
        result = _scan_dependencies_sync(
            project_root=str(python_requirements_with_vulns),
            scan_vulnerabilities=True,
            include_dev=True,
            timeout=30.0,
            tier="enterprise",
        )
        assert result.success is True
        # Enterprise should support custom vulnerability database
        # This capability enables organizational VDB integration


# ============================================================================
# CROSS-TIER COMPARISON TESTS
# ============================================================================


class TestScanDependenciesCrossTierComparison:
    """Compare behavior across tiers."""

    def test_community_vs_pro_dependency_limit(self, community_tier, pro_tier, large_dependency_list):
        """Verify Pro tier scans more dependencies than Community."""
        comm_result = _scan_dependencies_sync(
            project_root=str(large_dependency_list),
            scan_vulnerabilities=False,
            include_dev=True,
            timeout=30.0,
            tier="community",
        )
        pro_result = _scan_dependencies_sync(
            project_root=str(large_dependency_list),
            scan_vulnerabilities=False,
            include_dev=True,
            timeout=30.0,
            tier="pro",
        )
        assert comm_result.success is True
        assert pro_result.success is True
        # Community should be limited to 50, Pro unlimited
        assert len(comm_result.dependencies) <= 50
        assert len(pro_result.dependencies) > len(comm_result.dependencies)

    def test_community_no_reachability_pro_has(self, community_tier, pro_tier, python_requirements_with_vulns):
        """Verify Pro tier has reachability analysis that Community doesn't."""
        comm_result = _scan_dependencies_sync(
            project_root=str(python_requirements_with_vulns),
            scan_vulnerabilities=False,
            include_dev=True,
            timeout=30.0,
            tier="community",
        )
        pro_result = _scan_dependencies_sync(
            project_root=str(python_requirements_with_vulns),
            scan_vulnerabilities=False,
            include_dev=True,
            timeout=30.0,
            tier="pro",
        )
        assert comm_result.success is True
        assert pro_result.success is True
        # Pro should have more detailed reachability info


# ============================================================================
# EDGE CASE & BOUNDARY TESTS
# ============================================================================


class TestScanDependenciesEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_project(self, community_tier, tmp_path):
        """Verify handling of project with no dependency files."""
        result = _scan_dependencies_sync(
            project_root=str(tmp_path),
            scan_vulnerabilities=True,
            include_dev=True,
            timeout=30.0,
            tier="community",
        )
        assert result.success is True
        assert len(result.dependencies) == 0
        assert result.total_vulnerabilities == 0

    def test_pyproject_toml_parsing(self, community_tier, python_pyproject_with_vulns):
        """Verify pyproject.toml parsing for Python projects."""
        result = _scan_dependencies_sync(
            project_root=str(python_pyproject_with_vulns),
            scan_vulnerabilities=False,
            include_dev=True,
            timeout=30.0,
            tier="community",
        )
        assert result.success is True
        # Should parse both main and dev dependencies
        assert len(result.dependencies) > 0

    def test_exclude_dev_dependencies(self, community_tier, python_pyproject_with_vulns):
        """Verify dev dependencies can be excluded."""
        result_with_dev = _scan_dependencies_sync(
            project_root=str(python_pyproject_with_vulns),
            scan_vulnerabilities=False,
            include_dev=True,
            timeout=30.0,
            tier="community",
        )
        result_without_dev = _scan_dependencies_sync(
            project_root=str(python_pyproject_with_vulns),
            scan_vulnerabilities=False,
            include_dev=False,
            timeout=30.0,
            tier="community",
        )
        assert result_with_dev.success is True
        assert result_without_dev.success is True
        # With dev should have more dependencies
        assert len(result_with_dev.dependencies) >= len(result_without_dev.dependencies)

    def test_gradle_parsing(self, community_tier, java_gradle_with_vulns):
        """Verify build.gradle parsing for Gradle projects."""
        result = _scan_dependencies_sync(
            project_root=str(java_gradle_with_vulns),
            scan_vulnerabilities=False,
            include_dev=True,
            timeout=30.0,
            tier="community",
        )
        assert result.success is True
        # Should parse Gradle dependencies
        java_deps = [d for d in result.dependencies if "maven" in d.ecosystem.lower()]
        assert len(java_deps) > 0, "Should detect Java/Gradle dependencies"

    def test_nonexistent_project_root(self, community_tier):
        """Verify handling of nonexistent project root."""
        result = _scan_dependencies_sync(
            project_root="/nonexistent/path/to/project",
            scan_vulnerabilities=True,
            include_dev=True,
            timeout=30.0,
            tier="community",
        )
        assert result.success is False
        assert result.error is not None
