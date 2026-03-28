# Enterprise Compliance - Quick Start Examples

**Last Updated:** February 12, 2026  
**Version:** 1.3.0  
**Time to Complete:** 5 minutes

---

## Quick Start: Run Your First Compliance Scan

### 1. Basic HIPAA Scan (Healthcare)

**Scan this code for HIPAA violations:**

```python
# patient_service.py - BEFORE compliance scan
import logging

def get_patient_record(patient_id):
    patient = database.fetch_patient(patient_id)
    
    # ❌ HIPAA001: PHI in logs
    logging.info(f"Retrieved patient SSN: {patient.ssn}")
    
    # ❌ HIPAA002: Unencrypted storage
    patient_file = open("patient_records.txt", "w")
    patient_file.write(str(patient))
    
    return patient
```

**Run Code Scalpel:**

```bash
# Using MCP server (Claude Desktop, VS Code, etc.)
# AI agent calls: code_policy_check(paths=["patient_service.py"], compliance_standards=["hipaa"])
```

**Results:**

```json
{
  "success": true,
  "data": {
    "compliance_reports": {
      "hipaa": {
        "compliance_score": 60,
        "findings": [
          {
            "rule_id": "HIPAA001",
            "severity": "CRITICAL",
            "line": 7,
            "description": "Potential PHI in log statement",
            "suggestion": "Never log PHI - use anonymized identifiers",
            "cwe_id": "CWE-532"
          },
          {
            "rule_id": "HIPAA002",
            "severity": "CRITICAL",
            "line": 10,
            "description": "PHI stored without encryption",
            "suggestion": "Encrypt PHI at rest and in transit"
          }
        ]
      }
    }
  }
}
```

**Fix the code:**

```python
# patient_service.py - AFTER fixing HIPAA violations
import logging
from encryption import encrypt_phi

def get_patient_record(patient_id):
    patient = database.fetch_patient(patient_id)
    
    # ✅ HIPAA compliant: Use anonymized ID
    logging.info(f"Retrieved patient record: {patient_id}")
    
    # ✅ HIPAA compliant: Encrypt before storage
    encrypted_data = encrypt_phi(str(patient))
    with open("patient_records.enc", "wb") as f:
        f.write(encrypted_data)
    
    return patient
```

**Re-scan:** Compliance score → **100** ✅

---

### 2. SOC2 API Security Scan (SaaS)

**Scan this API for SOC2 violations:**

```python
# api.py - BEFORE compliance scan
from flask import Flask, request

app = Flask(__name__)

# ❌ SOC2001: Missing authentication
@app.get("/api/users")
def get_users():
    # No @require_auth decorator
    return database.get_all_users()

# ❌ SOC2003: No input validation
@app.post("/api/users")
def create_user():
    user_data = request.json  # Direct use without validation
    return database.create_user(user_data)
```

**Run Code Scalpel:**

```bash
# AI agent calls: code_policy_check(paths=["api.py"], compliance_standards=["soc2"])
```

**Results:**

```json
{
  "compliance_reports": {
    "soc2": {
      "compliance_score": 40,
      "findings": [
        {
          "rule_id": "SOC2001",
          "severity": "ERROR",
          "line": 6,
          "description": "API endpoint without authentication check",
          "suggestion": "Add authentication decorator to all endpoints"
        },
        {
          "rule_id": "SOC2003",
          "severity": "ERROR",
          "line": 14,
          "description": "User input accessed without validation",
          "suggestion": "Validate all user input before processing"
        }
      ]
    }
  }
}
```

**Fix the code:**

```python
# api.py - AFTER fixing SOC2 violations
from flask import Flask, request
from auth import require_auth
from validators import validate_user_data

app = Flask(__name__)

# ✅ SOC2 compliant: Authentication required
@app.get("/api/users")
@require_auth
def get_users():
    return database.get_all_users()

# ✅ SOC2 compliant: Input validation
@app.post("/api/users")
@require_auth
def create_user():
    user_data = request.json
    validate_user_data(user_data)  # Validation before use
    return database.create_user(user_data)
```

**Re-scan:** Compliance score → **100** ✅

---

### 3. PCI-DSS Payment Security Scan (E-commerce)

**Scan this payment code for PCI-DSS violations:**

```python
# payment_processor.py - BEFORE compliance scan
import logging
import requests

def process_payment(card_number, cvv, amount):
    # ❌ PCI001: Card data in logs
    logging.info(f"Processing payment for card: {card_number}")
    
    # ❌ PCI002: Unencrypted card storage
    card_file = open("transactions.txt", "w")
    card_file.write(f"{card_number},{cvv},{amount}")
    
    # ❌ PCI003: Insecure transmission
    response = requests.post(
        "http://payment-gateway.com/charge",  # HTTP not HTTPS
        json={"card": card_number, "amount": amount}
    )
    return response.json()
```

