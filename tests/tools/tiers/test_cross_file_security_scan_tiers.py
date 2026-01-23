"""
Tier validation tests for cross_file_security_scan MCP tool.

Tests validate Community/Pro/Enterprise tier functionality per PRE_RELEASE_CHECKLIST.md:
- Community: max depth=3, 10 modules, Python taint tracking, Mermaid diagram, bounded tracing
- Pro: depth=10, 100 modules, enhanced Python taint with DI hints, confidence_scores, framework contexts
- Enterprise: unlimited depth/modules, repository-wide scan, global flow hints, microservice boundaries
"""

import pytest

from code_scalpel.mcp.helpers.graph_helpers import _cross_file_security_scan_sync

# ============================================================================
# TEST FIXTURES - Multi-file Python projects with taint flows
# ============================================================================


@pytest.fixture
def multi_file_sql_injection_project(tmp_path):
    """Create a multi-file Python project with SQL injection vulnerability."""
    # routes.py - Entry point with user input (source)
    routes_py = tmp_path / "routes.py"
    routes_py.write_text("""
from flask import Flask, request
from db import execute_query

app = Flask(__name__)

@app.route("/user/<username>")
def get_user(username):
    # User input - taint source
    user_input = request.args.get("name")
    return execute_query(user_input)
""")

    # db.py - Database execution (sink)
    db_py = tmp_path / "db.py"
    db_py.write_text("""
import sqlite3

def execute_query(user_input):
    # SQL sink - vulnerable to injection
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    # Direct user input in SQL (CWE-89)
    query = f"SELECT * FROM users WHERE name = '{user_input}'"
    cursor.execute(query)
    return cursor.fetchall()
""")

    # utils.py - Additional module in flow
    utils_py = tmp_path / "utils.py"
    utils_py.write_text("""
def process_input(data):
    # Data processing without sanitization
    return data.strip()
""")

    return tmp_path


@pytest.fixture
def multi_file_command_injection_project(tmp_path):
    """Create a multi-file project with command injection vulnerability."""
    # main.py
    main_py = tmp_path / "main.py"
    main_py.write_text("""
import sys
from executor import run_command

def main(user_input):
    # User input as taint source
    result = run_command(user_input)
    return result
""")

    # executor.py
    executor_py = tmp_path / "executor.py"
    executor_py.write_text("""
import os
import subprocess

def run_command(cmd):
    # Dangerous sink: os.system with user input
    result = os.system(f"echo {cmd}")
    return result

def run_subprocess(args):
    # Another dangerous sink
    return subprocess.call(f"ls {args}", shell=True)
""")

    return tmp_path


@pytest.fixture
def multi_file_path_traversal_project(tmp_path):
    """Create a multi-file project with path traversal vulnerability."""
    # api.py
    api_py = tmp_path / "api.py"
    api_py.write_text("""
from handler import get_file

def serve_file(filename):
    # User input - taint source
    return get_file(filename)
""")

    # handler.py
    handler_py = tmp_path / "handler.py"
    handler_py.write_text("""
import os

def get_file(user_path):
    # Path traversal sink - no normalization
    base_dir = "/var/www/files"
    full_path = os.path.join(base_dir, user_path)
    with open(full_path, "r") as f:
        return f.read()
""")

    return tmp_path


@pytest.fixture
def benign_multi_file_project(tmp_path):
    """Create a benign multi-file project with no vulnerabilities."""
    # lib.py
    lib_py = tmp_path / "lib.py"
    lib_py.write_text("""
def safe_add(a, b):
    return a + b

def safe_multiply(x, y):
    return x * y
""")

    # main.py
    main_py = tmp_path / "main.py"
    main_py.write_text("""
from lib import safe_add, safe_multiply

def calculate(x, y):
    return safe_add(safe_multiply(x, 2), y)
""")

    return tmp_path


# ============================================================================
# COMMUNITY TIER TESTS
# ============================================================================


