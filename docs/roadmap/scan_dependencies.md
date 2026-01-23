# scan_dependencies Tool Roadmap

**Tool Name:** `scan_dependencies`  
**Tool Version:** v1.0  
**Code Scalpel Version:** v3.3.1  
**Current Status:** Stable  
**Primary Module:** `src/code_scalpel/mcp/server.py`  
**Tier Availability:** All tiers (Community, Pro, Enterprise)

---

## Configuration Files

| File | Purpose |
|------|---------|
| `src/code_scalpel/licensing/features.py` | Tier capability definitions |
| `.code-scalpel/limits.toml` | Numeric limits (max_dependencies) |
| `.code-scalpel/response_config.json` | Output filtering |
| `.code-scalpel/dependency-policy.toml` | Blocked packages (Enterprise) |

---

## Overview

The `scan_dependencies` tool scans project dependencies for known vulnerabilities using the OSV (Open Source Vulnerabilities) database.

**Why AI Agents Need This:**
- **Security awareness:** Agents know about vulnerable dependencies before generating code
- **Supply chain safety:** Detect typosquatting and malicious packages
- **Compliance:** Enterprise compliance reporting for security audits
- **Smart suggestions:** Agents can suggest safe package alternatives
- **Risk quantification:** Supply chain risk scoring for informed decisions

---

## Research Queries for Future Development

### Foundational Research
| Topic | Query | Purpose |
|-------|-------|---------|
| Vulnerability Databases | "open source vulnerability databases comparison OSV NVD" | Data source optimization |
| Reachability | "vulnerability reachability analysis static analysis" | Reduce false positives |
| Supply Chain | "software supply chain attack detection methods" | Better detection |
| SBOM | "software bill of materials generation standards SPDX CycloneDX" | SBOM support |

### Language-Specific Research
| Topic | Query | Purpose |
|-------|-------|---------|
| PyPI Security | "python package index malicious package detection" | Better Python scanning |
| npm Security | "npm dependency confusion attack prevention" | JavaScript improvements |
| Maven | "java dependency vulnerability scanning tools" | Java support |
| Go Modules | "go module proxy vulnerability checking" | Go support |

### Advanced Techniques
| Topic | Query | Purpose |
|-------|-------|---------|
| ML Detection | "machine learning malicious package detection" | AI-powered scanning |
| Risk Prediction | "dependency risk prediction software metrics" | Better risk scoring |
| Update Safety | "automated dependency update safety verification" | Safe auto-updates |
| License AI | "automated license compatibility checking" | Smarter compliance |

---

## Current Capabilities (v1.0)

### Community Tier
- ✅ CVE detection via OSV API (`osv_vulnerability_detection`)
- ✅ Severity scoring (CVSS) (`severity_scoring`)
- ✅ Supports Python (requirements.txt, pyproject.toml)
- ✅ Supports JavaScript (package.json)
- ✅ Supports Java (pom.xml, build.gradle)
- ✅ Basic remediation suggestions (`fixed_version` field)
- ⚠️ **Limits:** max_dependencies=50

### Pro Tier
- ✅ All Community features (unlimited dependencies)
- ✅ Vulnerability reachability analysis (`reachability_analysis`)
- ✅ License compliance checking (`license_compliance`)
- ✅ Typosquatting detection (`typosquatting_detection`)
- ✅ Supply chain risk scoring (`supply_chain_risk_scoring`)
- ✅ False positive reduction via reachability (`false_positive_reduction`)
- 🔄 Update recommendations (`update_recommendations`) - **Planned for v1.1**

### Enterprise Tier
- ✅ All Pro features
- 🔄 Custom vulnerability database (`custom_vulnerability_database`) - **Planned for v1.1**
- 🔄 Private dependency scanning (`private_dependency_scanning`) - **Planned for v1.1**
- 🔄 Automated remediation PRs (`automated_remediation`) - **Planned for v1.1**
- ✅ Policy-based blocking (`policy_based_blocking`)
- ✅ Compliance reporting (SOC2, ISO) (`compliance_reporting`)

---

## Return Model: DependencyScanResult

