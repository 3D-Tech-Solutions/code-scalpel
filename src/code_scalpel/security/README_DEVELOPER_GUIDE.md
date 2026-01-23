# Security Analysis Module - Developer Guide

**Version:** v3.0.0 "Autonomy"  
**Status:** Production-Ready with Migration Plan  
**Last Updated:** December 21, 2025

---

## Overview

<!-- TODO [COMMUNITY]: Taint analysis, vulnerability detection, polyglot sink detection (current)
     TODO [PRO]: Real-time incremental scanning and threat modeling
     TODO [ENTERPRISE]: ML-powered vulnerability discovery and APT detection -->

The Security Analysis module provides **comprehensive vulnerability detection** across multiple programming languages. It is the backbone of Code Scalpel's security scanning capabilities, implementing:

- **Taint Analysis** - Track untrusted data flow through code
- **Vulnerability Detection** - Identify SQL injection, XSS, command injection, path traversal, etc.
- **Polyglot Sink Detection** - Unified dangerous operation detection across Python, Java, JavaScript, TypeScript
- **Dependency Scanning** - Check for known CVEs in third-party dependencies
- **Cross-File Analysis** - Trace vulnerabilities spanning multiple files
- **Event-Streaming Security** - Taint tracking for Kafka, Pub/Sub, message queues

---

## Architecture Overview

<!-- TODO [COMMUNITY]: Basic taint_tracker, security_analyzer, unified_sink_detector (current)
     TODO [PRO]: Add behavioral analyzer and anomaly detector modules
     TODO [ENTERPRISE]: Add graph neural network and ML-based vulnerability discovery -->

### Current Structure (Pre-Migration)

```
src/code_scalpel/symbolic_execution_tools/
├── taint_tracker.py               [2,386 lines - Core taint analysis]
├── security_analyzer.py           [975 lines - High-level vulnerability detection]
├── unified_sink_detector.py       [959 lines - Polyglot sink detection]
├── cross_file_taint.py            [1,282 lines - Multi-file taint tracking]
├── vulnerability_scanner.py       [631 lines - CVE and dependency scanning]
└── kafka_taint_tracker.py         [1,080 lines - Event-streaming security]
```

### Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SOURCE CODE INPUT                            │
│  (Python, Java, JavaScript, TypeScript - single or multi-file)      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │  AST Parsing    │
                    │  (ast_tools/)   │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
    ┌────▼─────┐      ┌─────▼──────┐      ┌───▼────────┐
    │TaintTrack│      │SecurityAnly│      │UnifiedSink │
    │   er     │      │  zer       │      │  Detector  │
    └────┬─────┘      └─────┬──────┘      └───┬────────┘
         │                  │                   │
         └──────────────────┼───────────────────┘
                            │
                   ┌────────▼────────┐
                   │ Vulnerability   │
                   │ Detection       │
                   │ (SQL, XSS, etc)│
                   └────────┬────────┘
                            │
    ┌───────────────────────┼───────────────────────┐
    │                       │                       │
┌───▼─────────┐    ┌────────▼────────┐    ┌───────▼───┐
│Single-File  │    │Cross-File Taint │    │Dependency │
│Results      │    │  Analysis       │    │  Scanning │
└──────┬──────┘    └────────┬────────┘    └───┬───────┘
       │                    │                  │
       └────────────────────┼──────────────────┘
                            │
                   ┌────────▼────────┐
                   │ Unified Report  │
                   │ - Vulnerabilities
                   │ - Taint Flows
                   │ - CWE Mappings
                   │ - Severity Scores
                   └─────────────────┘
```

---

<!-- TODO [COMMUNITY]: Basic variable taint tracking (current)
     TODO [PRO]: Support for implicit flows (control dependencies)
     TODO [ENTERPRISE]: Probabilistic taint analysis for transient flows -->

## Module Details

### 1. TaintTracker (2,386 lines)

**File:** `symbolic_execution_tools/taint_tracker.py`  
**Purpose:** Core taint analysis engine  
<!-- TODO [PRO]: Add TaintContext class for flow-sensitive analysis
     TODO [ENTERPRISE]: Add TaintGraph for complex dependency tracking -->

**Tests:** 128 test methods

#### Key Classes

```python
class TaintSource(Enum):
    """Where untrusted data enters the system."""
    USER_INPUT          # request.args, input(), etc.
    FILE_CONTENT        # open(), file reads
    NETWORK_DATA        # socket.recv(), urllib
    ENVIRONMENT_VAR     # os.environ
    DATABASE_RESULT     # Database queries (conditional)

