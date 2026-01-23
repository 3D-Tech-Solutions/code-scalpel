# Unified Governance Module

**Version:** 3.1.0  
**Last Updated:** December 21, 2025

---

## Overview

The **Unified Governance** module provides enterprise-grade orchestration of policy enforcement, change budgeting, and compliance reporting. It bridges the `policy_engine` (OPA/Rego policies) and `policy` (change budgets) modules into a single, coherent governance system.

### Key Capabilities

- **Unified Evaluation** - Single API for policy + budget + semantic checks
- **Role-Based Policies** - Hierarchical policy inheritance (developer → reviewer → architect)
- **Compliance Reporting** - Enterprise audit trails and metrics
- **Violation Aggregation** - Combined reporting from all governance sources
- **Context-Aware Evaluation** - User, session, project context tracking
- **Override Management** - Human oversight with audit trails

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│         UNIFIED GOVERNANCE LAYER                     │
│   (Orchestrates all governance mechanisms)          │
└─────────────────────────────────────────────────────┘
                      │
       ┌──────────────┼──────────────┐
       │              │              │
       ▼              ▼              ▼
┌──────────────┐ ┌──────────┐ ┌──────────────┐
│ PolicyEngine │ │  Change  │ │   Semantic   │
│  (OPA/Rego)  │ │  Budget  │ │   Analyzer   │
└──────────────┘ └──────────┘ └──────────────┘
       │              │              │
       └──────────────┴──────────────┘
                      │
                      ▼
         ┌──────────────────────────┐
         │   COMPLIANCE REPORTING   │
         │   • Audit logs           │
         │   • Security posture     │
         │   • Recommendations      │
         └──────────────────────────┘
```

### Module Components

| Component | Purpose | Key Classes |
|-----------|---------|-------------|
| **unified_governance.py** | Main orchestration | `UnifiedGovernance`, `GovernanceDecision`, `GovernanceViolation` |
| **compliance_reporter.py** | Reporting & metrics | `ComplianceReporter`, `ComplianceReport`, `SecurityPosture` |
| **audit_log.py** | Immutable audit trail | `AuditLog` |

### Relationship to Other Modules

- **policy_engine/** - Declarative OPA/Rego policies (imported, not duplicated)
- **policy/** - Change budget constraints (imported)
- **governance/** - Orchestrates the above + adds compliance layer

---

## Quick Start

### Basic Usage

```python
from code_scalpel.governance import UnifiedGovernance

# Initialize with config directory
gov = UnifiedGovernance(".code-scalpel")

# Define operation to evaluate
operation = {
    "type": "code_edit",
    "code": 'cursor.execute("SELECT * FROM users WHERE id=" + user_id)',
    "language": "python",
    "file_path": "src/database.py"
}

# Evaluate against all governance mechanisms
decision = gov.evaluate(operation)

if decision.allowed:
    print("✅ Operation approved")
    apply_modification(operation)
else:
    print(f"❌ Operation denied: {decision.reason}")
    
    # Check violations by source
    for v in decision.policy_violations:
        print(f"  [POLICY] {v.rule}: {v.message}")
    
    for v in decision.budget_violations:
        print(f"  [BUDGET] {v.rule}: {v.actual}/{v.limit}")
    
    for v in decision.semantic_violations:
        print(f"  [SEMANTIC] {v.rule}: {v.message}")
```

### With Context

```python
from code_scalpel.governance import UnifiedGovernance, GovernanceContext

gov = UnifiedGovernance(".code-scalpel")

# Add context for role-based policies and audit trails
context = GovernanceContext(
    user="developer@example.com",
    role="developer",
    session_id="abc123",
    project="my-app"
)

decision = gov.evaluate(operation, context)
```

### Compliance Reporting

```python
from code_scalpel.governance import ComplianceReporter
from code_scalpel.governance.audit_log import AuditLog
from code_scalpel.policy_engine import PolicyEngine
from datetime import datetime, timedelta

# Initialize components
audit_log = AuditLog(".code-scalpel/audit.log")
policy_engine = PolicyEngine(".code-scalpel/policy.yaml")

reporter = ComplianceReporter(audit_log, policy_engine)

# Generate weekly report
end_date = datetime.now()
start_date = end_date - timedelta(days=7)

report = reporter.generate_report(
    time_range=(start_date, end_date),
    format="json"
)

print(f"Total operations: {report.summary.total_operations}")
print(f"Violations: {report.summary.total_violations}")
print(f"Security posture: {report.security_posture.score}/100")

# Recommendations
for rec in report.recommendations:
    print(f"[{rec.priority}] {rec.title}")
    print(f"  {rec.description}")
