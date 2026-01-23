# Demo 4: Enterprise Features - For Organizations at Scale
 
**Duration**: 20-30 minutes
**Audience**: CTOs, Security teams, Enterprise architects
**Goal**: Demonstrate Enterprise-exclusive capabilities for compliance, governance, and advanced security
 
---
 
## 🎯 Key Message
 
**"Enterprise tier provides the governance, compliance, and advanced analysis capabilities that regulated industries and large organizations require."**
 
---
 
## 🏢 Enterprise Tier Exclusive Features
 
| Feature | Pro | Enterprise | Use Case |
|---------|-----|------------|----------|
| **Cross-File Taint Tracking** | ❌ | ✅ | Trace vulnerabilities across 10+ files |
| **Custom Policy Engine** | ❌ | ✅ | Enforce org-specific standards |
| **Compliance Reporting** | ❌ | ✅ | SOC2, PCI-DSS, HIPAA audits |
| **Reachability Analysis** | ❌ | ✅ | Is vulnerable code actually called? |
| **Priority Ordering** | ❌ | ✅ | Business impact + technical severity |
| **Bug Reproduction** | ❌ | ✅ | Generate PoC from crash logs |
| **Type Contract Validation** | ❌ | ✅ | Frontend/backend type safety |
| **Zod Schema Generation** | ❌ | ✅ | Runtime validation from types |
| **Custom Security Rules** | ❌ | ✅ | Organization-specific patterns |
| **File Size Limit** | 10MB | 100MB | Handle large generated files |
| **Cryptographic Policies** | ❌ | ✅ | Tamper-proof policy signatures |
 
---
 
## 💰 Enterprise ROI
 
**Enterprise Tier Cost**: Custom pricing (typically $200-500/seat/month)
 
**Value Delivered**:
- **Compliance audit prep** = $50,000-200,000 saved per audit
- **Data breach prevention** = $4.45M average breach cost avoided
- **False positive reduction** = 80% fewer wasted hours
- **Onboarding acceleration** = 50% faster for new developers
- **M&A due diligence** = $100,000+ in security assessment savings
- **Custom policy enforcement** = 90% reduction in standards violations
 
**Break-even**: Avoid one compliance violation or pass one audit faster.
 
---
 
## 🎬 Demo Script
 
### Part 1: Cross-File Taint Tracking (6 minutes)
 
**Scenario**: Vulnerability originates in one file, flows through 5+ files, and manifests in a completely different module
 
#### 1.1 The Challenge with Pro Tier
 
**Setup**: Multi-file application with SQL injection that spans 4 files
 
```
user_input (routes.py)
  ↓
validate_input (validators.py) [bypassed]
  ↓
build_query (query_builder.py) [vulnerable concatenation]
  ↓
execute_query (database.py) [executes unsafe SQL]
```
 
**Pro Tier Analysis** (single-file focused):
```json
{
  "file": "database.py",
  "findings": [
    {
      "type": "sql_injection",
      "line": 45,
      "message": "SQL injection risk - dynamic query",
      "confidence": 0.40,  // Low confidence - can't trace source
      "notes": "Unable to determine if input is sanitized upstream"
    }
  ]
}
```
 
**Talking Point**:
> "Pro tier finds the vulnerability in database.py but can't tell if it's a real issue or if the input was sanitized earlier. With 40% confidence, you'd likely ignore this finding. That's a mistake."
 
---
 
#### 1.2 Enterprise Tier: Full Taint Flow Analysis
 
