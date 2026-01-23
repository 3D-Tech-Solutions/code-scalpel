<!-- [20251215_DOCS] Compliance: SOC 2 Controls Mapping -->

# SOC 2 Controls Mapping

This document maps Code Scalpel's capabilities to SOC 2 Trust Services Criteria (TSC).

---

## SOC 2 Overview

SOC 2 is an auditing framework based on five Trust Services Criteria:

1. **Security** - Protection against unauthorized access
2. **Availability** - System availability for operation
3. **Processing Integrity** - Complete and accurate processing
4. **Confidentiality** - Protection of confidential information
5. **Privacy** - Collection and use of personal information

Code Scalpel primarily supports **Security** and **Confidentiality** criteria through secure development practices.

---

## Security (Common Criteria)

### CC6: Logical and Physical Access Controls

| Criteria | Description | Code Scalpel Support |
|----------|-------------|---------------------|
| CC6.1 | Logical access security | Detect hardcoded credentials |
| CC6.6 | Protection from malicious software | Vulnerability detection |
| CC6.7 | Manage system vulnerabilities | SAST + SCA scanning |

#### CC6.1 Implementation

**Secret Detection:**
```
Tool: security_scan
Detects: API keys, passwords, private keys, tokens
Evidence: Scan reports showing no hardcoded credentials
```

#### CC6.7 Implementation

**Vulnerability Management:**
```
Tools: security_scan, scan_dependencies
Process: CI/CD integration with blocking on HIGH severity
Evidence: Scan history showing remediation timeline
```

---

### CC7: System Operations

| Criteria | Description | Code Scalpel Support |
|----------|-------------|---------------------|
| CC7.1 | Detect security events | Vulnerability findings |
| CC7.2 | Monitor system components | Dependency monitoring |
| CC7.4 | Respond to incidents | Remediation guidance |

#### CC7.1 Implementation

**Security Event Detection:**
```
Tool: security_scan
Detection: Injection, XSS, SSTI, XXE, Path Traversal
Alert: JSON reports with severity classification
```

---

### CC8: Change Management

| Criteria | Description | Code Scalpel Support |
|----------|-------------|---------------------|
| CC8.1 | Authorization of changes | PR scanning before merge |

#### CC8.1 Implementation

**Change Authorization:**
```
Tool: simulate_refactor
Process: Verify no new vulnerabilities before applying changes
Evidence: Pre/post scan comparison
```

---

## Confidentiality (C Series)

### C1: Confidential Information

| Criteria | Description | Code Scalpel Support |
|----------|-------------|---------------------|
| C1.1 | Identify confidential information | Secret scanning |
| C1.2 | Protect confidential information | Detect exposure |

#### Implementation

**Confidential Information Protection:**
```
Tool: security_scan (secret detection)
Patterns: AWS keys, database credentials, API tokens
Evidence: No secrets in codebase reports
```

---

## Supplemental Criteria

### Software Development (S Series)

These criteria are particularly relevant for technology companies:

| Criteria | Description | Code Scalpel Support |
|----------|-------------|---------------------|
| S1.1 | Secure development processes | SAST integration |
| S1.2 | Testing for vulnerabilities | Automated security testing |
| S1.3 | Security review of changes | PR scanning |

---

## Control Activities by Tool

### security_scan

| SOC 2 Control | Evidence Generated |
|---------------|-------------------|
| CC6.1 | No hardcoded credentials report |
| CC6.7 | Vulnerability scan results |
| CC7.1 | Security findings with severity |
| C1.1 | Secret detection results |

### scan_dependencies

| SOC 2 Control | Evidence Generated |
|---------------|-------------------|
| CC6.7 | Vulnerable dependency list |
| CC7.2 | Third-party component inventory |

### simulate_refactor

| SOC 2 Control | Evidence Generated |
|---------------|-------------------|
| CC8.1 | Pre-change security validation |

### crawl_project

| SOC 2 Control | Evidence Generated |
|---------------|-------------------|
| CC6.7 | Complete software inventory |

---

## Evidence Generation for Audits

### Sample Security Scan Evidence

```json
{
  "soc2_control": "CC6.7",
  "evidence_type": "vulnerability_scan",
  "scan_date": "2025-12-15",
  "tool_version": "Code Scalpel 2.0.1",
  "results": {
    "files_analyzed": 235,
    "vulnerabilities": {
      "critical": 0,
      "high": 0,
      "medium": 2,
      "low": 5
    },
    "remediation_status": "medium_in_progress"
  },
  "next_scan": "2025-12-22"
}
```

### Sample Dependency Scan Evidence

```json
{
  "soc2_control": "CC7.2",
  "evidence_type": "dependency_scan",
  "scan_date": "2025-12-15",
  "dependencies_scanned": 45,
  "vulnerable_dependencies": 1,
  "vulnerability_details": [
    {
      "package": "requests",
      "version": "2.25.0",
      "cve": "CVE-2023-XXXXX",
      "severity": "MEDIUM",
      "fixed_version": "2.31.0"
    }
  ]
}
```

---

## Audit Preparation Checklist

### For CC6.7 (Vulnerability Management)

- [ ] Run `security_scan` on all repositories
- [ ] Run `scan_dependencies` for SCA
- [ ] Document remediation process
- [ ] Show historical scan trends

### For CC7.1 (Security Event Detection)

- [ ] Configure CI/CD integration
- [ ] Set up alerting for HIGH/CRITICAL
- [ ] Document incident response process

### For C1.1 (Confidential Information)

- [ ] Run secret scanning
- [ ] Verify no credentials in code
- [ ] Document secret management process

---

## Limitations

Code Scalpel does **not** address:

| SOC 2 Area | Reason |
|------------|--------|
| Physical security | Infrastructure scope |
| Network security | Runtime scope |
| Access management | IAM scope |
| Availability controls | Infrastructure scope |
| Privacy controls | Data handling scope |

---

## References

- [AICPA SOC 2](https://www.aicpa.org/soc4so)
- [CWE Coverage Matrix](CWE_COVERAGE_MATRIX.md)
- [NIST CSF Alignment](NIST_CSF_ALIGNMENT.md)