class TaintLevel(Enum):
    """How dangerous is the tainted data?"""
    UNTAINTED          # No taint
    LOW                # Maybe tainted (conservative)
    MEDIUM             # Likely tainted
    HIGH               # Definitely tainted
    CRITICAL           # Multi-stage attack confirmed

class SecuritySink(Enum):
    """Where dangerous operations happen."""
    SQL_QUERY          # cursor.execute()
    XSS_SINK           # render_template(), innerHTML
    COMMAND_EXEC       # os.system(), subprocess.run()
    FILE_OPERATION     # open(), os.remove()
<!-- TODO [PRO]: Add analyze_implicit_flows() for control-based taint
     TODO [ENTERPRISE]: Add symbolic_taint() for constraint-based analysis -->

    TEMPLATE_RENDER    # Jinja2, Django templates
    XML_PARSE          # XML parsing with XXE risk
    LDAP_QUERY         # LDAP directory search
```

#### Core Methods

```python
def add_source(self, name: str, taint_level: TaintLevel) -> None:
    """Mark a variable as a taint source."""
    
def track_taint(self, code: str) -> List[Vulnerability]:
    """Analyze code and return detected vulnerabilities."""
    
def find_taint_flows(self) -> List[TaintFlow]:
    """Get all taint flows from source → sink."""
```

#### Example Usage

```python
from code_scalpel.symbolic_execution_tools.taint_tracker import (
    TaintTracker, TaintLevel
)

tracker = TaintTracker()
tracker.add_source("request.args", TaintLevel.HIGH)
tracker.add_sink("execute", TaintLevel.CRITICAL)

code = """
user_id = request.args.get('id')
query = f"SELECT * FROM users WHERE id={user_id}"
cursor.execute(query)  # SQL INJECTION!
"""

vulnerabilities = tracker.track_taint(code)
for vuln in vulnerabilities:
    print(f"Vulnerability: {vuln.type}")
    print(f"Taint Path: {vuln.taint_flow}")
    print(f"Location: {vuln.location}")
```

<!-- TODO [COMMUNITY]: SQL, XSS, command injection detection (current)
     TODO [PRO]: Add context-aware false positive reduction
     TODO [ENTERPRISE]: Add semantic-aware vulnerability discovery -->

### 2. SecurityAnalyzer (975 lines)

**File:** `symbolic_execution_tools/security_analyzer.py`  
**Purpose:** High-level vulnerability detection  
**Tests:** 128 test methods (combined with taint tracker)

#### Detected Vulnerabilities

<!-- TODO [PRO]: Add prototype pollution, DOM clobbering detection
     TODO [ENTERPRISE]: Add polymorphic attack pattern detection -->

- **SQL Injection (CWE-89)** - Tainted SQL queries
- **Cross-Site Scripting (CWE-79)** - Unsanitized HTML/JS output
- **Command Injection (CWE-78)** - OS command execution with taint
- **Path Traversal (CWE-22)** - File path manipulation
- **XXE (CWE-611)** - XML external entity attacks
- **SSTI (CWE-1336)** - Server-side template injection
- **LDAP Injection (CWE-90)** - LDAP filter injection

#### Key Functions

```python
def analyze_security(code: str) -> SecurityResult:
    """Analyze code for security vulnerabilities."""
    
def find_sql_injections(code: str) -> List[Vulnerability]:
    """Find SQL injection vulnerabilities."""
    
def find_xss(code: str) -> List[Vulnerability]:
    """Find XSS vulnerabilities."""
    
def find_command_injections(code: str) -> List[Vulnerability]:
    """Find command injection vulnerabilities."""
```

#### Example Usage

```python
from code_scalpel.symbolic_execution_tools.security_analyzer import (
    analyze_security
)