**Run Code Scalpel:**

```bash
# AI agent calls: code_policy_check(paths=["payment_processor.py"], compliance_standards=["pci_dss"])
```

**Results:**

```json
{
  "compliance_reports": {
    "pci_dss": {
      "compliance_score": 20,
      "findings": [
        {
          "rule_id": "PCI001",
          "severity": "CRITICAL",
          "line": 6,
          "description": "Payment card data in logs",
          "suggestion": "Never log payment card data - use transaction IDs"
        },
        {
          "rule_id": "PCI002",
          "severity": "CRITICAL",
          "line": 9,
          "description": "Payment card data stored without encryption",
          "suggestion": "Encrypt all card data at rest"
        },
        {
          "rule_id": "PCI003",
          "severity": "CRITICAL",
          "line": 13,
          "description": "Payment card data transmitted insecurely",
          "suggestion": "Use HTTPS for all payment card data transmission"
        }
      ]
    }
  }
}
```

**Fix the code:**

```python
# payment_processor.py - AFTER fixing PCI-DSS violations
import logging
import requests
from encryption import encrypt_card_data

def process_payment(card_number, cvv, amount):
    # ✅ PCI compliant: Log transaction ID, not card data
    transaction_id = generate_transaction_id()
    logging.info(f"Processing payment: {transaction_id}")
    
    # ✅ PCI compliant: Encrypt card data before storage
    encrypted_data = encrypt_card_data(card_number, cvv)
    with open("transactions.enc", "wb") as f:
        f.write(encrypted_data)
    
    # ✅ PCI compliant: HTTPS transmission
    response = requests.post(
        "https://payment-gateway.com/charge",  # HTTPS
        json={"transaction_id": transaction_id, "amount": amount}
    )
    return response.json()
```

**Re-scan:** Compliance score → **100** ✅

---

### 4. Multi-Standard Scan (Healthcare Fintech)

**Scan code that must comply with HIPAA + PCI-DSS + GDPR:**

```python
# billing_service.py
def bill_patient(patient_email, card_number, medical_charges):
    # Potential violations across 3 standards
    logging.info(f"Billing {patient_email} card {card_number} for {medical_charges}")
```

**Run Code Scalpel:**

```bash
# AI agent calls: code_policy_check(
#     paths=["billing_service.py"], 
#     compliance_standards=["hipaa", "pci_dss", "gdpr"]
# )
```

**Results show violations across all 3 standards:**

```json
{
  "compliance_reports": {
    "hipaa": {
      "compliance_score": 80,
      "findings": [{"rule_id": "HIPAA001", "description": "Medical charges in logs"}]
    },
    "pci_dss": {
      "compliance_score": 80,
      "findings": [{"rule_id": "PCI001", "description": "Card number in logs"}]
    },
    "gdpr": {
      "compliance_score": 80,
      "findings": [{"rule_id": "GDPR001", "description": "Email without consent check"}]
    }
  }
}
```

---

### 5. Generate PDF Compliance Report

**Get a PDF report for auditors:**

> [20260310_DOCS] PDF compliance reports are Enterprise-only. If Community or Pro callers request `generate_report=True` or `compliance_standards=[...]`, the MCP tool now returns an explicit `upgrade_required` error instead of silently degrading to a basic scan. See [../compliance/README.md](../compliance/README.md) for the live runtime contract.

```bash
# AI agent calls: code_policy_check(
#     paths=["src/"], 
#     compliance_standards=["hipaa", "soc2"], 
#     generate_report=True
# )
```

**Response includes base64-encoded PDF:**

```json
{
  "data": {
    "pdf_report": "JVBERi0xLjQKJeLjz9MKMSAwIG9iago8PC9UeXBlL0NhdGFsb2cvUGFnZXMgMiAw...",
    "compliance_reports": {...}
  }
}
```

**Decode and save PDF:**

```python
import base64

pdf_data = base64.b64decode(result["data"]["pdf_report"])
with open("compliance_report.pdf", "wb") as f:
    f.write(pdf_data)
```

**PDF contains:**
- ✅ Compliance scores for each standard
- ✅ Detailed violations with line numbers
- ✅ Severity classifications
- ✅ Remediation suggestions
- ✅ Timestamp and audit trail

---

## Real-World Examples

### Example 1: Healthcare Startup (Seed Stage)

**Scenario:** Building patient portal, need HIPAA compliance for Series A

**Before Code Scalpel:**
- Manual code reviews: 3 days
- HIPAA consultant: $15,000
- Compliance gaps found: After production deployment 😱