**Enterprise Tier Analysis**:
```json
{
  "finding_id": "TAINT-001",
  "type": "sql_injection",
  "severity": "critical",
  "confidence": 0.95,  // High confidence with full trace
 
  "taint_flow": {
    "source": {
      "file": "routes.py",
      "line": 12,
      "function": "search_products",
      "variable": "request.args['query']",
      "classification": "untrusted_user_input"
    },
 
    "propagation": [
      {
        "file": "routes.py",
        "line": 13,
        "function": "search_products",
        "operation": "passed_to_function",
        "target": "validate_input(query)"
      },
      {
        "file": "validators.py",
        "line": 8,
        "function": "validate_input",
        "operation": "validation_bypassed",
        "reason": "Returns None instead of raising exception",
        "taint_status": "still_tainted"
      },
      {
        "file": "query_builder.py",
        "line": 25,
        "function": "build_search_query",
        "operation": "string_concatenation",
        "code": "f\"SELECT * FROM products WHERE name LIKE '%{search_term}%'\"",
        "taint_status": "propagated_to_sql"
      },
      {
        "file": "database.py",
        "line": 45,
        "function": "execute_query",
        "operation": "executed_as_sql",
        "sink": "cursor.execute(query)",
        "taint_status": "vulnerability_realized"
      }
    ],
 
    "sanitizers_encountered": [
      {
        "file": "validators.py",
        "line": 5,
        "function": "validate_input",
        "effectiveness": "ineffective",
        "reason": "Validation can be bypassed with None return"
      }
    ],
 
    "attack_vector": "User input → bypassed validation → string concatenation → SQL execution",
    "exploitability": "high",
    "reachability": "public_api_endpoint"
  },
 
  "remediation": {
    "primary": "Use parameterized query in query_builder.py line 25",
    "secondary": "Fix validator to raise exception instead of returning None",
    "code_fix": "cursor.execute(\"SELECT * FROM products WHERE name LIKE ?\", (f'%{search_term}%',))"
  }
}
```
 
**Talking Point**:
> "Enterprise tier traces the taint from user input through 4 files. It shows that validation was bypassed, tracks the string concatenation, and proves the vulnerability is exploitable. Confidence is now 95% instead of 40%. This is a critical fix, not a maybe."
 
**Visual Diagram** (show on screen):
```
TAINT FLOW VISUALIZATION:
 
[User Input]
    ↓ (tainted)
[Validator] ← Bypassed (still tainted)
    ↓ (tainted)
[Query Builder] ← String concatenation (taint propagated)
    ↓ (tainted SQL)
[Database] ← Executed (VULNERABILITY!)
 
FILES ANALYZED: 4
FUNCTIONS TRACED: 6
CONFIDENCE: 95%
```
 
---
 
### Part 2: Custom Policy Engine (5 minutes)
 
**Scenario**: Organization has specific coding standards beyond OWASP
 
#### 2.1 Creating a Custom Policy
 
**Organization Requirements** (example: FinTech company):
1. All financial calculations must use Decimal, not float
2. All API responses must include request_id for tracing
3. Database transactions must include audit logging
4. No direct access to user credentials (must use auth service)
5. All external API calls must have timeout and retry logic
 
**Policy Definition** (YAML):
```yaml
# .code-scalpel/policies/fintech-standards.yaml
 
policy_name: "FinTech Security & Compliance Standards"
version: "2.1.0"
enforced_by: "Security Team"
signature: "..." # Cryptographic signature (tamper-proof)
 
rules:
  - id: "FINTECH-001"
    name: "Use Decimal for Currency"
    severity: "high"
    description: "Financial calculations must use Decimal to avoid floating-point errors"
    pattern:
      language: "python"
      code: |
        def ${func_name}(*${params}):
          ${body}
          ${result} = ${left} * ${right}  # or + or - or /
      where:
        - func_name contains ["calculate", "total", "price", "amount", "payment"]
        - left.type == "float" OR right.type == "float"
    fix_suggestion: "from decimal import Decimal; use Decimal('${value}')"
 
  - id: "FINTECH-002"
    name: "API Responses Must Include Trace ID"
    severity: "medium"
    description: "All API responses must include request_id for distributed tracing"
    pattern:
      language: "python"
      code: |
        @app.route(${path})
        def ${func_name}():
          return ${response}
      where:
        - response is dict or jsonify()
        - "request_id" not in response.keys
    fix_suggestion: "Add request_id to response: {'request_id': g.request_id, ...}"
 
  - id: "FINTECH-003"
    name: "Database Transactions Must Be Audited"
    severity: "critical"
    description: "All database writes must log to audit trail"
    pattern:
      language: "python"
      code: |
        ${db_call}(${operation})
      where:
        - db_call in ["session.add", "session.delete", "cursor.execute"]
        - operation contains ["INSERT", "UPDATE", "DELETE"]
        - not followed by "audit_log.create"
    fix_suggestion: "Add audit logging after DB operation"
 
  - id: "FINTECH-004"
    name: "No Direct Credential Access"
    severity: "critical"
    description: "Access user credentials only through auth service"
    pattern:
      language: "python"
      code: |
        ${var} = ${user}.password
      where:
        - user is User model or similar
        - not in file "auth/service.py"
    fix_suggestion: "Use auth_service.verify_password() instead"
 
  - id: "FINTECH-005"
    name: "External API Calls Must Have Timeouts"
    severity: "high"
    description: "Prevent hanging on external service failures"
    pattern:
      language: "python"
      code: |
        requests.${method}(${url}, ${kwargs})
      where:
        - "timeout" not in kwargs
    fix_suggestion: "Add timeout parameter: requests.get(url, timeout=5)"
```
 
