<!-- [20251215_DOCS] Compliance: CWE Coverage Matrix -->

# CWE Coverage Matrix

This document maps Code Scalpel's security detection capabilities to Common Weakness Enumeration (CWE) identifiers.

---

## Coverage Summary

| Category | CWEs Covered | Detection Rate |
|----------|--------------|----------------|
| Injection | 8 | 90% |
| Authentication | 2 | 40% |
| Cryptographic | 3 | 70% |
| Data Exposure | 3 | 80% |
| Configuration | 2 | 50% |
| **Total** | **18** | **66%** |

---

## Injection Vulnerabilities

### CWE-89: SQL Injection

**Status:** [COMPLETE] Fully Supported

**Detection Method:** Taint analysis from user input to SQL execution sinks

**Sinks Monitored:**
- `cursor.execute()`
- `connection.execute()`
- `db.query()`
- `session.execute()`

**Sanitizers Recognized:**
- Parameterized queries (`?` placeholders)
- `int()` type coercion
- `str.isdigit()` validation

**Example:**
```python
# DETECTED
user_id = request.args.get("id")
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

# SAFE (parameterized)
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
```

---

### CWE-78: OS Command Injection

**Status:** [COMPLETE] Fully Supported

**Detection Method:** Taint flow to command execution functions

**Sinks Monitored:**
- `os.system()`
- `subprocess.run()`
- `subprocess.call()`
- `subprocess.Popen()`
- `os.popen()`

**Sanitizers Recognized:**
- `shlex.quote()`
- `shlex.split()`

---

### CWE-79: Cross-Site Scripting (XSS)

**Status:** [COMPLETE] Fully Supported

**Detection Method:** Taint flow to HTML output sinks

**Sinks Monitored:**
- `render_template_string()` (Flask)
- `Markup()` (Jinja2)
- `innerHTML` (JavaScript)
- `document.write()` (JavaScript)

**Sanitizers Recognized:**
- `html.escape()`
- `markupsafe.escape()`
- `bleach.clean()`

---

### CWE-22: Path Traversal

**Status:** [COMPLETE] Fully Supported

**Detection Method:** Taint flow to file operations

**Sinks Monitored:**
- `open()`
- `os.path.join()`
- `pathlib.Path()`
- `shutil.copy()`

**Sanitizers Recognized:**
- `os.path.basename()`
- `os.path.realpath()` with validation

---

### CWE-94: Code Injection

**Status:** [COMPLETE] Fully Supported

**Detection Method:** Taint flow to code execution

**Sinks Monitored:**
- `eval()`
- `exec()`
- `compile()`
- `__import__()`

---

### CWE-611: XXE (XML External Entity)

**Status:** [COMPLETE] Fully Supported

**Detection Method:** Pattern matching + taint analysis

**Sinks Monitored:**
- `xml.etree.ElementTree.parse()`
- `lxml.etree.parse()`
- `xml.sax.parse()`

**Safe Alternatives Recognized:**
- `defusedxml.*`

---

### CWE-1336: SSTI (Server-Side Template Injection)

**Status:** [COMPLETE] Fully Supported

**Detection Method:** Taint flow to template constructors

**Sinks Monitored:**
- `jinja2.Template()`
- `mako.template.Template()`
- `django.template.Template()`

---

### CWE-943: NoSQL Injection

**Status:** [COMPLETE] Supported (v1.3.0+)

**Detection Method:** Taint flow to NoSQL query methods

**Sinks Monitored:**
- `collection.find()`
- `collection.find_one()`
- `collection.aggregate()`

---

## Cryptographic Vulnerabilities

### CWE-327: Use of Broken Crypto Algorithm

**Status:** [WARNING] Partial Support

**Detection Method:** Pattern matching for weak algorithms

**Detected Patterns:**
- `md5()`
- `sha1()` (when used for security)
- `DES`, `RC4`

---

### CWE-328: Reversible One-Way Hash

**Status:** [WARNING] Partial Support

**Detection Method:** Heuristic analysis

---

### CWE-798: Hardcoded Credentials

**Status:** [COMPLETE] Fully Supported

**Detection Method:** Secret scanning with regex patterns

**Patterns Detected:**
- AWS keys (`AKIA...`)
- API keys (generic patterns)
- Private keys (`-----BEGIN`)
- Passwords in strings

---

## Data Exposure Vulnerabilities

### CWE-200: Exposure of Sensitive Information

**Status:** [WARNING] Partial Support

**Detection Method:** Pattern matching for sensitive data logging

---

### CWE-532: Information in Log Files

**Status:** [WARNING] Partial Support

**Detection Method:** Taint flow to logging functions

---

### CWE-312: Cleartext Storage of Sensitive Info

**Status:** [COMPLETE] Supported

**Detection Method:** Pattern matching + context analysis

---

## Deserialization Vulnerabilities

### CWE-502: Deserialization of Untrusted Data

**Status:** [COMPLETE] Fully Supported

**Detection Method:** Taint flow to deserialization

**Sinks Monitored:**
- `pickle.loads()`
- `pickle.load()`
- `yaml.load()` (without safe_load)
- `json.loads()` with eval

---

## Coverage by Language

### Python

| CWE | Status |
|-----|--------|
| CWE-89 (SQLi) | [COMPLETE] Full |
| CWE-78 (Command) | [COMPLETE] Full |
| CWE-79 (XSS) | [COMPLETE] Full |
| CWE-22 (Path) | [COMPLETE] Full |
| CWE-94 (Code) | [COMPLETE] Full |
| CWE-611 (XXE) | [COMPLETE] Full |
| CWE-1336 (SSTI) | [COMPLETE] Full |
| CWE-502 (Deserial) | [COMPLETE] Full |
| CWE-798 (Secrets) | [COMPLETE] Full |

### JavaScript/TypeScript

| CWE | Status |
|-----|--------|
| CWE-79 (DOM XSS) | [COMPLETE] Full |
| CWE-94 (eval) | [COMPLETE] Full |
| CWE-78 (Command) | [COMPLETE] Full |
| CWE-89 (SQLi) | [WARNING] Partial |
| CWE-1321 (Prototype) | [WARNING] Partial |

### Java

| CWE | Status |
|-----|--------|
| CWE-89 (SQLi) | [COMPLETE] Full |
| CWE-78 (Command) | [COMPLETE] Full |
| CWE-611 (XXE) | [COMPLETE] Full |
| CWE-502 (Deserial) | [COMPLETE] Full |

---

## Roadmap: Planned CWE Coverage

| CWE | Description | Target Version |
|-----|-------------|----------------|
| CWE-918 | SSRF | v2.1.0 |
| CWE-352 | CSRF | v2.1.0 |
| CWE-384 | Session Fixation | v2.2.0 |
| CWE-307 | Brute Force | v2.2.0 |
| CWE-434 | Unrestricted Upload | v2.3.0 |

---

## References

- [MITRE CWE Database](https://cwe.mitre.org/)
- [OWASP Top 10 Mapping](OWASP_TOP_10_MAPPING.md)
- [ADR-006: Security Taint Model](../adr/ADR-006-security-taint-model.md)