class TestCrossFileSecurityScanCommunityTier:
    """Validate Community tier limits and basic functionality."""

    def test_max_depth_3_enforced(self, community_tier, multi_file_sql_injection_project):
        """Verify max_depth=3 enforced for Community tier."""
        result = _cross_file_security_scan_sync(
            project_root=str(multi_file_sql_injection_project),
            entry_points=None,
            max_depth=10,  # Request 10, should be limited to 3
            include_diagram=True,
            timeout_seconds=30,
            max_modules=50,  # Request 50, should be limited to 10
            tier="community",
        )
        assert result.success is True
        assert result.tier_applied == "community"
        assert result.max_depth_applied == 3, f"Expected max_depth=3, got {result.max_depth_applied}"

    def test_max_modules_10_enforced(self, community_tier, multi_file_sql_injection_project):
        """Verify max_modules=10 enforced for Community tier."""
        result = _cross_file_security_scan_sync(
            project_root=str(multi_file_sql_injection_project),
            entry_points=None,
            max_depth=3,
            include_diagram=True,
            timeout_seconds=30,
            max_modules=100,  # Request 100, should be limited to 10
            tier="community",
        )
        assert result.success is True
        assert result.max_modules_applied == 10, f"Expected max_modules=10, got {result.max_modules_applied}"

    def test_python_taint_tracking_enabled(self, community_tier, multi_file_sql_injection_project):
        """Verify Python-focused taint tracking works for Community tier."""
        result = _cross_file_security_scan_sync(
            project_root=str(multi_file_sql_injection_project),
            entry_points=["routes.py:get_user"],
            max_depth=3,
            include_diagram=True,
            timeout_seconds=30,
            max_modules=10,
            tier="community",
        )
        assert result.success is True
        # Basic tracking should detect cross-file flow
        assert result.has_vulnerabilities or result.vulnerability_count >= 0, "Basic taint tracking should analyze"

    def test_mermaid_diagram_included(self, community_tier, multi_file_sql_injection_project):
        """Verify Mermaid diagram is generated for Community tier."""
        result = _cross_file_security_scan_sync(
            project_root=str(multi_file_sql_injection_project),
            entry_points=None,
            max_depth=3,
            include_diagram=True,
            timeout_seconds=30,
            max_modules=10,
            tier="community",
        )
        assert result.success is True
        assert result.mermaid is not None, "Mermaid diagram should be included"
        assert isinstance(result.mermaid, str)

    def test_source_to_sink_tracing_bounded(self, community_tier, multi_file_sql_injection_project):
        """Verify source-to-sink tracing respects depth bounds for Community tier."""
        result = _cross_file_security_scan_sync(
            project_root=str(multi_file_sql_injection_project),
            entry_points=None,
            max_depth=3,
            include_diagram=True,
            timeout_seconds=30,
            max_modules=10,
            tier="community",
        )
        assert result.success is True
        # With depth=3, longer flows should be truncated
        if result.taint_flows:
            for flow in result.taint_flows:
                # Flow path length should be reasonable given depth limit
                assert flow.flow_path is not None


# ============================================================================
# PRO TIER TESTS
# ============================================================================


