# Policy Engine Architecture

**Version:** 3.1.0  
**Last Updated:** December 21, 2025  
**Status:** Production-Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Core Components](#core-components)
4. [Integration with Code Scalpel](#integration-with-code-scalpel)
5. [Security Model](#security-model)
6. [Usage Patterns](#usage-patterns)
7. [Configuration](#configuration)
8. [Extension Points](#extension-points)
9. [Best Practices](#best-practices)

---

## Overview

The **Policy Engine** is Code Scalpel's enterprise-grade governance system that provides declarative, programmatic control over AI agent code modifications. It implements a **FAIL CLOSED** security model where any error results in operation denial, ensuring maximum safety for production systems.

### Key Capabilities

- **Declarative Policy-as-Code** using Open Policy Agent (OPA) Rego language
- **Quantitative Change Budgeting** to prevent runaway modifications
- **Semantic Security Analysis** for SQL injection, XSS, and other vulnerabilities
- **Role-Based Governance** with policy inheritance
- **Human Override System** with audit trails and TOTP-based verification
- **Tamper-Resistant Enforcement** using cryptographic verification
- **Compliance Reporting** with metrics and analytics

### Version History

| Version | Date | Features |
|---------|------|----------|
| 1.0.0 | 2024 | Initial policy engine with OPA/Rego |
| 2.5.0 | Dec 2024 | Guardian release - Tamper resistance, semantic analysis |
| 3.0.0 | Dec 2024 | Change budgeting, blast radius control |
| 3.1.0 | Dec 2024 | Unified governance system |

---

## Architecture

### Three-Tier Governance System

The policy engine implements a layered architecture with three complementary enforcement mechanisms:

```
┌─────────────────────────────────────────────────────────┐
│              UNIFIED GOVERNANCE LAYER                    │
│  (Orchestrates policy, budget, and semantic checks)     │
└─────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   POLICY     │  │   BUDGET     │  │  SEMANTIC    │
│   ENGINE     │  │   CONTROL    │  │  ANALYZER    │
│              │  │              │  │              │
│ OPA/Rego     │  │ Quantitative │  │ Pattern      │
│ Rules        │  │ Limits       │  │ Detection    │
└──────────────┘  └──────────────┘  └──────────────┘
        │                  │                  │
        └──────────────────┴──────────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │   AUDIT & COMPLIANCE    │
              │   - Logging             │
              │   - Reporting           │
              │   - Metrics             │
              └─────────────────────────┘
```

### Module Organization

```
code_scalpel/
├── policy_engine/              # Core OPA/Rego enforcement
│   ├── policy_engine.py        # PolicyEngine class
│   ├── semantic_analyzer.py    # Security pattern detection
│   ├── tamper_resistance.py    # Cryptographic integrity
│   ├── crypto_verify.py        # HMAC/manifest verification
│   ├── audit_log.py            # HMAC-signed audit trail
│   ├── models.py               # Data models
│   └── exceptions.py           # Custom exceptions
│
├── policy/                     # Change budget control
│   └── change_budget.py        # ChangeBudget class
│
└── governance/                 # Unified governance system
    ├── unified_governance.py   # UnifiedGovernance class
    ├── compliance_reporter.py  # Metrics and reporting
    ├── audit_log.py            # Governance audit logging
    └── policy_engine.py        # Legacy wrapper (deprecated)
```

---

## Core Components

### 1. Policy Engine (`policy_engine.policy_engine`)

**Purpose:** Evaluate code operations against declarative Rego policies

**Key Classes:**
- `PolicyEngine`: Main policy evaluation engine
- `Policy`: Represents a single Rego policy rule
- `PolicyDecision`: Result of policy evaluation
- `Operation`: Code modification operation to evaluate

**Features:**
- Load policies from YAML configuration files
- Execute Rego rules via OPA CLI
- Support DENY, WARN, and AUDIT actions
- Policy violation tracking with severity levels
- Human override system with time-limited codes

**Example:**
```python
from code_scalpel.policy_engine import PolicyEngine, Operation

# Initialize with policy file
engine = PolicyEngine(".code-scalpel/policy.yaml")

# Define operation to check
operation = Operation(
    type="code_edit",
    code='cursor.execute("SELECT * FROM users WHERE id=" + user_id)',
    language="python",
    file_path="app.py"
)

# Evaluate against policies
decision = engine.evaluate(operation)

if not decision.allowed:
    print(f"DENIED: {decision.reason}")
    for violation in decision.violations:
        print(f"  [{violation.severity}] {violation.policy_name}")
        print(f"    {violation.message}")
```

**Policy YAML Structure:**
```yaml
policies:
  - name: no-raw-sql
    description: Prevent raw SQL injection vulnerabilities
    severity: CRITICAL
    action: DENY
    rule: |
      package code_scalpel.policy
      
      default allow = false
      
      allow {
        not contains_sql_injection
      }
      
      contains_sql_injection {
        contains(input.code, "execute(")
        contains(input.code, "+")
      }
```

### 2. Semantic Analyzer (`policy_engine.semantic_analyzer`)

**Purpose:** Detect security vulnerabilities through semantic code analysis

**Key Features:**
- SQL injection detection (concatenation, f-strings, format, StringBuilder)
- XSS vulnerability detection (coming soon)
- Path traversal detection (coming soon)
- Command injection detection (coming soon)

**Supported Languages:**
- Python (AST-based analysis)
- Java (pattern matching)
- JavaScript/TypeScript (pattern matching)

**Example:**
```python
from code_scalpel.policy_engine.semantic_analyzer import SemanticAnalyzer

analyzer = SemanticAnalyzer()

# Detects SQL via concatenation
code1 = 'query = "SELECT * FROM users WHERE id=" + user_id'
has_sql1 = analyzer.contains_sql_sink(code1, "python")  # True

# Detects SQL via f-string
code2 = 'query = f"SELECT * FROM {table} WHERE id={user_id}"'
has_sql2 = analyzer.contains_sql_sink(code2, "python")  # True

# Safe parameterized query
code3 = 'cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))'
has_sql3 = analyzer.contains_sql_sink(code3, "python")  # False
```

**Detection Methods:**

| Language | Method | Patterns Detected |
|----------|--------|-------------------|
| Python | AST parsing | String concatenation (+), f-strings, .format(), % formatting |
| Java | Regex patterns | StringBuilder.append(), StringBuffer, String + operations |
| JavaScript | Regex patterns | Template literals, string concatenation |

### 3. Change Budget Control (`policy.change_budget`)

**Purpose:** Enforce quantitative limits on code modifications

**Key Classes:**
- `ChangeBudget`: Budget configuration and validation
- `Operation`: Code change operation
- `FileChange`: Changes to a single file
- `BudgetViolation`: Budget constraint violation

**Budget Constraints:**
```yaml
budgets:
  default:
    max_files: 10           # Maximum files modified per operation
    max_lines: 500          # Maximum total lines changed
    max_complexity: 100     # Maximum cyclomatic complexity added
    allowed_paths:          # Glob patterns for allowed files
      - "src/**/*.py"
      - "tests/**/*.py"
    forbidden_paths:        # Glob patterns for forbidden files
      - "src/core/security/**"
      - "*.config"
      - ".env*"
```

**Example:**
```python
from code_scalpel.policy import ChangeBudget, Operation, FileChange

# Load budget configuration
budget = ChangeBudget.from_yaml(".code-scalpel/budgets.yaml")

# Create operation with changes
operation = Operation(
    changes=[
        FileChange(
            file_path="src/app.py",
            added_lines=["new_code_1", "new_code_2"],
            removed_lines=["old_code"]
        )
    ],
    description="Add feature X"
)

# Validate against budget
decision = budget.evaluate(operation)

if not decision.allowed:
    print(f"Budget exceeded: {decision.reason}")
    for violation in decision.violations:
        print(f"  {violation.constraint}: {violation.actual} > {violation.limit}")
```

**Budget Metrics:**

| Metric | Description | Calculation |
|--------|-------------|-------------|
| `max_files` | File count limit | `len(operation.affected_files)` |
| `max_lines` | Line change limit | `sum(file.lines_changed)` |
| `max_complexity` | Complexity limit | AST-based cyclomatic complexity |
| Path matching | File path constraints | Glob pattern matching |

### 4. Unified Governance (`governance.unified_governance`)

**Purpose:** Orchestrate policy, budget, and semantic analysis into single decision

**Key Classes:**
- `UnifiedGovernance`: Main orchestrator
- `GovernanceDecision`: Combined evaluation result
- `GovernanceViolation`: Unified violation representation
- `ViolationSource`: Enum (POLICY, BUDGET, SEMANTIC, CONFIG)

**Features:**
- Single point of evaluation for all constraints
- Combined violation reporting
- Configurable severity-based blocking (CRITICAL, HIGH, MEDIUM)
- Decision history tracking
- Context-aware evaluation (user, session, project)

**Example:**
```python
from code_scalpel.governance import UnifiedGovernance, GovernanceContext

# Initialize with config directory
gov = UnifiedGovernance(".code-scalpel")

# Optional: Add context
context = GovernanceContext(
    user="developer@example.com",
    session_id="abc123",
    project="my-app"
)

# Evaluate operation
operation = {
    "type": "code_edit",
    "code": "cursor.execute('SELECT * FROM users')",
    "language": "python",
    "file_path": "src/database.py"
}

decision = gov.evaluate(operation, context)

if not decision.allowed:
    print(f"Governance check failed: {decision.reason}")
    
    # Violations by source
    for v in decision.policy_violations:
        print(f"[POLICY] {v.rule}: {v.message}")
    
    for v in decision.budget_violations:
        print(f"[BUDGET] {v.rule}: {v.actual}/{v.limit}")
    
    for v in decision.semantic_violations:
        print(f"[SEMANTIC] {v.rule}: {v.message}")
```

**Severity-Based Blocking:**

The unified governance system blocks operations based on violation severity:

| Severity | Source | Action |
|----------|--------|--------|
| CRITICAL | Any | Always block |
| HIGH | Any | Always block |
| MEDIUM | POLICY, BUDGET | Block |
| MEDIUM | SEMANTIC | Warn only |
| LOW | Any | Warn only |
| INFO | Any | Log only |

### 5. Tamper Resistance (`policy_engine.tamper_resistance`)

**Purpose:** Ensure policy file integrity through cryptographic verification

**Key Features:**
- SHA-256 hash verification of policy files
- HMAC-based manifest signatures
- File permission enforcement (read-only policies)
- Audit trail of access attempts

**Example:**
```python
from code_scalpel.policy_engine import TamperResistance

# Initialize tamper resistance
tr = TamperResistance(policy_path=".code-scalpel/policy.yaml")

# Automatically:
# 1. Sets policy file to read-only (chmod 444)
# 2. Computes SHA-256 hash
# 3. Stores hash in secure location
# 4. Validates on every access

# Any modification triggers TamperDetectedError
```

### 6. Audit Logging (`policy_engine.audit_log`, `governance.audit_log`)

**Purpose:** Immutable audit trail of all policy decisions

**Key Features:**
- HMAC-signed log entries (SHA-256)
- Tamper-evident sequential logging
- Structured JSON format
- Timestamped entries with millisecond precision

**Log Entry Format:**
```json
{
  "timestamp": "2025-12-21T10:30:45.123Z",
  "event_type": "policy_evaluation",
  "operation": {
    "type": "code_edit",
    "file_path": "src/app.py",
    "language": "python"
  },
  "decision": {
    "allowed": false,
    "reason": "SQL injection detected"
  },
  "violations": [...],
  "context": {
    "user": "developer@example.com",
    "session": "abc123"
  },
  "signature": "hmac-sha256:abcdef123456..."
}
```

### 7. Compliance Reporting (`governance.compliance_reporter`)

**Purpose:** Generate compliance metrics and security posture reports

**Key Features:**
- Policy violation trend analysis
- Override usage tracking
- Security posture scoring
- Recommendation generation

**Example:**
```python
from code_scalpel.governance import ComplianceReporter

reporter = ComplianceReporter(audit_log_path=".code-scalpel/audit.log")

# Generate compliance report
report = reporter.generate_report(
    start_date="2025-12-01",
    end_date="2025-12-21"
)

print(f"Total operations: {report.summary.total_operations}")
print(f"Violations: {report.summary.total_violations}")
print(f"Override rate: {report.summary.override_rate:.2%}")
print(f"Security posture: {report.security_posture.score}/100")

# Recommendations
for rec in report.recommendations:
    print(f"[{rec.priority}] {rec.title}")
    print(f"  {rec.description}")
```

---

## Integration with Code Scalpel

### Integration Points

The policy engine integrates with Code Scalpel at multiple levels:

```
┌─────────────────────────────────────────────────────┐
│         Code Scalpel Architecture                    │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────┐         ┌──────────────┐         │
│  │   MCP Server │◄────────┤ Autonomy     │         │
│  │              │         │ Engine       │         │
│  └──────┬───────┘         └──────┬───────┘         │
│         │                        │                  │
│         │   ┌────────────────────┘                  │
│         │   │                                       │
│         ▼   ▼                                       │
│  ┌──────────────────────────┐                      │
│  │  UNIFIED GOVERNANCE       │                      │
│  │  • Policy Engine          │                      │
│  │  • Budget Control         │                      │
│  │  • Semantic Analysis      │                      │
│  └──────────────────────────┘                      │
│         │                                            │
│         ▼                                            │
│  ┌──────────────────────────┐                      │
│  │   Code Modification       │                      │
│  │   • AST Tools             │                      │
│  │   • Parsers               │                      │
│  │   • IR Normalizers        │                      │
│  └──────────────────────────┘                      │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### 1. Autonomy Engine Integration

The autonomy engine (AI-driven code modification) checks governance before every change:

```python
# In autonomy/engine.py
from code_scalpel.governance import UnifiedGovernance

class AutonomyEngine:
    def __init__(self, config_dir: str):
        self.governance = UnifiedGovernance(config_dir)
    
    def apply_modification(self, operation):
        # Check governance BEFORE modification
        decision = self.governance.evaluate(operation)
        
        if not decision.allowed:
            raise PolicyViolation(decision.reason)
        
        # Proceed with modification
        return self._execute_modification(operation)
```

### 2. MCP Server Integration

The MCP (Model Context Protocol) server enforces governance at the API boundary:

```python
# In mcp/server.py
@server.tool()
async def modify_code(code: str, file_path: str):
    """MCP tool for code modification."""
    # Governance check at API boundary
    decision = governance.evaluate({
        "type": "code_edit",
        "code": code,
        "file_path": file_path
    })
    
    if not decision.allowed:
        return {
            "success": False,
            "error": decision.reason,
            "violations": [v.dict() for v in decision.violations]
        }
    
    # Proceed with modification
    return modify_code_internal(code, file_path)
```

### 3. CLI Integration

The command-line interface provides governance validation:

```bash
# Validate operation before execution
code-scalpel check --policy .code-scalpel/policy.yaml \
                   --budget .code-scalpel/budgets.yaml \
                   --operation operation.json

# Output:
# ✓ Policy check passed
# ✗ Budget check failed: max_files exceeded (15 > 10)
# ✗ Semantic check failed: SQL injection detected in src/app.py
```

### 4. Pre-commit Hook Integration

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Run governance check on staged changes
code-scalpel governance-check --staged

if [ $? -ne 0 ]; then
    echo "Governance check failed. Commit blocked."
    exit 1
fi
```

---

## Security Model

### FAIL CLOSED Architecture

The policy engine implements a **fail closed** security model where any error results in operation denial:

```
┌─────────────────────────────────────────┐
│  Evaluation Result                      │
├─────────────────────────────────────────┤
│                                          │
│  Success Cases (ALLOW):                 │
│    ✓ All policies pass                  │
│    ✓ All budgets satisfied              │
│    ✓ No semantic violations             │
│                                          │
│  Failure Cases (DENY):                  │
│    ✗ Policy violation detected          │
│    ✗ Budget exceeded                    │
│    ✗ Semantic vulnerability found       │
│    ✗ OPA CLI not available              │
│    ✗ Policy file parse error            │
│    ✗ Budget config parse error          │
│    ✗ Rego evaluation error              │
│    ✗ File not accessible                │
│    ✗ Tamper detected                    │
│    ✗ ANY exception occurred             │
│                                          │
└─────────────────────────────────────────┘
```

### Defense in Depth

Multiple layers of security enforcement:

1. **Cryptographic Integrity**
   - SHA-256 hashing of policy files
   - HMAC signatures on audit logs
   - Manifest-based verification

2. **Access Control**
   - Read-only policy files (chmod 444)
   - Secure storage of HMAC keys
   - Environment-based secret management

3. **Audit Trail**
   - Immutable log entries
   - Tamper-evident signatures
   - Full decision history

4. **Human Oversight**
   - TOTP-based override system
   - Time-limited override codes
   - Justification requirements
   - Audit of all overrides

### Threat Model

| Threat | Mitigation |
|--------|------------|
| Policy file tampering | SHA-256 verification, read-only permissions |
| Audit log manipulation | HMAC signatures, append-only logging |
| Unauthorized overrides | TOTP codes, time limits, audit trail |
| OPA CLI compromise | Hash verification, sandboxed execution |
| Configuration injection | Schema validation, type checking |
| Replay attacks | Timestamp validation, nonce usage |

---

## Usage Patterns

### Pattern 1: Basic Policy Enforcement

**Use Case:** Block SQL injection in Python code

```python
from code_scalpel.policy_engine import PolicyEngine, Operation

# 1. Create policy.yaml
policy_yaml = """
policies:
  - name: no-sql-injection
    description: Block SQL injection patterns
    severity: CRITICAL
    action: DENY
    rule: |
      package code_scalpel.policy
      default allow = false
      allow { not has_sql_injection }
      has_sql_injection {
        contains(input.code, "execute")
        contains(input.code, "+")
      }
"""

# 2. Initialize engine
engine = PolicyEngine("policy.yaml")

# 3. Evaluate operation
op = Operation(
    type="code_edit",
    code='cursor.execute("SELECT * FROM users WHERE id=" + user_id)',
    language="python"
)

decision = engine.evaluate(op)
assert not decision.allowed  # Blocked!
```

### Pattern 2: Change Budget Control

**Use Case:** Limit blast radius of modifications

```python
from code_scalpel.policy import ChangeBudget, Operation, FileChange

# 1. Create budgets.yaml
budget_yaml = """
budgets:
  default:
    max_files: 5
    max_lines: 200
    forbidden_paths:
      - "src/core/**"
"""

# 2. Load budget
budget = ChangeBudget.from_yaml("budgets.yaml")

# 3. Create operation
op = Operation(changes=[
    FileChange(
        file_path="src/app.py",
        added_lines=["line1", "line2", ...],  # 100 lines
        removed_lines=["old1", "old2", ...]   # 50 lines
    ),
    FileChange(file_path="src/utils.py", ...)
])

# 4. Validate
decision = budget.evaluate(op)
if not decision.allowed:
    print(f"Budget exceeded: {decision.violations}")
```

### Pattern 3: Unified Governance

**Use Case:** Combined policy + budget + semantic checks

```python
from code_scalpel.governance import UnifiedGovernance, GovernanceContext

# 1. Setup (one-time)
gov = UnifiedGovernance(".code-scalpel")

# 2. Add context (optional)
ctx = GovernanceContext(
    user="dev@example.com",
    session_id="abc123"
)

# 3. Evaluate
decision = gov.evaluate(operation, ctx)

# 4. Handle result
if decision.allowed:
    apply_modification(operation)
else:
    log_denial(decision)
    notify_user(decision.violations)
```

### Pattern 4: Semantic Analysis Integration

**Use Case:** Detect security vulnerabilities in code modifications

```python
from code_scalpel.policy_engine import SemanticAnalyzer

analyzer = SemanticAnalyzer()

# Check multiple vulnerabilities
def check_security(code: str, language: str) -> List[str]:
    issues = []
    
    if analyzer.contains_sql_sink(code, language):
        issues.append("SQL injection risk detected")
    
    # Future: XSS, path traversal, command injection
    
    return issues

# Use in policy evaluation
issues = check_security(operation.code, operation.language)
if issues:
    return PolicyDecision(
        allowed=False,
        reason=f"Security issues: {', '.join(issues)}"
    )
```

### Pattern 5: Human Override Workflow

**Use Case:** Allow emergency overrides with audit trail

```python
from code_scalpel.policy_engine import PolicyEngine

engine = PolicyEngine("policy.yaml")

# 1. Initial evaluation
decision = engine.evaluate(operation)

if not decision.allowed:
    # 2. Request override
    override = engine.request_override(
        operation=operation,
        decision=decision,
        justification="Emergency production fix for ticket #12345",
        human_code="abc123xyz"  # From authenticator app
    )
    
    # 3. Check override approval
    if override.approved:
        # Override granted - proceed with caution
        apply_modification(operation)
        notify_security_team(override)
    else:
        # Override denied
        escalate_to_security(operation, override.reason)
```

---

## Configuration

### Directory Structure

```
.code-scalpel/
├── policy.yaml           # OPA/Rego policies
├── budgets.yaml          # Change budget constraints
├── config.yaml           # Unified governance config
├── audit.log             # Audit trail (HMAC-signed)
├── manifest.json         # Cryptographic manifest
└── .secrets/
    └── hmac.key          # HMAC signing key
```

### policy.yaml Format

```yaml
# OPA/Rego Policy Configuration
version: "1.0"

policies:
  - name: no-raw-sql
    description: Prevent SQL injection via string concatenation
    severity: CRITICAL          # CRITICAL | HIGH | MEDIUM | LOW | INFO
    action: DENY                # DENY | WARN | AUDIT
    rule: |
      package code_scalpel.policy
      
      default allow = false
      
      # Allow if no SQL injection detected
      allow {
        not contains_sql_injection
      }
      
      # Detect SQL injection patterns
      contains_sql_injection {
        contains(input.code, "execute")
        regex.match(`SELECT|INSERT|UPDATE|DELETE`, input.code)
        contains(input.code, "+")
      }
  
  - name: no-eval
    description: Block dynamic code execution
    severity: HIGH
    action: DENY
    rule: |
      package code_scalpel.policy
      
      default allow = true
      
      allow = false {
        contains(input.code, "eval(")
      }

# Global settings
settings:
  fail_closed: true            # Fail closed on errors
  audit_all: true              # Log all evaluations
  require_justification: true  # Require override justification
  override_timeout: 300        # Override code validity (seconds)
```

### budgets.yaml Format

```yaml
# Change Budget Configuration
version: "1.0"

budgets:
  # Default budget for all operations
  default:
    max_files: 10              # Maximum files per operation
    max_lines: 500             # Maximum lines changed
    max_complexity: 100        # Maximum cyclomatic complexity added
    
    # Path constraints (glob patterns)
    allowed_paths:
      - "src/**/*.py"
      - "tests/**/*.py"
      - "docs/**/*.md"
    
    forbidden_paths:
      - "src/core/security/**"
      - "src/core/auth/**"
      - "*.config"
      - ".env*"
      - "secrets/**"
  
  # Override for critical files
  critical_files:
    applies_to:
      - "src/core/**"
      - "src/auth/**"
    max_files: 1
    max_lines: 50
    max_complexity: 10
  
  # Refactoring budget
  refactoring:
    applies_to:
      - "src/legacy/**"
    max_files: 20
    max_lines: 1000
    max_complexity: 200

# Global settings
settings:
  strict_mode: true           # Fail on any violation
  complexity_method: "cyclomatic"  # cyclomatic | cognitive
```

### config.yaml Format (Unified Governance)

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

---

## Extension Points

### 1. Custom Policy Rules (Rego)

Add domain-specific policies:

```rego
# custom-policies.rego
package code_scalpel.custom

# Prevent hardcoded secrets
deny_hardcoded_secrets {
    contains(input.code, "password")
    contains(input.code, "=")
    contains(input.code, "\"")
}

# Require specific imports
require_logging {
    input.language == "python"
    input.file_path contains "src/"
    not contains(input.code, "import logging")
}

# Architectural constraints
deny_cross_layer_access {
    input.file_path contains "presentation/"
    contains(input.code, "from database")
}
```

### 2. Custom Semantic Analyzers

Extend semantic analysis for new vulnerability types:

```python
from code_scalpel.policy_engine.semantic_analyzer import SemanticAnalyzer

class CustomSemanticAnalyzer(SemanticAnalyzer):
    def contains_xss_sink(self, code: str, language: str) -> bool:
        """Detect XSS vulnerabilities."""
        if language == "python":
            return self._detect_python_xss(code)
        return False
    
    def _detect_python_xss(self, code: str) -> bool:
        """Check for unescaped HTML output."""
        import ast
        tree = ast.parse(code)
        
        for node in ast.walk(tree):
            # Check for render_template with user input
            if isinstance(node, ast.Call):
                if self._is_render_call(node):
                    if self._has_unescaped_input(node):
                        return True
        return False
```

### 3. Custom Budget Constraints

Add new budget metrics:

```python
from code_scalpel.policy import ChangeBudget

class CustomChangeBudget(ChangeBudget):
    def calculate_technical_debt(self, operation: Operation) -> int:
        """Calculate technical debt score."""
        debt = 0
        for change in operation.changes:
            # Check for code smells
            debt += self._count_long_methods(change)
            debt += self._count_duplicates(change)
            debt += self._count_violations(change)
        return debt
    
    def validate_custom(self, operation: Operation) -> List[BudgetViolation]:
        """Custom validation logic."""
        violations = []
        
        debt = self.calculate_technical_debt(operation)
        if debt > self.config.get("max_technical_debt", 50):
            violations.append(BudgetViolation(
                constraint="max_technical_debt",
                limit=50,
                actual=debt,
                message="Technical debt threshold exceeded"
            ))
        
        return violations
```

### 4. Custom Compliance Metrics

Add domain-specific compliance tracking:

```python
from code_scalpel.governance import ComplianceReporter

class CustomComplianceReporter(ComplianceReporter):
    def calculate_hipaa_score(self) -> float:
        """Calculate HIPAA compliance score."""
        violations = self.get_hipaa_violations()
        total_ops = self.get_total_operations()
        return 100 * (1 - len(violations) / total_ops)
    
    def get_hipaa_violations(self) -> List[Violation]:
        """Get HIPAA-specific violations."""
        return [v for v in self.violations 
                if v.policy_name in ["phi-protection", "access-logging"]]
```

---

## Best Practices

### 1. Policy Design

**DO:**
- ✅ Start with CRITICAL severity, relax as needed
- ✅ Use specific, descriptive policy names
- ✅ Include justification in policy descriptions
- ✅ Test policies in AUDIT mode first
- ✅ Version control your policy files

**DON'T:**
- ❌ Create overly permissive catch-all policies
- ❌ Mix multiple concerns in one policy
- ❌ Skip policy documentation
- ❌ Hardcode environment-specific values

**Example Good Policy:**
```yaml
- name: sql-injection-protection
  description: |
    Prevents SQL injection by blocking string concatenation in database queries.
    Enforced in all production code. See SEC-101 for details.
  severity: CRITICAL
  action: DENY
  rule: |
    # Clear, focused rule
    package code_scalpel.security
    default allow = false
    allow { not has_sql_concatenation }
```

### 2. Budget Configuration

**DO:**
- ✅ Set conservative defaults
- ✅ Create role-specific budgets
- ✅ Use path patterns effectively
- ✅ Monitor budget violations
- ✅ Adjust based on metrics

**DON'T:**
- ❌ Set unlimited budgets
- ❌ Ignore forbidden_paths
- ❌ Skip complexity limits
- ❌ Use overly restrictive budgets for refactoring

**Recommended Budget Levels:**

| Operation Type | max_files | max_lines | max_complexity |
|----------------|-----------|-----------|----------------|
| Bug fix | 3 | 100 | 20 |
| Feature addition | 10 | 500 | 100 |
| Refactoring | 20 | 1000 | 200 |
| Critical security | 1 | 50 | 10 |

### 3. Semantic Analysis

**DO:**
- ✅ Run semantic analysis before policy checks
- ✅ Combine with static analysis tools
- ✅ Customize for your tech stack
- ✅ Keep analyzer patterns updated
- ✅ Log all vulnerability detections

**DON'T:**
- ❌ Rely solely on semantic analysis
- ❌ Ignore false positives
- ❌ Skip language-specific analyzers
- ❌ Forget to update detection patterns

### 4. Override Management

**DO:**
- ✅ Require strong justification
- ✅ Set short timeout periods
- ✅ Audit all overrides
- ✅ Review override patterns
- ✅ Escalate frequent overrides

**DON'T:**
- ❌ Allow unlimited overrides
- ❌ Skip override justification
- ❌ Ignore override audit logs
- ❌ Use static override codes

**Override Workflow:**
```python
# 1. Request override with justification
override = engine.request_override(
    operation=op,
    decision=decision,
    justification="Production incident #12345 - Database timeout causing service degradation",
    human_code=get_totp_code()  # From authenticator
)

# 2. Verify approval
if override.approved:
    # 3. Log override
    audit.log_override(override, operation)
    
    # 4. Proceed with operation
    result = apply_modification(operation)
    
    # 5. Notify security team
    notify_security_team({
        "operation": operation,
        "override": override,
        "result": result
    })
```

### 5. Audit and Compliance

**DO:**
- ✅ Enable audit logging for all evaluations
- ✅ Review audit logs regularly
- ✅ Generate compliance reports
- ✅ Track metrics over time
- ✅ Integrate with SIEM systems

**DON'T:**
- ❌ Disable audit logging
- ❌ Ignore compliance warnings
- ❌ Skip log retention policies
- ❌ Forget log rotation

**Audit Log Analysis:**
```python
from code_scalpel.governance import ComplianceReporter

# Generate weekly compliance report
reporter = ComplianceReporter(".code-scalpel/audit.log")
report = reporter.generate_report(
    start_date="2025-12-14",
    end_date="2025-12-21"
)

# Key metrics
print(f"Operations: {report.summary.total_operations}")
print(f"Violations: {report.summary.total_violations}")
print(f"Override rate: {report.summary.override_rate:.2%}")

# Identify trends
if report.summary.override_rate > 0.10:  # >10% overrides
    alert_security_team("High override rate detected")

# Most violated policies
for policy, count in report.top_violations:
    if count > 10:
        review_policy(policy)  # May need adjustment
```

### 6. Testing Policies

**DO:**
- ✅ Write unit tests for policies
- ✅ Test both allow and deny cases
- ✅ Use representative code samples
- ✅ Test edge cases
- ✅ Validate policy syntax

**Example Test:**
```python
import pytest
from code_scalpel.policy_engine import PolicyEngine, Operation

def test_sql_injection_policy():
    engine = PolicyEngine("test-policy.yaml")
    
    # Test 1: Should block SQL concatenation
    bad_code = 'cursor.execute("SELECT * FROM users WHERE id=" + user_id)'
    op = Operation(type="code_edit", code=bad_code, language="python")
    decision = engine.evaluate(op)
    assert not decision.allowed
    assert "no-sql-injection" in decision.violated_policies
    
    # Test 2: Should allow parameterized queries
    good_code = 'cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))'
    op = Operation(type="code_edit", code=good_code, language="python")
    decision = engine.evaluate(op)
    assert decision.allowed
    
    # Test 3: Should allow safe operations
    safe_code = 'print("Hello world")'
    op = Operation(type="code_edit", code=safe_code, language="python")
    decision = engine.evaluate(op)
    assert decision.allowed
```

### 7. Performance Optimization

**DO:**
- ✅ Cache policy evaluations when possible
- ✅ Use async evaluation for large operations
- ✅ Profile slow policies
- ✅ Batch similar operations
- ✅ Monitor evaluation latency

**DON'T:**
- ❌ Skip performance testing
- ❌ Ignore slow policy rules
- ❌ Evaluate unchanged operations
- ❌ Use blocking I/O in critical paths

---

## Conclusion

The Policy Engine architecture provides comprehensive governance for AI-driven code modifications through a three-tier system:

1. **Policy Engine** - Declarative rules via OPA/Rego
2. **Change Budgeting** - Quantitative blast radius control
3. **Semantic Analysis** - Security pattern detection

All orchestrated through the **Unified Governance** system with full audit trails, compliance reporting, and tamper-resistant enforcement.

### Key Takeaways

- **FAIL CLOSED** security model ensures maximum safety
- **Layered defense** provides redundant protection
- **Audit trails** enable compliance and forensics
- **Human overrides** balance security with practicality
- **Extensibility** allows customization for any domain

### Resources

- **Source Code:** `src/code_scalpel/policy_engine/`, `src/code_scalpel/governance/`
- **Tests:** `tests/test_policy_engine.py`, `tests/test_unified_governance.py`
- **Examples:** `examples/policy_examples/`
- **OPA Documentation:** https://www.openpolicyagent.org/docs/

---

**Document Version:** 1.0  
**Last Updated:** December 21, 2025  
**Maintainer:** Code Scalpel Team