**With Code Scalpel:**
- Automated scan: 30 seconds
- Found 47 HIPAA violations
- Fixed before deployment
- Series A compliance due diligence: ✅ PASSED

**Cost Savings:** $15,000 + prevented breach incident

---

### Example 2: SaaS Company (Growth Stage)

**Scenario:** Enterprise customers requiring SOC2 Type II

**Before Code Scalpel:**
- Security audit: 2 weeks
- Found gaps in authentication, logging
- Delayed enterprise deals

**With Code Scalpel:**
- Continuous compliance monitoring in CI/CD
- SOC2 violations detected pre-merge
- PDF reports for auditors
- SOC2 certification: ✅ ACHIEVED

**Business Impact:** Won $2M enterprise contract requiring SOC2

---

### Example 3: E-commerce Platform (Scale Stage)

**Scenario:** Processing 100K+ transactions/day, PCI-DSS required

**Before Code Scalpel:**
- PCI-DSS consultant: $50,000/year
- Quarterly compliance audits: 5 days each
- Violations found in production

**With Code Scalpel:**
- Automated PCI-DSS scanning in every PR
- Zero card data leaks to logs
- Compliance score: 98/100
- Annual audit prep: 2 days vs 5 days

**Cost Savings:** $50,000/year + reduced audit time 60%

---

## Integration Examples

### Example 1: GitHub Actions CI/CD

```yaml
# .github/workflows/compliance.yml
name: Compliance Check

on: [pull_request]

jobs:
  hipaa-compliance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run HIPAA Compliance Scan
        run: |
          # MCP server runs compliance check
          code-scalpel check --standard hipaa --paths src/
          
      - name: Fail if critical violations
        run: |
          if [ $COMPLIANCE_SCORE -lt 80 ]; then
            echo "HIPAA compliance score too low: $COMPLIANCE_SCORE"
            exit 1
          fi
```

### Example 2: Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Running compliance checks..."

# Scan staged files for HIPAA violations
code-scalpel check --standard hipaa --staged

if [ $? -ne 0 ]; then
  echo "❌ Compliance violations detected. Commit blocked."
  echo "Run 'code-scalpel check --standard hipaa --fix' to auto-fix."
  exit 1
fi

echo "✅ Compliance check passed"
```

### Example 3: VS Code with MCP

**Claude Desktop integration:**

```json
{
  "mcpServers": {
    "code-scalpel": {
      "command": "uvx",
      "args": ["code-scalpel"],
      "env": {
        "CODE_SCALPEL_LICENSE_PATH": "/path/to/license.jwt"
      }
    }
  }
}
```

**Usage in Claude:**
- "Scan this file for HIPAA violations"
- Claude calls `code_policy_check` tool automatically
- Results shown with specific line numbers and fixes

---

## Testing Your Compliance Scans

### Verify Pattern Detection

```python
# test_compliance.py
import pytest
from code_scalpel.mcp.tools.policy import code_policy_check

@pytest.mark.asyncio
async def test_hipaa_detection():
    """Verify HIPAA violations are detected."""
    
    # Write test file with known violation
    with open("test_code.py", "w") as f:
        f.write('logging.info(f"Patient SSN: {ssn}")')
    
    # Run compliance check
    result = await code_policy_check(
        paths=["test_code.py"],
        compliance_standards=["hipaa"]
    )
    
    # Verify HIPAA001 detected
    findings = result["data"]["compliance_reports"]["hipaa"]["findings"]
    assert any(f["rule_id"] == "HIPAA001" for f in findings)
    assert any("SSN" in f["description"] for f in findings)
```

**Run tests:**

```bash
pytest test_compliance.py -v
```

---

## Next Steps

1. **Read Full Documentation:**
   - [Enterprise Compliance for CTOs](ENTERPRISE_COMPLIANCE_FOR_CTOS.md) - Business value
   - [Enterprise Compliance for Engineers](ENTERPRISE_COMPLIANCE_FOR_ENGINEERS.md) - Technical details
   - [Compliance Verification Report](../testing/COMPLIANCE_VERIFICATION_REPORT.md) - Test evidence

2. **Try It Yourself:**
   - Install Code Scalpel: `pip install code-scalpel`
   - Get Enterprise license: Contact sales
   - Run first scan: See examples above

3. **Integrate with Your Workflow:**
   - Add to CI/CD pipeline
   - Configure pre-commit hooks
   - Enable MCP in VS Code/Claude Desktop

4. **Get Support:**
   - Documentation: https://github.com/code-scalpel/code-scalpel/docs
   - Issues: https://github.com/code-scalpel/code-scalpel/issues
   - Enterprise support: enterprise@code-scalpel.com

---

**Last Updated:** February 12, 2026  
**Version:** Code Scalpel 1.3.0  
**Test Coverage:** 93 compliance tests (100% passing)