code = """
def login(request):
    username = request.form.get('username')
    password = request.form.get('password')
    
    # SQL INJECTION!
    query = f"SELECT * FROM users WHERE username='{username}'"
    user = db.query(query)
<!-- TODO [COMMUNITY]: Python, Java, JavaScript, TypeScript sink detection (current)
     TODO [PRO]: Add Ruby, Go, C# language support
     TODO [ENTERPRISE]: Add framework-specific sinks (Django, Rails, Spring, etc) -->

    
    # XSS!
    return render_template('welcome.html', message=username)
<!-- TODO [PRO]: Add framework-aware sink detection
     TODO [ENTERPRISE]: Add vulnerability chain detection (multiple sinks) -->

"""

result = analyze_security(code)
print(f"Found {len(result.vulnerabilities)} vulnerabilities")
for vuln in result.vulnerabilities:
    print(f"  - {vuln.type} at line {vuln.line}")
```

### 3. UnifiedSinkDetector (959 lines)

**File:** `symbolic_execution_tools/unified_sink_detector.py`  
**Purpose:** Polyglot dangerous operation detection  
**Tests:** 38 test methods  
**Languages:** Python, Java, JavaScript, TypeScript

#### Features

- **Language-Agnostic Sinks** - Detect dangerous operations across languages
- **Confidence Scoring** - 0.0-1.0 confidence for each pattern
- **OWASP Top 10 2021 Complete** - All 10 categories mapped
- **Context-Aware** - Understands sanitization and parameterization

#### Supported Sinks by Language

**Python:**
- SQL: `cursor.execute()`, `execute_query()`, `db.execute()`
- XSS: `render_template()`, `jinja2.Template()`
- Commands: `os.system()`, `subprocess.run()`, `os.popen()`
- Files: `open()`, `os.remove()`, `os.chmod()`

**Java:**
- SQL: `executeQuery()`, `executeUpdate()`, `PreparedStatement`
- Commands: `ProcessBuilder`, `Runtime.exec()`
- Files: `File`, `FileWriter`, `FileInputStream`

**JavaScript/TypeScript:**
- DOM: `innerHTML`, `eval()`, `Function()`
- SQL: `query()`, `execute()` (custom frameworks)
- Commands: `child_process.exec()`, `execSync()`

#### Example Usage

```python
from code_scalpel.symbolic_execution_tools.unified_sink_detector import (
    UnifiedSinkDetector
)

detector = UnifiedSinkDetector()

# Python code
result = detector.detect("python", """
cursor.execute("SELECT * FROM users WHERE id=" + user_id)
""")

# Java code
result = detector.detect("java", """
Connection conn = DriverManager.getConnection(url);
PreparedStatement stmt = conn.prepareStatement(query);
stmt.execute();
""")

# JavaScript code
result = detector.detect("javascript", """
const sql = "SELECT * FROM users WHERE id=" + userId;
db.query(sql);
""")
```

### 4. CrossFileTaintTracker (1,282 lines)

**File:** `symbolic_execution_tools/cross_file_taint.py`  
**Purpose:** Multi-file vulnerability analysis  
**Tests:** 25 test methods

#### Capabilities

- **Import Graph Analysis** - Track data flow across file boundaries
- **Function Call Tracing** - Follow taint through function calls
- **Vulnerability Chains** - Detect vulnerabilities spanning 3+ files
- **Circular Import Detection** - Prevent infinite analysis loops

#### Example: Multi-File Vulnerability

```python
# routes.py
from flask import request
from db import execute_query

def get_user():
    user_id = request.args.get('id')  # TAINT SOURCE
    return execute_query(user_id)
```

```python
# db.py
def execute_query(user_id):
    query = f"SELECT * FROM users WHERE id={user_id}"
    cursor.execute(query)  # TAINT SINK - SQL INJECTION!
```

**Detection:**
```python
from code_scalpel.symbolic_execution_tools.cross_file_taint import (
    CrossFileTaintTracker
)

tracker = CrossFileTaintTracker()
results = tracker.analyze_project("src/")

for vuln in results.vulnerabilities:
    print(f"Vulnerability: {vuln.type}")
    print(f"Source file: {vuln.source_file}:{vuln.source_line}")
    print(f"Sink file: {vuln.sink_file}:{vuln.sink_line}")
    print(f"Path: {' → '.join(vuln.call_path)}")
