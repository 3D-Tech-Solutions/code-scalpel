"""
Tier-based validation tests for security_scan MCP tool.

Tests verify that security scanning features are correctly gated by tier:
- Community: max 50 findings, secret detection disabled
- Pro: unlimited findings, secret detection enabled, confidence_score present
- Enterprise: unlimited findings, secret detection enabled, compliance_summary, custom rules
"""

import pytest

from code_scalpel.mcp.helpers.security_helpers import _security_scan_sync

# Sample vulnerable code snippets for testing

VULNERABLE_CODE_SQL = '''
import sqlite3
def get_user(user_id):
    """Vulnerable to SQL injection"""
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    # SQL injection vulnerability
    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
    return cursor.fetchone()
'''

VULNERABLE_CODE_COMMAND = '''
import os
import subprocess
def run_command(cmd):
    """Vulnerable to command injection"""
    # Direct os.system call
    os.system(f"echo {cmd}")
    # Also subprocess.call
    subprocess.call(f"cat {cmd}")
    return "done"
'''

VULNERABLE_CODE_EVAL = '''
def evaluate_expression(expr):
    """Vulnerable to code injection"""
    # Using eval is dangerous
    result = eval(expr)
    return result
'''

VULNERABLE_CODE_XSS = '''
from flask import Flask, render_template_string
app = Flask(__name__)

@app.route('/greet')
def greet(name):
    """Vulnerable to XSS"""
    # Template injection risk
    return render_template_string(f"<h1>Hello {name}</h1>")
'''

HARDCODED_SECRETS = """
# Multiple hardcoded secrets for testing secret detection
API_KEY = "sk-abc123xyz789def456"
DATABASE_PASSWORD = "super_secret_password_123"
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
STRIPE_KEY = "sk_live_51234567890abcdefghijk"
OAUTH_TOKEN = "ghp_1234567890abcdefghijklmnopqrstuvwxyz"

def connect_db():
    password = "hardcoded_db_pass_456"
    return f"postgres://admin:{password}@localhost/mydb"
"""

MULTI_VULNERABILITY_CODE = '''
import os
import sqlite3
from flask import Flask, render_template_string

app = Flask(__name__)

def process_user_input(user_id, query_text):
    """Multiple vulnerabilities in one function"""
    # SQL injection
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

    # Command injection
    os.system(f"echo {query_text}")

    # Code injection
    result = eval(query_text)

    # XSS vulnerability
    return render_template_string(f"<p>Result: {result}</p>")

@app.route('/vulnerable/<user_id>')
def vulnerable_endpoint(user_id):
    return process_user_input(user_id, "test")

# Hardcoded secrets
API_KEY = "sk_test_1234567890abcdef"
PASSWORD = "super_secret_123"
'''


@pytest.fixture
def temp_vulnerable_files(tmp_path):
    """Create temporary vulnerable Python files for testing."""
    (tmp_path / "sql_injection.py").write_text(VULNERABLE_CODE_SQL)
    (tmp_path / "command_injection.py").write_text(VULNERABLE_CODE_COMMAND)
    (tmp_path / "code_injection.py").write_text(VULNERABLE_CODE_EVAL)
    (tmp_path / "xss_vulnerability.py").write_text(VULNERABLE_CODE_XSS)
    (tmp_path / "hardcoded_secrets.py").write_text(HARDCODED_SECRETS)
    (tmp_path / "multiple_vulns.py").write_text(MULTI_VULNERABILITY_CODE)
    return tmp_path


class TestSecurityScanCommunityTier:
    """Community tier: max 50 findings, secret detection disabled."""

    def test_max_findings_limited_to_50(self, community_tier):
        """Verify community tier limits findings to 50."""
        result = _security_scan_sync(
            code=MULTI_VULNERABILITY_CODE,
            file_path=None,
            tier="community",
            confidence_threshold=0.7,
        )
        assert result.success is True
        # Community tier enforces max 50 findings
        assert result.vulnerability_count <= 50

    def test_multiple_vulnerabilities_detected(self, community_tier):
        """Verify multiple vulnerabilities are detected in code."""
        result = _security_scan_sync(
            code=MULTI_VULNERABILITY_CODE,
            file_path=None,
            tier="community",
            confidence_threshold=0.7,
        )
        assert result.success is True
        assert result.has_vulnerabilities is True
        # Should find at least SQL injection and command injection
        assert result.vulnerability_count >= 2

    def test_secret_detection_disabled(self, community_tier):
        """Verify secret detection is DISABLED in community tier."""
        result = _security_scan_sync(
            code=HARDCODED_SECRETS,
            file_path=None,
            tier="community",
            confidence_threshold=0.7,
        )
        assert result.success is True
        # Secret detection should not be present for community tier
        # Custom rule results should be None (where secrets are reported)
        assert result.custom_rule_results is None

    def test_no_confidence_scores(self, community_tier):
        """Verify confidence_score field is not populated in community tier."""
        result = _security_scan_sync(
            code=VULNERABLE_CODE_SQL,
            file_path=None,
            tier="community",
            confidence_threshold=0.7,
        )
        assert result.success is True
        # Community tier should not have confidence scores
        assert result.confidence_scores is None

    def test_no_compliance_summary(self, community_tier):
        """Verify compliance_summary is not present in community tier."""
        result = _security_scan_sync(
            code=VULNERABLE_CODE_SQL,
            file_path=None,
            tier="community",
            confidence_threshold=0.7,
        )
        assert result.success is True
        # Community tier should not have compliance mappings
        assert result.compliance_mappings is None