---
 
#### 2.2 Running Policy Checks
 
**Prompt**: `Check code against our FinTech policy`
 
**Tool Call**: `code_policy_check`
```json
{
  "policy_file": ".code-scalpel/policies/fintech-standards.yaml",
  "scope": "project",
  "fail_on_violations": false
}
```
 
**Enterprise Tier Output**:
```json
{
  "policy": "FinTech Security & Compliance Standards v2.1.0",
  "policy_verified": true,  // Cryptographic signature valid
  "policy_signature_valid": true,
  "enforced_by": "Security Team",
 
  "violations": [
    {
      "rule_id": "FINTECH-001",
      "file": "billing/calculator.py",
      "line": 34,
      "code": "total = price * quantity",
      "severity": "high",
      "message": "Financial calculation using float instead of Decimal",
      "fix": "from decimal import Decimal; total = Decimal(str(price)) * Decimal(str(quantity))",
      "compliance_impact": "PCI-DSS 6.5.8 - Calculation errors"
    },
    {
      "rule_id": "FINTECH-002",
      "file": "api/routes.py",
      "line": 67,
      "code": "return jsonify({'status': 'success', 'data': result})",
      "severity": "medium",
      "message": "API response missing request_id for tracing",
      "fix": "return jsonify({'request_id': g.request_id, 'status': 'success', 'data': result})"
    },
    {
      "rule_id": "FINTECH-004",
      "file": "admin/users.py",
      "line": 89,
      "code": "if user.password == input_password:",
      "severity": "critical",
      "message": "Direct access to user credentials outside auth service",
      "fix": "Use: auth_service.verify_password(user.id, input_password)",
      "compliance_impact": "SOC2 CC6.1 - Logical access controls"
    }
  ],
 
  "summary": {
    "total_files_scanned": 156,
    "total_violations": 3,
    "critical": 1,
    "high": 1,
    "medium": 1,
    "low": 0,
    "pass": false
  }
}
```
 
**Talking Point**:
> "Enterprise tier lets you codify your organization's standards. This FinTech company requires Decimal for money, request IDs for tracing, and no direct credential access. These aren't OWASP issues - they're your business requirements. Enterprise tier enforces them automatically."
 
---
 
#### 2.3 Policy Signature Verification
 
**Security Feature**: Policies are cryptographically signed to prevent tampering
 
**Tool Call**: `verify_policy_integrity`
```json
{
  "policy_file": ".code-scalpel/policies/fintech-standards.yaml",
  "public_key_file": ".code-scalpel/public_key.pem"
}
```
 
**Output**:
```json
{
  "policy_file": "fintech-standards.yaml",
  "signature_valid": true,
  "signer": "security-team@company.com",
  "signed_at": "2026-01-15T10:00:00Z",
  "expires_at": "2027-01-15T10:00:00Z",
  "tampered": false,
  "message": "Policy signature is valid and has not been tampered with"
}
```
 
**Talking Point**:
> "Policies are cryptographically signed by your security team. Developers can't modify or bypass them. This ensures consistent enforcement across your entire organization."
 