```

### 5. VulnerabilityScanner (631 lines)

<!-- TODO [COMMUNITY]: Python, JS, Java package manager support (current)
     TODO [PRO]: Add Go, Rust, .NET package manager support
     TODO [ENTERPRISE]: Add transitive dependency analysis and license compliance -->

**File:** `symbolic_execution_tools/vulnerability_scanner.py`  
**Purpose:** Dependency scanning and CVE detection  
**Tests:** 23 test methods  
**Standard:** A06:2021 - Vulnerable and Outdated Components

#### Supported Package Managers

<!-- TODO [PRO]: Add private registry support (Artifactory, Nexus)
     TODO [ENTERPRISE]: Add supply chain attestation and SBOM generation -->

- **Python:** requirements.txt, pyproject.toml, setup.py
- **JavaScript/Node:** package.json, package-lock.json
- **Java:** pom.xml, build.gradle
<!-- TODO [PRO]: Add GHSA (GitHub Security Advisory) detection
     TODO [ENTERPRISE]: Add zero-day vulnerability detection via ML -->


#### CVE Detection

```python
from code_scalpel.symbolic_execution_tools.vulnerability_scanner import (
    VulnerabilityScanner
)

scanner = VulnerabilityScanner()

# Scan Python dependencies
vulns = scanner.scan_file("requirements.txt")
for vuln in vulns:
    print(f"Package: {vuln.package} {vuln.version}")
    print(f"Vulnerability: {vuln.cve_id}")
    print(f"Severity: {vuln.severity}")  # CRITICAL, HIGH, MEDIUM, LOW
    print(f"Update to: {vuln.fixed_version}")
```

#### Severity Levels

| Level | CVSS Score | Action |
|-------|-----------|--------|
| CRITICAL | 9.0-10.0 | Block deployment |
<!-- TODO [COMMUNITY]: Kafka taint tracking (current)
     TODO [PRO]: Add AWS Kinesis, GCP Pub/Sub, Azure Service Bus support
     TODO [ENTERPRISE]: Add real-time event pipeline security monitoring -->

| HIGH | 7.0-8.9 | Require review |
| MEDIUM | 4.0-6.9 | Plan fix |
<!-- TODO [PRO]: Add schema registry validation (Confluent)
     TODO [ENTERPRISE]: Add distributed tracing integration (Jaeger/Zipkin) -->

| LOW | 0.1-3.9 | Track |

### 6. KafkaTaintTracker (1,080 lines)

**File:** `symbolic_execution_tools/kafka_taint_tracker.py`  
**Purpose:** Event-streaming security (Kafka, Pub/Sub, message queues)  
**Tests:** 48 test methods

#### Features

- **Event Schema Analysis** - Detect schema drift vulnerabilities
- **Message Taint Tracking** - Track sensitive data in events
- **Consumer/Producer Analysis** - Verify message security boundaries
- **Multi-Broker Support** - Kafka, AWS Kinesis, GCP Pub/Sub

#### Example Usage

```python
from code_scalpel.symbolic_execution_tools.kafka_taint_tracker import (
    KafkaTaintTracker
)

tracker = KafkaTaintTracker()

# Monitor Kafka producer
result = tracker.analyze_producer("""
def publish_user_event(user_data):
    producer.send('user-events', {
        'user_id': user_data['id'],
<!-- TODO [COMMUNITY]: Basic unit tests for all modules (current)
     TODO [PRO]: Add integration tests and end-to-end security scenarios
     TODO [ENTERPRISE]: Add fuzzing and adversarial ML testing -->

        'credit_card': user_data['cc']  # SENSITIVE DATA!
    })
""")

for issue in result.security_issues:
    print(f"Issue: {issue.type}")
    print(f"Sensitive data leaked: {issue.leaked_fields}")