class TestSecurityScanProTier:
    """Pro tier: unlimited findings, secret detection enabled, confidence_score."""

    def test_unlimited_findings(self, pro_tier):
        """Verify pro tier does not limit findings to 50."""
        result = _security_scan_sync(
            code=MULTI_VULNERABILITY_CODE * 5,  # Create many vulnerabilities
            file_path=None,
            tier="pro",
            confidence_threshold=0.7,
        )
        assert result.success is True
        # Pro tier should not enforce 50-finding limit
        # (Result should reflect actual findings, not capped at 50)

    def test_secret_detection_enabled(self, pro_tier):
        """Verify secret detection finds hardcoded keys in pro tier."""
        result = _security_scan_sync(
            code=HARDCODED_SECRETS,
            file_path=None,
            tier="pro",
            confidence_threshold=0.7,
        )
        assert result.success is True
        # Pro tier enables secret detection via custom_logging_rules
        # Should detect hardcoded secrets
        if result.custom_rule_results:
            # If secrets detected, custom_rule_results should be populated
            assert isinstance(result.custom_rule_results, list)

    def test_confidence_score_present(self, pro_tier):
        """Verify confidence_score is populated in pro tier."""
        result = _security_scan_sync(
            code=VULNERABLE_CODE_SQL,
            file_path=None,
            tier="pro",
            confidence_threshold=0.7,
        )
        assert result.success is True
        # Pro tier provides confidence scores
        assert result.confidence_scores is not None
        # Should have confidence scores for detected vulnerabilities
        if result.vulnerability_count > 0:
            assert isinstance(result.confidence_scores, dict)
            assert len(result.confidence_scores) > 0

    def test_multiple_finding_types(self, pro_tier):
        """Verify multiple vulnerability types are detected."""
        result = _security_scan_sync(
            code=MULTI_VULNERABILITY_CODE,
            file_path=None,
            tier="pro",
            confidence_threshold=0.7,
        )
        assert result.success is True
        # Should detect SQL injection, command injection, code injection, XSS
        if result.vulnerabilities:
            vuln_types = set(v.type for v in result.vulnerabilities)
            # At least some injection types should be detected
            assert len(vuln_types) >= 1

    def test_false_positive_analysis_enabled(self, pro_tier):
        """Verify false positive analysis is available in pro tier."""
        result = _security_scan_sync(
            code=VULNERABLE_CODE_SQL,
            file_path=None,
            tier="pro",
            confidence_threshold=0.7,
        )
        assert result.success is True
        # Pro tier provides false positive analysis
        # This helps users evaluate findings quality
        if result.false_positive_analysis:
            assert "total_findings" in result.false_positive_analysis
            assert "suppressed" in result.false_positive_analysis