```

---

## API Reference

### UnifiedGovernance

Main orchestration class that evaluates operations against all governance mechanisms.

#### Constructor

```python
UnifiedGovernance(
    config_dir: str | Path,
    policy_config: Optional[str] = None,
    budget_config: Optional[str] = None
)
```

**Parameters:**
- `config_dir` - Directory containing governance configs (.code-scalpel/)
- `policy_config` - Optional path to policy.yaml (defaults to config_dir/policy.yaml)
- `budget_config` - Optional path to budgets.yaml (defaults to config_dir/budgets.yaml)

#### Methods

##### evaluate()

```python
def evaluate(
    operation: Dict[str, Any],
    context: Optional[GovernanceContext] = None
) -> GovernanceDecision
```

Evaluate an operation against all governance mechanisms.

**Parameters:**
- `operation` - Operation to evaluate (dict with type, code, file_path, etc.)
- `context` - Optional context (user, role, session)

**Returns:** `GovernanceDecision` with allowed flag and violations

##### evaluate_with_override()

```python
def evaluate_with_override(
    operation: Dict[str, Any],
    override_code: str,
    justification: str,
    context: Optional[GovernanceContext] = None
) -> GovernanceDecision
```

Evaluate with human override capability.

**Parameters:**
- `operation` - Operation to evaluate
- `override_code` - TOTP code from authenticator
- `justification` - Reason for override
- `context` - Optional context

**Returns:** `GovernanceDecision` (may be allowed via override)

---

### GovernanceDecision

Result of governance evaluation.

#### Properties

```python
@dataclass
class GovernanceDecision:
    allowed: bool                          # Overall decision
    reason: str                            # Primary reason for decision
    violations: List[GovernanceViolation]  # All violations
    source: ViolationSource                # Primary violation source
    context: Optional[GovernanceContext]   # Evaluation context
    timestamp: datetime                    # When evaluated
    decision_id: str                       # Unique ID for audit
```

#### Helper Properties

```python
decision.policy_violations      # Filter violations by POLICY source
decision.budget_violations      # Filter violations by BUDGET source
decision.semantic_violations    # Filter violations by SEMANTIC source
decision.config_violations      # Filter violations by CONFIG source

decision.critical_violations    # Filter by CRITICAL severity
decision.high_violations        # Filter by HIGH severity
decision.medium_violations      # Filter by MEDIUM severity
```

---

### GovernanceViolation

A single governance constraint violation.

```python
@dataclass
class GovernanceViolation:
    rule: str                        # Name of violated constraint
    severity: str                    # CRITICAL, HIGH, MEDIUM, LOW
    message: str                     # Human-readable message
    source: ViolationSource          # POLICY, BUDGET, SEMANTIC, CONFIG
    limit: Optional[int] = None      # Budget limit (if applicable)
    actual: Optional[int] = None     # Actual value (if applicable)
```

**Example:**
```python
violation = GovernanceViolation(
    rule="max_files_exceeded",
    severity="HIGH",
    message="Modified 15 files, limit is 10",
    source=ViolationSource.BUDGET,
    limit=10,
    actual=15
)
```

---

### ViolationSource (Enum)

Source of a governance violation.

```python
class ViolationSource(Enum):
    POLICY = "policy"        # OPA/Rego policy violation
    BUDGET = "budget"        # Change budget constraint violation
    SEMANTIC = "semantic"    # Semantic security analysis violation
    CONFIG = "config"        # Configuration/validation error
```

---

### ComplianceReporter

Generate compliance reports for enterprise audits.

#### Constructor

```python
ComplianceReporter(
    audit_log: AuditLog,
    policy_engine: Optional[PolicyEngine] = None
)
```

**Parameters:**
- `audit_log` - Audit log containing event history
- `policy_engine` - Optional policy engine for validation (requires policy_engine module)

#### Methods

##### generate_report()

```python
def generate_report(
    time_range: Tuple[datetime, datetime],
    format: str = "json"
) -> ComplianceReport | str | bytes
```

Generate compliance report for specified time range.

**Parameters:**
- `time_range` - (start, end) datetime tuple
- `format` - "json", "html", or "pdf"

**Returns:** ComplianceReport object (or formatted string/bytes)

---

### ComplianceReport

Complete compliance report structure.

```python
@dataclass
class ComplianceReport:
    generated_at: datetime
    time_range: Tuple[datetime, datetime]
    summary: ReportSummary
    policy_violations: ViolationAnalysis
    override_analysis: OverrideAnalysis
    security_posture: SecurityPosture
    recommendations: List[Recommendation]
```

**Sub-structures:**

#### ReportSummary
```python
@dataclass
class ReportSummary:
    total_operations: int
    total_violations: int
    total_overrides: int
    violation_rate: float      # violations / operations
    override_rate: float       # overrides / operations
    most_violated_policies: List[Tuple[str, int]]