```

---

## Testing Infrastructure

### Test Files (10 Total, 325 Tests)

| Test File | Tests | Focus |
|-----------|-------|-------|
| test_security_analysis.py | 128 | Taint tracking, vulnerability detection |
| test_cross_file_taint.py | 25 | Multi-file taint flows |
| test_unified_sink_detector.py | 38 | Polyglot sinks, OWASP coverage |
| test_vulnerability_scanner.py | 23 | CVE scanning, dependency analysis |
| test_adversarial_security.py | 20 | Edge cases, attack patterns |
| test_framework_sinks.py | 16 | Framework-specific sinks |
| test_kafka_taint_tracker.py | 48 | Event-streaming security |
| test_ssr_security.py | 16 | Server-side rendering security |
| test_java_security_sinks.py | 2 | Java-specific patterns |
| test_mcp_unified_sink.py | 9 | MCP tool integration |

**Total Test Code:** 5,985 lines

<!-- TODO [COMMUNITY]: Unit tests for basic functionality (current)
     TODO [PRO]: Add integration tests and real-world scenarios
     TODO [ENTERPRISE]: Add fuzzing, adversarial testing, and mutation testing -->

### Running Tests

```bash
# All security tests
pytest tests/test_*security*.py tests/test_*taint*.py tests/test_*vulnerability*.py tests/test_*sink*.py -v

# Specific test file
pytest tests/test_security_analysis.py -v

# With coverage
pytest tests/test_security_analysis.py --cov=code_scalpel.symbolic_execution_tools
```

---

## MCP Tool Integration

<!-- TODO [COMMUNITY]: Basic MCP tools for security scanning (current)
     TODO [PRO]: Add incremental scanning and caching support
     TODO [ENTERPRISE]: Add streaming results and real-time scanning -->

The security module powers these Code Scalpel MCP tools:

### 1. security_scan

```python
from code_scalpel.mcp_server import MCP_TOOLS

# Scan a single file for vulnerabilities
result = MCP_TOOLS['security_scan'](
    file_path="src/handlers.py"
)

for vuln in result.vulnerabilities:
    print(f"{vuln.type}: {vuln.description}")
    print(f"Severity: {vuln.severity}")
    print(f"CWE: {vuln.cwe}")
```

### 2. cross_file_security_scan

```python
# Scan entire project for cross-file vulnerabilities
result = MCP_TOOLS['cross_file_security_scan'](
    project_root="src/"
)

for vuln in result.vulnerabilities:
    print(f"Vulnerability spanning {len(vuln.files)} files")
    print(f"Call path: {' → '.join(vuln.call_path)}")
```

### 3. scan_dependencies

```python
# Check for CVEs in dependencies
result = MCP_TOOLS['scan_dependencies'](
    path="requirements.txt"
)

for vuln in result.vulnerabilities:
    print(f"{vuln.package} {vuln.version} - {vuln.cve_id}")
```

### 4. unified_sink_detect

```python
# Polyglot sink detection
result = MCP_TOOLS['unified_sink_detect'](
    code="cursor.execute(user_input)",
    language="python"
)

for sink in result.sinks:
    print(f"Sink: {sink.name} (confidence: {sink.confidence})")