---
 
### Part 3: Compliance Reporting (4 minutes)
 
**Scenario**: SOC2 audit requires evidence of secure coding practices
 
#### 3.1 Generate Compliance Report
 
**Prompt**: `Generate SOC2 compliance report for this codebase`
 
**Tool Call**: `code_policy_check` with `compliance_framework: "soc2"`
```json
{
  "compliance_framework": "soc2",
  "scope": "project",
  "output_format": "audit_report"
}
```
 
**Enterprise Tier Output**: `soc2-compliance-report-2026-01-19.pdf`
 
```markdown
# SOC2 Compliance Report
**Date**: January 19, 2026
**Organization**: Example Corp
**Codebase**: Production v3.2.1
**Auditor**: Code Scalpel Enterprise v1.0.0
 
## Executive Summary
- **Total Files Analyzed**: 1,247
- **Compliance Status**: 94.3% compliant
- **Critical Issues**: 2
- **High Issues**: 15
- **Medium Issues**: 42
 
## SOC2 Trust Service Criteria Coverage
 
### CC6.1 - Logical and Physical Access Controls
**Status**: ✅ 98% Compliant
 
**Requirements**:
- Access to credentials must be controlled
- Authentication mechanisms must be secure
- Session management must be robust
 
**Findings**:
✅ PASS: All authentication uses bcrypt with cost factor ≥ 12
✅ PASS: Session tokens are cryptographically random (32 bytes)
✅ PASS: No hardcoded credentials found in 1,247 files
❌ FAIL: 2 instances of weak password validation (CC6.1.4)
 
**Evidence**:
- File: auth/password_policy.py, Line: 23
  - Issue: Minimum password length is 6 (should be 12)
  - Recommendation: Update PASSWORD_MIN_LENGTH = 12
 
### CC6.6 - Logical and Physical Access Control - Encryption
**Status**: ✅ 100% Compliant
 
✅ PASS: All data at rest uses AES-256
✅ PASS: All API endpoints enforce TLS 1.2+
✅ PASS: No weak cryptography detected (no MD5, SHA1, DES)
 
### CC6.7 - System Operations - Data Transmission
**Status**: ⚠️ 91% Compliant
 
❌ FAIL: 15 HTTP requests without timeout (DoS risk)
❌ FAIL: 3 external API calls without rate limiting
 
**Remediation Required**:
1. Add timeout to all requests.get() calls
2. Implement rate limiting on external integrations
3. Expected effort: 8 hours
 
### CC7.2 - System Monitoring - Threat Detection
**Status**: ✅ 97% Compliant
 
✅ PASS: Security scanning integrated in CI/CD
✅ PASS: Dependency vulnerability scanning active
❌ FAIL: 42 info-level security findings not tracked
 
## Audit Evidence
 
**Scan Metadata**:
- Scan ID: SCAN-20260119-1234
- Duration: 18 minutes 32 seconds
- Tools Used: Code Scalpel Enterprise v1.0.0
- Signature: [Cryptographic hash of scan results]
 
**Attestation**:
This report was generated by Code Scalpel Enterprise with tamper-proof
logging. All findings are reproducible and can be re-verified.
 
Signed by: security-automation@example.com
Timestamp: 2026-01-19T14:32:00Z
Report Hash: sha256:a1b2c3d4e5f6...
```
 
**Talking Point**:
> "Enterprise tier generates audit-ready compliance reports mapped to SOC2, PCI-DSS, HIPAA, or custom frameworks. Hand this to your auditor - no manual evidence gathering required. This saves weeks of audit prep."
 
---
 
### Part 4: Reachability Analysis (4 minutes)
 
**Scenario**: You found 100 vulnerabilities. Which ones can attackers actually reach?
 
#### 4.1 The Problem with Traditional Scanning
 
**Traditional Output** (Pro tier):
```json
{
  "findings": [
    {"type": "sql_injection", "file": "legacy/admin_panel.py", "line": 45},
    {"type": "xss", "file": "api/search.py", "line": 102},
    {"type": "command_injection", "file": "utils/diagnostics.py", "line": 234},
    // ... 97 more findings
  ],
  "total": 100
}
```
 
