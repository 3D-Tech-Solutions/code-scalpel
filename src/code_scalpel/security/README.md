# Security Analysis

**Vulnerability detection, taint analysis, and security pattern recognition**

---

## Overview

This directory contains Code Scalpel's **security analysis engine**. It provides:

<!-- TODO [COMMUNITY]: Taint analysis and vulnerability detection for Python/Java/JavaScript/TypeScript
     TODO [PRO]: Real-time scanning with incremental analysis and change tracking
     TODO [ENTERPRISE]: AI-powered vulnerability discovery and advanced persistent threat detection -->

- **Taint Analysis** - Track untrusted data flow from sources to sinks
- **Vulnerability Detection** - SQL injection, XSS, command injection, path traversal, etc.
- **Security Pattern Recognition** - Hardcoded secrets, weak crypto, dangerous patterns
- **Polyglot Sink Detection** - Unified detection across Python, JavaScript, TypeScript, Java
- **Cross-File Security Scanning** - Vulnerabilities spanning multiple files
- **Dependency Scanning** - Check for CVEs in third-party dependencies

---

## Data Flow

### Taint Analysis Pipeline

<!-- TODO [COMMUNITY]: Intra-file taint tracking (current)
     TODO [PRO]: Support for implicit flows (control flow analysis)
     TODO [ENTERPRISE]: Timing-sensitive taint (transient flows) and probabilistic analysis -->

```
Source Code
    ↓
SecurityAnalyzer.analyze()
    ├─ Identify TAINT SOURCES (user input, file reads, network)
    │  ├─ request.args, request.form
    │  ├─ input(), raw_input()
    │  ├─ open(), socket.recv()
    │  └─ os.environ
    │
    ├─ Track TAINT PROPAGATION
    │  ├─ Variable assignments
    │  ├─ Function parameters
    │  ├─ String concatenation
    │  ├─ List/dict operations
    │  └─ Function returns
    │
    └─ Detect DANGEROUS SINKS
       ├─ SQL execution (sql(), execute())
       ├─ Command execution (system(), exec(), os.popen())
       ├─ Template rendering (render_template())
       ├─ File operations (open(), unlink())
       ├─ XML parsing (parse(), fromstring())
       └─ LDAP queries (search(), bind())

<!-- TODO [COMMUNITY]: Basic cross-file taint tracking (current)
     TODO [PRO]: Module-level vulnerability aggregation and dependency analysis
     TODO [ENTERPRISE]: Distributed vulnerability analysis with shared cache -->

    ↓
Vulnerabilities Detected (with flow path)
```

### Cross-File Security Scanning
```
Project Root
    ↓
CrossFileScan.analyze()
    ├─ Build import graph
    │  ├─ Identify all imports
    │  ├─ Resolve to source files
    │  └─ Track circular imports
    │
    ├─ Trace taint across files
    │  ├─ Entry points (routes, main)
    │  ├─ Follow function calls
    │  ├─ Track data transformations
    │  └─ Limit search depth (prevent explosion)
    │
    └─ Report vulnerabilities with paths
       ├─ Source file:line
       ├─ Flow through intermediate files
       └─ Sink file:line

<!-- TODO [COMMUNITY]: OSV database vulnerability checking (current)
     TODO [PRO]: Supply chain security: SBOM generation and licensing analysis
     TODO [ENTERPRISE]: Transitive dependency tracking and supply chain attestation -->

    ↓
Cross-File Vulnerabilities (with complete call path)
```

### Dependency Scanning
```
Package Manifests
├─ requirements.txt
├─ package.json
├─ pom.xml
└─ pyproject.toml
    ↓
DependencyScanner.scan()
    ├─ Parse manifests
    ├─ Extract package names + versions
    ├─ Query OSV database (Google)
    ├─ Check for known CVEs
    └─ Calculate severity
    ↓
Vulnerability Report
├─ Package name
├─ Installed version
├─ Vulnerable versions
├─ CVE IDs
├─ Severity (CRITICAL, HIGH, MEDIUM, LOW)
└─ Remediation (update to version X)
```