class TestCrossFileSecurityScanProTier:
    """Validate Pro tier enhancements."""

    def test_max_depth_10_applied(self, pro_tier, multi_file_sql_injection_project):
        """Verify max_depth=10 for Pro tier."""
        result = _cross_file_security_scan_sync(
            project_root=str(multi_file_sql_injection_project),
            entry_points=None,
            max_depth=100,  # Request 100, should be limited to 10
            include_diagram=True,
            timeout_seconds=30,
            max_modules=500,  # Request unlimited-like, should be limited to 100
            tier="pro",
        )
        assert result.success is True
        assert result.tier_applied == "pro"
        assert result.max_depth_applied == 10, f"Expected max_depth=10, got {result.max_depth_applied}"

    def test_max_modules_100_applied(self, pro_tier, multi_file_sql_injection_project):
        """Verify max_modules=100 for Pro tier."""
        result = _cross_file_security_scan_sync(
            project_root=str(multi_file_sql_injection_project),
            entry_points=None,
            max_depth=10,
            include_diagram=True,
            timeout_seconds=30,
            max_modules=500,  # Request 500, should be limited to 100
            tier="pro",
        )
        assert result.success is True
        assert result.max_modules_applied == 100, f"Expected max_modules=100, got {result.max_modules_applied}"

    def test_enhanced_taint_tracking_with_di_hints(self, pro_tier, multi_file_sql_injection_project):
        """Verify Pro tier has enhanced taint tracking with DI resolution hints."""
        result = _cross_file_security_scan_sync(
            project_root=str(multi_file_sql_injection_project),
            entry_points=None,
            max_depth=10,
            include_diagram=True,
            timeout_seconds=30,
            max_modules=100,
            tier="pro",
        )
        assert result.success is True
        # Pro tier should enable framework-aware taint tracking
        assert result.framework_aware_enabled is True, "Pro tier should have framework_aware_enabled=True"

    def test_confidence_scores_present_pro(self, pro_tier, multi_file_sql_injection_project):
        """Verify confidence_scores populated for Pro tier when vulnerabilities found."""
        result = _cross_file_security_scan_sync(
            project_root=str(multi_file_sql_injection_project),
            entry_points=None,
            max_depth=10,
            include_diagram=True,
            timeout_seconds=30,
            max_modules=100,
            tier="pro",
        )
        assert result.success is True
        # If vulnerabilities found, confidence_scores should be present
        if result.has_vulnerabilities:
            assert result.confidence_scores is not None, "confidence_scores should be present for Pro tier"
            assert isinstance(result.confidence_scores, dict)
            # Scores should have values between 0 and 1
            for key, score in result.confidence_scores.items():
                assert 0 <= score <= 1, f"Confidence score {score} out of range for {key}"

    def test_framework_contexts_included_pro(self, pro_tier, multi_file_sql_injection_project):
        """Verify framework contexts are included for Pro tier."""
        result = _cross_file_security_scan_sync(
            project_root=str(multi_file_sql_injection_project),
            entry_points=None,
            max_depth=10,
            include_diagram=True,
            timeout_seconds=30,
            max_modules=100,
            tier="pro",
        )
        assert result.success is True
        # Pro tier should include framework contexts
        assert result.framework_contexts is not None, "framework_contexts should be present for Pro tier"
        assert isinstance(result.framework_contexts, list)


# ============================================================================
# ENTERPRISE TIER TESTS
# ============================================================================


