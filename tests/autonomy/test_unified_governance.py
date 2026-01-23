"""
Unified Governance Integration Tests.

[20251221_TEST] Integration tests for unified governance system

Tests integration of:
- PolicyEngine (OPA/Rego policies)
- ChangeBudget (quantitative constraints)
- SemanticAnalyzer (security pattern detection)
- ComplianceReporter (audit/metrics)
"""

import pytest

from code_scalpel.governance.change_budget import FileChange
from code_scalpel.governance.change_budget import Operation as BudgetOperation
from code_scalpel.governance.unified_governance import (
    GovernanceContext,
    UnifiedGovernance,
    ViolationSource,
)


class TestUnifiedGovernanceSemanticAnalysis:
    """Test semantic security analysis integration."""

    def test_sql_injection_detection(self, tmp_path):
        """Test SQL injection detection in unified evaluation."""
        gov = UnifiedGovernance(str(tmp_path))

        operation = {
            "type": "code_edit",
            "code": "cursor.execute('SELECT * FROM users WHERE id=' + user_id)",
            "language": "python",
            "file_path": "app.py",
        }

        decision = gov.evaluate(operation)

        assert not decision.allowed
        assert any(v.rule == "sql_injection_risk" for v in decision.violations)
        assert any(v.source == ViolationSource.SEMANTIC for v in decision.violations)

    def test_xss_detection_javascript(self, tmp_path):
        """Test XSS detection in JavaScript code."""
        gov = UnifiedGovernance(str(tmp_path))

        operation = {
            "type": "code_edit",
            "code": "document.getElementById('content').innerHTML = userInput;",
            "language": "javascript",
            "file_path": "app.js",
        }

        decision = gov.evaluate(operation)

        assert not decision.allowed
        assert any(v.rule == "xss_risk" for v in decision.violations)

    def test_command_injection_detection(self, tmp_path):
        """Test command injection detection."""
        gov = UnifiedGovernance(str(tmp_path))

        operation = {
            "type": "code_edit",
            "code": "os.system('grep ' + user_search + ' /var/log/auth.log')",
            "language": "python",
            "file_path": "log_search.py",
        }

        decision = gov.evaluate(operation)

        assert not decision.allowed
        assert any(v.rule == "command_injection_risk" for v in decision.violations)

    def test_path_traversal_detection(self, tmp_path):
        """Test path traversal detection."""
        gov = UnifiedGovernance(str(tmp_path))

        operation = {
            "type": "code_edit",
            "code": "with open(request.args['filename']) as f: return f.read()",
            "language": "python",
            "file_path": "file_handler.py",
        }

        decision = gov.evaluate(operation)

        assert not decision.allowed
        assert any(v.rule == "path_traversal_risk" for v in decision.violations)

    def test_xxe_injection_detection(self, tmp_path):
        """Test XXE injection detection."""
        gov = UnifiedGovernance(str(tmp_path))

        operation = {
            "type": "code_edit",
            "code": "import xml.etree.ElementTree as ET\ntree = ET.parse(user_xml_file)",
            "language": "python",
            "file_path": "xml_parser.py",
        }

        decision = gov.evaluate(operation)

        assert not decision.allowed
        assert any(v.rule == "xxe_injection_risk" for v in decision.violations)

    def test_parameterized_sql_allowed(self, tmp_path):
        """Test that parameterized SQL is allowed."""
        gov = UnifiedGovernance(str(tmp_path))

        operation = {
            "type": "code_edit",
            "code": "cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))",
            "language": "python",
            "file_path": "app.py",
        }

        decision = gov.evaluate(operation)

        # Should not have SQL injection violations
        sql_violations = [v for v in decision.violations if "sql_injection" in v.rule]
        assert len(sql_violations) == 0


