#!/usr/bin/env python3
"""
Bandit Parser - Security Vulnerability Analysis.
=================================================

Bandit is a security-focused static analysis tool for Python code. It finds
common security issues like hardcoded passwords, SQL injection, and unsafe
deserialization. This module provides structured parsing of Bandit output.

Implementation Status: COMPLETED
Priority: P2 - HIGH

Bandit Features:
    - Security vulnerability detection
    - CWE (Common Weakness Enumeration) mapping
    - Severity and confidence scoring
    - SARIF output for IDE integration
    - Baseline support for legacy code
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


# =============================================================================
# Enums
# =============================================================================


class BanditSeverity(Enum):
    """Severity levels for Bandit issues."""

    UNDEFINED = "UNDEFINED"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

    @property
    def level(self) -> int:
        """Get numeric level for comparison."""
        levels = {"UNDEFINED": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
        return levels.get(self.value, 0)


class BanditConfidence(Enum):
    """Confidence levels for Bandit issues."""

    UNDEFINED = "UNDEFINED"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

    @property
    def level(self) -> int:
        """Get numeric level for comparison."""
        levels = {"UNDEFINED": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
        return levels.get(self.value, 0)


class BanditCategory(Enum):
    """Categories of Bandit security checks."""

    MISC = "misc"  # B1xx - Misc checks
    BLACKLIST_CALLS = "blacklist_calls"  # B3xx - Dangerous function calls
    BLACKLIST_IMPORTS = "blacklist_imports"  # B4xx - Dangerous imports
    CRYPTO = "crypto"  # B5xx - Cryptography issues
    INJECTION = "injection"  # B6xx - Injection vulnerabilities
    XSS = "xss"  # B7xx - XSS vulnerabilities


# =============================================================================
# CWE Mapping
# =============================================================================


@dataclass
class CWEInfo:
    """Common Weakness Enumeration information."""

    id: int
    name: str
    link: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> CWEInfo | None:
        """Create from Bandit JSON dict."""
        if data is None:
            return None
        return cls(
            id=data.get("id", 0),
            name=data.get("name", ""),
            link=data.get("link"),
        )


# CWE mapping - Maps CWE IDs to human-readable descriptions
CWE_DATABASE: dict[int, str] = {
    78: "OS Command Injection",
    79: "Cross-site Scripting (XSS)",
    89: "SQL Injection",
    94: "Code Injection",
    259: "Use of Hard-coded Password",
    295: "Improper Certificate Validation",
    326: "Inadequate Encryption Strength",
    327: "Use of Broken Crypto Algorithm",
    330: "Insufficient Randomness",
    377: "Insecure Temporary File",
    502: "Deserialization of Untrusted Data",
    611: "XXE (XML External Entity)",
    676: "Use of Potentially Dangerous Function",
    703: "Improper Exception Handling",
    732: "Incorrect Permission Assignment",
}


# CWE-specific fix suggestions - Maps CWE IDs to remediation guidance
CWE_FIX_SUGGESTIONS: dict[int, dict[str, Any]] = {
    78: {
        "title": "Prevent OS Command Injection",
        "description": "OS command injection occurs when untrusted input is passed to system commands.",
        "fixes": [
            "Use subprocess with shell=False and pass arguments as a list",
            "Validate and sanitize all user inputs before use in commands",
            "Use allowlists for permitted commands/arguments",
            "Avoid using os.system(), os.popen(), or shell=True",
        ],
        "code_example": """# Bad: Vulnerable to injection
os.system(f"ls {user_input}")

# Good: Use subprocess with list args
import subprocess
subprocess.run(["ls", validated_path], check=True)""",
        "references": [
            "https://cheatsheetseries.owasp.org/cheatsheets/OS_Command_Injection_Defense_Cheat_Sheet.html",
        ],
    },
    79: {
        "title": "Prevent Cross-Site Scripting (XSS)",
        "description": "XSS allows attackers to inject malicious scripts into web pages.",
        "fixes": [
            "Always escape output when rendering in HTML context",
            "Use templating engines with auto-escaping enabled",
            "Implement Content Security Policy (CSP) headers",
            "Validate and sanitize all user inputs",
        ],
        "code_example": '''# Bad: Direct output of user input
return f"<div>{user_input}</div>"

# Good: Escape the output
from markupsafe import escape
return f"<div>{escape(user_input)}</div>"''',
        "references": [
            "https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html",
        ],
    },
    89: {
        "title": "Prevent SQL Injection",
        "description": "SQL injection allows attackers to manipulate database queries.",
        "fixes": [
            "Use parameterized queries or prepared statements",
            "Use ORM methods instead of raw SQL",
            "Validate and sanitize all user inputs",
            "Apply principle of least privilege to database accounts",
        ],
        "code_example": """# Bad: String formatting in SQL
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

# Good: Parameterized query
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))""",
        "references": [
            "https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html",
        ],
    },
    94: {
        "title": "Prevent Code Injection",
        "description": "Code injection allows execution of arbitrary code through user input.",
        "fixes": [
            "Avoid eval(), exec(), and compile() with user input",
            "Use ast.literal_eval() for parsing simple data structures",
            "Implement strict input validation",
            "Use sandboxed environments for code execution",
        ],
        "code_example": """# Bad: Using eval with user input
result = eval(user_expression)