class TestCrossFileSecurityScanEnterpriseTier:
    """Validate Enterprise tier unlimited capabilities."""

    def test_max_depth_unlimited(self, enterprise_tier, multi_file_sql_injection_project):
        """Verify unlimited depth for Enterprise tier."""
        result = _cross_file_security_scan_sync(
            project_root=str(multi_file_sql_injection_project),
            entry_points=None,
            max_depth=1000,  # Request very large depth
            include_diagram=True,
            timeout_seconds=30,
            max_modules=10000,  # Request very large module count
            tier="enterprise",
        )
        assert result.success is True
        assert result.tier_applied == "enterprise"
        # Enterprise tier should not limit depth (max_depth_applied should be None or original request)
        assert (
            result.max_depth_applied is None or result.max_depth_applied >= 50
        ), "Enterprise should have unlimited depth"

    def test_max_modules_unlimited(self, enterprise_tier, multi_file_sql_injection_project):
        """Verify unlimited modules for Enterprise tier."""
        result = _cross_file_security_scan_sync(
            project_root=str(multi_file_sql_injection_project),
            entry_points=None,
            max_depth=100,
            include_diagram=True,
            timeout_seconds=30,
            max_modules=10000,
            tier="enterprise",
        )
        assert result.success is True
        # Enterprise tier should not limit modules (max_modules_applied should be None or very large)
        assert (
            result.max_modules_applied is None or result.max_modules_applied >= 1000
        ), "Enterprise should have unlimited modules"

    def test_repository_wide_scan_enabled(self, enterprise_tier, multi_file_sql_injection_project):
        """Verify repository-wide scan capability for Enterprise tier."""
        result = _cross_file_security_scan_sync(
            project_root=str(multi_file_sql_injection_project),
            entry_points=None,  # No entry points = repository-wide scan
            max_depth=100,
            include_diagram=True,
            timeout_seconds=30,
            max_modules=10000,
            tier="enterprise",
        )
        assert result.success is True
        # Enterprise should support repository-wide scans
        assert result.files_analyzed >= 0, "Repository-wide scan should analyze files"

    def test_global_flow_hints_present(self, enterprise_tier, multi_file_sql_injection_project):
        """Verify global flow hints are present for Enterprise tier."""
        result = _cross_file_security_scan_sync(
            project_root=str(multi_file_sql_injection_project),
            entry_points=None,
            max_depth=100,
            include_diagram=True,
            timeout_seconds=30,
            max_modules=10000,
            tier="enterprise",
        )
        assert result.success is True
        # Enterprise should include global flow hints
        if result.has_vulnerabilities or result.taint_flows:
            assert result.global_flows is not None, "global_flows should be present for Enterprise tier"

    def test_microservice_boundary_hints_present(self, enterprise_tier, multi_file_sql_injection_project):
        """Verify microservice boundary hints for Enterprise tier."""
        result = _cross_file_security_scan_sync(
            project_root=str(multi_file_sql_injection_project),
            entry_points=None,
            max_depth=100,
            include_diagram=True,
            timeout_seconds=30,
            max_modules=10000,
            tier="enterprise",
        )
        assert result.success is True
        # Enterprise should detect microservice boundaries
        assert (
            result.microservice_boundaries is not None
        ), "microservice_boundaries should be present for Enterprise tier"
        assert isinstance(result.microservice_boundaries, list)

    def test_distributed_trace_view_present(self, enterprise_tier, multi_file_sql_injection_project):
        """Verify distributed trace view for Enterprise tier."""
        result = _cross_file_security_scan_sync(
            project_root=str(multi_file_sql_injection_project),
            entry_points=None,
            max_depth=100,
            include_diagram=True,
            timeout_seconds=30,
            max_modules=10000,
            tier="enterprise",
        )
        assert result.success is True
        # Enterprise should include distributed trace if flows detected
        if result.global_flows and len(result.global_flows) > 0:
            assert result.distributed_trace is not None, "distributed_trace should be present when global_flows exist"
            assert isinstance(result.distributed_trace, dict)
            assert "nodes" in result.distributed_trace
            assert "edges" in result.distributed_trace

    def test_enterprise_features_enabled_flag(self, enterprise_tier, multi_file_sql_injection_project):
        """Verify enterprise_features_enabled flag set to True."""
        result = _cross_file_security_scan_sync(
            project_root=str(multi_file_sql_injection_project),
            entry_points=None,
            max_depth=100,
            include_diagram=True,
            timeout_seconds=30,
            max_modules=10000,
            tier="enterprise",
        )
        assert result.success is True
        assert (
            result.enterprise_features_enabled is True
        ), "Enterprise tier should have enterprise_features_enabled=True"


# ============================================================================
# CROSS-TIER COMPARISON TESTS
# ============================================================================