class TestUnifiedGovernanceBudgetIntegration:
    """Test budget constraint integration."""

    def test_budget_violation_detection(self, tmp_path):
        """Test that budget violations are detected in unified evaluation."""
        # Create a budget config
        budget_config = tmp_path / "budget.yaml"
        budget_config.write_text("""
budgets:
  default:
    max_files: 1
    max_lines_per_file: 10
    max_total_lines: 20
""")

        gov = UnifiedGovernance(str(tmp_path))

        # Create operation that violates budget
        operation = BudgetOperation(
            changes=[
                FileChange(
                    file_path="file1.py",
                    added_lines=["x = 1"] * 15,  # Exceeds max_lines_per_file
                ),
            ],
        )

        decision = gov.evaluate(operation)

        assert not decision.allowed
        assert any(v.source == ViolationSource.BUDGET for v in decision.violations)

    def test_budget_within_limits_allowed(self, tmp_path):
        """Test that operations within budget limits are allowed."""
        budget_config = tmp_path / "budget.yaml"
        budget_config.write_text("""
budgets:
  default:
    max_files: 5
    max_lines_per_file: 100
    max_total_lines: 300
""")

        gov = UnifiedGovernance(str(tmp_path))

        operation = BudgetOperation(
            changes=[
                FileChange(
                    file_path="file1.py",
                    added_lines=["x = 1"] * 5,  # Within limits
                ),
            ],
        )

        decision = gov.evaluate(operation)

        # Should not have budget violations
        budget_violations = [v for v in decision.violations if v.source == ViolationSource.BUDGET]
        assert len(budget_violations) == 0


class TestUnifiedGovernanceContextAwareness:
    """Test role and context-aware governance."""

    def test_context_user_role_tracked(self, tmp_path):
        """Test that user role is included in governance context."""
        gov = UnifiedGovernance(str(tmp_path))

        context = GovernanceContext(
            user_role="developer",
            team="backend",
            environment="staging",
        )

        operation = {"type": "code_edit", "code": "x = 1", "language": "python"}

        gov.evaluate(operation, context)

        # Check decision was logged with context
        history = gov.get_decision_history(limit=1)
        assert len(history) > 0
        assert history[0]["user_role"] == "developer"
        assert history[0]["team"] == "backend"

    def test_environment_tracking(self, tmp_path):
        """Test that environment is tracked in decisions."""
        gov = UnifiedGovernance(str(tmp_path))

        context = GovernanceContext(environment="production")

        operation = {"type": "code_edit", "code": "x = 1", "language": "python"}

        gov.evaluate(operation, context)

        history = gov.get_decision_history(limit=1)
        assert history[0]["environment"] == "production"


class TestUnifiedGovernanceViolationTracking:
    """Test violation tracking and categorization."""

    def test_semantic_violations_categorized(self, tmp_path):
        """Test that semantic violations are properly categorized."""
        gov = UnifiedGovernance(str(tmp_path))

        operation = {
            "type": "code_edit",
            "code": "os.system('echo ' + user_input)",
            "language": "python",
        }

        decision = gov.evaluate(operation)

        semantic_vios = decision.semantic_violations
        assert len(semantic_vios) > 0
        assert all(v.source == ViolationSource.SEMANTIC for v in semantic_vios)

    def test_critical_violations_identified(self, tmp_path):
        """Test that CRITICAL violations are identified."""
        gov = UnifiedGovernance(str(tmp_path))

        operation = {
            "type": "code_edit",
            "code": "cursor.execute('SELECT * FROM users WHERE id=' + user_id)",
            "language": "python",
        }

        decision = gov.evaluate(operation)

        critical = decision.critical_violations
        assert len(critical) > 0
        assert all(v.severity == "CRITICAL" for v in critical)

    def test_violation_summary(self, tmp_path):
        """Test comprehensive violation summary."""
        gov = UnifiedGovernance(str(tmp_path))

        operation = {
            "type": "code_edit",
            "code": "eval(user_code)",
            "language": "python",
        }

        decision = gov.evaluate(operation)

        summary = decision.get_summary()
        assert "Denied" in summary or "violation" in summary.lower()
        assert len(summary) > 0


# [20251221_TODO] Add policy hierarchy tests:
#   - Test role-based policy differentiation
#   - Test policy inheritance from parent roles
#   - Test policy override workflows
#   - Test team-specific policy customization

# [20251221_TODO] Add compliance metrics tests:
#   - Test violation rate tracking
#   - Test compliance report generation
#   - Test trend analysis over time
#   - Test SLA monitoring

# [20251221_TODO] Add cross-system integration tests:
#   - Test PolicyEngine + ChangeBudget interaction
#   - Test SemanticAnalyzer + PolicyEngine interaction
#   - Test override workflows
#   - Test audit trail completeness

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