---

## Core Modules (4)

<!-- TODO [COMMUNITY]: Basic analyzer, scanner, patterns, sink_detector modules
     TODO [PRO]: Add behavior analysis module for context-aware detection
     TODO [ENTERPRISE]: Add ML-based anomaly detector and graph neural network modules -->

| Module | Purpose | Key Classes | Status |
| **scanner.py** | Vulnerability scanning orchestration | `VulnerabilityScanner`, `ScanResult` | ✅ Stable |
| **patterns.py** | Security vulnerability patterns | Pattern definitions, CWE mappings | ✅ Stable |
| **sink_detector.py** | Dangerous sink detection (polyglot) | `SinkDetector`, sink registry | ✅ Stable |


<!-- TODO [PRO]: Add PII detection and sensitive data classification
     TODO [ENTERPRISE]: Add data lineage tracking for compliance (GDPR/CCPA) -->

---

## Vulnerability Coverage

<!-- TODO [COMMUNITY]: SQL, NoSQL, LDAP, Command, XXE, SSTI injection detection
     TODO [PRO]: Add prototype pollution, DOM clobbering, prototype chain pollution
     TODO [ENTERPRISE]: Add polymorphic injection patterns (polyglot attacks) -->

### Injection Attacks
- **SQL Injection (CWE-89)** - Tainted SQL queries

<!-- TODO [PRO]: Add elliptic curve vulnerability detection
     TODO [ENTERPRISE]: Add cryptographic protocol analysis and hybrid security assessment -->


<!-- TODO [ENTERPRISE]: Add code gadget chain detection and deserialization exploit analysis -->

- **NoSQL Injection (CWE-943)** - MongoDB/unstructured injection
- **LDAP Injection (CWE-90)** - LDAP filter injection
- **Command Injection (CWE-78)** - OS command execution
- **XXE (CWE-611)** - XML external entity attacks
- **SSTI (CWE-1336)** - Server-side template injection

<!-- TODO [PRO]: Add CORS misconfiguration detection
     TODO [ENTERPRISE]: Add OAuth/OIDC vulnerability analysis and SPA security assessment -->


### Data Exposure
- **Path Traversal (CWE-22)** - File path traversal
- **Hardcoded Secrets (CWE-798)** - API keys, passwords in code
- **Information Disclosure** - Sensitive data exposure

### Cryptography
- **Weak Crypto (CWE-327)** - MD5, SHA-1, DES usage
- **Insufficient Entropy** - Poor random number generation

### Code Execution
- **Code Injection (CWE-94)** - eval(), exec() usage
- **Dangerous Patterns** - shell=True in subprocess, pickle usage

### Web Security
- **Cross-Site Scripting (CWE-79)** - Unsanitized HTML/JS output
- **CSRF (CWE-352)** - Cross-site request forgery

---

## Usage Examples

### Basic Security Scan

```python
from code_scalpel.security import SecurityAnalyzer

analyzer = SecurityAnalyzer()
result = analyzer.scan_file("src/handlers.py")

for vuln in result.vulnerabilities:
    print(f"{vuln.type}: {vuln.description}")
    print(f"Severity: {vuln.severity}")
    print(f"Location: {vuln.file}:{vuln.line}")
```

### Taint Tracking

```python
from code_scalpel.security import TaintTracker

tracker = TaintTracker()
tracker.add_source("request.args", taint_level="HIGH")
tracker.add_sink("execute", taint_level="CRITICAL")

flows = tracker.find_taint_flows(code)
for flow in flows:
    print(f"Taint flow: {flow.source} → {flow.sink}")
    print(f"Path: {' → '.join(flow.path)}")
```

### Dependency Vulnerability Scanning

```python
from code_scalpel.ast_tools import OSVClient

client = OSVClient()
vulns = client.scan_dependencies("requirements.txt")

for vuln in vulns:
    print(f"{vuln.package} {vuln.version}")
    print(f"CVE: {vuln.cve_id}")
    print(f"Severity: {vuln.cvss_score}")
```

