"""
Code Policy Check - Pattern Definitions.

[20251226_FEATURE] v3.4.0 - Pattern definitions for code analysis.

This module defines patterns for detecting:
- Python anti-patterns (Community tier)
- Security patterns (Pro tier)
- Async/await patterns (Pro tier)
- Best practice patterns (Pro tier)
"""

from __future__ import annotations

import ast
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import cast

from .models import ViolationSeverity


class PatternCategory(str, Enum):
    """Categories of patterns."""

    ANTIPATTERN = "antipattern"
    SECURITY = "security"
    ASYNC = "async"
    BEST_PRACTICE = "best_practice"
    STYLE = "style"


@dataclass
class PatternDefinition:
    """
    Defines a pattern to detect in code.

    [20251226_FEATURE] Core pattern definition structure.
    """

    id: str
    name: str
    description: str
    category: PatternCategory
    severity: ViolationSeverity
    # Either regex pattern or AST node type to match
    regex_pattern: str | None = None
    ast_node_types: tuple[type, ...] | None = None
    # Validation function for AST patterns
    ast_validator: Callable[[ast.AST], bool] | None = None
    suggestion: str | None = None
    cwe_id: str | None = None


# =============================================================================
# PYTHON ANTIPATTERNS (Community Tier)
# =============================================================================

PYTHON_ANTIPATTERNS: list[PatternDefinition] = [
    # [20251226_FEATURE] Bare except detection
    PatternDefinition(
        id="PY001",
        name="bare_except",
        description="Bare except clause catches all exceptions including SystemExit and KeyboardInterrupt",
        category=PatternCategory.ANTIPATTERN,
        severity=ViolationSeverity.WARNING,
        ast_node_types=(ast.ExceptHandler,),
        ast_validator=lambda node: cast(ast.ExceptHandler, node).type is None,  # type: ignore[reportAttributeAccessIssue]
        suggestion="Specify exception type: 'except Exception:' or more specific type",
    ),
    # [20251226_FEATURE] Mutable default argument detection
    PatternDefinition(
        id="PY002",
        name="mutable_default_arg",
        description="Mutable default argument in function definition",
        category=PatternCategory.ANTIPATTERN,
        severity=ViolationSeverity.WARNING,
        ast_node_types=(ast.FunctionDef, ast.AsyncFunctionDef),
        ast_validator=lambda node: any(  # type: ignore[reportAttributeAccessIssue]
            isinstance(default, (ast.List, ast.Dict, ast.Set))
            for default in cast(ast.FunctionDef, node).args.defaults
            + [d for d in cast(ast.FunctionDef, node).args.kw_defaults if d is not None]
        ),
        suggestion="Use None as default and initialize in function body: 'def f(x=None): x = x or []'",
    ),
    # [20251226_FEATURE] Global statement detection
    PatternDefinition(
        id="PY003",
        name="global_statement",
        description="Use of global statement can lead to hard-to-track bugs",
        category=PatternCategory.ANTIPATTERN,
        severity=ViolationSeverity.INFO,
        ast_node_types=(ast.Global,),
        suggestion="Consider passing values as function arguments or using a class",
    ),
    # [20251226_FEATURE] Star import detection
    PatternDefinition(
        id="PY004",
        name="star_import",
        description="Star import pollutes namespace and makes code harder to understand",
        category=PatternCategory.ANTIPATTERN,
        severity=ViolationSeverity.WARNING,
        ast_node_types=(ast.ImportFrom,),
        ast_validator=lambda node: any(alias.name == "*" for alias in cast(ast.ImportFrom, node).names),  # type: ignore[union-attr]
        suggestion="Import specific names: 'from module import name1, name2'",
    ),
    # [20251226_FEATURE] Assert in production code
    PatternDefinition(
        id="PY005",
        name="assert_statement",
        description="Assert statements are removed when Python runs with -O flag",
        category=PatternCategory.ANTIPATTERN,
        severity=ViolationSeverity.INFO,
        ast_node_types=(ast.Assert,),
        suggestion="Use explicit if-statements with raise for production validation",
    ),
    # [20251226_FEATURE] exec() usage
    PatternDefinition(
        id="PY006",
        name="exec_usage",
        description="exec() is dangerous and should be avoided",
        category=PatternCategory.ANTIPATTERN,
        severity=ViolationSeverity.ERROR,
        ast_node_types=(ast.Call,),
        ast_validator=lambda node: (  # type: ignore[union-attr]
            isinstance(cast(ast.Call, node).func, ast.Name) and cast(ast.Name, cast(ast.Call, node).func).id == "exec"
        ),
        suggestion="Refactor to avoid dynamic code execution",
        cwe_id="CWE-94",
    ),
    # [20251226_FEATURE] eval() usage
    PatternDefinition(
        id="PY007",
        name="eval_usage",
        description="eval() is dangerous and should be avoided",
        category=PatternCategory.ANTIPATTERN,
        severity=ViolationSeverity.ERROR,
        ast_node_types=(ast.Call,),
        ast_validator=lambda node: (  # type: ignore[union-attr]
            isinstance(cast(ast.Call, node).func, ast.Name) and cast(ast.Name, cast(ast.Call, node).func).id == "eval"
        ),
        suggestion="Use ast.literal_eval() for safe evaluation of literals",
        cwe_id="CWE-94",
    ),
    # [20251226_FEATURE] Using type() for comparison
    PatternDefinition(
        id="PY008",
        name="type_comparison",
        description="Use isinstance() instead of type() for type checking",
        category=PatternCategory.ANTIPATTERN,
        severity=ViolationSeverity.WARNING,
        regex_pattern=r"\btype\s*\([^)]+\)\s*==",
        suggestion="Use isinstance(obj, Type) for type checking",
    ),
    # [20251226_FEATURE] Empty except with pass
    PatternDefinition(
        id="PY009",
        name="empty_except",
        description="Empty except block silently swallows errors",
        category=PatternCategory.ANTIPATTERN,
        severity=ViolationSeverity.ERROR,
        ast_node_types=(ast.ExceptHandler,),
        ast_validator=lambda node: (  # type: ignore[union-attr]
            len(cast(ast.ExceptHandler, node).body) == 1 and isinstance(cast(ast.ExceptHandler, node).body[0], ast.Pass)
        ),
        suggestion="At minimum, log the exception: 'except Exception as e: logger.error(e)'",
    ),
    # [20251226_FEATURE] Using input() for passwords
    PatternDefinition(
        id="PY010",
        name="input_password",
        description="Using input() for passwords exposes them on screen",
        category=PatternCategory.ANTIPATTERN,
        severity=ViolationSeverity.ERROR,
        regex_pattern=r"input\s*\([^)]*(?:password|passwd|pwd|secret|token|key)[^)]*\)",
        suggestion="Use getpass.getpass() for password input",
        cwe_id="CWE-549",
    ),
]