# Good: Use ast.literal_eval for data
import ast
result = ast.literal_eval(user_data)  # Only for literals""",
        "references": [
            "https://cheatsheetseries.owasp.org/cheatsheets/Injection_Prevention_Cheat_Sheet.html",
        ],
    },
    259: {
        "title": "Remove Hard-coded Credentials",
        "description": "Hard-coded passwords can be extracted from source code or binaries.",
        "fixes": [
            "Use environment variables for credentials",
            "Use a secrets management system (Vault, AWS Secrets Manager)",
            "Use configuration files with restricted permissions (not in VCS)",
            "Implement credential rotation policies",
        ],
        "code_example": """# Bad: Hard-coded password
password = "secret123"

# Good: Use environment variable
import os
password = os.environ.get("DB_PASSWORD")""",
        "references": [
            "https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html",
        ],
    },
    295: {
        "title": "Implement Proper Certificate Validation",
        "description": "Disabling certificate validation allows man-in-the-middle attacks.",
        "fixes": [
            "Always verify SSL/TLS certificates in production",
            "Use trusted CA certificates",
            "Implement certificate pinning for sensitive applications",
            "Keep certificate stores updated",
        ],
        "code_example": """# Bad: Disabled verification
requests.get(url, verify=False)

# Good: Enable verification (default)
requests.get(url)  # verify=True is default""",
        "references": [
            "https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Security_Cheat_Sheet.html",
        ],
    },
    327: {
        "title": "Use Strong Cryptographic Algorithms",
        "description": "Weak cryptographic algorithms can be broken by attackers.",
        "fixes": [
            "Use SHA-256 or SHA-3 instead of MD5/SHA-1 for hashing",
            "Use AES-256 instead of DES/3DES for encryption",
            "Use TLS 1.2 or higher",
            "Follow current NIST recommendations",
        ],
        "code_example": """# Bad: Weak hash
import hashlib
hash = hashlib.md5(data).hexdigest()

# Good: Strong hash
hash = hashlib.sha256(data).hexdigest()""",
        "references": [
            "https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html",
        ],
    },
    330: {
        "title": "Use Cryptographically Secure Random Numbers",
        "description": "Predictable random values can be exploited in security contexts.",
        "fixes": [
            "Use secrets module for security-sensitive randomness",
            "Use os.urandom() for cryptographic purposes",
            "Never use random module for security (tokens, passwords, etc.)",
        ],
        "code_example": """# Bad: Predictable random
import random
token = random.randint(0, 999999)

# Good: Cryptographically secure
import secrets
token = secrets.token_hex(16)""",
        "references": [
            "https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html",
        ],
    },
    502: {
        "title": "Prevent Insecure Deserialization",
        "description": "Deserializing untrusted data can lead to remote code execution.",
        "fixes": [
            "Use JSON instead of pickle for data serialization",
            "Validate and sanitize serialized data before deserializing",
            "Implement integrity checks (HMAC) on serialized data",
            "Run deserialization in sandboxed environments",
        ],
        "code_example": """# Bad: Pickle with untrusted data
import pickle
data = pickle.loads(user_data)

# Good: Use JSON
import json
data = json.loads(user_data)""",
        "references": [
            "https://cheatsheetseries.owasp.org/cheatsheets/Deserialization_Cheat_Sheet.html",
        ],
    },
    611: {
        "title": "Prevent XML External Entity (XXE) Attacks",
        "description": "XXE attacks exploit XML parsers to access local files or internal services.",
        "fixes": [
            "Use defusedxml library instead of standard xml modules",
            "Disable DTD processing and external entities",
            "Use JSON instead of XML when possible",
            "Validate and sanitize XML input",
        ],
        "code_example": """# Bad: Standard XML parser
import xml.etree.ElementTree as ET
tree = ET.parse(untrusted_xml)

# Good: Use defusedxml
import defusedxml.ElementTree as ET
tree = ET.parse(untrusted_xml)""",
        "references": [
            "https://cheatsheetseries.owasp.org/cheatsheets/XML_External_Entity_Prevention_Cheat_Sheet.html",
        ],
    },
}


# OWASP Top 10 2021 Mapping - Maps CWE IDs to OWASP categories
class OWASPCategory(Enum):
    """OWASP Top 10 2021 Categories."""

    A01_BROKEN_ACCESS_CONTROL = "A01:2021-Broken Access Control"
    A02_CRYPTOGRAPHIC_FAILURES = "A02:2021-Cryptographic Failures"
    A03_INJECTION = "A03:2021-Injection"
    A04_INSECURE_DESIGN = "A04:2021-Insecure Design"
    A05_SECURITY_MISCONFIGURATION = "A05:2021-Security Misconfiguration"
    A06_VULNERABLE_COMPONENTS = "A06:2021-Vulnerable and Outdated Components"
    A07_AUTH_FAILURES = "A07:2021-Identification and Authentication Failures"
    A08_DATA_INTEGRITY_FAILURES = "A08:2021-Software and Data Integrity Failures"
    A09_LOGGING_FAILURES = "A09:2021-Security Logging and Monitoring Failures"
    A10_SSRF = "A10:2021-Server-Side Request Forgery"


# Map CWE IDs to OWASP Top 10 categories
OWASP_TOP_10_MAPPING: dict[int, OWASPCategory] = {
    # A01: Broken Access Control
    22: OWASPCategory.A01_BROKEN_ACCESS_CONTROL,  # Path Traversal
    284: OWASPCategory.A01_BROKEN_ACCESS_CONTROL,  # Improper Access Control
    285: OWASPCategory.A01_BROKEN_ACCESS_CONTROL,  # Improper Authorization
    732: OWASPCategory.A01_BROKEN_ACCESS_CONTROL,  # Incorrect Permission Assignment
    # A02: Cryptographic Failures
    259: OWASPCategory.A02_CRYPTOGRAPHIC_FAILURES,  # Hard-coded Password
    295: OWASPCategory.A02_CRYPTOGRAPHIC_FAILURES,  # Improper Cert Validation
    326: OWASPCategory.A02_CRYPTOGRAPHIC_FAILURES,  # Inadequate Encryption Strength
    327: OWASPCategory.A02_CRYPTOGRAPHIC_FAILURES,  # Broken Crypto Algorithm
    330: OWASPCategory.A02_CRYPTOGRAPHIC_FAILURES,  # Insufficient Randomness
    # A03: Injection
    78: OWASPCategory.A03_INJECTION,  # OS Command Injection
    79: OWASPCategory.A03_INJECTION,  # XSS (also fits here)
    89: OWASPCategory.A03_INJECTION,  # SQL Injection
    94: OWASPCategory.A03_INJECTION,  # Code Injection
    611: OWASPCategory.A03_INJECTION,  # XXE
    917: OWASPCategory.A03_INJECTION,  # Expression Language Injection
    # A04: Insecure Design
    209: OWASPCategory.A04_INSECURE_DESIGN,  # Info Exposure Through Error
    256: OWASPCategory.A04_INSECURE_DESIGN,  # Plaintext Storage of Password
    # A05: Security Misconfiguration
    16: OWASPCategory.A05_SECURITY_MISCONFIGURATION,  # Configuration
    377: OWASPCategory.A05_SECURITY_MISCONFIGURATION,  # Insecure Temp File
    # A06: Vulnerable Components (typically detected by dependency scanners)
    # A07: Identification and Authentication Failures
    287: OWASPCategory.A07_AUTH_FAILURES,  # Improper Authentication
    288: OWASPCategory.A07_AUTH_FAILURES,  # Authentication Bypass
    # A08: Software and Data Integrity Failures
    502: OWASPCategory.A08_DATA_INTEGRITY_FAILURES,  # Deserialization
    # A09: Security Logging and Monitoring Failures
    703: OWASPCategory.A09_LOGGING_FAILURES,  # Improper Exception Handling
    # A10: Server-Side Request Forgery
    918: OWASPCategory.A10_SSRF,  # SSRF
    # Potentially dangerous functions (multiple categories)
    676: OWASPCategory.A03_INJECTION,  # Use of Potentially Dangerous Function
}

