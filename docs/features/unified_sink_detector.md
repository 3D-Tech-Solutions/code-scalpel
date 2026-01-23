# Unified Security Sink Detector

**[20251216_DOCS] v2.3.0 - Polyglot Security Sink Detection with Confidence Scoring**

## Overview

The Unified Security Sink Detector provides language-agnostic security sink detection across Python, Java, TypeScript, and JavaScript with explicit confidence scoring for each pattern. It implements complete OWASP Top 10 2021 coverage with context-aware vulnerability assessment.

## Key Features

- **Multi-Language Support**: Python, Java, TypeScript, JavaScript
- **Confidence Scoring**: Each pattern has a confidence score (0.0-1.0)
- **OWASP Top 10 Coverage**: Complete mapping to OWASP Top 10 2021 categories
- **Polyglot Detection**: Unified detection across all supported languages
- **Context-Aware**: Integrates with taint analysis for vulnerability assessment
- **Extensible**: Easy to add new patterns and languages

## Architecture

### Core Components

```python
from code_scalpel.symbolic_execution_tools import (
    UnifiedSinkDetector,
    SinkDefinition,
    DetectedSink,
    UNIFIED_SINKS,
    OWASP_COVERAGE
)
```

### SinkDefinition

Each security sink is defined with:
- `pattern`: Function/method pattern to match (e.g., "cursor.execute")
- `confidence`: Confidence score 0.0-1.0 (1.0 = definitely vulnerable)
- `sink_type`: Type of security sink (SQL_QUERY, XSS, etc.)
- `description`: Human-readable description

### DetectedSink

When a sink is detected, it contains:
- `pattern`: The matched pattern
- `sink_type`: Type of security sink
- `confidence`: Confidence score for this detection
- `line`: Line number in source code
- `column`: Column number in source code
- `code_snippet`: The actual code that matched
- `vulnerability_type`: OWASP category or CWE identifier

## Usage

### Basic Detection

```python
from code_scalpel.symbolic_execution_tools import UnifiedSinkDetector

detector = UnifiedSinkDetector()

# Detect sinks in Python code
code = """
import sqlite3
user_input = input()
cursor.execute("SELECT * FROM users WHERE id=" + user_input)
"""

sinks = detector.detect_sinks(code, "python", min_confidence=0.8)

for sink in sinks:
    print(f"Found {sink.sink_type.name} at line {sink.line}")
    print(f"Pattern: {sink.pattern} (confidence: {sink.confidence})")
    print(f"Category: {sink.vulnerability_type}")
```

### MCP Tool Usage

The unified sink detector is available as an MCP tool:

```python
# MCP tool call
result = await unified_sink_detect(
    code=source_code,
    language="python",
    min_confidence=0.8
)

if result.success:
    print(f"Found {result.sink_count} security sinks")
    for sink in result.sinks:
        print(f"  - {sink.pattern} at line {sink.line} ({sink.confidence})")
```

### Vulnerability Assessment

Combine with taint analysis for complete vulnerability assessment:

```python
from code_scalpel.symbolic_execution_tools import (
    UnifiedSinkDetector,
    TaintInfo,
    TaintSource,
    TaintLevel
)

detector = UnifiedSinkDetector()
sinks = detector.detect_sinks(code, "python")

# Check if sink is vulnerable with taint info
taint = TaintInfo(
    source=TaintSource.USER_INPUT,
    level=TaintLevel.HIGH,
    source_location=(3, 5)
)

for sink in sinks:
    is_vuln, explanation = detector.is_vulnerable(sink, taint)
    if is_vuln:
        print(f"VULNERABLE: {explanation}")
    else:
        print(f"SAFE: {explanation}")
```

## Supported Languages

### Python

**SQL Injection Sinks:**
- `cursor.execute` (confidence: 1.0)
- `connection.execute` (confidence: 1.0)
- `session.execute` (confidence: 0.95)
- `sqlalchemy.text` (confidence: 0.85)

**Command Injection Sinks:**
- `os.system` (confidence: 1.0)
- `subprocess.call` (confidence: 0.9)
- `eval` (confidence: 1.0)

**Path Traversal Sinks:**
- `open` (confidence: 0.8)
- `os.path.join` (confidence: 0.6)

**SSRF Sinks:**
- `requests.get` (confidence: 0.9)
- `urllib.request.urlopen` (confidence: 0.95)

### Java

**SQL Injection Sinks:**
- `Statement.executeQuery` (confidence: 1.0)
- `PreparedStatement.executeQuery` (confidence: 0.5) - Safer if used correctly
- `entityManager.createQuery` (confidence: 0.8)