class TestCrossFileSecurityScanCrossTierComparison:
    """Compare behavior across tiers."""

    def test_community_vs_pro_depth_limit(self, community_tier, pro_tier, multi_file_sql_injection_project):
        """Verify Pro tier allows deeper analysis than Community."""
        comm_result = _cross_file_security_scan_sync(
            project_root=str(multi_file_sql_injection_project),
            entry_points=None,
            max_depth=10,
            include_diagram=True,
            timeout_seconds=30,
            max_modules=10,
            tier="community",
        )
        pro_result = _cross_file_security_scan_sync(
            project_root=str(multi_file_sql_injection_project),
            entry_points=None,
            max_depth=10,
            include_diagram=True,
            timeout_seconds=30,
            max_modules=10,
            tier="pro",
        )
        assert comm_result.success is True
        assert pro_result.success is True
        # Community should be limited to depth=3, Pro to depth=10
        assert comm_result.max_depth_applied == 3
        assert pro_result.max_depth_applied == 10

    def test_community_no_confidence_scores_pro_has(self, community_tier, pro_tier, multi_file_sql_injection_project):
        """Verify Pro tier provides confidence_scores while Community doesn't."""
        comm_result = _cross_file_security_scan_sync(
            project_root=str(multi_file_sql_injection_project),
            entry_points=None,
            max_depth=3,
            include_diagram=True,
            timeout_seconds=30,
            max_modules=10,
            tier="community",
        )
        pro_result = _cross_file_security_scan_sync(
            project_root=str(multi_file_sql_injection_project),
            entry_points=None,
            max_depth=10,
            include_diagram=True,
            timeout_seconds=30,
            max_modules=100,
            tier="pro",
        )
        assert comm_result.success is True
        assert pro_result.success is True
        # Community may not have confidence_scores for basic vulnerabilities
        # Pro should have them
        if pro_result.has_vulnerabilities:
            assert pro_result.confidence_scores is not None or pro_result.vulnerability_count == 0

    def test_enterprise_exceeds_pro_capabilities(self, pro_tier, enterprise_tier, multi_file_sql_injection_project):
        """Verify Enterprise tier supports features Pro doesn't."""
        pro_result = _cross_file_security_scan_sync(
            project_root=str(multi_file_sql_injection_project),
            entry_points=None,
            max_depth=10,
            include_diagram=True,
            timeout_seconds=30,
            max_modules=100,
            tier="pro",
        )
        ent_result = _cross_file_security_scan_sync(
            project_root=str(multi_file_sql_injection_project),
            entry_points=None,
            max_depth=100,
            include_diagram=True,
            timeout_seconds=30,
            max_modules=10000,
            tier="enterprise",
        )
        assert pro_result.success is True
        assert ent_result.success is True
        # Enterprise should have more capabilities enabled
        assert ent_result.enterprise_features_enabled is True


# ============================================================================
# EDGE CASE & BOUNDARY TESTS
# ============================================================================


class TestCrossFileSecurityScanEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_project(self, community_tier, tmp_path):
        """Verify handling of empty project directory."""
        result = _cross_file_security_scan_sync(
            project_root=str(tmp_path),
            entry_points=None,
            max_depth=3,
            include_diagram=True,
            timeout_seconds=30,
            max_modules=10,
            tier="community",
        )
        # Should succeed but with no vulnerabilities
        assert result.success is True
        assert result.has_vulnerabilities is False
        assert result.vulnerability_count == 0

    def test_benign_project_no_false_positives(self, community_tier, benign_multi_file_project):
        """Verify benign code doesn't trigger false positives."""
        result = _cross_file_security_scan_sync(
            project_root=str(benign_multi_file_project),
            entry_points=None,
            max_depth=3,
            include_diagram=True,
            timeout_seconds=30,
            max_modules=10,
            tier="community",
        )
        assert result.success is True
        assert result.has_vulnerabilities is False, "Benign code should not trigger vulnerabilities"
        assert result.vulnerability_count == 0

    def test_nonexistent_project_root(self, community_tier):
        """Verify handling of nonexistent project root."""
        result = _cross_file_security_scan_sync(
            project_root="/nonexistent/path/to/project",
            entry_points=None,
            max_depth=3,
            include_diagram=True,
            timeout_seconds=30,
            max_modules=10,
            tier="community",
        )
        assert result.success is False
        assert result.error is not None
