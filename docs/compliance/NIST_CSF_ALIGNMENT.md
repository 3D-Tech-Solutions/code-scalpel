<!-- [20251215_DOCS] Compliance: NIST Cybersecurity Framework Alignment -->

# NIST Cybersecurity Framework Alignment

This document maps Code Scalpel's capabilities to the NIST Cybersecurity Framework (CSF) 2.0.

---

## Framework Overview

The NIST CSF provides a structured approach to managing cybersecurity risk through six core functions:

1. **Govern (GV)** - Establish and monitor cybersecurity strategy
2. **Identify (ID)** - Understand assets and risks
3. **Protect (PR)** - Implement safeguards
4. **Detect (DE)** - Identify cybersecurity events
5. **Respond (RS)** - Take action on detected events
6. **Recover (RC)** - Restore capabilities

---

## Code Scalpel's Role

Code Scalpel operates primarily in the **Identify** and **Detect** functions, supporting secure software development practices.

---

## Alignment Matrix

### Identify (ID)

| Subcategory | ID | Code Scalpel Capability | Coverage |
|-------------|----|-----------------------|----------|
| Asset Management | ID.AM-01 | Project crawling identifies all code assets | [COMPLETE] Full |
| Asset Management | ID.AM-02 | Software inventory via dependency scanning | [COMPLETE] Full |
| Risk Assessment | ID.RA-01 | Vulnerability detection in code | [COMPLETE] Full |
| Risk Assessment | ID.RA-02 | Threat identification via taint analysis | [COMPLETE] Full |
| Supply Chain | ID.SC-04 | Dependency vulnerability scanning (OSV) | [COMPLETE] Full |

#### Implementation Details

**ID.AM-01: Hardware/Software Inventory**
```
Tool: crawl_project
Output: Complete file inventory with functions, classes, complexity metrics
```

**ID.AM-02: Software Platform Inventory**
```
Tool: scan_dependencies
Output: All dependencies with versions from requirements.txt, pyproject.toml, package.json
```

**ID.RA-01: Vulnerability Identification**
```
Tools: security_scan, cross_file_security_scan
Output: Vulnerabilities with CWE mappings, severity, and remediation guidance
```

---

### Protect (PR)

| Subcategory | ID | Code Scalpel Capability | Coverage |
|-------------|----|-----------------------|----------|
| Identity Management | PR.AA-05 | Authentication flow analysis | [WARNING] Partial |
| Data Security | PR.DS-01 | Sensitive data detection (secrets) | [COMPLETE] Full |
| Data Security | PR.DS-02 | Data-in-transit patterns | [WARNING] Partial |
| Secure Development | PR.PS-01 | Security vulnerability detection | [COMPLETE] Full |
| Secure Development | PR.PS-02 | Secure coding pattern validation | [COMPLETE] Full |

#### Implementation Details

**PR.DS-01: Data-at-Rest Protection**
```
Tool: security_scan (secret detection)
Detects: Hardcoded credentials, API keys, private keys
```

**PR.PS-01/02: Secure Software Development**
```
Tools: security_scan, simulate_refactor
Validates: No new vulnerabilities introduced in code changes
```

---

### Detect (DE)

| Subcategory | ID | Code Scalpel Capability | Coverage |
|-------------|----|-----------------------|----------|
| Continuous Monitoring | DE.CM-01 | Static analysis in CI/CD | [COMPLETE] Full |
| Continuous Monitoring | DE.CM-06 | External service monitoring (deps) | [COMPLETE] Full |
| Adverse Event Analysis | DE.AE-02 | Vulnerability correlation | [COMPLETE] Full |
| Adverse Event Analysis | DE.AE-03 | Impact analysis via call graph | [COMPLETE] Full |

#### Implementation Details

**DE.CM-01: Network Monitoring (Static Analysis)**
```
Integration: CI/CD pipeline via CLI or MCP
Continuous scanning of code changes for vulnerabilities
```

**DE.CM-06: External Service Monitoring**
```
Tool: scan_dependencies
Queries OSV database for known vulnerabilities in dependencies
```

**DE.AE-03: Impact Analysis**
```
Tools: get_call_graph, get_symbol_references
Determines blast radius of vulnerable code
```

---

### Respond (RS)

| Subcategory | ID | Code Scalpel Capability | Coverage |
|-------------|----|-----------------------|----------|
| Incident Analysis | RS.AN-03 | Vulnerability forensics via taint paths | [COMPLETE] Full |
| Incident Mitigation | RS.MI-01 | Safe code modification | [COMPLETE] Full |
| Incident Mitigation | RS.MI-02 | Remediation guidance | [WARNING] Partial |

#### Implementation Details

**RS.AN-03: Forensics / Impact Analysis**
```
Tool: security_scan
Output: Taint propagation paths showing how untrusted data reaches sinks
```

**RS.MI-01: Incident Containment**
```
Tool: update_symbol
Safely patch vulnerable code with backup and validation
```

---

## CSF Implementation Tiers

Code Scalpel supports organizations at different maturity levels:

### Tier 1: Partial
- Ad-hoc security scans via CLI
- Manual review of findings

### Tier 2: Risk Informed
- Integrated into development workflow
- Vulnerability prioritization by severity

### Tier 3: Repeatable
- CI/CD integration with automated gates
- Consistent scanning policies

### Tier 4: Adaptive
- Continuous monitoring via MCP agents
- AI-assisted remediation

---

## Recommended Integration

### For NIST CSF Compliance

1. **Identify Phase:**
   - Run `crawl_project` on all repositories
   - Schedule `scan_dependencies` weekly
   - Maintain software inventory

2. **Protect Phase:**
   - Enable secret scanning in CI/CD
   - Use `simulate_refactor` before merging

3. **Detect Phase:**
   - Run `security_scan` on every PR
   - Configure alerts for HIGH/CRITICAL findings

4. **Respond Phase:**
   - Use taint paths to understand vulnerabilities
   - Apply fixes with `update_symbol`

---

## Evidence Generation

Code Scalpel produces evidence suitable for NIST CSF audits:

```json
{
  "framework": "NIST CSF 2.0",
  "control": "DE.CM-01",
  "evidence_type": "vulnerability_scan",
  "timestamp": "2025-12-15T00:00:00Z",
  "findings": {
    "total": 5,
    "critical": 0,
    "high": 1,
    "medium": 3,
    "low": 1
  },
  "tool_version": "2.0.1"
}
```

---

## References

- [NIST CSF 2.0](https://www.nist.gov/cyberframework)
- [CWE Coverage Matrix](CWE_COVERAGE_MATRIX.md)
- [OWASP Top 10 Mapping](OWASP_TOP_10_MAPPING.md)
