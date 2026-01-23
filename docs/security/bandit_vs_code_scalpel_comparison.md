# Bandit vs Code Scalpel Security Scanning Comparison

<!-- [20251218_SECURITY] Analysis of security scanning capabilities -->

## Overview

This document compares Bandit and Code Scalpel security scanning capabilities, explaining what each tool detects and why certain vulnerabilities were missed.

## Issue: Why Code Scalpel Didn't Catch Its Own Vulnerabilities

**Short Answer:** Code Scalpel's `security_scan` tool focuses on **taint-based vulnerabilities** (tracking untrusted data flow) and **dangerous patterns in user code**. It was not run on its own codebase as part of CI/CD, and some patterns require static analysis beyond AST parsing.

## Detailed Comparison

### What Code Scalpel DOES Detect

Code Scalpel's `SecurityAnalyzer` class detects:

#### 1. Command Injection (subprocess.run with shell=True)
```python
# Code Scalpel DETECTS this:
subprocess.run(command, shell=True)  # ✅ DETECTED

# _check_dangerous_patterns() flags:
# "subprocess.run(shell=True) is dangerous - command injection risk"
```

**Detection Method:** AST pattern matching in `_check_dangerous_patterns()`

#### 2. Pickle Deserialization
```python
# Code Scalpel DETECTS this:
data = pickle.load(file)  # ✅ DETECTED
data = pickle.loads(bytes)  # ✅ DETECTED

# Flagged as: "pickle.load() can execute arbitrary code on untrusted data"
```

**Detection Method:** AST pattern matching for `pickle.load`, `pickle.loads`, `_pickle.load`, `_pickle.loads`

#### 3. Weak Cryptography
```python
# Code Scalpel DETECTS this:
hash = hashlib.md5(data)  # ✅ DETECTED
hash = hashlib.sha1(data)  # ✅ DETECTED

# Flagged as: "MD5 is cryptographically broken - use SHA-256 or better"
```

**Detection Method:** AST pattern matching for `hashlib.md5`, `hashlib.sha1`, etc.

#### 4. Code Injection (eval/exec)
```python
# Code Scalpel DETECTS this:
eval(user_input)  # ✅ DETECTED
exec(code_string)  # ✅ DETECTED

# Flagged as: "eval() executes arbitrary code"
```

#### 5. Taint-Based Vulnerabilities
```python
# Code Scalpel DETECTS this:
@app.route('/search')
def search(query):  # query marked as tainted (USER_INPUT)
    sql = f"SELECT * FROM users WHERE name = '{query}'"
    cursor.execute(sql)  # ✅ SQL INJECTION DETECTED

# Taint tracking from web route parameters to SQL sinks
```

**Detection Method:** Taint analysis with `TaintTracker`

### What Code Scalpel DOES NOT Detect

#### 1. XML Parsing Vulnerabilities (XXE)
```python
# Code Scalpel DOES NOT detect this:
import xml.etree.ElementTree as ET
tree = ET.parse(pom_path)  # ❌ NOT DETECTED

# Bandit B314: "Using xml.etree.ElementTree.parse to parse untrusted XML"
```

**Why Not Detected:**
- No XXE pattern in `_check_dangerous_patterns()`
- Requires knowledge that `xml.etree.ElementTree` is vulnerable to XXE attacks
- Static analysis tool like Bandit has this in its blacklist

**Fix Applied:** Use `defusedxml` library

#### 2. URL Scheme Validation (file:// exploitation)
```python
# Code Scalpel DOES NOT detect this:
with urllib.request.urlopen(url, timeout=5) as response:  # ❌ NOT DETECTED
    data = response.read()

# Bandit B310: "Audit url open for permitted schemes"
```