```python
class DependencyScanResult(BaseModel):
    # Core fields (All Tiers)
    success: bool                              # Whether scan succeeded
    dependencies: list[DependencyInfo]         # Scanned dependencies
    vulnerabilities: list[VulnerabilityInfo]   # Found CVEs
    total_dependencies: int                    # Total deps scanned
    vulnerable_count: int                      # Deps with vulnerabilities
    highest_severity: str                      # "critical" | "high" | "medium" | "low"
    scan_duration_ms: int                      # Scan time in milliseconds
    
    # Pro Tier
    reachable_vulns: list[VulnerabilityInfo]   # Actually reachable in code
    license_issues: list[LicenseIssue]         # License compliance problems
    typosquat_warnings: list[TyposquatWarning] # Potential typosquatting
    supply_chain_score: float                  # 0-100 risk score
    update_recommendations: list[UpdateRec]    # Safe upgrade paths
    
    # Enterprise Tier
    compliance_report: ComplianceReport        # SOC2/ISO/PCI compliance
    policy_violations: list[PolicyViolation]   # Blocked package violations
    sbom: SBOM | None                          # Software Bill of Materials
    
    error: str | None                          # Error message if failed
```

---

## Usage Examples

### Community Tier
```python
result = await scan_dependencies(
    project_root="/path/to/project"
)
# Returns: dependencies (max 50), vulnerabilities, severity info
# Supports requirements.txt, package.json, pom.xml
```

### Pro Tier
```python
result = await scan_dependencies(
    project_root="/path/to/project",
    check_reachability=True,
    check_licenses=True
)
# Additional: reachable_vulns, license_issues, typosquat_warnings,
#             supply_chain_score, update_recommendations
# Unlimited dependencies
```

### Enterprise Tier
```python
result = await scan_dependencies(
    project_root="/path/to/project",
    compliance_frameworks=["soc2", "pci-dss"],
    generate_sbom=True
)
# Additional: compliance_report, policy_violations, sbom
# Full compliance reporting
```

---

## MCP Request/Response Examples