# Test info database - Maps test IDs to descriptions and metadata
TEST_INFO: dict[str, dict[str, Any]] = {
    # B1xx - Misc checks
    "B101": {
        "name": "assert_used",
        "description": "Use of assert detected. Assert statements are removed when Python is run with -O flag.",
        "cwe_id": 703,
        "severity": "LOW",
        "fix_suggestion": "Use proper exception handling instead of assert for runtime checks.",
    },
    "B102": {
        "name": "exec_used",
        "description": "Use of exec detected.",
        "cwe_id": 78,
        "severity": "MEDIUM",
        "fix_suggestion": "Avoid exec() if possible. If necessary, validate and sanitize inputs.",
    },
    "B103": {
        "name": "set_bad_file_permissions",
        "description": "Chmod setting a permissive mask on file.",
        "cwe_id": 732,
        "severity": "MEDIUM",
        "fix_suggestion": "Use more restrictive file permissions (e.g., 0o600 for private files).",
    },
    "B104": {
        "name": "hardcoded_bind_all_interfaces",
        "description": "Possible binding to all interfaces.",
        "cwe_id": 78,
        "severity": "MEDIUM",
        "fix_suggestion": "Bind to specific interface addresses instead of 0.0.0.0.",
    },
    "B105": {
        "name": "hardcoded_password_string",
        "description": "Possible hardcoded password.",
        "cwe_id": 259,
        "severity": "LOW",
        "fix_suggestion": "Use environment variables or secure secret management.",
    },
    "B106": {
        "name": "hardcoded_password_funcarg",
        "description": "Possible hardcoded password in function argument.",
        "cwe_id": 259,
        "severity": "LOW",
        "fix_suggestion": "Use environment variables or secure secret management.",
    },
    "B107": {
        "name": "hardcoded_password_default",
        "description": "Possible hardcoded password in default argument.",
        "cwe_id": 259,
        "severity": "LOW",
        "fix_suggestion": "Use environment variables or secure secret management.",
    },
    "B108": {
        "name": "hardcoded_tmp_directory",
        "description": "Probable insecure usage of temp file/directory.",
        "cwe_id": 377,
        "severity": "MEDIUM",
        "fix_suggestion": "Use tempfile module for secure temporary file handling.",
    },
    "B110": {
        "name": "try_except_pass",
        "description": "Try/except block with pass - exceptions silently ignored.",
        "cwe_id": 703,
        "severity": "LOW",
        "fix_suggestion": "Log exceptions or handle them appropriately.",
    },
    "B112": {
        "name": "try_except_continue",
        "description": "Try/except block with continue - exceptions silently ignored.",
        "cwe_id": 703,
        "severity": "LOW",
        "fix_suggestion": "Log exceptions or handle them appropriately.",
    },
    # B2xx - Misc additional
    "B201": {
        "name": "flask_debug_true",
        "description": "Flask app appears to be run with debug=True.",
        "cwe_id": 94,
        "severity": "HIGH",
        "fix_suggestion": "Never use debug=True in production. Use environment variable.",
    },
    # B3xx - Blacklist calls
    "B301": {
        "name": "pickle",
        "description": "Pickle usage detected - insecure deserialization.",
        "cwe_id": 502,
        "severity": "MEDIUM",
        "fix_suggestion": "Use json or other safe serialization format.",
    },
    "B302": {
        "name": "marshal",
        "description": "Marshal usage detected - insecure deserialization.",
        "cwe_id": 327,
        "severity": "MEDIUM",
        "fix_suggestion": "Use json or other safe serialization format.",
    },
    "B303": {
        "name": "md5",
        "description": "MD5 usage detected - cryptographically weak.",
        "cwe_id": 327,
        "severity": "MEDIUM",
        "fix_suggestion": "Use SHA-256 or stronger hash function.",
    },
    "B304": {
        "name": "des",
        "description": "DES usage detected - cryptographically weak.",
        "cwe_id": 327,
        "severity": "HIGH",
        "fix_suggestion": "Use AES encryption instead.",
    },
    "B305": {
        "name": "cipher",
        "description": "Cipher usage detected - potential weak crypto.",
        "cwe_id": 327,
        "severity": "MEDIUM",
        "fix_suggestion": "Ensure strong cipher modes and key sizes.",
    },
    "B306": {
        "name": "mktemp_q",
        "description": "Use of insecure tempfile.mktemp.",
        "cwe_id": 377,
        "severity": "MEDIUM",
        "fix_suggestion": "Use tempfile.mkstemp() or tempfile.TemporaryFile().",
    },
    "B307": {
        "name": "eval",
        "description": "Use of eval() detected.",
        "cwe_id": 676,
        "severity": "MEDIUM",
        "fix_suggestion": "Use ast.literal_eval() for parsing or avoid eval entirely.",
    },
    "B308": {
        "name": "mark_safe",
        "description": "Use of mark_safe() may lead to XSS.",
        "cwe_id": 79,
        "severity": "MEDIUM",
        "fix_suggestion": "Ensure content is properly sanitized before marking safe.",
    },
    "B310": {
        "name": "urllib_urlopen",
        "description": "Audit url open for permitted schemes.",
        "cwe_id": 676,
        "severity": "MEDIUM",
        "fix_suggestion": "Validate URL schemes and use requests library with timeout.",
    },
    "B311": {
        "name": "random",
        "description": "Standard pseudo-random generators not suitable for security.",
        "cwe_id": 330,
        "severity": "LOW",
        "fix_suggestion": "Use secrets module for cryptographic purposes.",
    },
    "B312": {
        "name": "telnetlib",
        "description": "Telnet-related functions found - not secure.",
        "cwe_id": 295,
        "severity": "HIGH",
        "fix_suggestion": "Use SSH instead of Telnet.",
    },
    "B324": {
        "name": "hashlib_new_insecure_functions",
        "description": "Use of insecure hash function.",
        "cwe_id": 327,
        "severity": "MEDIUM",
        "fix_suggestion": "Use SHA-256 or stronger hash function.",
    },
    # B4xx - Blacklist imports
    "B401": {
        "name": "import_telnetlib",
        "description": "Telnetlib imported - not secure.",
        "cwe_id": 295,
        "severity": "HIGH",
        "fix_suggestion": "Use paramiko or other SSH libraries.",
    },
    "B402": {
        "name": "import_ftplib",
        "description": "FTPlib imported - not secure.",
        "cwe_id": 295,
        "severity": "HIGH",
        "fix_suggestion": "Use SFTP or FTPS for secure file transfer.",
    },
    "B403": {
        "name": "import_pickle",
        "description": "Pickle imported - insecure deserialization.",
        "cwe_id": 502,
        "severity": "LOW",
        "fix_suggestion": "Consider using json for serialization.",
    },
    "B404": {
        "name": "import_subprocess",
        "description": "Subprocess imported - potential command injection.",
        "cwe_id": 78,
        "severity": "LOW",
        "fix_suggestion": "Audit subprocess usage and avoid shell=True.",
    },
    # B5xx - Crypto
    "B501": {
        "name": "request_with_no_cert_validation",
        "description": "Requests call with verify=False.",
        "cwe_id": 295,
        "severity": "HIGH",
        "fix_suggestion": "Always verify SSL certificates in production.",
    },
    "B502": {
        "name": "ssl_with_bad_version",
        "description": "SSL with insecure protocol version.",
        "cwe_id": 327,
        "severity": "HIGH",
        "fix_suggestion": "Use TLS 1.2 or higher.",
    },
    "B503": {
        "name": "ssl_with_bad_defaults",
        "description": "SSL with insecure default settings.",
        "cwe_id": 327,
        "severity": "MEDIUM",
        "fix_suggestion": "Use ssl.create_default_context() for secure defaults.",
    },
    "B504": {
        "name": "ssl_with_no_version",
        "description": "SSL/TLS without version specified.",
        "cwe_id": 295,
        "severity": "MEDIUM",
        "fix_suggestion": "Explicitly specify TLS 1.2 or higher.",
    },
    "B505": {
        "name": "weak_cryptographic_key",
        "description": "Weak cryptographic key size detected.",
        "cwe_id": 326,
        "severity": "HIGH",
        "fix_suggestion": "Use at least 2048-bit keys for RSA, 256-bit for ECC.",
    },
    "B506": {
        "name": "yaml_load",
        "description": "Use of unsafe yaml.load().",
        "cwe_id": 676,
        "severity": "MEDIUM",
        "fix_suggestion": "Use yaml.safe_load() instead.",
    },
    "B507": {
        "name": "ssh_no_host_key_verification",
        "description": "SSH client with host key verification disabled.",
        "cwe_id": 295,
        "severity": "HIGH",
        "fix_suggestion": "Enable host key verification for SSH connections.",
    },
    # B6xx - Injection
    "B601": {
        "name": "paramiko_calls",
        "description": "Paramiko call with shell=True - command injection risk.",
        "cwe_id": 78,
        "severity": "HIGH",
        "fix_suggestion": "Avoid shell=True, use exec_command() with validated input.",
    },
    "B602": {
        "name": "subprocess_popen_with_shell_equals_true",
        "description": "Subprocess with shell=True - command injection risk.",
        "cwe_id": 78,
        "severity": "HIGH",
        "fix_suggestion": "Use shell=False and pass args as list.",
    },
    "B603": {
        "name": "subprocess_without_shell_equals_true",
        "description": "Subprocess without shell - audit for untrusted input.",
        "cwe_id": 78,
        "severity": "LOW",
        "fix_suggestion": "Validate and sanitize inputs passed to subprocess.",
    },
    "B604": {
        "name": "any_other_function_with_shell_equals_true",
        "description": "Function called with shell=True.",
        "cwe_id": 78,
        "severity": "MEDIUM",
        "fix_suggestion": "Avoid shell=True if possible.",
    },
    "B605": {
        "name": "start_process_with_a_shell",
        "description": "Starting process with shell - command injection risk.",
        "cwe_id": 78,
        "severity": "HIGH",
        "fix_suggestion": "Avoid starting processes with shell interpretation.",
    },
    "B606": {
        "name": "start_process_with_no_shell",
        "description": "Starting process without shell - audit for input.",
        "cwe_id": 78,
        "severity": "LOW",
        "fix_suggestion": "Validate inputs passed to process.",
    },
    "B607": {
        "name": "start_process_with_partial_path",
        "description": "Starting process with partial path.",
        "cwe_id": 78,
        "severity": "LOW",
        "fix_suggestion": "Use full paths to executables.",
    },
    "B608": {
        "name": "hardcoded_sql_expressions",
        "description": "Possible SQL injection via string formatting.",
        "cwe_id": 89,
        "severity": "MEDIUM",
        "fix_suggestion": "Use parameterized queries.",
    },
    "B609": {
        "name": "linux_commands_wildcard_injection",
        "description": "Possible wildcard injection.",
        "cwe_id": 611,
        "severity": "HIGH",
        "fix_suggestion": "Quote or escape wildcards in shell commands.",
    },
    "B610": {
        "name": "django_extra_used",
        "description": "Django extra() with raw SQL - injection risk.",
        "cwe_id": 94,
        "severity": "MEDIUM",
        "fix_suggestion": "Use Django ORM methods instead of raw SQL.",
    },
    "B611": {
        "name": "django_rawsql_used",
        "description": "Django RawSQL - SQL injection risk.",
        "cwe_id": 94,
        "severity": "MEDIUM",
        "fix_suggestion": "Use Django ORM methods instead of raw SQL.",
    },
    # B7xx - XSS
    "B701": {
        "name": "jinja2_autoescape_false",
        "description": "Jinja2 with autoescape disabled - XSS risk.",
        "cwe_id": 94,
        "severity": "HIGH",
        "fix_suggestion": "Enable autoescape in Jinja2 templates.",
    },
    "B702": {
        "name": "use_of_mako_templates",
        "description": "Mako templates used - potential XSS.",
        "cwe_id": 79,
        "severity": "MEDIUM",
        "fix_suggestion": "Enable strict mode and escape output in Mako templates.",
    },
    "B703": {
        "name": "django_mark_safe",
        "description": "Django mark_safe with potential user input - XSS risk.",
        "cwe_id": 94,
        "severity": "MEDIUM",
        "fix_suggestion": "Sanitize content before using mark_safe().",
    },
}


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class BanditIssue:
    """A single Bandit security issue."""

    test_id: str  # e.g., "B105"
    test_name: str  # e.g., "hardcoded_password_string"
    issue_text: str  # Human-readable description
    filename: str  # File path
    line_number: int  # Line number
    line_range: list[int]  # Range of lines
    col_offset: int = 0  # Column offset
    end_col_offset: int | None = None
    severity: BanditSeverity = BanditSeverity.MEDIUM
    confidence: BanditConfidence = BanditConfidence.MEDIUM
    code: str | None = None  # Code snippet
    cwe: CWEInfo | None = None  # CWE information
    more_info: str | None = None  # Link to documentation
    nosec: bool = False  # If marked with # nosec

    @property
    def location(self) -> str:
        """Get formatted location string."""
        return f"{self.filename}:{self.line_number}:{self.col_offset}"

    @property
    def category(self) -> BanditCategory:
        """Get the issue category based on test ID."""
        prefix = self.test_id[:2] if len(self.test_id) >= 2 else ""
        category_map = {
            "B1": BanditCategory.MISC,
            "B2": BanditCategory.MISC,
            "B3": BanditCategory.BLACKLIST_CALLS,
            "B4": BanditCategory.BLACKLIST_IMPORTS,
            "B5": BanditCategory.CRYPTO,
            "B6": BanditCategory.INJECTION,
            "B7": BanditCategory.XSS,
        }
        return category_map.get(prefix, BanditCategory.MISC)

    @property
    def risk_score(self) -> int:
        """Calculate a risk score (0-9) based on severity and confidence."""
        return self.severity.level * self.confidence.level

    def format(self, *, show_code: bool = False) -> str:
        """Format the issue for display."""
        parts = [
            f"{self.location}: [{self.severity.value}/{self.confidence.value}] " f"{self.test_id} {self.issue_text}"
        ]
        if self.cwe:
            parts.append(f"  CWE-{self.cwe.id}: {self.cwe.name}")
        if show_code and self.code:
            parts.append(f"  >>> {self.code.strip()}")
        return "\n".join(parts)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BanditIssue:
        """Create from Bandit JSON output dict."""
        try:
            severity = BanditSeverity(data.get("issue_severity", "MEDIUM"))
        except ValueError:
            severity = BanditSeverity.MEDIUM

        try:
            confidence = BanditConfidence(data.get("issue_confidence", "MEDIUM"))
        except ValueError:
            confidence = BanditConfidence.MEDIUM

        return cls(
            test_id=data.get("test_id", ""),
            test_name=data.get("test_name", ""),
            issue_text=data.get("issue_text", ""),
            filename=data.get("filename", ""),
            line_number=data.get("line_number", 0),
            line_range=data.get("line_range", []),
            col_offset=data.get("col_offset", 0),
            end_col_offset=data.get("end_col_offset"),
            severity=severity,
            confidence=confidence,
            code=data.get("code"),
            cwe=CWEInfo.from_dict(data.get("issue_cwe")),
            more_info=data.get("more_info"),
        )