```

<!-- TODO [COMMUNITY]: Phase 1 - Core injection and sink detection (complete)
     TODO [PRO]: Phase 2 - Framework-specific rules and advanced taint analysis
     TODO [ENTERPRISE]: Phase 3 - ML-powered detection and automated remediation -->

---

## Development Roadmap

### Phase 1: Core Detection (✅ Complete)

- [x] Taint analysis
- [x] SQL injection detection
- [x] XSS detection
- [x] Command injection detection
- [x] Hardcoded secret detection
- [x] Weak cryptography detection
<!-- TODO [PRO]: Add Django, Flask, FastAPI framework-specific rules
     TODO [PRO]: Add context-sensitive taint tracking for accuracy
     TODO [ENTERPRISE]: Add transitive dependency analysis and SBOM generation -->

- [x] OSV dependency scanning

### Phase 2: Enhanced Detection (🔄 Planned)

**Framework-Specific Rules** (25 TODOs)
- [ ] Django security rules
- [ ] Flask security rules
- [ ] FastAPI async security
- [ ] Spring Boot rules

<!-- TODO [PRO]: Context-sensitive taint tracking
     TODO [ENTERPRISE]: Probabilistic taint analysis for complex flows -->

- [ ] Express.js middleware rules
- [ ] React/Next.js SSR rules


<!-- TODO [ENTERPRISE]: Transitive dependency tracking and attestation
     TODO [ENTERPRISE]: License compliance and vulnerability lifecycle tracking -->

**Advanced Taint Analysis** (15 TODOs)
- [ ] Context-sensitive taint tracking
- [ ] Field-sensitive tracking
- [ ] Object-sensitive analysis
- [ ] Interprocedural taint flow
- [ ] Taint laundering detection

<!-- TODO [ENTERPRISE]: Custom rule definition language and policy enforcement
     TODO [ENTERPRISE]: SIEM integration and compliance mapping (PCI-DSS, HIPAA)
     TODO [ENTERPRISE]: Automated remediation and vulnerability lifecycle tracking -->


**Supply Chain Security** (10 TODOs)
- [ ] Transitive dependency tracking
- [ ] License compliance checking
- [ ] Supply chain risk assessment
- [ ] Dependency update recommendations

<!-- TODO [ENTERPRISE]: ML-powered detection and automated fix generation
     TODO [ENTERPRISE]: Continuous security monitoring and risk trending
     TODO [ENTERPRISE]: Integration with SAST, DAST, and container scanning -->

**Enterprise Features** (20 TODOs)
- [ ] Custom rule definition language
- [ ] Policy-based enforcement
- [ ] Vulnerability lifecycle tracking
- [ ] SIEM integration
- [ ] Compliance mapping (PCI-DSS, HIPAA, SOC2)

### Phase 3: Enterprise (Future)

- [ ] Automated remediation
- [ ] Security metrics & trending
- [ ] Risk scoring & prioritization
- [ ] Integration with external SAST/DAST tools

---

## Common Use Cases

<!-- TODO [PRO]: Add complexity reduction hints for developers
     TODO [ENTERPRISE]: Add automated remediation suggestions -->

### Use Case 1: Find SQL Injections in Web Application

```python
from code_scalpel.security.analyzers import SecurityAnalyzer

analyzer = SecurityAnalyzer()

# Single file scan
result = analyzer.scan_file("src/api/handlers.py")

# Filter for SQL injections
sql_injections = [
    v for v in result.vulnerabilities 
    if v.type == "SQL_INJECTION"
]

for vuln in sql_injections:
    print(f"SQL Injection at {vuln.file}:{vuln.line}")
    print(f"Taint flow: {vuln.taint_flow}")
```

### Use Case 2: Audit Dependency Security

```python
from code_scalpel.security.dependencies import VulnerabilityScanner

scanner = VulnerabilityScanner()

# Scan all dependencies
vulns = scanner.scan_directory(".")

# Group by severity
critical = [v for v in vulns if v.severity == "CRITICAL"]
high = [v for v in vulns if v.severity == "HIGH"]

print(f"Critical: {len(critical)}")
print(f"High: {len(high)}")

# Print remediation steps
for vuln in critical:
    print(f"\nUpdate {vuln.package}:")
    print(f"  Current: {vuln.version}")
    print(f"  Fixed: {vuln.fixed_version}")
```

### Use Case 3: Multi-File Vulnerability Analysis

```python
from code_scalpel.security.analyzers.cross_file_taint import CrossFileTaintTracker

tracker = CrossFileTaintTracker()

# Analyze entire project
results = tracker.analyze_project("src/")

# Show vulnerability chains
for vuln in results.vulnerabilities:
    print(f"{vuln.type}:")
    for i, file_step in enumerate(vuln.files):
        print(f"  {i+1}. {file_step['file']}:{file_step['line']}")
```

---

## Migration Status

<!-- TODO [COMMUNITY]: Complete migration to security/ directory (v3.1.0)
     TODO [PRO]: Add backward compatibility layer for existing integrations
     TODO [ENTERPRISE]: Add migration utilities for users -->

**Current Location:** `src/code_scalpel/symbolic_execution_tools/`  
**Target Location:** `src/code_scalpel/security/` (Coming in v3.1.0)

**Migration Plan:** See [SECURITY_MIGRATION_PLAN.md](./SECURITY_MIGRATION_PLAN.md)

**Deprecation Timeline:**
- v3.1.0: Reorganization with backward compatibility shims
- v3.2.0: Deprecation shims removed

**No Breaking Changes:** Deprecation shims will maintain backward compatibility for 6 months.

---

## Best Practices

<!-- TODO [PRO]: Add automated best practices linter
     TODO [ENTERPRISE]: Add industry-specific best practices (OWASP, NIST, CIS) -->

### 1. Always Mark Taint Sources

```python
tracker = TaintTracker()
tracker.add_source("request.args", TaintLevel.HIGH)
tracker.add_source("user_input", TaintLevel.HIGH)
tracker.add_source("file_content", TaintLevel.MEDIUM)
```

### 2. Use Parameterized Queries

```python
# ❌ VULNERABLE
query = f"SELECT * FROM users WHERE id={user_id}"