**Talking Point**:
> "Pro tier found 100 issues. But are they all exploitable? Is the vulnerable code even reachable from user input? You don't know. So you waste time triaging all 100."
 
---
 
#### 4.2 Enterprise Tier: Reachability Analysis
 
**Enterprise Tier Output**:
```json
{
  "findings": [
    {
      "type": "sql_injection",
      "file": "legacy/admin_panel.py",
      "line": 45,
      "reachability": {
        "status": "unreachable",
        "reason": "Function is never called in codebase",
        "last_used": "2023-04-12 (deprecated)",
        "priority": "low",
        "recommendation": "Remove dead code"
      }
    },
    {
      "type": "xss",
      "file": "api/search.py",
      "line": 102,
      "reachability": {
        "status": "publicly_reachable",
        "entry_points": [
          "POST /api/search (public, no auth)"
        ],
        "call_chain": [
          "flask_app.route('/api/search') → search_handler() → render_results() → [VULN]"
        ],
        "priority": "critical",
        "recommendation": "Fix immediately - public API endpoint"
      }
    },
    {
      "type": "command_injection",
      "file": "utils/diagnostics.py",
      "line": 234,
      "reachability": {
        "status": "internal_only",
        "entry_points": [
          "Admin panel (requires root privileges)"
        ],
        "authentication_required": "admin_role",
        "priority": "medium",
        "recommendation": "Fix during next sprint - low exploitability"
      }
    }
  ],
 
  "summary": {
    "total_findings": 100,
    "publicly_reachable": 12,  // FIX THESE FIRST
    "authenticated_reachable": 23,  // FIX NEXT
    "internal_only": 38,  // Lower priority
    "unreachable_dead_code": 27,  // Can delete
    "time_saved": "80% reduction in triage effort"
  }
}
```
 
**Talking Point**:
> "Enterprise tier performs reachability analysis. Of 100 findings, only 12 are publicly reachable. Those are your critical fixes. 27 are in dead code that should be deleted. Reachability analysis reduces triage time by 80%."
 
**Visual Priority Matrix**:
```
PRIORITY MATRIX (Enterprise Tier):
 
         │ High Severity  │ Medium        │ Low
─────────┼────────────────┼───────────────┼─────────
Public   │ 🔴 12 (P0)    │ 🟡 18 (P1)    │ 🟢 5 (P2)
API      │ FIX NOW       │ THIS WEEK     │ THIS MONTH
─────────┼────────────────┼───────────────┼─────────
Auth     │ 🟡 8 (P1)     │ 🟢 15 (P2)    │ ⚪ 12 (P3)
Required │ THIS WEEK     │ THIS MONTH    │ BACKLOG
─────────┼────────────────┼───────────────┼─────────
Internal │ 🟢 3 (P2)     │ ⚪ 22 (P3)    │ ⚪ 13 (P3)
Only     │ THIS MONTH    │ BACKLOG       │ OPTIONAL
─────────┼────────────────┼───────────────┼─────────
Dead     │ 🗑️ 27 (DELETE)│               │
Code     │ REMOVE        │               │
 
Action Plan:
  Week 1: Fix 12 public high-severity
  Week 2-4: Fix 8 auth high + 18 public medium
  Month 2: Fix remaining authenticated issues
  Backlog: Internal-only issues
  Cleanup: Delete 27 dead code files
```
 
---
 
### Part 5: Type Evaporation Detection (4 minutes)
 
**Scenario**: TypeScript frontend → Python backend → Types become `any`
 
#### 5.1 The Type Safety Problem
 
**Frontend** (TypeScript):
```typescript
// frontend/src/api/users.ts
interface User {
  id: number;
  email: string;
  role: 'admin' | 'user' | 'guest';
  balance: number;
}
 
async function updateUser(userId: number, updates: Partial<User>): Promise<User> {
  const response = await fetch(`/api/users/${userId}`, {
    method: 'PATCH',
    body: JSON.stringify(updates)
  });
  return response.json();  // Type is "any" at runtime!
}
```
 