```

#### SecurityPosture
```python
@dataclass
class SecurityPosture:
    score: int                 # 0-100
    grade: str                 # A-F
    strengths: List[str]
    weaknesses: List[str]
    risk_level: str           # LOW, MEDIUM, HIGH, CRITICAL
```

#### Recommendation
```python
@dataclass
class Recommendation:
    priority: str              # HIGH, MEDIUM, LOW
    category: str              # Policy Tuning, Policy Adjustment, etc.
    title: str
    description: str
    action: str
```

---

## Configuration

The governance module uses configuration files from the `.code-scalpel/` directory:

### config.yaml - Unified Configuration

```yaml
# Unified Governance Configuration
version: "3.1.0"

# Component toggles
components:
  policy_engine: true         # Enable OPA/Rego policies
  change_budget: true         # Enable budget constraints
  semantic_analysis: true     # Enable security pattern detection

# Blocking configuration
blocking:
  critical: true              # Block CRITICAL violations
  high: true                  # Block HIGH violations
  medium:
    policy: true              # Block MEDIUM policy violations
    budget: true              # Block MEDIUM budget violations
    semantic: false           # Warn only for MEDIUM semantic
  low: false                  # Never block LOW
  info: false                 # Never block INFO

# Context settings
context:
  track_users: true           # Track user context
  track_sessions: true        # Track session context
  require_context: false      # Require context for evaluation

# Audit settings
audit:
  log_all_evaluations: true   # Log all policy checks
  log_context: true           # Include context in logs
  signature_algorithm: "hmac-sha256"
  retention_days: 365         # Keep logs for 1 year

# Compliance settings
compliance:
  enabled: true
  report_schedule: "daily"    # daily | weekly | monthly
  metrics_retention: 90       # Days to keep metrics
```

### Related Configuration Files

- **policy.yaml** - OPA/Rego policies (see [policy_engine/README.md](../policy_engine/README.md))
- **budgets.yaml** - Change budgets (see [policy/README.md](../policy/README.md))

---

## Usage Patterns

### Pattern 1: Pre-commit Hook

```python
from code_scalpel.governance import UnifiedGovernance
import sys

def pre_commit_check():
    """Check staged changes against governance."""
    gov = UnifiedGovernance(".code-scalpel")
    
    # Get staged changes
    staged_files = get_staged_files()
    
    operation = {
        "type": "commit",
        "files": staged_files,
        "description": get_commit_message()
    }
    
    decision = gov.evaluate(operation)
    
    if not decision.allowed:
        print(f"❌ Commit blocked: {decision.reason}")
        for v in decision.violations:
            print(f"  [{v.severity}] {v.rule}: {v.message}")
        sys.exit(1)
    
    print("✅ Governance check passed")
```

### Pattern 2: CI/CD Pipeline

```python
from code_scalpel.governance import UnifiedGovernance

def ci_governance_check():
    """Run governance checks in CI pipeline."""
    gov = UnifiedGovernance(".code-scalpel")
    
    # Check PR changes
    pr_changes = get_pr_changes()
    
    operation = {
        "type": "pull_request",
        "changes": pr_changes,
        "author": os.environ.get("PR_AUTHOR")
    }
    
    decision = gov.evaluate(operation)
    
    # Generate report
    report_path = "governance-report.json"
    with open(report_path, "w") as f:
        json.dump({
            "allowed": decision.allowed,
            "reason": decision.reason,
            "violations": [
                {
                    "rule": v.rule,
                    "severity": v.severity,
                    "message": v.message,
                    "source": v.source.value
                }
                for v in decision.violations
            ]
        }, f, indent=2)
    
    return 0 if decision.allowed else 1
```

### Pattern 3: Real-time IDE Integration

```python
from code_scalpel.governance import UnifiedGovernance

class GovernanceExtension:
    """VS Code extension for real-time governance checks."""
    
    def __init__(self):
        self.gov = UnifiedGovernance(".code-scalpel")
    
    def on_code_edit(self, code: str, file_path: str):
        """Check code edit against governance."""
        operation = {
            "type": "code_edit",
            "code": code,
            "file_path": file_path,
            "language": detect_language(file_path)
        }
        
        decision = self.gov.evaluate(operation)
        
        if not decision.allowed:
            # Show inline warnings/errors
            for v in decision.violations:
                self.show_diagnostic(
                    file_path=file_path,
                    severity=v.severity,
                    message=f"{v.rule}: {v.message}"
                )
```

### Pattern 4: Weekly Compliance Report

```python
from code_scalpel.governance import ComplianceReporter
from code_scalpel.governance.audit_log import AuditLog
from datetime import datetime, timedelta

def generate_weekly_report():
    """Generate and email weekly compliance report."""
    audit_log = AuditLog(".code-scalpel/audit.log")
    reporter = ComplianceReporter(audit_log)
    
    # Last 7 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    # Generate HTML report
    report = reporter.generate_report(
        time_range=(start_date, end_date),
        format="html"
    )
    
    # Email to stakeholders
    send_email(
        to=["tech-lead@example.com", "security@example.com"],
        subject=f"Weekly Governance Report - {start_date.strftime('%Y-%m-%d')}",
        html_body=report
    )