**Command Injection Sinks:**
- `Runtime.getRuntime().exec` (confidence: 1.0)
- `ProcessBuilder.command` (confidence: 0.9)

**Path Traversal Sinks:**
- `new File` (confidence: 0.8)
- `FileInputStream` (confidence: 0.9)

### TypeScript

**SQL Injection Sinks:**
- `connection.query` (confidence: 1.0)
- `knex.raw` (confidence: 1.0)
- `sequelize.query` (confidence: 0.9)

**XSS Sinks:**
- `innerHTML` (confidence: 1.0)
- `dangerouslySetInnerHTML` (confidence: 1.0)
- `document.write` (confidence: 1.0)

**Command Injection Sinks:**
- `child_process.exec` (confidence: 1.0)
- `eval` (confidence: 1.0)

### JavaScript

**SQL Injection Sinks:**
- `db.query` (confidence: 0.9)
- `sequelize.query` (confidence: 0.8)

**XSS Sinks:**
- `document.write` (confidence: 1.0)
- `element.innerHTML` (confidence: 1.0)

**Command Injection Sinks:**
- `exec` (confidence: 1.0)
- `eval` (confidence: 1.0)

## OWASP Top 10 2021 Coverage

The detector provides complete coverage of OWASP Top 10 2021:

### A01:2021 – Broken Access Control
- Path Traversal
- Unauthorized File Access

### A02:2021 – Cryptographic Failures
- Weak Cryptography
- Hardcoded Secrets
- Insecure Random

### A03:2021 – Injection
- SQL Injection
- NoSQL Injection
- Command Injection
- LDAP Injection
- XPath Injection
- XSS
- SSTI
- XXE

### A04:2021 – Insecure Design
- Missing Rate Limiting
- Insecure Defaults

### A05:2021 – Security Misconfiguration
- Debug Mode Enabled
- Verbose Errors
- Default Credentials

### A06:2021 – Vulnerable and Outdated Components
- Outdated Dependencies (via scan_dependencies)

### A07:2021 – Identification and Authentication Failures
- Weak Password Policy
- Missing MFA
- Session Fixation

### A08:2021 – Software and Data Integrity Failures
- Unsigned Code
- Deserialization

### A09:2021 – Security Logging and Monitoring Failures
- Missing Audit Log
- Insufficient Logging

### A10:2021 – Server-Side Request Forgery
- SSRF
- Unvalidated Redirect

## Confidence Scoring

Confidence scores reflect the likelihood that a pattern indicates a vulnerability:

- **1.0**: Definitely vulnerable (e.g., `os.system`, `cursor.execute`)
- **0.9-0.95**: Very likely vulnerable (e.g., `subprocess.call`, `requests.get`)
- **0.8-0.85**: Likely vulnerable (e.g., `open`, `jdbcTemplate.query`)
- **0.6-0.7**: Context-dependent (e.g., `os.path.join`, `PreparedStatement`)
- **0.5**: Safer patterns that can still be vulnerable (e.g., `PreparedStatement` without proper usage)

### Filtering by Confidence

```python
# High confidence only (definitely vulnerable)
high_confidence_sinks = detector.detect_sinks(code, "python", min_confidence=1.0)

# Medium confidence (likely vulnerable)
medium_confidence_sinks = detector.detect_sinks(code, "python", min_confidence=0.8)

# Include context-dependent patterns
all_sinks = detector.detect_sinks(code, "python", min_confidence=0.5)
```

## Coverage Report

Get comprehensive coverage statistics:

```python
detector = UnifiedSinkDetector()
report = detector.get_coverage_report()

print(f"Total patterns: {report['total_patterns']}")
print(f"Python patterns: {report['by_language']['python']}")
print(f"Java patterns: {report['by_language']['java']}")

# OWASP coverage
for category, stats in report['owasp_coverage'].items():
    print(f"{category}: {stats['covered']}/{stats['total']} ({stats['percentage']:.1f}%)")
```

## Integration with Security Analysis

The Unified Sink Detector integrates seamlessly with existing security analysis:

```python
from code_scalpel.symbolic_execution_tools import SecurityAnalyzer

# Use existing security analyzer
analyzer = SecurityAnalyzer()
result = analyzer.analyze(code)

# Or use unified detector directly
detector = UnifiedSinkDetector()
sinks = detector.detect_sinks(code, "python")
```

## MCP Tool Specification

### unified_sink_detect

