# Enterprise Compliance for Engineers: Technical Implementation Guide

> [20260310_DOCS] Runtime tier-gating and compliance-request semantics changed after this guide was first written. Use [../compliance/README.md](../compliance/README.md) as the current source of truth for live behavior.

**Target Audience:** Software Engineers, Platform Engineers, DevOps Engineers, Security Engineers  
**Last Updated:** March 10, 2026  
**Version:** 2.1.x  
**Prerequisite Reading:** [ENTERPRISE_COMPLIANCE_FOR_CTOS.md](ENTERPRISE_COMPLIANCE_FOR_CTOS.md)

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Tier Enforcement Mechanism](#tier-enforcement-mechanism)
3. [Compliance Detection Implementation](#compliance-detection-implementation)
4. [Integration Examples](#integration-examples)
5. [Testing & Verification](#testing--verification)
6. [Configuration Reference](#configuration-reference)
7. [Troubleshooting](#troubleshooting)
8. [API Reference](#api-reference)

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────┐
│ AI Agent (Claude, GitHub Copilot, Cursor, etc.)    │
│ - Makes MCP tool calls                              │
│ - Receives pass/fail results                        │
│ - NO access to tier enforcement logic               │
└─────────────────────────────────────────────────────┘
                        │
                        │ MCP Protocol (HTTP/stdio)
                        ▼
┌─────────────────────────────────────────────────────┐
│ Code Scalpel MCP Server                             │
│ ┌─────────────────────────────────────────────────┐ │
│ │ License Validator (RSA-2048 JWT verification)   │ │
│ │ - Reads .jwt license file                       │ │
│ │ - Verifies cryptographic signature              │ │
│ │ - Returns tier: "community" / "pro" / "enterprise"│
│ └─────────────────────────────────────────────────┘ │
│                        │                             │
│                        ▼                             │
│ ┌─────────────────────────────────────────────────┐ │
│ │ Capability Gating (limits.toml + features.toml) │ │
│ │ - Enforces tier-based limits                    │ │
│ │ - Blocks unauthorized capabilities              │ │
│ └─────────────────────────────────────────────────┘ │
│                        │                             │
│                        ▼                             │
│ ┌─────────────────────────────────────────────────┐ │
│ │ code_policy_check Tool                          │ │
│ │ - AST parsing (Python, JS, TS, Java)           │ │
│ │ - Pattern matching (regex + semantic)          │ │
│ │ - Taint analysis (data flow tracking)          │ │
│ │ - Compliance rule evaluation                    │ │
│ └─────────────────────────────────────────────────┘ │
│                        │                             │
│                        ▼                             │
│ ┌─────────────────────────────────────────────────┐ │
│ │ ToolResponseEnvelope                            │ │
│ │ {                                                │ │
│ │   "data": {...},        # Results               │ │
│ │   "tier_applied": "enterprise",                 │ │
│ │   "duration_ms": 1250,                          │ │
│ │   "error": null                                 │ │
│ │ }                                                │ │
│ └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### Data Flow for Compliance Check

1. **License Validation** (happens once at server startup)
   - Read JWT file from `CODE_SCALPEL_LICENSE_PATH` env var
   - Verify signature with RSA public key (`vault-prod-2026-01.pem`)
   - Cache tier in memory: `_current_tier = "enterprise"`

2. **Capability Check** (happens on every tool call)
   - Read `features.toml`: `compliance_auditing` feature available?
   - Read `limits.toml`: `max_files` limit enforced?
    - If tier insufficient for requested compliance auditing or PDF generation: return an explicit `upgrade_required` error

3. **Compliance Analysis** (if tier check passes)
   - Parse source code files with AST parsers
    - Apply built-in compliance patterns from `code_policy_check.patterns`
    - Optionally layer organization policy configuration discovered by `load_effective_policy()`
   - Detect violations via pattern matching + taint analysis
   - Generate structured results (JSON) with line numbers, severity, remediation

4. **Response Packaging**
   - Wrap results in `ToolResponseEnvelope`
   - Add metadata: `tier_applied`, `duration_ms`, `files_checked`
   - Return to AI agent (agent sees only final results, not internals)

---

## Tier Enforcement Mechanism

### License File Structure

**Location:** `$CODE_SCALPEL_LICENSE_PATH` (default: `.code-scalpel/license/license.jwt`)

**JWT Structure:**
```json
{
  "header": {
    "alg": "RS256",
    "typ": "JWT"
  },
  "payload": {
    "tier": "enterprise",
    "issued_at": "2026-01-01T00:00:00Z",
    "expires_at": "2027-01-01T00:00:00Z",
    "organization": "Acme Corp",
    "license_id": "ent-20260101-abc123"
  },
  "signature": "..." // RSA-2048 signature
}
```

**Verification Process:**
```python
# From src/code_scalpel/licensing/tier_detector.py

def _verify_license(license_path: Path) -> Optional[str]:
    """Verify JWT license and return tier."""
    with open(license_path, "r") as f:
        token = f.read().strip()
    
    # Load RSA public key
    public_key = load_pem_public_key(PUBLIC_KEY_PEM)
    
    # Verify signature
    try:
        payload = jwt.decode(token, public_key, algorithms=["RS256"])
        return payload["tier"]  # "community" / "pro" / "enterprise"
    except jwt.InvalidSignatureError:
        return None  # License tampered with
    except jwt.ExpiredSignatureError:
        return None  # License expired
```

**Key Security Properties:**
- Private key held only by Code Scalpel license server (not distributed)
- Public key embedded in `src/code_scalpel/licensing/vault-prod-2026-01.pem`
- Tampering with license causes signature verification failure
- No tier upgrades possible without valid license signed by private key

### Capability Gating

**Configuration: `src/code_scalpel/capabilities/features.toml`**
```toml
[community.code_policy_check]
capabilities = [
    "style_guide_checking",
    "pep8_validation",
    "basic_linting",
    "pattern_matching",
    "import_validation"
]

[pro.code_policy_check]
capabilities = [
    # All community capabilities (inherited)
    "style_guide_checking",
    "pep8_validation",
    "basic_linting",
    "pattern_matching",
    "import_validation",
    # Pro additions
    "best_practice_analysis",
    "security_pattern_detection",
    "custom_rule_engine",
    "async_error_detection",
    "context_aware_analysis"
]

[enterprise.code_policy_check]
capabilities = [
    # All Pro capabilities (inherited)
    # ... (all 10 Pro capabilities)
    # Enterprise additions
    "hipaa_compliance",
    "soc2_compliance",
    "gdpr_compliance",
    "pci_dss_compliance",
    "compliance_auditing",
    "audit_trail_generation",
    "pdf_certification_reports"
]
```

**Runtime Enforcement:**
```python
# From src/code_scalpel/mcp/tools/policy.py

@mcp.tool()
async def code_policy_check(
    paths: list[str],
    compliance_standards: Optional[list[str]] = None,
    generate_report: bool = False
) -> ToolResponseEnvelope:
    """Check code against compliance standards."""
    
    # 1. Detect tier from license
    tier = get_current_tier()  # "enterprise"
    
    # 2. Check if compliance features available
    if compliance_standards and tier != "enterprise":
        return ToolResponseEnvelope(
            error="Compliance standards require Enterprise tier",
        )
    
    # 3. Check if report generation available
    if generate_report and tier != "enterprise":
        return ToolResponseEnvelope(
            error="Compliance PDF reports require Enterprise tier",
        )
    
    # 4. Enforce limits from limits.toml
    limits = get_tool_limits(tier, "code_policy_check")
    if len(paths) > limits["max_files"]:
        paths = paths[:limits["max_files"]]
    
    # 5. Run analysis (only if all checks pass)
    results = await _run_compliance_analysis(paths, compliance_standards)
    
    return ToolResponseEnvelope(
        data=results,
        tier_applied=tier,
        duration_ms=elapsed_time
    )
```

---

## Compliance Detection Implementation

### Detection Strategies

Code Scalpel uses three complementary strategies:

1. **Pattern Matching** (fastest, highest precision)
   - Regex patterns for known violation signatures
   - Example: `re.compile(r'password\s*=\s*["\'].*["\']')` detects hardcoded passwords

2. **AST Analysis** (accurate, context-aware)
   - Parse code into abstract syntax tree
   - Semantic analysis of function calls, variable assignments, control flow
   - Example: Detect unencrypted database writes by analyzing AST nodes

3. **Taint Analysis** (comprehensive, data flow tracking)
   - Track tainted data from sources (user input, files) to sinks (database, output)
   - Detect if sanitization happens between source and sink
   - Example: User input → SQL query without parameterization = SQL injection

### HIPAA Compliance Detection

**Rule: Unencrypted PHI Storage**

**Detection Logic:**
```python
# From src/code_scalpel/analyzers/compliance/hipaa.py

def detect_unencrypted_phi_storage(ast_tree: ast.Module) -> list[Violation]:
    """Detect storage of PHI without encryption."""
    violations = []
    
    for node in ast.walk(ast_tree):
        # Look for variable assignments with PHI-related names
        if isinstance(node, ast.Assign):
            var_names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if any(is_phi_variable(name) for name in var_names):
                # Check if encrypt() is called on the value
                if not has_encryption_call(node.value):
                    violations.append(Violation(
                        rule="HIPAA-164.312(a)(2)(iv)",
                        severity="CRITICAL",
                        line=node.lineno,
                        message="PHI stored without encryption",
                        remediation="Use encryption before storing PHI"
                    ))
    
    return violations

def is_phi_variable(name: str) -> bool:
    """Check if variable name suggests PHI."""
    phi_keywords = [
        "ssn", "social_security", "patient_name", "medical_record",
        "diagnosis", "prescription", "treatment", "health_info"
    ]
    return any(keyword in name.lower() for keyword in phi_keywords)

def has_encryption_call(node: ast.AST) -> bool:
    """Check if node contains encryption function call."""
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name):
            return node.func.id in ("encrypt", "aes_encrypt", "rsa_encrypt")
    return False
```

**Example Code Triggering Violation:**
```python
# VIOLATION: Unencrypted PHI storage
patient_ssn = "123-45-6789"
db.save("patients", {"ssn": patient_ssn})

# COMPLIANT: Encrypted PHI storage
patient_ssn = "123-45-6789"
encrypted_ssn = encrypt(patient_ssn, key=SECRET_KEY)
db.save("patients", {"ssn": encrypted_ssn})
```

**Test Verification:**
See `tests/tools/code_policy_check/test_enterprise_compliance_comprehensive.py::test_hipaa_unencrypted_phi_detection`

### SOC2 Compliance Detection

**Rule: Missing Audit Logging**

**Detection Logic:**
```python
# From src/code_scalpel/analyzers/compliance/soc2.py

def detect_missing_audit_logging(ast_tree: ast.Module) -> list[Violation]:
    """Detect security-sensitive operations without audit logging."""
    violations = []
    
    for node in ast.walk(ast_tree):
        if isinstance(node, ast.Call):
            # Check for authentication/authorization operations
            if is_security_operation(node):
                # Verify audit log call exists in same scope
                if not has_audit_log_in_scope(node):
                    violations.append(Violation(
                        rule="SOC2-CC1.2",
                        severity="HIGH",
                        line=node.lineno,
                        message="Security operation missing audit log",
                        remediation="Add audit_log() call after operation"
                    ))
    
    return violations

def is_security_operation(node: ast.Call) -> bool:
    """Check if call is security-sensitive."""
    if isinstance(node.func, ast.Attribute):
        method = node.func.attr
        return method in (
            "login", "logout", "authenticate", "authorize",
            "grant_permission", "revoke_permission", "delete_user"
        )
    return False

def has_audit_log_in_scope(node: ast.Call) -> bool:
    """Check if audit logging exists after this operation."""
    # Walk siblings in parent scope
    parent = get_parent_scope(node)
    for sibling in ast.walk(parent):
        if isinstance(sibling, ast.Call):
            if isinstance(sibling.func, ast.Name):
                if sibling.func.id in ("audit_log", "log_security_event"):
                    return True
    return False
```

**Example Code Triggering Violation:**
```python
# VIOLATION: No audit log after security operation
def admin_delete_user(user_id):
    user = db.query("users").get(user_id)
    user.delete()  # Missing audit log!
    return {"status": "deleted"}

# COMPLIANT: Audit log after security operation
def admin_delete_user(user_id):
    user = db.query("users").get(user_id)
    user.delete()
    audit_log("admin_delete_user", user_id=user_id, actor=current_user())
    return {"status": "deleted"}
```

**Test Verification:**
See `tests/tools/code_policy_check/test_enterprise_compliance_comprehensive.py::test_soc2_missing_audit_logs`

### GDPR Compliance Detection

**Rule: Missing Consent Mechanism**

**Detection Logic:**
```python
# From src/code_scalpel/analyzers/compliance/gdpr.py

def detect_missing_consent(ast_tree: ast.Module) -> list[Violation]:
    """Detect personal data processing without consent check."""
    violations = []
    
    for node in ast.walk(ast_tree):
        if isinstance(node, ast.Assign):
            # Look for personal data collection
            if is_personal_data_collection(node):
                # Verify consent check exists before collection
                if not has_consent_check_before(node):
                    violations.append(Violation(
                        rule="GDPR-Article-6",
                        severity="CRITICAL",
                        line=node.lineno,
                        message="Personal data collected without consent verification",
                        remediation="Add consent check before processing personal data"
                    ))
    
    return violations

def is_personal_data_collection(node: ast.Assign) -> bool:
    """Check if assignment collects personal data."""
    # Check for form inputs with personal data fields
    if isinstance(node.value, ast.Call):
        if isinstance(node.value.func, ast.Attribute):
            if node.value.func.attr == "get_form_data":
                # Check for personal data field names in arguments
                for arg in node.value.args:
                    if isinstance(arg, ast.Constant):
                        if arg.value in ("email", "name", "address", "phone"):
                            return True
    return False

def has_consent_check_before(node: ast.Assign) -> bool:
    """Check if consent verification precedes data collection."""
    # Walk previous siblings in parent scope
    parent = get_parent_scope(node)
    for sibling in reversed(list(ast.walk(parent))):
        if sibling.lineno < node.lineno:
            if isinstance(sibling, ast.If):
                # Check for consent-related condition
                condition = ast.unparse(sibling.test)
                if "consent" in condition.lower() or "agreed" in condition.lower():
                    return True
    return False
```

**Example Code Triggering Violation:**
```python
# VIOLATION: No consent check before data collection
def register_user(request):
    email = request.form.get_form_data("email")  # Missing consent check!
    name = request.form.get_form_data("name")
    db.save("users", {"email": email, "name": name})

# COMPLIANT: Consent check before data collection
def register_user(request):
    if not request.form.get("gdpr_consent_agreed"):
        return {"error": "Consent required"}
    
    email = request.form.get_form_data("email")
    name = request.form.get_form_data("name")
    db.save("users", {"email": email, "name": name})
```

**Test Verification:**
See `tests/tools/code_policy_check/test_enterprise_compliance_comprehensive.py::test_gdpr_missing_consent`

---

## Pattern Detection Examples with Code

### HIPAA Violations - Healthcare

**Example 1: HIPAA001 - PHI in Logs**

```python
# ❌ VIOLATION DETECTED (Line 4)
def process_patient_record(patient):
    patient_data = get_patient_info(patient.id)
    # HIPAA001 (CRITICAL): PHI in log statement
    logger.info(f"Processing SSN: {patient_data['ssn']}")
```

**Why This is Detected:**
- Regex: `(?i)(?:log|print|logger)\s*[.(]\s*[^)]*(?:ssn|social_security|patient_id|medical_record|diagnosis)`
- Matches: `logger.info` + `ssn`
- Severity: CRITICAL
- CWE-532: Insertion of Sensitive Information into Log File

**FIX:**
```python
# ✅ COMPLIANT
def process_patient_record(patient):
    patient_data = get_patient_info(patient.id)
    # Use anonymized identifier
    logger.info(f"Processing patient ID: {patient.id}")
```

---

**Example 2: HIPAA002 - Unencrypted PHI Storage**

```python
# ❌ VIOLATION DETECTED (Line 3)
def save_patient_data(patient_info):
    # HIPAA002 (CRITICAL): PHI stored without encryption
    patient_file = open("patient_records.txt", "w")
    patient_file.write(json.dumps(patient_info))
```

**Why This is Detected:**
- Regex: `(?i)(?:patient|medical|health).*=.*(?:open|write|json\.dump)`
- Matches: `patient_file = open(...)`
- Severity: CRITICAL

**FIX:**
```python
# ✅ COMPLIANT
from encryption import encrypt_phi

def save_patient_data(patient_info):
    # Encrypt before storage
    encrypted_data = encrypt_phi(json.dumps(patient_info))
    with open("patient_records.enc", "wb") as f:
        f.write(encrypted_data)
```

---

### SOC2 Violations - SaaS Security

**Example 1: SOC2001 - Missing Authentication**

```python
# ❌ VIOLATION DETECTED (Line 4)
from flask import Flask, request
app = Flask(__name__)

@app.get("/api/users")  # SOC2001 (ERROR): No authentication decorator
def get_users():
    return database.get_all_users()
```

**Why This is Detected:**
- Regex: `@(?:app|router)\.(?:get|post|put|delete)\s*\([^)]+\)\s*(?:async\s+)?def\s+\w+\s*\([^)]*\)(?:(?!@require_auth|@login_required|@authenticated).)*?:`
- Negative lookahead: No `@require_auth`, `@login_required`, or `@authenticated` decorator
- Severity: ERROR

**FIX:**
```python
# ✅ COMPLIANT
from flask import Flask, request
from auth import require_auth

app = Flask(__name__)

@app.get("/api/users")
@require_auth  # Authentication decorator added
def get_users():
    return database.get_all_users()
```

---

**Example 2: SOC2003 - Missing Input Validation**

```python
# ❌ VIOLATION DETECTED (Line 5)
@app.post("/api/users")
@require_auth
def create_user():
    # SOC2003 (ERROR): User input without validation
    user_data = request.json  # Direct use without validation
    return database.create_user(user_data)
```

**Why This is Detected:**
- Regex: `(?i)(?:request\.(?:args|form|json|data)|input\()`
- Matches: `request.json` access
- Severity: ERROR

**FIX:**
```python
# ✅ COMPLIANT
from validators import validate_user_schema

@app.post("/api/users")
@require_auth
def create_user():
    user_data = request.json
    validate_user_schema(user_data)  # Validation before use
    return database.create_user(user_data)
```

---

### GDPR Violations - Privacy

**Example 1: GDPR001 - PII Without Consent**

```python
# ❌ VIOLATION DETECTED (Line 4)
def register_user():
    # GDPR001 (CRITICAL): PII collected without consent check
    email = request.form["email"]
    name = request.form["name"]
    database.save_user({"email": email, "name": name})
```

**Why This is Detected:**
- Regex: `(?i)(?:email|phone|address|name).*=.*(?:request|input|form)`
- Matches: `email = request.form`
- Severity: CRITICAL

**FIX:**
```python
# ✅ COMPLIANT
def register_user():
    # Check GDPR consent first
    if not request.form.get("gdpr_consent_agreed"):
        raise ConsentRequiredError("GDPR consent required")
    
    email = request.form["email"]
    name = request.form["name"]
    database.save_user({
        "email": email,
        "name": name,
        "consent_timestamp": datetime.now()
    })
```

---

### PCI-DSS Violations - Payment Card Security

**Example 1: PCI001 - Card Data in Logs**

```python
# ❌ VIOLATION DETECTED (Line 4)
def process_payment(card_number, cvv):
    # PCI001 (CRITICAL): Payment card data in logs
    logger.info(f"Processing card: {card_number}, CVV: {cvv}")
    # ... payment processing
```

**Why This is Detected:**
- Regex: `(?i)(?:log|print)\s*\([^)]*(?:card|credit|ccn|pan)`
- Matches: `logger.info` + `card`
- Severity: CRITICAL

**FIX:**
```python
# ✅ COMPLIANT
def process_payment(card_number, cvv):
    transaction_id = generate_transaction_id()
    # Log transaction ID only, never card data
    logger.info(f"Processing transaction: {transaction_id}")
    # ... payment processing with encrypted card data
```

---

**Example 2: PCI002 - Unencrypted Card Storage**

```python
# ❌ VIOLATION DETECTED (Line 3)
def store_payment_method(card_number, exp_date):
    # PCI002 (CRITICAL): Card data stored without encryption
    card_data = open("payment_methods.txt", "w")
    card_data.write(f"{card_number},{exp_date}")
```

**Why This is Detected:**
- Regex: `(?i)(?:card|credit|payment).*=.*(?:open|write|save)`
- Matches: `card_data = open(...)`
- Severity: CRITICAL

**FIX:**
```python
# ✅ COMPLIANT
from encryption import encrypt_card_data

def store_payment_method(card_number, exp_date):
    # Encrypt card data before storage
    encrypted = encrypt_card_data(card_number, exp_date)
    with open("payment_methods.enc", "wb") as f:
        f.write(encrypted)
```

---

**Example 3: PCI003 - Insecure Transmission**

```python
# ❌ VIOLATION DETECTED (Line 4)
def charge_card(card_number, amount):
    # PCI003 (CRITICAL): Card data transmitted over HTTP
    response = requests.post(
        "http://payment-gateway.com/charge",  # HTTP not HTTPS!
        json={"card": card_number, "amount": amount}
    )
```

**Why This is Detected:**
- Regex: `(?i)(?:http|requests\.(?:get|post)).*(?:card|credit|payment)`
- Matches: `requests.post` + `http://` + `card`
- Severity: CRITICAL

**FIX:**
```python
# ✅ COMPLIANT
def charge_card(card_number, amount):
    # Always use HTTPS for card data transmission
    tokenized_card = tokenize_card(card_number)
    response = requests.post(
        "https://payment-gateway.com/charge",  # HTTPS enforced
        json={"token": tokenized_card, "amount": amount}
    )
```

---

## Testing Pattern Detection

### Verify Patterns Detect Correctly

```python
# test_hipaa_detection.py
import pytest
from code_scalpel.mcp.tools.policy import code_policy_check

@pytest.mark.asyncio
async def test_hipaa001_phi_in_logs():
    """Verify HIPAA001 detects PHI in log statements."""
    
    # Create test file with known violation
    test_code = '''
import logging
def process_patient(ssn):
    logging.info(f"Patient SSN: {ssn}")  # Should be detected
'''
    
    with open("test_hipaa.py", "w") as f:
        f.write(test_code)
    
    # Run compliance check
    result = await code_policy_check(
        paths=["test_hipaa.py"],
        compliance_standards=["hipaa"]
    )
    
    # Verify HIPAA001 was detected
    findings = result["data"]["compliance_reports"]["hipaa"]["findings"]
    hipaa001_findings = [f for f in findings if f["rule_id"] == "HIPAA001"]
    
    assert len(hipaa001_findings) > 0, "HIPAA001 should be detected"
    assert hipaa001_findings[0]["severity"] == "CRITICAL"
    assert hipaa001_findings[0]["line"] == 4  # SSN logging line
```

**Run Test:**
```bash
pytest test_hipaa_detection.py -v
```

---

## Multi-Standard Scanning Example

### Healthcare Fintech (HIPAA + PCI-DSS + GDPR)

```python
# billing_service.py - BEFORE FIX
import logging

def bill_patient_card(patient_email, card_number, medical_charges):
    # ❌ Triple violation: HIPAA001 + GDPR001 + PCI001
    logging.info(
        f"Billing {patient_email} card {card_number} for {medical_charges}"
    )
```

**Scan Results:**

```json
{
  "compliance_reports": {
    "hipaa": {
      "compliance_score": 80,
      "findings": [
        {
          "rule_id": "HIPAA001",
          "severity": "CRITICAL",
          "line": 5,
          "description": "Medical charges in  log (PHI)"
        }
      ]
    },
    "gdpr": {
      "compliance_score": 80,
      "findings": [
        {
          "rule_id": "GDPR001",
          "severity": "CRITICAL",
          "line": 5,
          "description": "Email logged without consent verification"
        }
      ]
    },
    "pci_dss": {
      "compliance_score": 80,
      "findings": [
        {
          "rule_id": "PCI001",
          "severity": "CRITICAL",
          "line": 5,
          "description": "Payment card number in logs"
        }
      ]
    }
  }
}
```

**AFTER FIX:**

```python
# billing_service.py - COMPLIANT
import logging
from encryption import encrypt_sensitive_data

def bill_patient_card(patient_email, card_number, medical_charges):
    # Generate transaction ID for logging
    transaction_id = generate_transaction_id()
    
    # ✅ Log transaction ID only (no PHI, PII, or card data)
    logging.info(f"Processing billing transaction: {transaction_id}")
    
    # ✅ Verify GDPR consent before using email
    if not has_consent(patient_email, purpose="billing"):
        raise ConsentRequiredError("Billing consent required")
    
    # ✅ Encrypt all sensitive data
    encrypted_billing = encrypt_sensitive_data({
        "email": patient_email,
        "card": card_number,
        "charges": medical_charges,
        "transaction_id": transaction_id
    })
    
    process_secure_transaction(encrypted_billing)
```

**New Compliance Scores:**
- HIPAA: 100/100 ✅
- GDPR: 100/100 ✅
- PCI-DSS: 100/100 ✅

---

## Integration Examples

### Example 1: CI/CD Pipeline Integration

**GitHub Actions Workflow:**
```yaml
# .github/workflows/compliance-check.yml
name: Compliance Check

on:
  pull_request:
    branches: [main, develop]

jobs:
  compliance:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install Code Scalpel
        run: pip install codescalpel
      
      - name: Configure Enterprise License
        env:
          LICENSE_JWT: ${{ secrets.CODE_SCALPEL_ENTERPRISE_LICENSE }}
        run: |
          mkdir -p .code-scalpel/license
          echo "$LICENSE_JWT" > .code-scalpel/license/license.jwt
      
      - name: Run Compliance Check
        run: |
          python -m code_scalpel.mcp.tools.policy \
            --paths src/ \
            --compliance HIPAA,SOC2,GDPR,PCI-DSS \
            --generate-report \
            --fail-on-violations \
            --output compliance_report.json
      
      - name: Upload Compliance Report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: compliance-report
          path: compliance_report.json
      
      - name: Comment on PR
        if: failure()
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const report = JSON.parse(fs.readFileSync('compliance_report.json'));
            const violations = report.data.violations;
            
            const comment = `## ⚠️ Compliance Violations Detected\\n\\n` +
              `Found ${violations.length} violations:\\n\\n` +
              violations.map(v => 
                `- **${v.severity}**: ${v.message} (${v.file}:${v.line})`
              ).join('\\n');
            
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: comment
            });
```

### Example 2: Pre-Commit Hook

**`.git/hooks/pre-commit`:**
```bash
#!/bin/bash
# Pre-commit hook for compliance checking

# Get list of staged Python files
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$')

if [ -z "$STAGED_FILES" ]; then
    echo "No Python files to check"
    exit 0
fi

# Run compliance check
python -m code_scalpel.mcp.tools.policy \
    --paths $STAGED_FILES \
    --compliance HIPAA,SOC2,GDPR \
    --fail-on-violations

if [ $? -ne 0 ]; then
    echo "❌ Compliance violations detected. Fix violations before committing."
    exit 1
fi

echo "✅ Compliance check passed"
exit 0
```

### Example 3: AI Agent Integration (Python)

```python
# AI agent using Code Scalpel MCP client

import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def check_compliance_with_ai_agent():
    """Example: AI agent checking codebase for HIPAA compliance."""
    
    # Connect to Code Scalpel MCP server
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "code_scalpel.mcp.server"],
        env={"CODE_SCALPEL_LICENSE_PATH": "/path/to/enterprise.jwt"}
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Call code_policy_check tool
            result = await session.call_tool(
                "code_policy_check",
                {
                    "paths": ["src/patient_portal/"],
                    "compliance_standards": ["HIPAA"],
                    "generate_report": True
                }
            )
            
            # Parse results
            data = result.content[0].text
            violations = data["violations"]
            
            # AI agent decision logic
            if violations:
                print(f"⚠️ Found {len(violations)} HIPAA violations:")
                for v in violations:
                    print(f"  - {v['severity']}: {v['message']} ({v['file']}:{v['line']})")
                
                # AI agent can now auto-fix violations
                # (implementation depends on specific AI agent framework)
            else:
                print("✅ No HIPAA violations detected")

if __name__ == "__main__":
    asyncio.run(check_compliance_with_ai_agent())
```

---

## Testing & Verification

### Test Structure

Code Scalpel has 95 tests verifying compliance features work correctly:

| Test Suite | File | Tests | Purpose |
|------------|------|-------|---------|
| **Enterprise Compliance** | `test_enterprise_compliance_comprehensive.py` | 22 | Verify HIPAA, SOC2, GDPR, PCI-DSS detection, audit trail, PDF reports |
| **Pro Features** | `test_pro_features_comprehensive.py` | 22 | Verify best practices, security patterns, custom rules, async error detection |
| **Tier Inheritance** | `test_tier_inheritance.py` | 24 | Prove Enterprise ⊇ Pro ⊇ Community mathematically |
| **Config Validation** | `test_config_validation.py` | 9 | Verify limits.toml and features.toml loaded correctly |
| **Integration Tests** | `test_compliance_integration.py` | 18 | End-to-end workflows with multiple standards |

### Running Tests Locally

**Full test suite:**
```bash
pytest tests/tools/code_policy_check/ -v
```

**Specific tier tests:**
```bash
# Enterprise compliance tests only
pytest tests/tools/code_policy_check/test_enterprise_compliance_comprehensive.py -v

# Tier inheritance tests only
pytest tests/tools/code_policy_check/test_tier_inheritance.py -v
```

**With coverage:**
```bash
pytest tests/tools/code_policy_check/ --cov=src/code_scalpel/mcp/tools/policy --cov-report=html
```

### Key Test Patterns

**Pattern 1: Inject Known Violations, Verify Detection**
```python
@pytest.mark.asyncio
async def test_hipaa_unencrypted_phi_detection(enterprise_tier, tmp_path):
    """Verify HIPAA detector catches unencrypted PHI."""
    # Inject violation
    violation_code = '''
patient_ssn = "123-45-6789"
db.save("patients", {"ssn": patient_ssn})
    '''
    test_file = tmp_path / "patient_storage.py"
    test_file.write_text(violation_code)
    
    # Run compliance check
    result = await code_policy_check(
        paths=[str(test_file)],
        compliance_standards=["HIPAA"]
    )
    
    # Verify detection
    assert result.tier_applied == "enterprise"
    violations = result.data["violations"]
    assert len(violations) > 0
    assert violations[0]["rule"] == "HIPAA-164.312(a)(2)(iv)"
    assert violations[0]["severity"] == "CRITICAL"
    assert "unencrypted" in violations[0]["message"].lower()
```

**Pattern 2: Verify Tier Inheritance**
```python
@pytest.mark.asyncio
async def test_enterprise_has_all_pro_capabilities(enterprise_tier):
    """Prove Enterprise ⊇ Pro using set theory."""
    # Get capabilities from features.toml
    pro_caps = set(get_tool_capabilities("pro", "code_policy_check"))
    ent_caps = set(get_tool_capabilities("enterprise", "code_policy_check"))
    
    # Set theory: Pro ⊆ Enterprise
    assert pro_caps.issubset(ent_caps), \
        f"Enterprise missing Pro capabilities: {pro_caps - ent_caps}"
    
    # Verify Pro-specific capabilities
    assert "best_practice_analysis" in ent_caps
    assert "security_pattern_detection" in ent_caps
    assert "custom_rule_engine" in ent_caps
```

**Pattern 3: Verify Compliant Code Passes**
```python
@pytest.mark.asyncio
async def test_gdpr_compliant_code_no_violations(enterprise_tier, tmp_path):
    """Verify GDPR-compliant code does not trigger false positives."""
    # Inject compliant code
    compliant_code = '''
def register_user(request):
    if not request.form.get("gdpr_consent_agreed"):
        return {"error": "Consent required"}
    
    email = request.form.get_form_data("email")
    db.save("users", {"email": email})
    '''
    test_file = tmp_path / "registration.py"
    test_file.write_text(compliant_code)
    
    # Run compliance check
    result = await code_policy_check(
        paths=[str(test_file)],
        compliance_standards=["GDPR"]
    )
    
    # Verify no false positives
    violations = result.data["violations"]
    assert len(violations) == 0, "Compliant code should not trigger violations"
```

---

## Configuration Reference

### Core Configuration Files

| File | Purpose | Format | Location |
|------|---------|--------|----------|
| **features.toml** | Capability definitions per tier | TOML | `src/code_scalpel/capabilities/features.toml` |
| **limits.toml** | Resource limits per tier | TOML | `src/code_scalpel/capabilities/limits.toml` |
| **code_policy_check/*.py** | Built-in compliance and policy patterns | Python | `src/code_scalpel/policy_engine/code_policy_check/` |
| **governance.yaml** | Optional organization-specific overlays and custom rules | YAML | `.code-scalpel/governance.yaml` |
| **license.jwt** | Cryptographic tier license | JWT | `$CODE_SCALPEL_LICENSE_PATH` |

### features.toml Structure

```toml
# Community tier (baseline)
[community.code_policy_check]
capabilities = [
    "style_guide_checking",
    "pep8_validation",
    "basic_linting",
    "pattern_matching",
    "import_validation"
]

# Pro tier (inherits + extends)
[pro.code_policy_check]
capabilities = [
    # ... all community capabilities
    "best_practice_analysis",
    "security_pattern_detection",
    "custom_rule_engine",
    "async_error_detection",
    "context_aware_analysis"
]

# Enterprise tier (inherits + extends)
[enterprise.code_policy_check]
capabilities = [
    # ... all pro capabilities
    "hipaa_compliance",
    "soc2_compliance",
    "gdpr_compliance",
    "pci_dss_compliance",
    "compliance_auditing",
    "audit_trail_generation",
    "pdf_certification_reports"
]
```

### limits.toml Structure

```toml
[community.code_policy_check]
max_files = 100        # Maximum files per scan
max_rules = 50         # Maximum custom rules
analysis_depth = 1     # AST analysis depth

[pro.code_policy_check]
max_files = -1         # Unlimited
max_rules = -1         # Unlimited
analysis_depth = 5     # Deeper AST analysis

[enterprise.code_policy_check]
max_files = -1         # Unlimited
max_rules = -1         # Unlimited
analysis_depth = 10    # Deepest AST analysis
```

### Compliance Rule Sources

> [20260310_DOCS] Built-in HIPAA, SOC2, GDPR, and PCI-DSS detection ships in the `code_policy_check` pattern modules. `.code-scalpel/governance.yaml` is an optional layering point for organization-specific overlays and custom rules; it is not the sole source of the standard compliance corpus.

```yaml
# Example organization overlay
hipaa_rules:
  - rule_id: HIPAA-164.312(a)(2)(iv)
    name: "Encryption of ePHI"
    severity: CRITICAL
    pattern: |
      # Detect variables with PHI-related names
      VARIABLE_PATTERN: (ssn|social_security|patient_name|medical_record|diagnosis)
      # Without encryption call
      VIOLATION: ASSIGN without (encrypt|aes_encrypt|rsa_encrypt)
    remediation: "Use encryption before storing PHI"

  - rule_id: HIPAA-164.312(b)
    name: "Audit Controls"
    severity: HIGH
    pattern: |
      # Detect PHI access without audit logging
      OPERATION: (db.query|db.get|db.save) with PHI_TABLE
      VIOLATION: no (audit_log|log_access) call within 3 lines
    remediation: "Add audit_log() after PHI access"

# SOC2 compliance rules
soc2_rules:
  - rule_id: SOC2-CC1.2
    name: "Security Event Logging"
    severity: HIGH
    pattern: |
      # Detect security operations without logging
      OPERATION: (login|logout|authenticate|authorize|grant_permission)
      VIOLATION: no (audit_log|log_security_event) within 5 lines
    remediation: "Add audit log after security operation"

# GDPR compliance rules
gdpr_rules:
  - rule_id: GDPR-Article-6
    name: "Lawfulness of Processing"
    severity: CRITICAL
    pattern: |
      # Detect personal data collection without consent
      OPERATION: get_form_data with (email|name|address|phone)
      VIOLATION: no (consent|agreed) check before operation
    remediation: "Verify GDPR consent before processing personal data"
```

---

## Troubleshooting

### Common Issues

#### Issue: "Compliance standards require Enterprise tier"

**Cause:** License file missing or invalid

**Solution:**
```bash
# Verify license file exists
echo $CODE_SCALPEL_LICENSE_PATH
ls -la $CODE_SCALPEL_LICENSE_PATH

# Verify license is valid JWT
python -c "
import jwt
with open('$CODE_SCALPEL_LICENSE_PATH') as f:
    token = f.read()
    # Decode without verification to inspect payload
    payload = jwt.decode(token, options={'verify_signature': False})
    print(f'Tier: {payload[\"tier\"]}')
    print(f'Expires: {payload[\"expires_at\"]}')
"
```

#### Issue: "False positives in compliance detection"

**Cause:** Overly broad pattern matching

**Solution:** Add an organization-specific overlay in `governance.yaml` or narrow the scan scope; built-in standard rules continue to come from the shipped policy modules:
```yaml
# Example: Ignore test files from HIPAA checks
hipaa_rules:
  - rule_id: HIPAA-164.312(a)(2)(iv)
    exclude_patterns:
      - "**/tests/**"
      - "**/*_test.py"
      - "**/test_*.py"
```

#### Issue: "Tier inheritance tests failing"

**Cause:** License fixtures not activated correctly

**Solution:**
```python
# Ensure fixtures activate BEFORE importing code_scalpel modules
@pytest.fixture
def enterprise_tier(monkeypatch):
    """Activate Enterprise tier."""
    license_path = Path(__file__).parent / "licenses" / "enterprise.jwt"
    monkeypatch.setenv("CODE_SCALPEL_LICENSE_PATH", str(license_path))
    yield
    # Import AFTER fixture sets env var
    from code_scalpel.mcp.tools import code_policy_check
```

---

## API Reference

### `code_policy_check` Tool

**Function Signature:**
```python
async def code_policy_check(
    paths: list[str],
    rules: Optional[list[str]] = None,
    compliance_standards: Optional[list[str]] = None,
    generate_report: bool = False
) -> ToolResponseEnvelope
```

**Parameters:**
- `paths` (`list[str]`): List of file paths or directories to analyze
- `rules` (`Optional[list[str]]`): Specific rule IDs to enforce (default: all rules)
- `compliance_standards` (`Optional[list[str]]`): Compliance standards to check (HIPAA, SOC2, GDPR, PCI-DSS)
- `generate_report` (`bool`): Generate PDF certification report (requires Enterprise tier)

**Returns:**
`ToolResponseEnvelope` containing:
```python
{
    "data": {
        "success": bool,
        "files_checked": int,
        "rules_applied": int,
        "violations": [
            {
                "rule": str,           # Rule ID (e.g., "HIPAA-164.312(a)(2)(iv)")
                "severity": str,       # CRITICAL, HIGH, MEDIUM, LOW
                "file": str,           # File path
                "line": int,           # Line number
                "message": str,        # Violation description
                "remediation": str     # How to fix
            }
        ],
        "compliance_reports": {    # Enterprise only
            "HIPAA": {
                "total_rules": int,
                "violations": int,
                "compliance_score": int  # 0-100
            }
        },
        "pdf_report": str,         # Enterprise only, base64-encoded PDF
        "audit_trail": [...]       # Enterprise only
    },
    "tier_applied": str,           # "enterprise"
    "duration_ms": int,
    "error": Optional[str]
}
```

**Example Usage:**
```python
result = await code_policy_check(
    paths=["src/patient_portal/"],
    compliance_standards=["HIPAA", "SOC2"],
    generate_report=True
)

if result.error:
    print(f"Error: {result.error}")
else:
    violations = result.data["violations"]
    print(f"Found {len(violations)} violations")
    
    # Print HIPAA compliance score
    hipaa_score = result.data["compliance_reports"]["HIPAA"]["compliance_score"]
    print(f"HIPAA Compliance Score: {hipaa_score}%")
```

---

## Advanced Topics

### Custom Compliance Rules

**Create custom organization rule in governance.yaml:**
```yaml
custom_rules:
  - rule_id: CUSTOM-001
    name: "Internal API Key Security"
    severity: CRITICAL
    tier: enterprise  # Only enforced in Enterprise tier
    pattern: |
      # Detect hardcoded API keys for internal services
      VARIABLE_PATTERN: (api_key|secret_key|internal_token)
      LITERAL_VALUE: STRING_LITERAL
      VIOLATION: not environment_variable
    categories: ["security", "best_practices"]
    remediation: "Load API keys from environment variables or secrets manager"
```

**Programmatic custom rules (Pro tier):**
```python
from code_scalpel.analyzers.rules import CustomRule

# Define custom rule
custom_rule = CustomRule(
    rule_id="CUSTOM-002",
    name="Async Function Timeout",
    severity="MEDIUM",
    detector=lambda node: (
        isinstance(node, ast.AsyncFunctionDef) and
        not has_timeout_decorator(node)
    ),
    remediation="Add @timeout(seconds=30) decorator to async functions"
)

# Register and use
result = await code_policy_check(
    paths=["src/"],
    rules=[custom_rule]
)
```

### Multi-Standard Compliance

**Scan for multiple standards simultaneously:**
```python
result = await code_policy_check(
    paths=["src/"],
    compliance_standards=["HIPAA", "SOC2", "GDPR", "PCI-DSS"]
)

# Results grouped by standard
for standard, report in result.data["compliance_reports"].items():
    print(f"{standard}: {report['compliance_score']}% compliant")
```

---

## Performance Optimization

### Analysis Performance Characteristics

| Files | LOC | Analysis Time (Community) | Analysis Time (Enterprise) |
|-------|-----|---------------------------|---------------------------|
| 10 | 5K | 0.5s | 1.2s (compliance overhead) |
| 100 | 50K | 3.2s | 8.7s |
| 1000 | 500K | 45s (limit: 100 files) | 127s |

**Optimization Strategies:**
1. **Incremental analysis:** Only scan changed files in CI/CD
2. **Parallel processing:** Pro/Enterprise support parallel file analysis
3. **Caching:** Enable AST cache for repeated scans
4. **Selective standards:** Only run relevant compliance standards

---

## Security Considerations

### License Tampering Protection

**Attack:** Modify JWT license file to upgrade tier

**Mitigation:** RSA-2048 signature verification
- Public key embedded in code
- Private key held by license server
- Signature mismatch = license rejected

**Verification:**
```python
# src/code_scalpel/licensing/tier_detector.py
def _verify_license_integrity(license_path: Path) -> bool:
    """Verify license has not been tampered with."""
    try:
        with open(license_path) as f:
            token = f.read()
        
        # Load embedded public key
        public_key = load_pem_public_key(PUBLIC_KEY_PEM)
        
        # Verify signature (raises exception if invalid)
        jwt.decode(token, public_key, algorithms=["RS256"])
        return True
    except (jwt.InvalidSignatureError, jwt.ExpiredSignatureError):
        return False
```

### Audit Trail Integrity

**Requirement:** Audit logs must be tamper-proof for compliance

**Implementation:** Cryptographic hash chain
```python
# Each audit entry contains hash of previous entry
def generate_audit_entry(event: dict, prev_hash: str) -> dict:
    """Generate tamper-proof audit entry."""
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event": event,
        "prev_hash": prev_hash
    }
    # Hash current entry including previous hash
    entry["hash"] = hashlib.sha256(
        json.dumps(entry, sort_keys=True).encode()
    ).hexdigest()
    return entry
```

---

## Additional Resources

- **CTO Guide:** [ENTERPRISE_COMPLIANCE_FOR_CTOS.md](ENTERPRISE_COMPLIANCE_FOR_CTOS.md)
- **Capability Matrix:** [COMPLIANCE_CAPABILITY_MATRIX.md](COMPLIANCE_CAPABILITY_MATRIX.md)
- **Test Documentation:** [tests/tools/code_policy_check/README.md](../../tests/tools/code_policy_check/README.md)
- **Release Notes:** [docs/release_notes/RELEASE_NOTES_v1.3.0.md](../release_notes/RELEASE_NOTES_v1.3.0.md)

---

## Document Metadata

- **Version:** 1.0.0
- **Last Updated:** February 1, 2026
- **Maintained By:** Code Scalpel Core Team
- **Review Cycle:** Quarterly
- **Feedback:** GitHub Issues or enterprise@codescalpel.io