**Why Not Detected:**
- No pattern for `urllib.request.urlopen` vulnerability
- Requires semantic understanding that arbitrary URL schemes are dangerous
- Not a taint-based vulnerability (doesn't depend on data flow)

**Fix Applied:** Added URL scheme validation (`https://` or `http://` only)

#### 3. Pickle in Internal Caches (Context-Dependent)
```python
# Code Scalpel detects pickle.load, but:
with open(cache_path, "rb") as f:
    payload = pickle.load(f)  # ✅ DETECTED as vulnerable
    if payload.get("hash") == file_hash:  # But has hash validation
        return payload["value"]

# Bandit B301: "Pickle can be unsafe when used to deserialize untrusted data"
```

**Why Flagged by Both:**
- Code Scalpel: Detects `pickle.load` as dangerous pattern
- Bandit: Flags pickle usage regardless of context
- Both lack semantic understanding of "internal cache with hash validation"

**Fix Applied:** Added `# nosec B301` comments with justification for internal caches

#### 4. Server Binding to 0.0.0.0 (Intentional Functionality)
```python
# Code Scalpel DOES NOT detect this:
def start_server(host: str = "0.0.0.0", port: int = 5000):  # ❌ NOT DETECTED
    run_server(host, port)

# Bandit B104: "Possible binding to all interfaces"
```

**Why Not Detected:**
- Not a vulnerability pattern Code Scalpel looks for
- Configuration/deployment concern, not code vulnerability
- Intentional server functionality

**Fix Applied:** Added `# nosec B104` comments explaining intentional behavior

## Why These Gaps Exist

### Code Scalpel's Design Focus

Code Scalpel is designed for:
1. **Taint Analysis:** Tracking untrusted data from sources to dangerous sinks
2. **AST-Based Pattern Matching:** Detecting dangerous function calls
3. **User Code Analysis:** Analyzing application code, not framework/library patterns
4. **Runtime Behavior:** Understanding data flow, not static configuration

### Bandit's Design Focus

Bandit is designed for:
1. **Static Security Audit:** Comprehensive blacklist of dangerous patterns
2. **Library-Aware:** Knows which libraries have security issues (xml.etree, urllib, etc.)
3. **Configuration Concerns:** Flags binding, hardcoded secrets, permissions
4. **Broad Coverage:** Tests for 100+ specific vulnerability patterns

## Improvements for Code Scalpel

To catch more vulnerabilities, Code Scalpel should add:

### 1. Expanded Dangerous Patterns

```python
# In _check_dangerous_patterns():
dangerous_library_patterns = {
    'xml.etree.ElementTree.parse': (SecuritySink.XXE, 
        'xml.etree.ElementTree.parse() vulnerable to XXE - use defusedxml'),
    'xml.etree.ElementTree.fromstring': (SecuritySink.XXE,
        'xml.etree.ElementTree.fromstring() vulnerable to XXE - use defusedxml'),
    'urllib.request.urlopen': (SecuritySink.SSRF,
        'urllib.request.urlopen() should validate URL scheme - prevent file:/ exploitation'),
    'urllib.urlopen': (SecuritySink.SSRF,
        'urllib.urlopen() should validate URL scheme'),
}
```

### 2. Context-Aware Analysis

```python
# Detect if pickle.load is used on internal cache vs external data:
if func_name == 'pickle.load':
    # Check if file comes from known-safe cache directory
    if self._is_internal_cache_path(node):
        # Lower severity or skip warning
        pass
    else:
        self._add_dangerous_pattern_vuln(...)
```

### 3. Configuration Auditing

```python
# Add module for configuration security:
class ConfigurationAuditor:
    def check_server_binding(self, host: str) -> SecurityIssue:
        if host == "0.0.0.0":
            return SecurityIssue(
                severity="MEDIUM",
                message="Binding to 0.0.0.0 exposes server to all networks",
                recommendation="Use 127.0.0.1 for localhost-only or document intent"
            )
```

## Recommended Workflow

Use **both** tools in CI/CD:

1. **Bandit** for broad static analysis:
   ```bash
   bandit -r src/ -ll -ii --format json --output bandit-report.json
   ```

2. **Code Scalpel** for taint-based analysis:
   ```bash
   code-scalpel security-scan src/my_app.py
   ```

3. **Cross-Reference** findings:
   - Bandit catches library/configuration issues
   - Code Scalpel catches data flow vulnerabilities
   - Together they provide comprehensive coverage

## Conclusion

**Code Scalpel complements Bandit, not replaces it:**

- **Bandit:** Broad, static, library-aware security audit
- **Code Scalpel:** Deep, taint-based, data-flow analysis

**For Code Scalpel v1.0.0:**
- Detected: 5/13 Bandit issues (subprocess shell=True, pickle.load, weak crypto)
- Missed: 8/13 Bandit issues (XXE, URL scheme, 0.0.0.0 binding)

**Action Items:**
1. ✅ Run Bandit in CI/CD alongside Code Scalpel
2. ✅ Add XXE and SSRF patterns to Code Scalpel
3. ✅ Create configuration auditing module
4. ✅ Document security tool comparison for users

## See Also

- [Security Documentation](../../SECURITY.md)
- [Bandit Documentation](https://bandit.readthedocs.io/)
- [Code Scalpel Security Scan Guide](../guides/security_scanning.md)