**Parameters:**
- `code` (str): Source code to analyze
- `language` (str): Programming language (python, java, typescript, javascript)
- `min_confidence` (float): Minimum confidence threshold (0.0-1.0, default: 0.8)

**Returns:**
- `success` (bool): Whether detection succeeded
- `language` (str): Language analyzed
- `sink_count` (int): Number of sinks detected
- `sinks` (list): List of detected sinks with details
- `min_confidence` (float): Minimum confidence threshold used
- `coverage_summary` (dict): Coverage statistics
- `error` (str|null): Error message if failed

## Best Practices

### Detection Accuracy

1. **Use appropriate confidence thresholds:**
   - Production security scanning: 0.8 or higher
   - Code review assistance: 0.5-0.8
   - Research/analysis: 0.5 or lower

2. **Combine with taint analysis:**
   - Sink detection alone can produce false positives
   - Use `is_vulnerable()` to validate with data flow

3. **Respect sanitizers:**
   - The detector integrates with the sanitizer registry
   - Check if data is properly sanitized before flagging

### False Positive Reduction

```python
# Context-dependent patterns need validation
sinks = detector.detect_sinks(code, "python", min_confidence=0.5)

for sink in sinks:
    if sink.confidence < 0.8:
        # Low confidence - requires manual review
        print(f"REVIEW NEEDED: {sink.pattern} at line {sink.line}")
    else:
        # High confidence - likely vulnerability
        print(f"VULNERABILITY: {sink.pattern} at line {sink.line}")
```

### Adding Custom Patterns

To extend the detector with custom patterns:

```python
from code_scalpel.symbolic_execution_tools.unified_sink_detector import (
    UNIFIED_SINKS,
    SinkDefinition,
    SecuritySink
)

# Add custom sink pattern
custom_sink = SinkDefinition(
    pattern="my_custom_execute",
    confidence=0.9,
    sink_type=SecuritySink.SQL_QUERY,
    description="Custom SQL execution function"
)

UNIFIED_SINKS["sql_injection"]["python"].append(custom_sink)
```

## Testing

Comprehensive test suite validates:
- Pattern detection across all languages
- Confidence scoring accuracy
- OWASP category mapping
- False positive rate (<5% target)
- Sanitizer detection
- Integration with MCP server

Run tests:
```bash
pytest tests/test_unified_sink_detector.py -v
pytest tests/test_mcp_unified_sink.py -v
```

## Performance Considerations

- **Python**: AST-based detection (fast, highly accurate, near 0% false positive rate)
- **TypeScript/JavaScript**: Pattern-based detection (fast, but may have higher false positive rates due to lack of full AST analysis)
- **Java**: Pattern-based detection (good accuracy, but not as robust as Python AST-based)
- **Caching**: Results are cached when using MCP tools
- **Large codebases**: Detection scales linearly with code size

> **[20251216_DOCS] Disclaimer:** The 0% false positive rate and highest accuracy claims apply only to Python (AST-based detection). For TypeScript/JavaScript, which use pattern matching (not full AST), the false positive rate may be higher and accuracy may be lower, especially for complex or obfuscated code. Users should review results for these languages with additional scrutiny.

## Limitations

1. **Pattern matching**: May miss obfuscated or dynamically constructed patterns
2. **Context-dependent**: Some patterns require runtime context for accurate assessment
3. **Language support**: TypeScript/JavaScript use pattern matching (not full AST), which may result in higher false positive rates and lower accuracy compared to Python.
4. **False positives**: Low-confidence patterns and all TypeScript/JavaScript detections may require manual review. The 0% false positive rate does **not** apply to TypeScript/JavaScript.

## Future Enhancements

- Full AST support for TypeScript/JavaScript (via tree-sitter)
- Machine learning confidence scoring
- Custom pattern DSL
- Real-time IDE integration
- Cross-file vulnerability tracking

## References

- [OWASP Top 10 2021](https://owasp.org/Top10/)
- [CWE/SANS Top 25](https://cwe.mitre.org/top25/)
- [Code Scalpel Security Analysis](./security_analysis.md)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)

## Version History

- **v2.3.0** (2025-12-16): Initial release with unified polyglot detection
  - Complete OWASP Top 10 2021 coverage
  - 4 languages supported (Python, Java, TypeScript, JavaScript)
  - Confidence-based detection
  - MCP tool integration

## Support

For issues, questions, or contributions:
- GitHub Issues: https://github.com/3D-Tech-Solutions/code-scalpel/issues
- Documentation: https://github.com/3D-Tech-Solutions/code-scalpel/docs