# =============================================================================
# SECURITY PATTERNS (Pro Tier)
# =============================================================================

SECURITY_PATTERNS: list[PatternDefinition] = [
    # [20251226_FEATURE] Hardcoded password detection
    PatternDefinition(
        id="SEC001",
        name="hardcoded_password",
        description="Hardcoded password detected",
        category=PatternCategory.SECURITY,
        severity=ViolationSeverity.CRITICAL,
        regex_pattern=r"""(?i)(?:password|passwd|pwd|secret|token|api_key)\s*=\s*['"][^'"]{4,}['"]""",
        suggestion="Use environment variables or a secrets manager",
        cwe_id="CWE-798",
    ),
    # [20251226_FEATURE] SQL string concatenation
    PatternDefinition(
        id="SEC002",
        name="sql_string_concat",
        description="SQL query built using string concatenation - potential SQL injection",
        category=PatternCategory.SECURITY,
        severity=ViolationSeverity.CRITICAL,
        regex_pattern=r"""(?i)(?:execute|cursor\.execute|query)\s*\([^)]*(?:\+|\.format|f['"])""",
        suggestion="Use parameterized queries: cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))",
        cwe_id="CWE-89",
    ),
    # [20251226_FEATURE] Shell injection via os.system
    PatternDefinition(
        id="SEC003",
        name="os_system_call",
        description="os.system() is vulnerable to shell injection",
        category=PatternCategory.SECURITY,
        severity=ViolationSeverity.ERROR,
        ast_node_types=(ast.Call,),
        ast_validator=lambda node: (  # type: ignore[union-attr]
            isinstance(cast(ast.Call, node).func, ast.Attribute)
            and isinstance(cast(ast.Attribute, cast(ast.Call, node).func).value, ast.Name)
            and cast(ast.Name, cast(ast.Attribute, cast(ast.Call, node).func).value).id == "os"
            and cast(ast.Attribute, cast(ast.Call, node).func).attr == "system"
        ),
        suggestion="Use subprocess.run() with shell=False and a list of arguments",
        cwe_id="CWE-78",
    ),
    # [20251226_FEATURE] Subprocess with shell=True
    PatternDefinition(
        id="SEC004",
        name="subprocess_shell",
        description="subprocess with shell=True is vulnerable to shell injection",
        category=PatternCategory.SECURITY,
        severity=ViolationSeverity.ERROR,
        regex_pattern=r"subprocess\.\w+\s*\([^)]*shell\s*=\s*True",
        suggestion="Use shell=False with a list of arguments",
        cwe_id="CWE-78",
    ),
    # [20251226_FEATURE] Pickle usage with untrusted data
    PatternDefinition(
        id="SEC005",
        name="pickle_usage",
        description="pickle can execute arbitrary code during deserialization",
        category=PatternCategory.SECURITY,
        severity=ViolationSeverity.WARNING,
        regex_pattern=r"pickle\.(?:load|loads)\s*\(",
        suggestion="Use JSON or other safe serialization formats for untrusted data",
        cwe_id="CWE-502",
    ),
    # [20251226_FEATURE] Yaml unsafe load
    PatternDefinition(
        id="SEC006",
        name="yaml_unsafe_load",
        description="yaml.load() without Loader is vulnerable to arbitrary code execution",
        category=PatternCategory.SECURITY,
        severity=ViolationSeverity.CRITICAL,
        regex_pattern=r"yaml\.load\s*\([^)]*\)(?!\s*,\s*Loader)",
        suggestion="Use yaml.safe_load() or specify Loader=yaml.SafeLoader",
        cwe_id="CWE-502",
    ),
    # [20251226_FEATURE] Hardcoded IP addresses
    PatternDefinition(
        id="SEC007",
        name="hardcoded_ip",
        description="Hardcoded IP address detected",
        category=PatternCategory.SECURITY,
        severity=ViolationSeverity.INFO,
        regex_pattern=r"""['"](?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)['"]""",
        suggestion="Use configuration files or environment variables for IP addresses",
    ),
    # [20251226_FEATURE] Insecure SSL context
    PatternDefinition(
        id="SEC008",
        name="insecure_ssl",
        description="SSL certificate verification disabled",
        category=PatternCategory.SECURITY,
        severity=ViolationSeverity.CRITICAL,
        regex_pattern=r"verify\s*=\s*False|ssl\._create_unverified_context",
        suggestion="Enable SSL certificate verification",
        cwe_id="CWE-295",
    ),
    # [20251226_FEATURE] Debug mode in production
    PatternDefinition(
        id="SEC009",
        name="debug_mode",
        description="Debug mode should be disabled in production",
        category=PatternCategory.SECURITY,
        severity=ViolationSeverity.WARNING,
        regex_pattern=r"(?:DEBUG|debug)\s*=\s*True|\.run\s*\([^)]*debug\s*=\s*True",
        suggestion="Use environment variable to control debug mode",
    ),
    # [20251226_FEATURE] MD5/SHA1 usage
    PatternDefinition(
        id="SEC010",
        name="weak_hash",
        description="MD5/SHA1 are cryptographically weak hash algorithms",
        category=PatternCategory.SECURITY,
        severity=ViolationSeverity.WARNING,
        regex_pattern=r"hashlib\.(?:md5|sha1)\s*\(",
        suggestion="Use SHA-256 or stronger: hashlib.sha256()",
        cwe_id="CWE-328",
    ),
]