@dataclass
class BanditFileMetrics:
    """Metrics for a single file."""

    filename: str
    loc: int = 0  # Lines of code
    nosec_count: int = 0  # Number of nosec suppression markers
    high_severity: int = 0
    medium_severity: int = 0
    low_severity: int = 0
    high_confidence: int = 0
    medium_confidence: int = 0
    low_confidence: int = 0

    @classmethod
    def from_dict(cls, filename: str, data: dict[str, Any]) -> BanditFileMetrics:
        """Create from Bandit metrics dict."""
        return cls(
            filename=filename,
            loc=data.get("loc", 0),
            nosec_count=data.get("nosec", 0),
            high_severity=data.get("SEVERITY.HIGH", 0),
            medium_severity=data.get("SEVERITY.MEDIUM", 0),
            low_severity=data.get("SEVERITY.LOW", 0),
            high_confidence=data.get("CONFIDENCE.HIGH", 0),
            medium_confidence=data.get("CONFIDENCE.MEDIUM", 0),
            low_confidence=data.get("CONFIDENCE.LOW", 0),
        )


@dataclass
class BanditConfig:
    """Configuration for Bandit analysis."""

    config_file: Path | None = None
    profile: str | None = None
    tests: list[str] = field(default_factory=list)  # Tests to run (e.g., ["B101", "B102"])
    skips: list[str] = field(default_factory=list)  # Tests to skip
    severity: BanditSeverity = BanditSeverity.LOW  # Minimum severity to report
    confidence: BanditConfidence = BanditConfidence.LOW  # Minimum confidence
    exclude_dirs: list[str] = field(default_factory=lambda: [".git", "__pycache__", "venv"])
    baseline: Path | None = None  # Baseline file for filtering
    recursive: bool = True

    def to_cli_args(self) -> list[str]:
        """Convert configuration to CLI arguments."""
        args = []

        if self.config_file:
            args.extend(["-c", str(self.config_file)])

        if self.profile:
            args.extend(["-p", self.profile])

        if self.tests:
            args.extend(["-t", ",".join(self.tests)])

        if self.skips:
            args.extend(["-s", ",".join(self.skips)])

        if self.severity != BanditSeverity.LOW:
            level = {"MEDIUM": "m", "HIGH": "h"}.get(self.severity.value, "l")
            args.extend(["-l" + level])

        if self.confidence != BanditConfidence.LOW:
            level = {"MEDIUM": "m", "HIGH": "h"}.get(self.confidence.value, "l")
            args.extend(["-i" + level])

        for dir_name in self.exclude_dirs:
            args.extend(["--exclude", dir_name])

        if self.baseline:
            args.extend(["-b", str(self.baseline)])

        if self.recursive:
            args.append("-r")

        return args