**Backend** (Python):
```python
# backend/api/users.py
@app.route('/api/users/<user_id>', methods=['PATCH'])
def update_user(user_id):
    updates = request.json  # Type is unknown!
    user = User.query.get(user_id)
 
    # Mass assignment vulnerability - no type validation
    for key, value in updates.items():
        setattr(user, key, value)
 
    db.session.commit()
    return jsonify(user.to_dict())
```
 
**Problem**:
- Frontend thinks it's type-safe
- Network boundary erases types
- Backend accepts anything
- Attacker sends: `{"balance": 9999999, "role": "admin"}`
 
---
 
#### 5.2 Enterprise Tier: Type Evaporation Detection
 
**Tool Call**: `type_evaporation_scan`
```json
{
  "frontend_dir": "frontend/src",
  "backend_dir": "backend/api",
  "api_contracts": true
}
```
 
**Enterprise Tier Output**:
```json
{
  "type_evaporation_findings": [
    {
      "contract_id": "UpdateUser",
      "frontend_endpoint": "PATCH /api/users/:id",
      "frontend_file": "frontend/src/api/users.ts",
      "frontend_type": "Partial<User>",
 
      "backend_endpoint": "PATCH /api/users/<user_id>",
      "backend_file": "backend/api/users.py",
      "backend_type": "Any",  // ❌ No validation
 
      "type_evaporation": {
        "severity": "critical",
        "status": "types_lost_at_boundary",
        "frontend_expects": {
          "id": "number",
          "email": "string",
          "role": "'admin' | 'user' | 'guest'",
          "balance": "number"
        },
        "backend_validates": {},  // ❌ Nothing!
        "attack_vector": "Mass assignment - can modify any field",
        "exploitability": "high"
      },
 
      "remediation": {
        "recommendation": "Add runtime validation with Zod schema",
        "auto_generated_schema": {
          "language": "python",
          "library": "pydantic",
          "code": `
from pydantic import BaseModel, Field
from typing import Literal, Optional
 
class UserUpdateSchema(BaseModel):
    id: Optional[int] = None
    email: Optional[str] = Field(None, regex=r'^[^@]+@[^@]+\.[^@]+$')
    role: Optional[Literal['admin', 'user', 'guest']] = None
    balance: Optional[float] = Field(None, ge=0)
 
    class Config:
        extra = 'forbid'  # Reject unknown fields
 
@app.route('/api/users/<user_id>', methods=['PATCH'])
def update_user(user_id):
    updates = UserUpdateSchema(**request.json)  # Validated!
    # ... safe to use updates
`
        }
      }
    }
  ],
 
  "summary": {
    "total_api_contracts": 47,
    "type_safe_contracts": 12,
    "type_evaporation_found": 35,
    "critical_evaporations": 8,
    "risk_level": "high"
  }
}
```
 
**Talking Point**:
> "Enterprise tier detects 'type evaporation' - where frontend types disappear at API boundaries. It generates runtime validation schemas (Pydantic, Zod) to enforce contracts. This prevents mass assignment, type confusion, and API breaking changes."
 
---
 
### Part 6: Bug Reproduction from Crash Logs (3 minutes)
 
**Scenario**: Production crash - need to reproduce locally
 
#### 6.1 Crash Log Input
 
**Production Error Log**:
```
[ERROR] 2026-01-19 14:32:18 - Unhandled exception in payment processing
Traceback (most recent call last):
  File "/app/billing/payments.py", line 89, in process_payment
    total = calculate_total(items, discount_code)
  File "/app/billing/calculator.py", line 34, in calculate_total
    tax = calculate_tax(subtotal, state)
  File "/app/billing/calculator.py", line 12, in calculate_tax
    rate = TAX_RATES[state]
KeyError: 'PR'
 
Request data:
  user_id: 12345
  items: [{"id": "SKU-001", "price": 29.99, "qty": 2}]
  state: "PR"  # Puerto Rico - not in TAX_RATES dict
  discount: "SAVE10"
```
 
---
 