# =============================================================================
# ASYNC PATTERNS (Pro Tier)
# =============================================================================

ASYNC_PATTERNS: list[PatternDefinition] = [
    # [20251226_FEATURE] Missing await on coroutine
    PatternDefinition(
        id="ASYNC001",
        name="missing_await",
        description="Coroutine called without await - result will be discarded",
        category=PatternCategory.ASYNC,
        severity=ViolationSeverity.ERROR,
        # This requires more complex analysis - detected by AST validator
        ast_node_types=(ast.Expr,),
        ast_validator=lambda node: (
            isinstance(node.value, ast.Call)  # type: ignore[reportAttributeAccessIssue]
            and isinstance(node.value.func, ast.Attribute)  # type: ignore[reportAttributeAccessIssue]
            and node.value.func.attr in ("fetch", "get", "post", "read", "write")  # type: ignore[reportAttributeAccessIssue]
        ),
        suggestion="Add 'await' before the coroutine call",
    ),
    # [20251226_FEATURE] Blocking call in async function
    PatternDefinition(
        id="ASYNC002",
        name="blocking_in_async",
        description="Blocking call in async function can freeze event loop",
        category=PatternCategory.ASYNC,
        severity=ViolationSeverity.WARNING,
        regex_pattern=r"(?:time\.sleep|requests\.\w+|urllib\.request)\s*\(",
        suggestion="Use async alternatives: asyncio.sleep(), aiohttp, etc.",
    ),
    # [20251226_FEATURE] Bare asyncio.run in async context
    PatternDefinition(
        id="ASYNC003",
        name="nested_asyncio_run",
        description="asyncio.run() cannot be called from running event loop",
        category=PatternCategory.ASYNC,
        severity=ViolationSeverity.ERROR,
        regex_pattern=r"asyncio\.run\s*\(",
        suggestion="Use 'await' directly or asyncio.create_task()",
    ),
    # [20251226_FEATURE] Fire and forget task without error handling
    PatternDefinition(
        id="ASYNC004",
        name="unhandled_task",
        description="Task created without storing reference may have unhandled exceptions",
        category=PatternCategory.ASYNC,
        severity=ViolationSeverity.WARNING,
        regex_pattern=r"asyncio\.create_task\s*\([^)]+\)(?!\s*\.\s*add_done_callback)",
        suggestion="Store task reference and add error callback or use TaskGroup",
    ),
    # [20251226_FEATURE] Async generator without proper cleanup
    PatternDefinition(
        id="ASYNC005",
        name="async_gen_cleanup",
        description="Async generator may need explicit cleanup with aclose()",
        category=PatternCategory.ASYNC,
        severity=ViolationSeverity.INFO,
        ast_node_types=(ast.AsyncFor,),
        suggestion="Consider using 'async with' or explicit aclose() for cleanup",
    ),
]