### Cross-File Security Analysis

```python
from code_scalpel.security import SecurityAnalyzer

analyzer = SecurityAnalyzer()
results = analyzer.cross_file_scan(project_root="src/")

for vuln in results.vulnerabilities:
    print(f"Vulnerability spanning files:")
    for file in vuln.affected_files:
        print(f"  - {file}")
```

---

## Taint Analysis

### Sources (Untrusted Input)
```python
# Web frameworks
request.args              # URL query parameters
request.form              # Form data
request.json              # JSON body
request.headers           # HTTP headers

# File/Network
open(file)                # File reading
socket.recv()             # Network input
os.environ                # Environment variables

# Databases
db.query()                # Database results (untrusted)
```

### Sinks (Dangerous Operations)
```python
# SQL
execute()                 # SQL execution
executemany()             # Batch execution

# Commands
os.system()               # OS command
subprocess.run()          # Subprocess

# File Operations
open(file, 'w')           # File writing
os.remove()               # File deletion

# Templates
render()                  # Template rendering
template()                # Template execution

# Code Execution
eval()                    # Python eval
exec()                    # Python exec
compile()                 # Dynamic compilation
```

### Propagation Rules
```python
# Variables
x = request.args['param']        # x is tainted
y = x.upper()                    # y is tainted (method call)
z = x + 'safe'                   # z is tainted (concatenation)

# Function calls
def process(data):               # data is tainted
    return data.strip()           # return is tainted

# Collections
list = [request.args['a']]        # list is tainted
dict = {'key': request.args}      # dict is tainted
```

---

## Severity Levels

| Level | CVSS Score | Action |
|-------|-----------|--------|
| **CRITICAL** | 9.0-10.0 | Block deployment |
| **HIGH** | 7.0-8.9 | Require review |
| **MEDIUM** | 4.0-6.9 | Plan fix |
| **LOW** | 0.1-3.9 | Track |
| **INFO** | N/A | Document |

---

## Integration with MCP Tools

| MCP Tool | Uses | Purpose |
|----------|------|---------|
| `security_scan` | SecurityAnalyzer | Scan single file |
| `cross_file_security_scan` | SecurityAnalyzer | Multi-file scan |
| `scan_dependencies` | OSVClient | Check CVEs |
| `unified_sink_detect` | SinkDetector | Detect sinks |

---

## Configuration

```python
from code_scalpel.security import SecurityAnalyzer

analyzer = SecurityAnalyzer(
    severity_threshold="medium",    # Min severity to report
    check_dependencies=True,        # Scan CVEs
    enable_taint_analysis=True,     # Track data flow
    custom_sources=[...],           # Custom source definitions
    custom_sinks=[...],             # Custom sink definitions
    timeout_seconds=300             # Analysis timeout
)
```

---

## Data Flow

### Input (FROM)
```
AST Tools (ast_tools/)
    ↓ (parsed AST, code structure)
Source Code Files
    ↓ (Python, Java, JS/TS, etc.)
Dependency Files (requirements.txt, package.json, pom.xml)
    ↓ (vulnerability scanning)
MCP Server (mcp_server.py)
    ↓ (tool invocation)
Agents (agents/, especially SecurityAgent)
```

### Processing (WITHIN)
```
Code Analysis
    ↓
TaintTracker
    ├─ Track sources (request.args, file reads, etc.)
    ├─ Propagate through assignments & calls
    └─ Find flows to sinks
    ↓
SecurityAnalyzer
    ├─ Pattern matching (hardcoded secrets, weak crypto)
    ├─ Vulnerability detection (SQL injection, XSS, etc.)
    └─ CWE mapping
    ↓
SinkDetector
    ├─ Identify dangerous operations
    └─ Cross-language sink detection
    ↓
Dependency Analysis
    ├─ Parse dependency files
    └─ Query OSV database for CVEs
```