#### 6.2 Enterprise Tier: Auto-Generate Reproduction Test
 
**Prompt**: `Generate a test to reproduce this crash`
 
**Tool Call**: `generate_unit_tests` with `bug_reproduction: true`
```json
{
  "crash_log": "path/to/crash.log",
  "include_fix": true
}
```
 
**Enterprise Tier Output**:
```python
# tests/test_bug_reproduction_PR_tax.py
# Auto-generated by Code Scalpel Enterprise
# Crash ID: CRASH-20260119-143218
 
import pytest
from billing.calculator import calculate_tax, calculate_total
 
def test_reproduce_crash_puerto_rico_tax():
    """
    Reproduces production crash: KeyError for Puerto Rico tax rate
 
    Production Crash: 2026-01-19 14:32:18
    Error: KeyError: 'PR'
    File: billing/calculator.py:12
    """
    state = "PR"  # Puerto Rico
    amount = 59.98  # From crash log: 2 × $29.99
 
    # This will raise KeyError (reproducing the bug)
    with pytest.raises(KeyError) as exc_info:
        calculate_tax(amount, state)
 
    assert str(exc_info.value) == "'PR'"
 
def test_bug_fix_puerto_rico_tax():
    """
    Verifies the bug fix works correctly.
 
    Fix: Add default value for unknown states
    """
    state = "PR"
    amount = 59.98
 
    # After fix, should return 0.0 (no tax) or appropriate PR rate
    tax = calculate_tax(amount, state)
    assert tax == 0.0 or tax == pytest.approx(6.59, 0.01)  # 11% PR rate
 
# Suggested fix:
"""
def calculate_tax(amount: float, state: str) -> float:
    # BEFORE (crashes on unknown states):
    rate = TAX_RATES[state]
 
    # AFTER (handles unknown states gracefully):
    rate = TAX_RATES.get(state, 0.0)  # Default to 0% for unknown states
 
    return round(amount * rate, 2)
"""
```
 
**Talking Point**:
> "Enterprise tier analyzes crash logs and generates exact reproduction tests. It extracts the input data from logs, recreates the error state, and suggests the fix. This turns a 4-hour debugging session into a 10-minute fix."
 
---
 
## 🎤 Presentation Talking Points
 
### Opening (2 minutes)
 
> "Enterprise tier is designed for organizations with regulatory requirements, complex codebases, and the need for governance. It builds on everything in Pro tier and adds capabilities that large organizations require."
 
### Key Differentiators (throughout demo)
 
**1. Cross-File Intelligence**:
> "Enterprise tier doesn't analyze files in isolation. It traces vulnerabilities across your entire architecture. This finds issues that single-file analysis misses."
 
**2. Custom Policies**:
> "Your organization has standards beyond OWASP. Enterprise tier lets you encode those as tamper-proof policies that auto-enforce across all developers."
 
**3. Compliance Automation**:
> "Audits are expensive and time-consuming. Enterprise tier generates compliance reports automatically. SOC2, PCI-DSS, HIPAA - whatever you need."
 
**4. Intelligent Prioritization**:
> "Reachability analysis tells you which vulnerabilities attackers can actually exploit. Fix 12 critical issues instead of triaging 100."
 
**5. Type Safety Across Boundaries**:
> "Modern apps have type-safe frontends and backends - but types evaporate at API boundaries. Enterprise tier detects this and generates runtime validation."
 
### ROI Closing (3 minutes)
 
> "Enterprise tier pricing is custom based on your organization size, but let's talk ROI:"
>
> **Compliance Audit Savings**:
> - Manual audit prep: 4 weeks × 2 engineers × $150/hour = $96,000
> - With Enterprise automated reports: 3 days × 1 engineer = $3,600
> - **Savings: $92,400 per audit**
>
> **Breach Prevention**:
> - Average data breach cost: $4.45 million
> - Enterprise tier finds cross-file vulnerabilities others miss
> - **Value: Priceless if it prevents one breach**
>
> **Developer Productivity**:
> - Reachability analysis: 80% less triage time = 20 hours/month saved
> - Custom policies: 90% fewer standards violations = 10 hours/month saved
> - Type evaporation detection: 50% fewer runtime errors = 15 hours/month saved
> - **Total: 45 hours/month × $150/hour × 50 developers = $337,500/month**
>
> "Enterprise tier pays for itself many times over in audit savings alone, before considering breach prevention and productivity gains."
 