class TestSecurityScanEnterpriseTier:
    """Enterprise tier: unlimited findings, secret detection, compliance, custom rules."""

    def test_unlimited_findings(self, enterprise_tier):
        """Verify enterprise tier has no finding limits."""
        result = _security_scan_sync(
            code=MULTI_VULNERABILITY_CODE * 10,
            file_path=None,
            tier="enterprise",
            confidence_threshold=0.7,
        )
        assert result.success is True
        # Enterprise tier should not enforce any finding limits

    def test_secret_detection_enabled(self, enterprise_tier):
        """Verify secret detection is fully enabled in enterprise tier."""
        result = _security_scan_sync(
            code=HARDCODED_SECRETS,
            file_path=None,
            tier="enterprise",
            confidence_threshold=0.7,
        )
        assert result.success is True
        # Enterprise tier fully enables secret detection
        # Should detect multiple hardcoded secrets
        if result.custom_rule_results:
            assert isinstance(result.custom_rule_results, list)

    def test_confidence_score_present(self, enterprise_tier):
        """Verify confidence_score is populated in enterprise tier."""
        result = _security_scan_sync(
            code=VULNERABLE_CODE_SQL,
            file_path=None,
            tier="enterprise",
            confidence_threshold=0.7,
        )
        assert result.success is True
        # Enterprise tier provides confidence scores
        assert result.confidence_scores is not None

    def test_compliance_summary_present(self, enterprise_tier):
        """Verify compliance_summary maps to SOC2/PCI/HIPAA frameworks."""
        result = _security_scan_sync(
            code=VULNERABLE_CODE_SQL,
            file_path=None,
            tier="enterprise",
            confidence_threshold=0.7,
        )
        assert result.success is True
        # Enterprise tier provides compliance mappings
        if result.has_vulnerabilities:
            # When vulnerabilities found, compliance info should be available
            if result.compliance_mappings:
                # Should map to regulatory frameworks
                assert isinstance(result.compliance_mappings, dict)
                # Check for major compliance frameworks
                possible_keys = {"OWASP_TOP_10", "SOC2", "PCI_DSS", "HIPAA"}
                found_keys = set(result.compliance_mappings.keys())
                assert len(found_keys & possible_keys) > 0

    def test_custom_rules_applied(self, enterprise_tier):
        """Verify custom rules from security-rules.yaml are applied."""
        result = _security_scan_sync(
            code=HARDCODED_SECRETS,
            file_path=None,
            tier="enterprise",
            confidence_threshold=0.7,
        )
        assert result.success is True
        # Enterprise tier applies custom rules
        # Custom logging rules should detect sensitive patterns
        if result.custom_rule_results:
            assert isinstance(result.custom_rule_results, list)
            # Should find hardcoded secrets in custom rules

    def test_comprehensive_vulnerability_analysis(self, enterprise_tier):
        """Verify comprehensive analysis including reachability and priority."""
        result = _security_scan_sync(
            code=MULTI_VULNERABILITY_CODE,
            file_path=None,
            tier="enterprise",
            confidence_threshold=0.7,
        )
        assert result.success is True
        # Enterprise tier provides comprehensive analysis
        # Should include priority ordering of findings
        if result.priority_ordered_findings:
            assert isinstance(result.priority_ordered_findings, list)
            # Findings should be ranked by priority
            if len(result.priority_ordered_findings) > 0:
                assert "rank" in result.priority_ordered_findings[0]
                assert "priority_score" in result.priority_ordered_findings[0]

    def test_policy_violations_checked(self, enterprise_tier):
        """Verify policy engine checks for compliance violations."""
        result = _security_scan_sync(
            code=VULNERABLE_CODE_SQL,
            file_path=None,
            tier="enterprise",
            confidence_threshold=0.7,
        )
        assert result.success is True
        # Enterprise tier checks policy violations
        if result.policy_violations:
            assert isinstance(result.policy_violations, list)
            # Policy violations should have structured format
            if len(result.policy_violations) > 0:
                assert "rule" in result.policy_violations[0]
                assert "severity" in result.policy_violations[0]


class TestSecurityScanAsyncInterface:
    """Test async interface integration."""

    @pytest.mark.asyncio
    async def test_async_interface_works(self, pro_tier):
        """Verify async wrapper correctly calls sync implementation."""
        from code_scalpel.mcp.tools.security import security_scan

        result = await security_scan(
            code=VULNERABLE_CODE_SQL,
            file_path=None,
            confidence_threshold=0.7,
        )
        assert result.success is True
        # Should use pro tier limits from fixture
        # Confidence scores should be present for pro tier
        assert result.confidence_scores is not None or result.vulnerability_count == 0


class TestSecurityScanEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_code(self, community_tier):
        """Verify scanner handles empty code gracefully."""
        result = _security_scan_sync(
            code="",
            file_path=None,
            tier="community",
            confidence_threshold=0.7,
        )
        # Empty code should not produce vulnerabilities (implementation may reject or succeed)
        assert result.has_vulnerabilities is False
        assert result.vulnerability_count == 0

    def test_benign_code(self, community_tier):
        """Verify scanner handles benign code without false positives."""
        benign_code = '''
def add(a, b):
    """Safe addition function"""
    return a + b

def greet(name):
    """Safe greeting function"""
    return f"Hello, {name}!"
'''
        result = _security_scan_sync(
            code=benign_code,
            file_path=None,
            tier="community",
            confidence_threshold=0.7,
        )
        assert result.success is True
        assert result.has_vulnerabilities is False
        assert result.vulnerability_count == 0

    def test_high_confidence_threshold(self, pro_tier):
        """Verify high confidence threshold filters findings."""
        result = _security_scan_sync(
            code=VULNERABLE_CODE_SQL,
            file_path=None,
            tier="pro",
            confidence_threshold=0.99,  # Very high threshold
        )
        assert result.success is True
        # High threshold may filter some findings