```

---

## Best Practices

### 1. Severity-Based Blocking

Configure blocking thresholds based on your risk tolerance:

| Environment | CRITICAL | HIGH | MEDIUM | LOW |
|-------------|----------|------|--------|-----|
| Production | ✅ Block | ✅ Block | ✅ Block | ⚠️ Warn |
| Staging | ✅ Block | ✅ Block | ⚠️ Warn | ℹ️ Audit |
| Development | ✅ Block | ⚠️ Warn | ⚠️ Warn | ℹ️ Audit |

### 2. Context Tracking

Always provide context for better audit trails and role-based policies:

```python
# Good: Provides full context
context = GovernanceContext(
    user="developer@example.com",
    role="developer",
    session_id=session_id,
    project="my-app",
    environment="production"
)
decision = gov.evaluate(operation, context)

# Bad: No context
decision = gov.evaluate(operation)  # Limited audit trail
```

### 3. Override Management

Require strong justification for overrides:

```python
# Good: Clear justification
decision = gov.evaluate_with_override(
    operation=operation,
    override_code=get_totp_code(),
    justification="Production incident #12345 - Database outage requires emergency schema rollback",
    context=context
)

# Bad: Weak justification
decision = gov.evaluate_with_override(
    operation=operation,
    override_code=get_totp_code(),
    justification="Need to deploy",  # Too vague!
    context=context
)
```

### 4. Regular Compliance Reviews

Schedule automatic compliance reports:

- **Daily** - Security posture monitoring
- **Weekly** - Team review of violations and trends
- **Monthly** - Executive summary and recommendations
- **Quarterly** - Policy effectiveness and tuning

### 5. Integration Testing

Test governance in CI/CD:

```python
def test_governance_denies_sql_injection():
    """Test that governance blocks SQL injection."""
    gov = UnifiedGovernance(".code-scalpel")
    
    bad_code = 'cursor.execute("SELECT * FROM users WHERE id=" + user_id)'
    
    operation = {
        "type": "code_edit",
        "code": bad_code,
        "language": "python"
    }
    
    decision = gov.evaluate(operation)
    
    assert not decision.allowed
    assert any(v.rule == "no-sql-injection" for v in decision.violations)
```

---

## Troubleshooting

### Issue: PolicyEngine import fails

**Error:**
```
ImportError: PolicyEngine module not available
```

**Solution:**
```bash
# Install OPA CLI
brew install opa  # macOS
# or
wget https://openpolicyagent.org/downloads/latest/opa_linux_amd64

# Install Python dependencies
pip install pyyaml
```

### Issue: Audit log permission denied

**Error:**
```
PermissionError: [Errno 13] Permission denied: '.code-scalpel/audit.log'
```

**Solution:**
```bash
# Fix permissions
chmod 644 .code-scalpel/audit.log
chown $USER .code-scalpel/audit.log
```

### Issue: HMAC signature verification fails

**Error:**
```
TamperDetectedError: Audit log signature invalid
```

**Solution:**
```bash
# Regenerate HMAC key (WARNING: invalidates old logs)
python -c "import secrets; print(secrets.token_hex(32))" > .code-scalpel/.secrets/hmac.key
chmod 400 .code-scalpel/.secrets/hmac.key
```

---

## Migration Guide

### From v2.5.0 to v3.1.0

**Before (v2.5.0):**
```python
# Separate imports and evaluations
from code_scalpel.policy_engine import PolicyEngine
from code_scalpel.policy import ChangeBudget

policy_engine = PolicyEngine("policy.yaml")
budget = ChangeBudget("budgets.yaml")

policy_decision = policy_engine.evaluate(operation)
budget_decision = budget.evaluate(operation)

# Manual combination
allowed = policy_decision.allowed and budget_decision.allowed
```

**After (v3.1.0):**
```python
# Single unified import and evaluation
from code_scalpel.governance import UnifiedGovernance

gov = UnifiedGovernance(".code-scalpel")
decision = gov.evaluate(operation)

# Automatic combination with detailed violation breakdown
if decision.allowed:
    proceed()
```

---

## Resources

- **Policy Engine Documentation:** [policy_engine/README.md](../policy_engine/README.md)
- **Change Budget Documentation:** [policy/README.md](../policy/README.md)
- **Configuration Guide:** [.code-scalpel/README.md](../../../.code-scalpel/README.md)
- **OPA Documentation:** https://www.openpolicyagent.org/docs/

---

**Document Version:** 1.0  
**Last Updated:** December 21, 2025  
**Maintainer:** Code Scalpel Team