@dataclass
class BanditReport:
    """Complete Bandit security analysis report."""

    issues: list[BanditIssue] = field(default_factory=list)
    file_metrics: dict[str, BanditFileMetrics] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    generated_at: datetime | None = None
    config: BanditConfig | None = None
    bandit_version: str | None = None

    @property
    def issue_count(self) -> int:
        """Get total number of issues."""
        return len(self.issues)

    @property
    def high_severity_count(self) -> int:
        """Get count of high severity issues."""
        return sum(1 for i in self.issues if i.severity == BanditSeverity.HIGH)

    @property
    def medium_severity_count(self) -> int:
        """Get count of medium severity issues."""
        return sum(1 for i in self.issues if i.severity == BanditSeverity.MEDIUM)

    @property
    def low_severity_count(self) -> int:
        """Get count of low severity issues."""
        return sum(1 for i in self.issues if i.severity == BanditSeverity.LOW)

    @property
    def total_loc(self) -> int:
        """Get total lines of code analyzed."""
        return sum(m.loc for m in self.file_metrics.values())

    @property
    def issues_by_severity(self) -> dict[BanditSeverity, list[BanditIssue]]:
        """Group issues by severity."""
        result: dict[BanditSeverity, list[BanditIssue]] = {}
        for issue in self.issues:
            result.setdefault(issue.severity, []).append(issue)
        return result

    @property
    def issues_by_file(self) -> dict[str, list[BanditIssue]]:
        """Group issues by file."""
        result: dict[str, list[BanditIssue]] = {}
        for issue in self.issues:
            result.setdefault(issue.filename, []).append(issue)
        return result

    @property
    def issues_by_test(self) -> dict[str, list[BanditIssue]]:
        """Group issues by test ID."""
        result: dict[str, list[BanditIssue]] = {}
        for issue in self.issues:
            result.setdefault(issue.test_id, []).append(issue)
        return result

    @property
    def issues_by_cwe(self) -> dict[int, list[BanditIssue]]:
        """Group issues by CWE ID."""
        result: dict[int, list[BanditIssue]] = {}
        for issue in self.issues:
            if issue.cwe:
                result.setdefault(issue.cwe.id, []).append(issue)
        return result

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the report."""
        return {
            "total_issues": self.issue_count,
            "total_loc": self.total_loc,
            "files_analyzed": len(self.file_metrics),
            "by_severity": {
                "high": self.high_severity_count,
                "medium": self.medium_severity_count,
                "low": self.low_severity_count,
            },
            "by_category": {cat.value: sum(1 for i in self.issues if i.category == cat) for cat in BanditCategory},
            "top_cwe": [
                {"cwe": cwe, "count": len(issues)}
                for cwe, issues in sorted(self.issues_by_cwe.items(), key=lambda x: -len(x[1]))[:5]
            ],
        }


# =============================================================================
# Parser Class
# =============================================================================


class BanditParser:
    """
    Parser for Bandit security scanner output.

    Bandit is a tool designed to find common security issues in Python code.
    It processes each file, builds an AST, and runs appropriate plugins
    against the AST nodes.

    Implementation Status:
        ✓ Core JSON parsing and analysis (P2-BANDIT-001)
        ✓ CWE mapping with test info database (P2-BANDIT-002)
        ✓ SARIF output support (P2-BANDIT-003)
        ✓ Baseline support with filtering (P3-BANDIT-004)

    Usage:
        >>> parser = BanditParser()
        >>> report = parser.analyze("src/")
        >>> for issue in report.issues:
        ...     if issue.severity == BanditSeverity.HIGH:
        ...         print(f"CRITICAL: {issue.issue_text}")
    """

    def __init__(self, *, bandit_path: str = "bandit"):
        """
        Initialize the Bandit parser.

        Args:
            bandit_path: Path to the bandit executable.
        """
        self.bandit_path = bandit_path
        self._version: str | None = None

    @property
    def version(self) -> str | None:
        """Get the Bandit version."""
        if self._version is None:
            try:
                result = subprocess.run(
                    [self.bandit_path, "--version"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                self._version = result.stdout.strip()
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
        return self._version

    def is_available(self) -> bool:
        """Check if Bandit is available."""
        try:
            subprocess.run(
                [self.bandit_path, "--version"],
                capture_output=True,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def analyze(
        self,
        target: str | Path | list[str | Path],
        *,
        config: BanditConfig | None = None,
    ) -> BanditReport:
        """
        Analyze Python files with Bandit.

        Runs Bandit security scanner and parses JSON output.

        Args:
            target: File, directory, or list of targets to analyze.
            config: Optional configuration override.

        Returns:
            BanditReport with security issues and metrics.
        """
        report = BanditReport(config=config, bandit_version=self.version)

        # Build targets list
        if isinstance(target, (str, Path)):
            targets = [str(target)]
        else:
            targets = [str(t) for t in target]

        # Build command - use JSON format for structured output
        cmd = [
            self.bandit_path,
            "-f",
            "json",
            "--exit-zero",  # Don't exit with error on findings
        ]

        if config:
            cmd.extend(config.to_cli_args())

        cmd.extend(targets)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )

            # Parse JSON output
            if result.stdout.strip():
                try:
                    data = json.loads(result.stdout)

                    # Parse issues
                    for issue_data in data.get("results", []):
                        report.issues.append(BanditIssue.from_dict(issue_data))

                    # Parse metrics
                    for filename, metrics in data.get("metrics", {}).items():
                        if filename != "_totals":
                            report.file_metrics[filename] = BanditFileMetrics.from_dict(filename, metrics)

                    # Parse timestamp
                    if "generated_at" in data:
                        try:
                            report.generated_at = datetime.fromisoformat(data["generated_at"].replace("Z", "+00:00"))
                        except ValueError:
                            pass

                    # Parse errors
                    report.errors.extend(data.get("errors", []))

                except json.JSONDecodeError as e:
                    report.errors.append(f"Failed to parse Bandit output: {e}")

            if result.stderr:
                # Bandit sometimes puts non-error info in stderr
                for line in result.stderr.strip().split("\n"):
                    if "error" in line.lower():
                        report.errors.append(line)

        except FileNotFoundError:
            report.errors.append(f"Bandit not found at: {self.bandit_path}")
        except subprocess.SubprocessError as e:
            report.errors.append(f"Bandit execution failed: {e}")

        return report

    def get_test_info(self, test_id: str) -> dict[str, Any] | None:
        """
        Get information about a specific Bandit test.

        Args:
            test_id: The test ID (e.g., "B105")

        Returns:
            Dictionary with test information or None if not found.
        """
        if test_id in TEST_INFO:
            info = TEST_INFO[test_id].copy()
            # Add CWE description if available
            if "cwe_id" in info and info["cwe_id"] in CWE_DATABASE:
                info["cwe_name"] = CWE_DATABASE[info["cwe_id"]]
            return info
        return None

    def load_baseline(self, baseline_path: Path) -> list[BanditIssue]:
        """
        Load issues from a baseline file.

        Args:
            baseline_path: Path to the baseline JSON file.

        Returns:
            List of BanditIssue from the baseline.
        """
        if not baseline_path.exists():
            return []

        with open(baseline_path) as f:
            data = json.load(f)

        return [BanditIssue.from_dict(issue) for issue in data.get("results", [])]

    def filter_with_baseline(
        self,
        report: BanditReport,
        baseline_issues: list[BanditIssue],
    ) -> BanditReport:
        """
        Filter a report against baseline issues.

        Issues that match baseline entries (same file, line, test_id) are removed.

        Args:
            report: The report to filter.
            baseline_issues: Issues from baseline to exclude.

        Returns:
            New BanditReport with only new issues.
        """
        # Create lookup set for baseline issues
        baseline_set = {(issue.filename, issue.line_number, issue.test_id) for issue in baseline_issues}

        # Filter out issues that exist in baseline
        new_issues = [
            issue for issue in report.issues if (issue.filename, issue.line_number, issue.test_id) not in baseline_set
        ]

        return BanditReport(
            issues=new_issues,
            file_metrics=report.file_metrics,
            errors=report.errors,
            generated_at=report.generated_at,
            config=report.config,
            bandit_version=report.bandit_version,
        )

    def to_sarif(self, report: BanditReport) -> dict[str, Any]:
        """
        Convert a BanditReport to SARIF format.

        SARIF (Static Analysis Results Interchange Format) is a standard
        format for static analysis tool output, supported by many IDEs.

        Args:
            report: The report to convert.

        Returns:
            SARIF-formatted dictionary.
        """
        sarif = {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "Bandit",
                            "version": report.bandit_version or "unknown",
                            "informationUri": "https://bandit.readthedocs.io/",
                            "rules": self._get_sarif_rules(report),
                        }
                    },
                    "results": [self._issue_to_sarif_result(issue) for issue in report.issues],
                }
            ],
        }
        return sarif

    def _get_sarif_rules(self, report: BanditReport) -> list[dict[str, Any]]:
        """Get unique rules from report for SARIF output."""
        seen_rules: set[str] = set()
        rules: list[dict[str, Any]] = []

        for issue in report.issues:
            if issue.test_id not in seen_rules:
                seen_rules.add(issue.test_id)
                rule: dict[str, Any] = {
                    "id": issue.test_id,
                    "name": issue.test_name,
                    "shortDescription": {"text": issue.test_name},
                }

                # Add test info if available
                test_info = self.get_test_info(issue.test_id)
                if test_info:
                    rule["fullDescription"] = {"text": test_info.get("description", "")}
                    rule["help"] = {"text": test_info.get("fix_suggestion", "")}

                # Add CWE relationship
                if issue.cwe:
                    rule["relationships"] = [
                        {
                            "target": {
                                "id": f"CWE-{issue.cwe.id}",
                                "toolComponent": {"name": "CWE"},
                            },
                            "kinds": ["superset"],
                        }
                    ]

                rules.append(rule)

        return rules

    def _issue_to_sarif_result(self, issue: BanditIssue) -> dict[str, Any]:
        """Convert a BanditIssue to SARIF result format."""
        level_map = {
            BanditSeverity.HIGH: "error",
            BanditSeverity.MEDIUM: "warning",
            BanditSeverity.LOW: "note",
            BanditSeverity.UNDEFINED: "none",
        }

        result: dict[str, Any] = {
            "ruleId": issue.test_id,
            "level": level_map.get(issue.severity, "warning"),
            "message": {"text": issue.issue_text},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": issue.filename},
                        "region": {
                            "startLine": issue.line_number,
                            "startColumn": issue.col_offset + 1,
                        },
                    }
                }
            ],
        }

        if issue.end_col_offset is not None:
            result["locations"][0]["physicalLocation"]["region"]["endColumn"] = issue.end_col_offset + 1

        # Add code snippet if available
        if issue.code:
            result["locations"][0]["physicalLocation"]["region"]["snippet"] = {"text": issue.code}

        return result

    def create_baseline(
        self,
        target: str | Path,
        output_file: Path,
        *,
        config: BanditConfig | None = None,
    ) -> bool:
        """
        Create a baseline file from current results.

        Runs Bandit and saves output to a baseline file for future filtering.

        Args:
            target: Target to analyze.
            output_file: Where to write the baseline.
            config: Optional configuration.

        Returns:
            True if successful.
        """
        # Run analysis and save results as baseline
        cmd = [
            self.bandit_path,
            "-f",
            "json",
            "-o",
            str(output_file),
        ]

        if config:
            cmd.extend(config.to_cli_args())

        cmd.append(str(target))

        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0

    def analyze_code(
        self,
        code: str,
        *,
        filename: str = "<stdin>",
        config: BanditConfig | None = None,
    ) -> BanditReport:
        """
        Analyze Python code from a string (stdin input support).

        This enables analyzing unsaved files or code snippets without
        writing them to disk first.

        Args:
            code: Python source code as a string.
            filename: Virtual filename to use in reports.
            config: Optional configuration override.

        Returns:
            BanditReport with security issues and metrics.
        """
        # Write code to a temporary file for Bandit to analyze
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
        ) as tmp_file:
            tmp_file.write(code)
            tmp_path = Path(tmp_file.name)

        try:
            # Analyze the temporary file
            report = self.analyze(tmp_path, config=config)

            # Replace the temp filename with the virtual filename
            for issue in report.issues:
                if issue.filename == str(tmp_path):
                    # Use object.__setattr__ since dataclass might be frozen
                    object.__setattr__(issue, "filename", filename)

            # Update file metrics keys
            if str(tmp_path) in report.file_metrics:
                metrics = report.file_metrics.pop(str(tmp_path))
                metrics.filename = filename
                report.file_metrics[filename] = metrics

            return report

        finally:
            # Clean up temporary file
            tmp_path.unlink(missing_ok=True)

    def get_cwe_fix_suggestion(self, cwe_id: int) -> dict[str, Any] | None:
        """
        Get fix suggestions for a specific CWE.

        Args:
            cwe_id: The CWE identifier (e.g., 78 for command injection).

        Returns:
            Dictionary with fix information or None if not found.
        """
        return CWE_FIX_SUGGESTIONS.get(cwe_id)

    def get_owasp_category(self, issue: BanditIssue) -> OWASPCategory | None:
        """
        Get the OWASP Top 10 category for an issue.

        Args:
            issue: The BanditIssue to categorize.

        Returns:
            OWASPCategory or None if not mapped.
        """
        if issue.cwe and issue.cwe.id in OWASP_TOP_10_MAPPING:
            return OWASP_TOP_10_MAPPING[issue.cwe.id]
        return None

    def get_issues_by_owasp(self, report: BanditReport) -> dict[OWASPCategory, list[BanditIssue]]:
        """
        Group report issues by OWASP Top 10 category.

        Args:
            report: The BanditReport to analyze.

        Returns:
            Dictionary mapping OWASP categories to issues.
        """
        result: dict[OWASPCategory, list[BanditIssue]] = {}
        for issue in report.issues:
            category = self.get_owasp_category(issue)
            if category:
                result.setdefault(category, []).append(issue)
        return result

    def validate_sarif(self, sarif: dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Validate a SARIF document against the schema.

        Performs structural validation of the SARIF output to ensure
        it conforms to the SARIF 2.1.0 specification.

        Args:
            sarif: The SARIF dictionary to validate.

        Returns:
            Tuple of (is_valid, list of error messages).
        """
        errors: list[str] = []

        # Check required top-level fields
        if "$schema" not in sarif:
            errors.append("Missing required field: $schema")

        if "version" not in sarif:
            errors.append("Missing required field: version")
        elif sarif["version"] != "2.1.0":
            errors.append(f"Unsupported SARIF version: {sarif['version']} (expected 2.1.0)")

        if "runs" not in sarif:
            errors.append("Missing required field: runs")
        elif not isinstance(sarif["runs"], list):
            errors.append("Field 'runs' must be an array")
        elif len(sarif["runs"]) == 0:
            errors.append("Field 'runs' must contain at least one run")
        else:
            # Validate each run
            for i, run in enumerate(sarif["runs"]):
                run_errors = self._validate_sarif_run(run, i)
                errors.extend(run_errors)

        return len(errors) == 0, errors

    def _validate_sarif_run(self, run: dict[str, Any], index: int) -> list[str]:
        """Validate a single SARIF run object."""
        errors: list[str] = []
        prefix = f"runs[{index}]"

        # Check tool field
        if "tool" not in run:
            errors.append(f"{prefix}: Missing required field: tool")
        else:
            tool = run["tool"]
            if "driver" not in tool:
                errors.append(f"{prefix}.tool: Missing required field: driver")
            else:
                driver = tool["driver"]
                if "name" not in driver:
                    errors.append(f"{prefix}.tool.driver: Missing required field: name")

        # Check results field
        if "results" not in run:
            errors.append(f"{prefix}: Missing required field: results")
        elif not isinstance(run["results"], list):
            errors.append(f"{prefix}.results: Must be an array")
        else:
            # Validate each result
            for j, result in enumerate(run["results"]):
                result_errors = self._validate_sarif_result(result, f"{prefix}.results[{j}]")
                errors.extend(result_errors)

        return errors

    def _validate_sarif_result(self, result: dict[str, Any], prefix: str) -> list[str]:
        """Validate a single SARIF result object."""
        errors: list[str] = []

        # Check required fields
        if "ruleId" not in result and "rule" not in result:
            errors.append(f"{prefix}: Must have either 'ruleId' or 'rule'")

        if "message" not in result:
            errors.append(f"{prefix}: Missing required field: message")
        elif "text" not in result["message"]:
            errors.append(f"{prefix}.message: Missing required field: text")

        # Validate locations if present
        if "locations" in result:
            if not isinstance(result["locations"], list):
                errors.append(f"{prefix}.locations: Must be an array")
            else:
                for k, loc in enumerate(result["locations"]):
                    if "physicalLocation" in loc:
                        phys = loc["physicalLocation"]
                        if "artifactLocation" not in phys and "region" not in phys:
                            errors.append(
                                f"{prefix}.locations[{k}].physicalLocation: " "Must have 'artifactLocation' or 'region'"
                            )

        # Validate level if present
        valid_levels = {"none", "note", "warning", "error"}
        if "level" in result and result["level"] not in valid_levels:
            errors.append(f"{prefix}.level: Invalid value '{result['level']}'")

        return errors