### MCP Request Format

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "mcp_code-scalpel_scan_dependencies",
    "arguments": {
      "project_root": "/home/user/my-project"
    }
  },
  "id": 1
}
```

### Community Tier Response

```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "dependencies": [
      {"name": "requests", "version": "2.28.0", "source": "requirements.txt"},
      {"name": "flask", "version": "2.2.0", "source": "requirements.txt"},
      {"name": "pyyaml", "version": "5.4.0", "source": "requirements.txt"}
    ],
    "vulnerabilities": [
      {
        "id": "CVE-2022-42969",
        "package": "pyyaml",
        "installed_version": "5.4.0",
        "fixed_version": "6.0.1",
        "severity": "critical",
        "cvss_score": 9.8,
        "description": "Arbitrary code execution via yaml.load()",
        "reference": "https://nvd.nist.gov/vuln/detail/CVE-2022-42969"
      }
    ],
    "total_dependencies": 45,
    "vulnerable_count": 3,
    "highest_severity": "critical",
    "scan_duration_ms": 1250,
    "reachable_vulns": null,
    "license_issues": null,
    "typosquat_warnings": null,
    "supply_chain_score": null,
    "update_recommendations": null,
    "compliance_report": null,
    "policy_violations": null,
    "sbom": null,
    "error": null
  },
  "id": 1
}
```

### Pro Tier Response

```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "dependencies": [
      {"name": "requests", "version": "2.28.0", "source": "requirements.txt"},
      {"name": "flask", "version": "2.2.0", "source": "requirements.txt"},
      {"name": "pyyaml", "version": "5.4.0", "source": "requirements.txt"}
    ],
    "vulnerabilities": [
      {
        "id": "CVE-2022-42969",
        "package": "pyyaml",
        "installed_version": "5.4.0",
        "fixed_version": "6.0.1",
        "severity": "critical",
        "cvss_score": 9.8,
        "description": "Arbitrary code execution via yaml.load()",
        "reference": "https://nvd.nist.gov/vuln/detail/CVE-2022-42969"
      }
    ],
    "total_dependencies": 125,
    "vulnerable_count": 5,
    "highest_severity": "critical",
    "scan_duration_ms": 3200,
    "reachable_vulns": [
      {
        "id": "CVE-2022-42969",
        "package": "pyyaml",
        "reachable": true,
        "call_path": ["src/config.py:load_config", "yaml.load()"],
        "evidence": "config.py line 45: yaml.load(f, Loader=yaml.FullLoader)"
      }
    ],
    "license_issues": [
      {
        "package": "some-gpl-lib",
        "license": "GPL-3.0",
        "issue": "GPL license incompatible with MIT project license",
        "severity": "high"
      }
    ],
    "typosquat_warnings": [
      {
        "package": "requets",
        "similar_to": "requests",
        "confidence": 0.95,
        "warning": "Possible typosquatting: 'requets' looks like 'requests'"
      }
    ],
    "supply_chain_score": 72.5,
    "update_recommendations": [
      {
        "package": "pyyaml",
        "current": "5.4.0",
        "recommended": "6.0.1",
        "breaking_changes": false,
        "reason": "Fixes CVE-2022-42969"
      },
      {
        "package": "flask",
        "current": "2.2.0",
        "recommended": "3.0.0",
        "breaking_changes": true,
        "reason": "Security improvements and Python 3.8+ required"
      }
    ],
    "compliance_report": null,
    "policy_violations": null,
    "sbom": null,
    "error": null
  },
  "id": 1
}
```

### Enterprise Tier Response

```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "dependencies": [],
    "vulnerabilities": [],
    "total_dependencies": 250,
    "vulnerable_count": 8,
    "highest_severity": "critical",
    "scan_duration_ms": 8500,
    "reachable_vulns": [],
    "license_issues": [],
    "typosquat_warnings": [],
    "supply_chain_score": 68.2,
    "update_recommendations": [],
    "compliance_report": {
      "frameworks": ["SOC2", "PCI-DSS"],
      "status": "partial",
      "soc2": {
        "status": "pass",
        "controls_checked": 12,
        "controls_passed": 12,
        "findings": []
      },
      "pci_dss": {
        "status": "fail",
        "controls_checked": 8,
        "controls_passed": 6,
        "findings": [
          {
            "control": "6.2",
            "description": "Critical vulnerabilities must be patched within 30 days",
            "violation": "CVE-2022-42969 (pyyaml) is 90 days old"
          },
          {
            "control": "6.5.1",
            "description": "Protect against injection flaws",
            "violation": "yaml.load() without safe loader detected"
          }
        ]
      },
      "generated_at": "2025-12-29T14:30:22Z",
      "report_id": "compliance-scan-20251229-143022"
    },
    "policy_violations": [
      {
        "policy": "blocked-packages",
        "package": "eval-unsafe",
        "version": "1.0.0",
        "reason": "Package is on organization blocklist",
        "action": "remove"
      }
    ],
    "sbom": {
      "format": "CycloneDX",
      "version": "1.4",
      "components_count": 250,
      "download_url": "/api/sbom/project-123-20251229.json",
      "generated_at": "2025-12-29T14:30:22Z"
    },
    "error": null
  },
  "id": 1
}
```

---

## Integration Points

### Related Tools
| Tool | Relationship |
|------|--------------|
| `security_scan` | Code-level security (deps are external) |
| `get_project_map` | Project structure context |
| `validate_paths` | Ensure dependency files accessible |
| `crawl_project` | Detect dependency file locations |

### Export Formats
| Format | Status | Use Case |
|--------|--------|----------|
| **JSON** | ✅ v1.0 | Programmatic analysis |
| **SARIF** | 🔄 v1.2 | IDE/CI integration |
| **SPDX** | 🔄 v1.4 | SBOM standard |
| **CycloneDX** | 🔄 v1.4 | SBOM standard |
| **CSV** | 🔄 v1.2 | Spreadsheet reports |

---

## Competitive Analysis

| Tool | Strengths | Weaknesses | Our Differentiation |
|------|-----------|------------|---------------------|
| **Snyk** | Extensive DB, good UI | Expensive | Tier-based, MCP-native |
| **Dependabot** | GitHub integration | GitHub-only | Cross-platform |
| **npm audit** | Built-in for JS | JS ecosystem only | Multi-language unified |
| **pip-audit** | Python-focused | Python only | Multi-language, supply chain |
| **OWASP Dependency-Check** | Enterprise-grade | Heavy, complex | Lightweight, AI-friendly |
| **Trivy** | Container + deps | Container focus | Code-first approach |

---

## Roadmap

### v1.1 (Q1 2026): Core Feature Completion

#### Pro Tier
- [ ] Update recommendations (`update_recommendations`)
  - Analyze breaking changes in upgrades
  - Suggest safe upgrade paths
  - Provide rollback guidance

#### Enterprise Tier
- [ ] Custom vulnerability database (`custom_vulnerability_database`)
  - Support private vulnerability databases
  - Integrate with internal security tools
  - Custom CVE definitions
- [ ] Private dependency scanning (`private_dependency_scanning`)
  - Scan private NPM/PyPI registries
  - Support authenticated package sources
  - Internal package vulnerability tracking
- [ ] Automated remediation PRs (`automated_remediation`)
  - Automatic pull request creation
  - Safe dependency version updates
  - Automated testing verification

### v1.2 (Q1 2026): Enhanced Detection

#### Community Tier
- [ ] .NET (NuGet) support
- [ ] Ruby (Gemfile) support

#### Pro Tier
- [ ] Go (go.mod) support
- [ ] Rust (Cargo.toml) support
- [ ] PHP (composer.json) support
- [ ] Transitive dependency analysis

#### Enterprise Tier
- [ ] Container image scanning
- [ ] Binary dependency scanning
- [ ] Custom policy enforcement

### v1.2 (Q2 2026): Integration & Automation

#### Community Tier
- [ ] GitHub Dependabot integration
- [ ] CI/CD pipeline integration
- [ ] SARIF output format

#### Pro Tier
- [ ] Automated PR creation for fixes
- [ ] Slack/Teams notifications
- [ ] Jira ticket creation

#### Enterprise Tier
- [ ] ServiceNow integration
- [ ] Custom webhook notifications
- [ ] SSO/SAML authentication

### v1.3 (Q3 2026): AI-Enhanced Analysis

#### Pro Tier
- [ ] ML-based severity contextualization
- [ ] Exploit likelihood prediction
- [ ] Automated patch verification

#### Enterprise Tier
- [ ] Custom risk models
- [ ] Threat intelligence integration
- [ ] Zero-day prediction

### v1.4 (Q4 2026): Advanced Features

#### Pro Tier
- [ ] Dependency upgrade recommendations
- [ ] Breaking change detection
- [ ] Performance impact analysis

#### Enterprise Tier
- [ ] Supply chain attack detection
- [ ] Dependency provenance verification
- [ ] SBOM (Software Bill of Materials) generation

---

## Known Issues & Limitations

### Current Limitations
- **Private packages:** Cannot scan private repositories without credentials
- **False positives:** Some vulnerabilities may not be reachable
- **OSV API limits:** Rate limits may apply

### Planned Fixes
- v1.1: Private registry support
- v1.2: Better reachability analysis
- v1.3: OSV API caching

---

## Success Metrics

### Performance Targets
- **Scan time:** <5s for 100 dependencies
- **Accuracy:** >95% correct vulnerability detection
- **False positive rate:** <10%

### Adoption Metrics
- **Usage:** 100K+ scans per month by Q4 2026
- **Vulnerabilities found:** 50K+ CVEs detected

---

## Dependencies

### Internal Dependencies
- `mcp/server.py` - MCP tool handler and implementation
- `security/dependencies/vulnerability_scanner.py` - Vulnerability scanner
- `security/dependencies/osv_client.py` - OSV API client
- `licensing/features.py` - Tier capability definitions

### External Dependencies
- OSV API (api.osv.dev)
- PyPI API (for license lookup)
- npm Registry API (for license lookup)

---

## Breaking Changes

None planned for v1.x series.

---

## Changelog

### v1.0 (December 31, 2025)
- **Community Tier:** CVE detection via OSV API with CVSS severity scoring
- **Community Tier:** Multi-language support (Python, JavaScript, Java)
- **Community Tier:** Basic remediation suggestions via `fixed_version` field
- **Pro Tier:** Added `reachability_analysis` capability with import scanning
- **Pro Tier:** Added `license_compliance` capability with PyPI/npm license lookup
- **Pro Tier:** Added `typosquatting_detection` with Levenshtein distance algorithm
- **Pro Tier:** Added `supply_chain_risk_scoring` with multi-factor risk calculation
- **Pro Tier:** Added `false_positive_reduction` via reachability analysis
- **Enterprise:** Added `compliance_reporting` with SOC2/ISO framework support (server.py#L7150-7250)
- **Enterprise:** Added `policy_based_blocking` with violation detection
- **Model:** Added `DependencyInfo.supply_chain_risk_score` and `supply_chain_risk_factors` fields
- **Model:** Added `DependencyScanResult.compliance_report` and `policy_violations` fields
- **Documentation:** Initial roadmap and testing documentation

---

**Last Updated:** January 8, 2026  
**Next Review:** March 31, 2026