---
 
## 📊 Tier Comparison Summary
 
| Feature | Community | Pro | Enterprise |
|---------|-----------|-----|------------|
| All tools | ✅ | ✅ | ✅ |
| Findings limit | 50 | ♾️ | ♾️ |
| File size | 1MB | 10MB | 100MB |
| Basic security | ✅ | ✅ | ✅ |
| Advanced security | ❌ | ✅ | ✅ |
| Sanitizer recognition | ❌ | ✅ | ✅ |
| Confidence scoring | ❌ | ✅ | ✅ |
| **Cross-file taint** | ❌ | ❌ | ✅ |
| **Custom policies** | ❌ | ❌ | ✅ |
| **Compliance reports** | ❌ | ❌ | ✅ |
| **Reachability analysis** | ❌ | ❌ | ✅ |
| **Type evaporation** | ❌ | ❌ | ✅ |
| **Bug reproduction** | ❌ | ❌ | ✅ |
| **Crypto signatures** | ❌ | ❌ | ✅ |
| **Price** | **Free** | **$29-49/mo** | **Custom** |
| **Best for** | **Individuals** | **Teams** | **Organizations** |
 
---
 
## ❓ Anticipated Questions
 
**Q: What size organization needs Enterprise tier?**
A: Typically 50+ developers, regulated industries (FinTech, HealthTech, GovTech), or companies with compliance requirements (SOC2, PCI-DSS, HIPAA).
 
**Q: Can we start with Pro and upgrade later?**
A: Absolutely. Many customers start with Pro and upgrade when they need compliance reporting or cross-file analysis.
 
**Q: Do you offer proof-of-concept trials?**
A: Yes. We provide 30-day Enterprise trials with full support to evaluate against your codebase.
 
**Q: Can Enterprise tier integrate with our CI/CD?**
A: Yes. Enterprise tier includes CI/CD integrations for Jenkins, GitLab, GitHub Actions, CircleCI, and custom pipelines.
 
**Q: What about on-premise deployment?**
A: Enterprise tier supports on-premise deployment for organizations with strict data residency requirements.
 
**Q: How are custom policies created?**
A: Your security team writes policies in YAML. We provide templates and support. Policies are cryptographically signed to prevent tampering.
 
**Q: What compliance frameworks do you support?**
A: SOC2, PCI-DSS, HIPAA, ISO 27001, NIST, CIS, and custom frameworks. We can map to your specific requirements.
 
---
 
## 🎁 Demo Files Included
 
- `cross_file_vuln/` - Multi-file taint flow example
- `custom_policy_example.yaml` - Sample FinTech policy
- `compliance_report_template.pdf` - SOC2 report example
- `type_evaporation_demo/` - Frontend/backend type mismatch
- `crash_log_example.txt` - Production crash for reproduction
- `enterprise_roi_calculator.xlsx` - ROI calculation tool
 
---
 
## 🎯 Success Criteria
 
After this demo, viewers should:
- ✅ Understand Enterprise is for regulated industries and large orgs
- ✅ See value in cross-file taint tracking and reachability analysis
- ✅ Recognize compliance automation as major time/cost saver
- ✅ Appreciate custom policy engine for organization-specific standards
- ✅ Feel confident requesting Enterprise trial or quote
 
---
 
## 🔗 Next Steps
 
1. 📞 **Schedule Custom Demo**: Demo with your codebase
2. 🚀 **Start Enterprise Trial**: 30-day full-access trial
3. 💬 **Talk to Solutions Team**: Custom pricing and deployment
4. 📄 **Review Case Studies**: See how similar organizations use Enterprise tier
 
---
 
**End of Demo 4**
 
*Total time: 20-30 minutes | Difficulty: Advanced | Target: Enterprise decision makers*