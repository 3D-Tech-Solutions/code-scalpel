<!-- [20251215_DOCS] Compliance: PCI DSS Relevance -->

# PCI DSS Relevance

This document explains how Code Scalpel supports PCI DSS (Payment Card Industry Data Security Standard) compliance for organizations handling cardholder data.

---

## PCI DSS Overview

PCI DSS v4.0 contains 12 requirements organized into 6 goals. Code Scalpel primarily supports **Requirement 6: Develop and Maintain Secure Systems and Software**.

---

## Relevant Requirements

### Requirement 6: Secure Development

| Req | Description | Code Scalpel Support |
|-----|-------------|---------------------|
| 6.2.1 | Secure development processes | Security scanning in SDLC |
| 6.2.2 | Annual security training | N/A (out of scope) |
| 6.2.3 | Code review for security | Automated vulnerability detection |
| 6.2.4 | Prevention of common vulnerabilities | CWE coverage for OWASP Top 10 |
| 6.3.1 | Security vulnerabilities identified/addressed | Taint analysis findings |
| 6.3.2 | Custom code reviewed for vulnerabilities | `security_scan` tool |

---

### Requirement 6.2.4: Prevent Common Vulnerabilities

PCI DSS 6.2.4 requires prevention of:

| Vulnerability Type | Code Scalpel Detection | CWE |
|-------------------|----------------------|-----|
| Injection flaws | [COMPLETE] SQL, Command, Code injection | CWE-89, 78, 94 |
| Buffer overflows | [WARNING] Limited (memory-safe languages) | CWE-120 |
| Insecure cryptography | [WARNING] Weak algorithm detection | CWE-327 |
| Insecure communications | [WARNING] Pattern matching | CWE-319 |
| Improper error handling | [WARNING] Partial | CWE-209 |
| XSS | [COMPLETE] Full taint analysis | CWE-79 |
| Improper access control | [WARNING] Partial | CWE-284 |
| CSRF | [FAILED] Not yet supported | CWE-352 |

---

### Requirement 6.3: Security Testing

**6.3.1 - Identifying Security Vulnerabilities**

Code Scalpel provides:
- Static Application Security Testing (SAST)
- Software Composition Analysis (SCA) via dependency scanning
- Secret detection for hardcoded credentials

**6.3.2 - Custom Code Review**

Code Scalpel supports:
- Automated code review for security issues
- Integration into CI/CD pipelines
- Pull request scanning

---

## Supporting Other Requirements

### Requirement 3: Protect Stored Account Data

| Req | Description | Code Scalpel Support |
|-----|-------------|---------------------|
| 3.4.1 | PAN rendered unreadable | Detect hardcoded PANs |
| 3.5.1 | Cryptographic key protection | Secret scanning for keys |

**Secret Detection Patterns:**
```python
# Detects potential PAN patterns
CARD_PATTERNS = [
    r'\b4[0-9]{12}(?:[0-9]{3})?\b',  # Visa
    r'\b5[1-5][0-9]{14}\b',           # Mastercard
    r'\b3[47][0-9]{13}\b',            # Amex
]
```

### Requirement 8: Identify and Authenticate Access

| Req | Description | Code Scalpel Support |
|-----|-------------|---------------------|
| 8.3.6 | Password complexity | Detect weak password patterns |
| 8.6.1 | Secure credential storage | Detect hardcoded credentials |

---

## Implementation for PCI Compliance

### Pre-Commit Scanning

```bash
# In pre-commit hook
code-scalpel security-scan --fail-on=HIGH
```

### CI/CD Integration

```yaml
# GitHub Actions example
- name: Security Scan
  run: |
    code-scalpel security-scan src/ --format=json > security-report.json
    code-scalpel scan-dependencies --fail-on-vulnerability
```

### Evidence Collection

```bash
# Generate PCI evidence
code-scalpel crawl-project --output=pci_inventory.json
code-scalpel security-scan --output=pci_security_scan.json
code-scalpel scan-dependencies --output=pci_dependency_scan.json
```

---

## Audit Evidence

Code Scalpel produces evidence for PCI audits:

### Requirement 6.3 Evidence

```json
{
  "requirement": "PCI DSS 6.3.2",
  "evidence_type": "security_code_review",
  "timestamp": "2025-12-15T00:00:00Z",
  "scan_results": {
    "files_scanned": 150,
    "vulnerabilities_found": 3,
    "critical": 0,
    "high": 1,
    "medium": 2,
    "remediated": true
  },
  "tool": "Code Scalpel v2.0.1"
}
```

### Requirement 6.2.4 Evidence

```json
{
  "requirement": "PCI DSS 6.2.4",
  "evidence_type": "vulnerability_prevention",
  "owasp_coverage": {
    "injection": "90%",
    "xss": "95%",
    "broken_auth": "40%",
    "sensitive_data": "80%"
  }
}
```

---

## Limitations for PCI DSS

Code Scalpel does **not** address:

| Requirement | Reason |
|-------------|--------|
| Network security (Req 1) | Infrastructure scope |
| Encryption in transit (Req 4) | Runtime scope |
| Access control (Req 7) | Configuration scope |
| Physical security (Req 9) | Physical scope |
| Logging (Req 10) | Runtime scope |
| Security testing (Req 11) | DAST/pentest scope |

---

## Recommended Complementary Tools

| Gap | Recommended Tool |
|-----|------------------|
| DAST | OWASP ZAP, Burp Suite |
| Infrastructure | Terraform compliance, AWS Config |
| Secrets management | HashiCorp Vault |
| WAF | Cloudflare, AWS WAF |
| Logging | Splunk, ELK Stack |

---

## References

- [PCI DSS v4.0](https://www.pcisecuritystandards.org/)
- [CWE Coverage Matrix](CWE_COVERAGE_MATRIX.md)
- [OWASP Top 10 Mapping](OWASP_TOP_10_MAPPING.md)