# =============================================================================
# BEST PRACTICE PATTERNS (Pro Tier)
# =============================================================================

BEST_PRACTICE_PATTERNS: list[PatternDefinition] = [
    # [20251226_FEATURE] Missing type hints on public functions
    PatternDefinition(
        id="BP001",
        name="missing_type_hints",
        description="Public function missing type annotations",
        category=PatternCategory.BEST_PRACTICE,
        severity=ViolationSeverity.INFO,
        ast_node_types=(ast.FunctionDef, ast.AsyncFunctionDef),
        ast_validator=lambda node: (
            not node.name.startswith("_")  # type: ignore[reportAttributeAccessIssue]
            and node.returns is None  # type: ignore[reportAttributeAccessIssue]
            and not any(arg.annotation for arg in node.args.args)  # type: ignore[reportAttributeAccessIssue]
        ),
        suggestion="Add type hints: 'def func(arg: Type) -> ReturnType:'",
    ),
    # [20251226_FEATURE] Missing docstring
    PatternDefinition(
        id="BP002",
        name="missing_docstring",
        description="Public function/class missing docstring",
        category=PatternCategory.BEST_PRACTICE,
        severity=ViolationSeverity.INFO,
        ast_node_types=(ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
        ast_validator=lambda node: (
            # [20260101_BUGFIX] Safe attribute access for AST node.name
            not getattr(node, "name", "").startswith("_")
            and (
                not getattr(node, "body", None)
                or not isinstance(node.body[0], ast.Expr)
                or not isinstance(node.body[0].value, ast.Constant)
                or not isinstance(node.body[0].value.value, str)
            )
        ),
        suggestion="Add a docstring describing the function/class purpose",
    ),
    # [20251226_FEATURE] Too many arguments
    PatternDefinition(
        id="BP003",
        name="too_many_args",
        description="Function has too many arguments (>7)",
        category=PatternCategory.BEST_PRACTICE,
        severity=ViolationSeverity.WARNING,
        ast_node_types=(ast.FunctionDef, ast.AsyncFunctionDef),
        ast_validator=lambda node: (len(node.args.args) + len(node.args.kwonlyargs) > 7),  # type: ignore[reportAttributeAccessIssue]
        suggestion="Consider using a dataclass or configuration object",
    ),
    # [20251226_FEATURE] Function too long
    PatternDefinition(
        id="BP004",
        name="function_too_long",
        description="Function is too long (>50 lines)",
        category=PatternCategory.BEST_PRACTICE,
        severity=ViolationSeverity.WARNING,
        ast_node_types=(ast.FunctionDef, ast.AsyncFunctionDef),
        ast_validator=lambda node: (
            hasattr(node, "end_lineno")
            and node.end_lineno  # type: ignore[reportAttributeAccessIssue]
            and (node.end_lineno - node.lineno) > 50  # type: ignore[reportAttributeAccessIssue]
        ),
        suggestion="Break down into smaller, focused functions",
    ),
    # [20251226_FEATURE] Nested too deep
    PatternDefinition(
        id="BP005",
        name="nested_too_deep",
        description="Code nesting too deep (>4 levels)",
        category=PatternCategory.BEST_PRACTICE,
        severity=ViolationSeverity.WARNING,
        # This requires specialized analysis
        suggestion="Extract nested logic into separate functions",
    ),
    # [20251226_FEATURE] Open file without context manager
    PatternDefinition(
        id="BP006",
        name="file_no_context",
        description="File opened without context manager",
        category=PatternCategory.BEST_PRACTICE,
        severity=ViolationSeverity.WARNING,
        regex_pattern=r"(?<!with\s)open\s*\([^)]+\)(?!\s*as\s)",
        suggestion="Use 'with open(...) as f:' for automatic file closing",
    ),
    # [20251226_FEATURE] Magic numbers
    PatternDefinition(
        id="BP007",
        name="magic_number",
        description="Magic number in code - use named constant",
        category=PatternCategory.BEST_PRACTICE,
        severity=ViolationSeverity.INFO,
        regex_pattern=r"(?<![a-zA-Z_])(?:0x[0-9a-fA-F]{4,}|\d{4,})(?![a-zA-Z_])",
        suggestion="Define a named constant: 'MAX_RETRIES = 1000'",
    ),
]


# =============================================================================
# COMPLIANCE PATTERNS (Enterprise Tier)
# =============================================================================

# HIPAA patterns for PHI handling
HIPAA_PATTERNS: list[PatternDefinition] = [
    PatternDefinition(
        id="HIPAA001",
        name="phi_logging",
        description="Potential PHI in log statement",
        category=PatternCategory.SECURITY,
        severity=ViolationSeverity.CRITICAL,
        regex_pattern=r"""(?i)(?:log|print|logger)\s*[.(]\s*[^)]*(?:ssn|social_security|patient_id|medical_record|diagnosis|dob|date_of_birth)""",
        suggestion="Never log PHI - use anonymized identifiers",
        cwe_id="CWE-532",
    ),
    PatternDefinition(
        id="HIPAA002",
        name="phi_plaintext",
        description="PHI stored without encryption",
        category=PatternCategory.SECURITY,
        severity=ViolationSeverity.CRITICAL,
        regex_pattern=r"""(?i)(?:patient|medical|health).*=.*(?:open|write|json\.dump)""",
        suggestion="Encrypt PHI at rest and in transit",
    ),
    PatternDefinition(
        id="HIPAA003",
        name="missing_audit_log",
        description="PHI access without audit logging",
        category=PatternCategory.SECURITY,
        severity=ViolationSeverity.WARNING,
        regex_pattern=r"""(?i)def\s+(?:get|fetch|retrieve)_(?:patient|medical|health)""",
        suggestion="Add audit logging for all PHI access",
    ),
]

# SOC2 patterns for security controls
SOC2_PATTERNS: list[PatternDefinition] = [
    PatternDefinition(
        id="SOC2001",
        name="missing_access_control",
        description="API endpoint without authentication check",
        category=PatternCategory.SECURITY,
        severity=ViolationSeverity.ERROR,
        regex_pattern=r"""@(?:app|router)\.(?:get|post|put|delete)\s*\([^)]+\)\s*(?:async\s+)?def\s+\w+\s*\([^)]*\)(?:(?!@require_auth|@login_required|@authenticated).)*?:""",
        suggestion="Add authentication decorator to all endpoints",
    ),
    PatternDefinition(
        id="SOC2002",
        name="no_rate_limiting",
        description="API endpoint without rate limiting",
        category=PatternCategory.SECURITY,
        severity=ViolationSeverity.WARNING,
        regex_pattern=r"""@(?:app|router)\.(?:get|post|put|delete)(?:(?!@rate_limit|@throttle).)*""",
        suggestion="Add rate limiting to prevent DoS attacks",
    ),
    PatternDefinition(
        id="SOC2003",
        name="no_input_validation",
        description="User input used without validation",
        category=PatternCategory.SECURITY,
        severity=ViolationSeverity.ERROR,
        regex_pattern=r"""request\.(?:form|args|json|data)\s*\[[^\]]+\](?!\s*\.\s*(?:strip|validate|sanitize))""",
        suggestion="Validate and sanitize all user input",
        cwe_id="CWE-20",
    ),
]

# GDPR patterns for data handling
GDPR_PATTERNS: list[PatternDefinition] = [
    PatternDefinition(
        id="GDPR001",
        name="pii_without_consent",
        description="PII collection without explicit consent check",
        category=PatternCategory.SECURITY,
        severity=ViolationSeverity.ERROR,
        regex_pattern=r"""(?i)(?:email|phone|address|name).*=.*request\.(?:form|json|args)(?:(?!consent|agreed|gdpr).)*""",
        suggestion="Verify user consent before collecting PII",
    ),
    PatternDefinition(
        id="GDPR002",
        name="no_data_retention_policy",
        description="Data storage without retention policy",
        category=PatternCategory.SECURITY,
        severity=ViolationSeverity.WARNING,
        regex_pattern=r"""(?:db|database|collection)\.(?:insert|save|create)(?:(?!expires|ttl|retention).)*""",
        suggestion="Implement data retention policy with automatic deletion",
    ),
    PatternDefinition(
        id="GDPR003",
        name="cross_border_transfer",
        description="Potential cross-border data transfer",
        category=PatternCategory.SECURITY,
        severity=ViolationSeverity.INFO,
        regex_pattern=r"""(?i)(?:s3|azure|gcs|cloudflare).*(?:upload|put|transfer)""",
        suggestion="Ensure compliance with data localization requirements",
    ),
]

# PCI-DSS patterns for payment data
PCI_DSS_PATTERNS: list[PatternDefinition] = [
    PatternDefinition(
        id="PCI001",
        name="card_number_logging",
        description="Credit card number in log statement",
        category=PatternCategory.SECURITY,
        severity=ViolationSeverity.CRITICAL,
        regex_pattern=r"""(?i)(?:log|print).*(?:card|credit|pan|account).*number""",
        suggestion="Never log full card numbers - use masked values",
        cwe_id="CWE-532",
    ),
    PatternDefinition(
        id="PCI002",
        name="card_storage",
        description="Credit card data stored without encryption",
        category=PatternCategory.SECURITY,
        severity=ViolationSeverity.CRITICAL,
        regex_pattern=r"""(?i)(?:card|credit|cvv|cvc).*=.*(?!encrypt|hash)""",
        suggestion="Never store CVV; encrypt card data with strong algorithms",
    ),
    PatternDefinition(
        id="PCI003",
        name="insecure_transmission",
        description="Payment data transmitted without TLS",
        category=PatternCategory.SECURITY,
        severity=ViolationSeverity.CRITICAL,
        regex_pattern=r"""http://.*(?:payment|checkout|card)""",
        suggestion="Always use HTTPS for payment data",
    ),
]


def get_patterns_for_tier(tier: str) -> list[PatternDefinition]:
    """
    Get all applicable patterns for a tier level.

    [20251226_FEATURE] Tier-based pattern selection.

    Args:
        tier: Tier level (community, pro, enterprise)

    Returns:
        List of pattern definitions for the tier
    """
    patterns: list[PatternDefinition] = []

    # Community tier: anti-patterns only
    patterns.extend(PYTHON_ANTIPATTERNS)

    if tier in ("pro", "enterprise"):
        # Pro tier: add security, async, and best practice patterns
        patterns.extend(SECURITY_PATTERNS)
        patterns.extend(ASYNC_PATTERNS)
        patterns.extend(BEST_PRACTICE_PATTERNS)

    if tier == "enterprise":
        # Enterprise tier: add compliance patterns
        patterns.extend(HIPAA_PATTERNS)
        patterns.extend(SOC2_PATTERNS)
        patterns.extend(GDPR_PATTERNS)
        patterns.extend(PCI_DSS_PATTERNS)

    return patterns


def get_compliance_patterns(standards: list[str]) -> list[PatternDefinition]:
    """
    Get patterns for specific compliance standards.

    [20251226_FEATURE] Enterprise tier compliance pattern selection.

    Args:
        standards: List of standards (hipaa, soc2, gdpr, pci_dss)

    Returns:
        List of pattern definitions for the standards
    """
    patterns: list[PatternDefinition] = []

    standard_map = {
        "hipaa": HIPAA_PATTERNS,
        "soc2": SOC2_PATTERNS,
        "gdpr": GDPR_PATTERNS,
        "pci_dss": PCI_DSS_PATTERNS,
        "pci-dss": PCI_DSS_PATTERNS,
    }

    for standard in standards:
        key = standard.lower().replace("-", "_")
        if key in standard_map:
            patterns.extend(standard_map[key])

    return patterns