# ✅ SAFE
query = "SELECT * FROM users WHERE id=?"
cursor.execute(query, (user_id,))
```

### 3. Escape Output Properly

```python
# ❌ VULNERABLE
template = render_template('template.html', user_message=user_input)

# ✅ SAFE
template = render_template('temp

<!-- TODO [PRO]: Add automatic dependency update suggestions
     TODO [ENTERPRISE]: Add supply chain attack detection for updates -->late.html', user_message=escape(user_input))
```

### 4. Keep Dependencies Updated

```bash
# Check for CVEs
code-scalpel scan-dependencies requirements.txt

# Update
pip install --upgrade vulnerable_package
```

### 5. Use Framework Security Libraries

```python
# Django
from django.db.models.raw_sql import RawSQL  # Use parameterization
from django.utils.html import escape  # XSS protection

# Flask
from werkzeug.security import check_password_hash  # Secure password handling
```

---

## Integration Points

### With Code Scalpel Modules

```
security/
├── Depends on: ast_tools, ir/
├── Imports from: symbolic_execution_tools (IR interpreter)
├── Tested by: 325 tests in tests/
└── Used by: mcp_server (MCP tools)
```

### With External Tools

```
CVE Scanning:
  - OSV API (Google) for dependency vulnerabilities
  - Supports: Python, npm, Maven

Pattern Matching:
  - AST-based analysis (language-agnostic)
  - Z3 symbolic execution (constraint solving)
```

---

## Performance Considerations

### Analysis Time

- **Single file scan:** <1 second (typical Python file)
- **Multi-file project scan:** 5-30 seconds (depends on project size)
- **Dependency scan:** <5 seconds (for 50+ dependencies)

### Memory Usage

- **Taint tracking:** ~50MB per 100K lines of code
- **Cross-file analysis:** ~100MB for typical projects
- **Dependency scanning:** Minimal (<10MB)

### Optimization Tips

1. **Exclude test files:** Speeds up analysis by 30-50%
2. **Use language-specific analysis:** Skip unused languages
3. **Cache results:** Reuse previous scan results for incremental updates

---

## Troubleshooting

### Issue: "Module not found" for security imports

**Solution:** Update import path to use new location (see Migration Plan)

```python
# Old (deprecated)
from code_scalpel.symbolic_execution_tools.taint_tracker import TaintTracker

# New
from code_scalpel.security.core.taint_tracker import TaintTracker
```

### Issue: False positives in taint analysis

**Solution:** Register custom sanitizers

```python
from code_scalpel.symbolic_execution_tools.taint_tracker import register_sanitizer

register_sanitizer("my_safe_function", sanitizes_input=True)
```

### Issue: Cross-file analysis too slow

**Solution:** Set depth limit and exclude directories

```python
from code_scalpel.symbolic_execution_tools.cross_file_taint import CrossFileTaintTracker

tracker = CrossFileTaintTracker(
    max_depth=3,  # Limit traversal depth
    exclude_dirs=[".venv", "tests", "docs"]
)
```

---

## Contributing

Security module contributions are welcome! Areas for improvement:

1. **Framework-specific rules** - Add Django, Flask, FastAPI rules
2. **Additional sinks** - Expand polyglot sink detection
3. **Performance optimization** - Improve analysis speed
4. **Test coverage** - Expand edge case testing

See [DEVELOPMENT_ROADMAP.md](../../DEVELOPMENT_ROADMAP.md) for more details.

---

## Reference Documentation

- **Architecture:** [docs/architecture/](../../docs/architecture/)
- **API Reference:** Code docstrings and type hints
- **Examples:** [examples/security_analysis_example.py](../../examples/)
- **Tests:** [tests/test_security_analysis.py](../../tests/)

---

**Last Updated:** December 21, 2025  
**Maintained By:** Code Scalpel Team  
**Status:** Production Ready ✅