# =============================================================================
# Utility Functions
# =============================================================================


def parse_bandit_json(output: str) -> BanditReport:
    """
    Parse Bandit JSON output into a report.

    Args:
        output: JSON string from bandit -f json

    Returns:
        BanditReport with issues and metrics.
    """
    report = BanditReport()

    if not output.strip():
        return report

    data = json.loads(output)

    for issue_data in data.get("results", []):
        report.issues.append(BanditIssue.from_dict(issue_data))

    for filename, metrics in data.get("metrics", {}).items():
        if filename != "_totals":
            report.file_metrics[filename] = BanditFileMetrics.from_dict(filename, metrics)

    report.errors = data.get("errors", [])

    return report


def format_security_report(report: BanditReport) -> str:
    """Format a Bandit security report for display."""
    lines = [
        "Security Analysis Report",
        "=" * 50,
        "",
        f"Issues found: {report.issue_count}",
        f"  - High severity: {report.high_severity_count}",
        f"  - Medium severity: {report.medium_severity_count}",
        f"  - Low severity: {report.low_severity_count}",
        "",
        f"Files analyzed: {len(report.file_metrics)}",
        f"Lines of code: {report.total_loc}",
        "",
    ]

    # High severity issues first
    high_issues = [i for i in report.issues if i.severity == BanditSeverity.HIGH]
    if high_issues:
        lines.append("🚨 HIGH SEVERITY ISSUES:")
        for issue in high_issues:
            lines.append(f"  {issue.location}")
            lines.append(f"    {issue.test_id}: {issue.issue_text}")
            if issue.cwe:
                lines.append(f"    CWE-{issue.cwe.id}: {issue.cwe.name}")
        lines.append("")

    # Medium severity summary
    medium_issues = [i for i in report.issues if i.severity == BanditSeverity.MEDIUM]
    if medium_issues:
        lines.append(f"⚠️  MEDIUM SEVERITY: {len(medium_issues)} issues")
        for issue in medium_issues[:5]:
            lines.append(f"  {issue.location}: {issue.test_id}")
        if len(medium_issues) > 5:
            lines.append(f"  ... and {len(medium_issues) - 5} more")
        lines.append("")

    return "\n".join(lines)