### Output (TO)
```
Vulnerability Results
    ├─ Taint flows (source → sink path)
    ├─ Vulnerabilities (type, CWE, CVSS)
    ├─ Pattern matches (secrets, weak crypto)
    ├─ Dependency CVEs (package, version, advisory)
    └─ Remediation suggestions
    ↓
Agents (SecurityAgent, CodeReviewAgent)
    ↓
MCP Tools (security_scan, cross_file_security_scan, scan_dependencies)
    ↓
User / Claude / Copilot
```

---

## Development Roadmap

### Phase 1: Core Detection (Complete ✅)
- [x] Taint analysis implementation
- [x] SQL injection detection
- [x] XSS detection
- [x] Command injection detection
- [x] Hardcoded secret detection (30+ patterns)
- [x] Weak cryptography detection
- [x] Pattern-based vulnerability matching
- [x] OSV dependency scanning

### Phase 2: Advanced Detection (Planned 🔄)

#### Enhanced Taint Analysis (8 TODOs)
- [ ] Context-sensitive taint analysis
- [ ] Field-sensitive tracking
- [ ] Object-sensitive analysis
- [ ] Interprocedural taint flow
- [ ] Taint "laundering" detection
- [ ] Implicit taint propagation
- [ ] Taint loss tracking
- [ ] Taint summary generation for libraries

#### Expanded Vulnerability Detection (12 TODOs)
- [ ] XXE (XML External Entity) expansion
- [ ] SSTI (Server-Side Template Injection) patterns
- [ ] LDAP injection detection
- [ ] Path traversal validation bypass
- [ ] CSRF token validation issues
- [ ] Authentication bypass patterns
- [ ] Authorization bypass patterns
- [ ] Insecure deserialization detection
- [ ] Unsafe reflection detection
- [ ] JAAS authentication issues
- [ ] Cryptographic key exposure
- [ ] Sensitive data logging

#### Enhanced Dependency Analysis (6 TODOs)
- [ ] Transitive dependency CVE tracking
- [ ] License compliance checking
- [ ] Dependency version recommendation
- [ ] Supply chain security analysis
- [ ] Dependency tree visualization
- [ ] Version constraint normalization

#### Framework-Specific Rules (10 TODOs)
- [ ] Django-specific security rules
- [ ] Flask-specific rules
- [ ] FastAPI-specific rules
- [ ] Spring Boot rules
- [ ] Express.js rules
- [ ] React security rules
- [ ] Vue.js security rules
- [ ] Next.js rules
- [ ] Rust-specific rules
- [ ] Go-specific rules

### Phase 3: Enterprise Features (Future)
- [ ] Custom rule definition language
- [ ] Policy-based scanning enforcement
- [ ] Vulnerability tracking & lifecycle
- [ ] SAST/DAST result correlation
- [ ] Security metrics & trending
- [ ] Risk scoring & prioritization
- [ ] Compliance mapping (CWE, OWASP, PCI-DSS)
- [ ] Automated remediation suggestions
- [ ] Integration with SIEM systems

1. **Sanitize Input** - Always validate and sanitize user input
2. **Use Parameterized Queries** - Never concatenate SQL
3. **Escape Output** - Escape HTML/JS output
4. **Use Security Libraries** - Rely on proven crypto/encoding libs
5. **Keep Dependencies Updated** - Scan for CVEs regularly
6. **Code Review** - Human review of security-critical code
7. **Automated Testing** - Include security tests in CI/CD

---

## File Structure

```
security/
├── README.md                [This file]
├── __init__.py              [Exports security modules]
├── analyzer.py              [Taint analysis]
├── scanner.py               [Vulnerability scanning]
├── patterns.py              [Security patterns]
└── sink_detector.py         [Sink detection]
```

---

**Last Updated:** December 21, 2025  
**Version:** v3.0.0  
**Status:** 4 Modules Stable ✅ (Total TODOs: 73)
