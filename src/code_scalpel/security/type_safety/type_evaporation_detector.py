"""
Type System Evaporation Detector - Cross-Language Type Boundary Analysis.

[20251229_FEATURE] v3.0.4 - Ninja Warrior Stage 3.1

This module detects vulnerabilities where TypeScript/JavaScript compile-time types
are trusted across network boundaries but evaporate at serialization:

1. **Unsafe Type Assertions**: `value as Type` on external input (DOM, API response)
2. **DOM Input Without Validation**: document.getElementById().value used directly
3. **Fetch Boundary Crossing**: JSON.stringify() erases type information
4. **Cross-File Type Trust**: Frontend types trusted by backend without re-validation

CRITICAL CONCEPT: Type Evaporation
==================================

TypeScript types exist ONLY at compile time. When data crosses boundaries:

    Frontend (TypeScript)                Backend (Python)
    ──────────────────────              ─────────────────
    type Role = 'admin' | 'user'        # No type info!
            │                                   │
            ▼                                   ▼
    JSON.stringify(payload)  ──────>  request.get_json()
            │                                   │
    TYPE INFO ERASED                   RAW STRING RECEIVED

This module flags:
- Type assertions on untrusted input
- Serialization boundaries where types evaporate
- Backend endpoints that trust frontend type contracts
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

# Type stubs for tree-sitter when not available
if TYPE_CHECKING:
    from tree_sitter import Language as TSLanguage
    from tree_sitter import Node as TSNode
    from tree_sitter import Parser as TSParser
else:
    TSLanguage = Any
    TSNode = Any
    TSParser = Any


# Try to import tree-sitter for TypeScript parsing
try:
    from tree_sitter import Language, Node, Parser

    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    Language = None  # type: ignore[misc,assignment]
    Parser = None  # type: ignore[misc,assignment]
    Node = None  # type: ignore[misc,assignment]


class TypeEvaporationRisk(Enum):
    """Categories of type evaporation vulnerabilities."""

    UNSAFE_TYPE_ASSERTION = auto()  # `as Type` on external input
    DOM_INPUT_UNTRUSTED = auto()  # document.getElementById().value
    FETCH_BOUNDARY = auto()  # JSON.stringify() erases types
    TYPE_UNION_UNENFORCED = auto()  # Union type not validated at runtime
    CROSS_FILE_TYPE_TRUST = auto()  # Backend trusts frontend types


@dataclass
class TypeEvaporationVulnerability:
    """A detected type evaporation vulnerability."""

    risk_type: TypeEvaporationRisk
    location: Tuple[int, int]  # (line, column)
    description: str
    code_snippet: str
    confidence: float  # 0.0 - 1.0
    remediation: str
    cwe_id: str = "CWE-20"  # Improper Input Validation
    related_type: Optional[str] = None  # The evaporated type name
    endpoint: Optional[str] = None  # API endpoint if detected

    @property
    def severity(self) -> str:
        """Calculate severity based on risk type."""
        high_risk = {
            TypeEvaporationRisk.UNSAFE_TYPE_ASSERTION,
            TypeEvaporationRisk.DOM_INPUT_UNTRUSTED,
            TypeEvaporationRisk.CROSS_FILE_TYPE_TRUST,
        }
        return "HIGH" if self.risk_type in high_risk else "MEDIUM"


@dataclass
class TypeEvaporationResult:
    """Result of type evaporation analysis."""

    vulnerabilities: List[TypeEvaporationVulnerability] = field(default_factory=list)
    type_definitions: Dict[str, Tuple[int, str]] = field(
        default_factory=dict
    )  # name -> (line, definition)
    fetch_endpoints: List[Tuple[str, int]] = field(default_factory=list)  # (url, line)
    dom_accesses: List[Tuple[str, int]] = field(
        default_factory=list
    )  # (element_id, line)
    type_assertions: List[Tuple[str, int, str]] = field(
        default_factory=list
    )  # (type, line, context)
    analyzed_lines: int = 0

    def has_vulnerabilities(self) -> bool:
        return len(self.vulnerabilities) > 0

    def summary(self) -> str:
        if not self.vulnerabilities:
            return "No type evaporation vulnerabilities detected."

        lines = [f"Found {len(self.vulnerabilities)} type evaporation issue(s):"]
        for v in self.vulnerabilities:
            lines.append(
                f"  - {v.risk_type.name} at line {v.location[0]}: {v.description}"
            )
        return "\n".join(lines)


class TypeEvaporationDetector:
    """
    Detects type system evaporation vulnerabilities in TypeScript/JavaScript code.

    Usage:
        detector = TypeEvaporationDetector()
        result = detector.analyze(typescript_code)
        for vuln in result.vulnerabilities:
            print(f"{vuln.risk_type.name} at line {vuln.location[0]}")
    """

    # DOM access patterns that introduce untrusted input
    DOM_INPUT_PATTERNS = {
        "document.getElementById",
        "document.querySelector",
        "document.querySelectorAll",
        "document.getElementsByClassName",
        "document.getElementsByTagName",
        "document.getElementsByName",
        "document.forms",
    }

    # Properties that extract actual values from DOM elements
    DOM_VALUE_PROPERTIES = {
        ".value",
        ".textContent",
        ".innerText",
        ".innerHTML",
        ".outerHTML",
        ".getAttribute(",
    }

    # Serialization boundaries where types evaporate
    SERIALIZATION_SINKS = {
        "JSON.stringify",
        "JSON.parse",  # Also dangerous - returns `any`
        "localStorage.setItem",
        "sessionStorage.setItem",
        "postMessage",
    }

    # Fetch/HTTP patterns.
    # Note: tree-sitter function text for member calls includes the member, e.g. "axios.post".
    FETCH_PATTERNS = {
        "fetch",
        "axios",
        "axios.get",
        "axios.post",
        "axios.put",
        "axios.delete",
        "axios.patch",
        "XMLHttpRequest",
        "$.ajax",
        "$.post",
        "$.get",
    }

    def _is_fetch_like(self, func_text: str) -> bool:
        ft = (func_text or "").strip()
        if ft in self.FETCH_PATTERNS:
            return True
        # Handle axios.<method> variations
        if ft.startswith("axios."):
            return True
        return False

    def _normalize_endpoint_candidate(self, raw: str) -> str:
        """Normalize an extracted endpoint candidate.

        - Removes ${...} from template strings
        - Strips scheme/host if present
        - Drops query/fragments
        - Ensures leading '/'
        """
        s = (raw or "").strip().strip("\"'`")
        if not s:
            return s

        # Remove template interpolations
        s = re.sub(r"\$\{[^}]+\}", "", s)
        s = s.strip()

        # Drop query/fragment
        s = s.split("#", 1)[0]
        s = s.split("?", 1)[0]

        # Strip scheme/host
        if "://" in s:
            parts = s.split("/", 3)
            if len(parts) >= 4:
                s = "/" + parts[3]

        s = s.strip()
        if s and not s.startswith("/"):
            # If it's clearly a path segment, normalize to a path.
            if "/" in s:
                s = "/" + s.lstrip("/")
        # Normalize trailing slash (except root)
        if len(s) > 1:
            s = s.rstrip("/")
        return s

    def __init__(self) -> None:
        """Initialize the detector with tree-sitter if available."""
        self._parser: Optional[TSParser] = None
        self._language: Optional[TSLanguage] = None

        if TREE_SITTER_AVAILABLE and Language is not None and Parser is not None:
            try:
                import tree_sitter_typescript as ts_ts

                self._language = Language(ts_ts.language_typescript())
                self._parser = Parser(self._language)
            except ImportError:
                pass

    def analyze(self, code: str, filename: str = "<string>") -> TypeEvaporationResult:
        """
        Analyze TypeScript/JavaScript code for type evaporation vulnerabilities.

        Args:
            code: The source code to analyze
            filename: Optional filename for error messages

        Returns:
            TypeEvaporationResult with detected vulnerabilities
        """
        result = TypeEvaporationResult()
        result.analyzed_lines = len(code.splitlines())

        # If tree-sitter is available, do AST-based analysis
        if self._parser is not None:
            self._analyze_with_tree_sitter(code, result)
        else:
            # Fallback to regex-based analysis
            self._analyze_with_regex(code, result)

        return result

    def _analyze_with_tree_sitter(
        self, code: str, result: TypeEvaporationResult
    ) -> None:
        """Analyze using tree-sitter AST parsing."""
        assert self._parser is not None  # Caller must verify tree-sitter is available
        tree = self._parser.parse(bytes(code, "utf-8"))
        root = tree.root_node
        lines = code.splitlines()

        # Track declared types for context
        self._extract_type_definitions(root, code, result)

        # Walk the AST
        self._walk_tree(root, code, lines, result)

    def _extract_type_definitions(
        self, root: TSNode, code: str, result: TypeEvaporationResult
    ) -> None:
        """Extract type alias and interface definitions."""

        def visit(node: TSNode):
            # Type aliases: type Role = 'admin' | 'user'
            if node.type == "type_alias_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = code[name_node.start_byte : name_node.end_byte]
                    definition = code[node.start_byte : node.end_byte]
                    result.type_definitions[name] = (
                        node.start_point[0] + 1,
                        definition,
                    )

            # Interfaces
            elif node.type == "interface_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = code[name_node.start_byte : name_node.end_byte]
                    definition = code[node.start_byte : node.end_byte]
                    result.type_definitions[name] = (
                        node.start_point[0] + 1,
                        definition,
                    )

            for child in node.children:
                visit(child)

        visit(root)

    def _walk_tree(
        self, node: TSNode, code: str, lines: List[str], result: TypeEvaporationResult
    ) -> None:
        """Walk the AST looking for type evaporation patterns."""

        # Check for type assertions: `value as Type`
        if node.type == "as_expression":
            self._check_type_assertion(node, code, lines, result)

        # Check for DOM access / serialization / fetch calls
        elif node.type == "call_expression":
            self._check_call_expression(node, code, lines, result)

        # Recurse
        for child in node.children:
            self._walk_tree(child, code, lines, result)

    def _check_type_assertion(
        self, node: TSNode, code: str, lines: List[str], result: TypeEvaporationResult
    ) -> None:
        """Check if a type assertion is on untrusted input."""
        line_num = node.start_point[0] + 1
        col_num = node.start_point[1]
        snippet = code[node.start_byte : node.end_byte]

        # Get the type being asserted
        type_node = None
        for child in node.children:
            if child.type in ("type_identifier", "predefined_type", "union_type"):
                type_node = child
                break

        type_name = (
            code[type_node.start_byte : type_node.end_byte] if type_node else "unknown"
        )

        # Check if the expression being cast is from DOM or external source
        expr_text = ""
        for child in node.children:
            if child.type not in ("as", "type_identifier", "predefined_type"):
                expr_text = code[child.start_byte : child.end_byte]
                break

        # Track all type assertions
        result.type_assertions.append((type_name, line_num, snippet))

        # Check if this is on DOM input
        is_dom_input = any(
            pattern in expr_text for pattern in self.DOM_INPUT_PATTERNS
        ) or any(prop in expr_text for prop in self.DOM_VALUE_PROPERTIES)

        # Check for chained assertions like: (x as HTMLInputElement).value as Role
        # This is the dangerous pattern in the test file
        is_chained_dom = ".value as" in snippet or "as HTMLInputElement" in expr_text

        if is_dom_input or is_chained_dom:
            result.vulnerabilities.append(
                TypeEvaporationVulnerability(
                    risk_type=TypeEvaporationRisk.UNSAFE_TYPE_ASSERTION,
                    location=(line_num, col_num),
                    description=f"Type assertion `as {type_name}` on DOM input - NO runtime enforcement",
                    code_snippet=snippet[:100],
                    confidence=0.95,
                    remediation=f"Add runtime validation: if (!['admin', 'user'].includes(value)) throw new Error('Invalid {type_name}')",
                    related_type=type_name,
                )
            )

    def _check_call_expression(
        self, node: TSNode, code: str, lines: List[str], result: TypeEvaporationResult
    ) -> None:
        """Check call expressions for DOM access and serialization."""
        func_name = self._get_function_name(node, code)

        line_num = node.start_point[0] + 1
        col_num = node.start_point[1]
        snippet = code[node.start_byte : node.end_byte]

        # Check for DOM access
        if any(pattern in func_name for pattern in self.DOM_INPUT_PATTERNS):
            # Extract element ID if available
            args_node = node.child_by_field_name("arguments")
            element_id = ""
            if args_node:
                for arg in args_node.children:
                    if arg.type == "string":
                        element_id = code[arg.start_byte : arg.end_byte].strip("'\"")
                        break

            result.dom_accesses.append((element_id or "unknown", line_num))

            # Check if value is accessed without type validation
            parent = node.parent
            while parent:
                parent_text = code[parent.start_byte : parent.end_byte]
                if ".value" in parent_text and "as " in parent_text:
                    result.vulnerabilities.append(
                        TypeEvaporationVulnerability(
                            risk_type=TypeEvaporationRisk.DOM_INPUT_UNTRUSTED,
                            location=(line_num, col_num),
                            description=f"DOM input from '{element_id}' used with type assertion - attacker controlled",
                            code_snippet=parent_text[:100],
                            confidence=0.95,
                            remediation="Validate DOM input against expected values before use",
                        )
                    )
                    break
                parent = parent.parent

        # Check for serialization boundaries
        if func_name in self.SERIALIZATION_SINKS:
            result.vulnerabilities.append(
                TypeEvaporationVulnerability(
                    risk_type=TypeEvaporationRisk.FETCH_BOUNDARY,
                    location=(line_num, col_num),
                    description=f"{func_name}() erases all TypeScript type information",
                    code_snippet=snippet[:100],
                    confidence=0.9,
                    remediation="Ensure backend performs validation - types do not survive serialization",
                )
            )

        # Check for fetch calls
        if self._is_fetch_like(func_name):
            self._check_fetch_call(node, code, lines, result)

    def _check_fetch_call(
        self, node: TSNode, code: str, lines: List[str], result: TypeEvaporationResult
    ) -> None:
        """Extract endpoint URL from fetch call."""
        line_num = node.start_point[0] + 1
        snippet = code[node.start_byte : node.end_byte]

        # Try to extract URL from first argument
        args_node = node.child_by_field_name("arguments")
        endpoint = None

        if args_node:
            for arg in args_node.children:
                arg_text = code[arg.start_byte : arg.end_byte]
                # Look for string literals
                if arg.type in ("string", "template_string"):
                    endpoint = arg_text.strip("'\"`")
                    break
                # Look for URL patterns
                url_match = re.search(r"['\"`]([^'\"]+)['\"`]", arg_text)
                if url_match:
                    endpoint = url_match.group(1)
                    break

        if endpoint:
            endpoint = self._normalize_endpoint_candidate(endpoint)
            if endpoint:
                result.fetch_endpoints.append((endpoint, line_num))

            # Check if body contains JSON.stringify
            if "JSON.stringify" in snippet:
                result.vulnerabilities.append(
                    TypeEvaporationVulnerability(
                        risk_type=TypeEvaporationRisk.FETCH_BOUNDARY,
                        location=(line_num, node.start_point[1]),
                        description=f"Type information lost at fetch() to {endpoint}",
                        code_snippet=snippet[:150],
                        confidence=0.95,
                        remediation=f"Backend at {endpoint} MUST validate all input - TypeScript types are erased",
                        endpoint=endpoint,
                    )
                )

    def _get_function_name(self, node: TSNode, code: str) -> str:
        """Extract function name from call expression."""
        func_node = node.child_by_field_name("function")
        if func_node:
            return code[func_node.start_byte : func_node.end_byte]
        return ""

    def _analyze_with_regex(self, code: str, result: TypeEvaporationResult) -> None:
        """Fallback regex-based analysis when tree-sitter is unavailable."""
        lines = code.splitlines()

        for i, line in enumerate(lines, 1):
            # Type assertions: `as Type`
            as_matches = re.finditer(r"\bas\s+(\w+)", line)
            for match in as_matches:
                type_name = match.group(1)
                result.type_assertions.append((type_name, i, line.strip()))

                # Check if DOM input
                if (
                    any(pattern in line for pattern in self.DOM_INPUT_PATTERNS)
                    or ".value" in line
                ):
                    result.vulnerabilities.append(
                        TypeEvaporationVulnerability(
                            risk_type=TypeEvaporationRisk.UNSAFE_TYPE_ASSERTION,
                            location=(i, match.start()),
                            description=f"Type assertion `as {type_name}` on potential DOM input",
                            code_snippet=line.strip()[:100],
                            confidence=0.8,
                            remediation=f"Add runtime validation for {type_name}",
                            related_type=type_name,
                        )
                    )

            # DOM access
            for pattern in self.DOM_INPUT_PATTERNS:
                if pattern in line:
                    id_match = re.search(r"\(['\"]([^'\"]+)['\"]\)", line)
                    element_id = id_match.group(1) if id_match else "unknown"
                    result.dom_accesses.append((element_id, i))

            # Fetch calls (fetch + axios)
            if "fetch(" in line:
                url_match = re.search(r"fetch\s*\(\s*(['\"`])([^'\"`]+)\1", line)
                if url_match:
                    result.fetch_endpoints.append(
                        (self._normalize_endpoint_candidate(url_match.group(2)), i)
                    )
                else:
                    # Template strings / concatenations: try to salvage a path suffix
                    tmpl = re.search(r"fetch\s*\(\s*(`)([^`]+)`", line)
                    if tmpl:
                        result.fetch_endpoints.append(
                            (self._normalize_endpoint_candidate(tmpl.group(2)), i)
                        )

            axios_match = re.search(
                r"\baxios\.(get|post|put|delete|patch)\s*\(\s*(['\"`])([^'\"`]+)\2",
                line,
            )
            if axios_match:
                result.fetch_endpoints.append(
                    (self._normalize_endpoint_candidate(axios_match.group(3)), i)
                )

            # JSON.stringify boundary
            if "JSON.stringify" in line:
                result.vulnerabilities.append(
                    TypeEvaporationVulnerability(
                        risk_type=TypeEvaporationRisk.FETCH_BOUNDARY,
                        location=(i, line.index("JSON.stringify")),
                        description="JSON.stringify() erases TypeScript type information",
                        code_snippet=line.strip()[:100],
                        confidence=0.9,
                        remediation="Backend must validate - types don't survive serialization",
                    )
                )

            # Type definitions
            type_match = re.match(r"^\s*type\s+(\w+)\s*=", line)
            if type_match:
                result.type_definitions[type_match.group(1)] = (i, line.strip())


# =============================================================================
# [20260314_FEATURE] Python Backend Type Evaporation Analyzer
# Detects where Python route handlers lose type information received from
# a typed TS/JS frontend (e.g. untyped params, Any annotations, dict access).
# Scope: route-handler functions ONLY (Flask/FastAPI/Django decorators).
# This is intentionally narrow: "TS/JS frontend → Python backend" contract only.
# =============================================================================


@dataclass
class PythonTypeEvaporationFinding:
    """A detected type evaporation pattern in a Python backend handler.

    [20260314_FEATURE] Represents a location where type information from a
    typed TS/JS contract boundary is lost or ignored in a Python handler.
    """

    pattern: str  # e.g. "UNTYPED_PARAMETER", "KWARGS_WILDCARD", "ANY_TYPE", etc.
    location: Tuple[int, int]  # (line, col)
    description: str
    function_name: str
    parameter_name: Optional[str]  # None when the finding is function-level
    code_snippet: str
    severity: str  # "high" | "medium" | "low"
    cwe_id: str  # CWE-20 (Improper Input Validation) for most evaporation patterns
    remediation: str
    vulnerability_type: str = field(init=False)  # alias for compatibility
    sink_location: Optional[Tuple[int, int]] = None  # alias used by outer model

    def __post_init__(self) -> None:
        # Alias for compatibility with SecurityAnalyzer result shape
        self.vulnerability_type = f"[Backend-TypeEvaporation] {self.pattern}"
        if self.sink_location is None:
            self.sink_location = self.location


# Flask / FastAPI / Django route decorator patterns (conservative whitelist)
_ROUTE_DECORATOR_METHODS = frozenset(
    {
        "route",
        "get",
        "post",
        "put",
        "delete",
        "patch",
        "head",
        "options",
        "api_route",
        "api_view",
        "action",
    }
)

# Known framework prefixes for route decorators
_ROUTE_DECORATOR_PREFIXES = frozenset({"app", "router", "bp", "blueprint", "api"})


def _is_route_decorator(dec: ast.expr) -> bool:
    """Return True if *dec* is a known web-framework route decorator.

    Accepts both `@app.get(...)` and `@arbitrary_name.get(...)` patterns so that
    blueprints / routers with custom variable names are included.
    """
    # @name(...)  — bare call, e.g. @api_view(['GET'])
    if isinstance(dec, ast.Call):
        func = dec.func
    else:
        func = dec

    if isinstance(func, ast.Attribute):
        method = func.attr
        # Accept known methods on any object (covers @users_bp.post, @v1_router.get, etc.)
        if method in _ROUTE_DECORATOR_METHODS:
            return True
        # Also accept known prefix + any attribute (e.g. @app.something_custom)
        if (
            isinstance(func.value, ast.Name)
            and func.value.id in _ROUTE_DECORATOR_PREFIXES
        ):
            return True
    elif isinstance(func, ast.Name) and func.id in _ROUTE_DECORATOR_METHODS:
        # @api_view / @action / @route used bare
        return True

    return False


class PythonBackendAnalyzer:
    """Detect type evaporation patterns in Python backend route handlers.

    [20260314_FEATURE] Uses Python's ``ast`` module to inspect route-handler
    function signatures and bodies for patterns where type information
    received from a typed TS/JS frontend is dropped or ignored.

    Only route handler functions (decorated with web-framework route decorators)
    are analysed. Non-route code is out of scope to avoid overclaiming beyond the
    "TS/JS frontend → Python backend" contract.
    """

    # Fully-qualified names that represent fully-typed Pydantic/dataclass params
    # (these do NOT constitute an evaporation finding).
    _TYPED_MODEL_BASES: frozenset[str] = frozenset(
        {"BaseModel", "TypedDict", "dataclass", "NamedTuple"}
    )

    def analyze(
        self, python_code: str, filename: str = "backend.py"
    ) -> list[PythonTypeEvaporationFinding]:
        """Analyse *python_code* for type evaporation in route handlers.

        Falls back to regex-based detection if the code cannot be parsed by
        ``ast.parse`` (mirrors the TypeScript detector's fallback pattern).

        Args:
            python_code: Python source code string.
            filename: Display name used in finding descriptions.

        Returns:
            List of :class:`PythonTypeEvaporationFinding` instances.
        """
        try:
            tree = ast.parse(python_code, filename=filename)
        except SyntaxError:
            return self._analyze_with_regex(python_code, filename)

        findings: list[PythonTypeEvaporationFinding] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if self._is_route_handler(node):
                    findings.extend(self._check_function(node, python_code))
        return findings

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_route_handler(self, func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        """Return True if the function has at least one route decorator."""
        return any(_is_route_decorator(dec) for dec in func.decorator_list)

    def _check_function(
        self,
        func: ast.FunctionDef | ast.AsyncFunctionDef,
        source: str,
    ) -> list[PythonTypeEvaporationFinding]:
        findings: list[PythonTypeEvaporationFinding] = []
        findings.extend(self._check_untyped_parameters(func, source))
        findings.extend(self._check_any_annotations(func, source))
        findings.extend(self._check_variadic_wildcards(func, source))
        findings.extend(self._check_request_data_access(func, source))
        findings.extend(self._check_missing_return_type(func, source))
        return findings

    def _annotation_name(self, ann: ast.expr | None) -> Optional[str]:
        """Extract a simple string representation of an annotation node."""
        if ann is None:
            return None
        if isinstance(ann, ast.Name):
            return ann.id
        if isinstance(ann, ast.Attribute):
            return ann.attr
        if isinstance(ann, ast.Subscript):
            return self._annotation_name(ann.value)
        return None

    def _snippet(self, source: str, lineno: int, n: int = 1) -> str:
        """Return *n* lines from *source* starting at 1-based *lineno*."""
        lines = source.splitlines()
        start = max(0, lineno - 1)
        end = min(len(lines), start + n)
        return "\n".join(lines[start:end])

    def _check_untyped_parameters(
        self,
        func: ast.FunctionDef | ast.AsyncFunctionDef,
        source: str,
    ) -> list[PythonTypeEvaporationFinding]:
        """Flag route-handler parameters that have no type annotation."""
        findings: list[PythonTypeEvaporationFinding] = []
        args = func.args
        all_args = args.args + args.posonlyargs + args.kwonlyargs

        for arg in all_args:
            if arg.arg in ("self", "cls"):
                continue
            if arg.annotation is None:
                findings.append(
                    PythonTypeEvaporationFinding(
                        pattern="UNTYPED_PARAMETER",
                        location=(arg.lineno, arg.col_offset),
                        description=(
                            f"Parameter '{arg.arg}' in route handler "
                            f"'{func.name}' has no type annotation — "
                            "type contract from TS/JS frontend is silently dropped."
                        ),
                        function_name=func.name,
                        parameter_name=arg.arg,
                        code_snippet=self._snippet(source, arg.lineno),
                        severity="high",
                        cwe_id="CWE-20",
                        remediation=(
                            f"Annotate '{arg.arg}' with a Pydantic model or explicit "
                            "type and add validation before use."
                        ),
                    )
                )
        return findings

    def _check_any_annotations(
        self,
        func: ast.FunctionDef | ast.AsyncFunctionDef,
        source: str,
    ) -> list[PythonTypeEvaporationFinding]:
        """Flag parameters annotated as ``typing.Any`` or bare ``Any``."""
        findings: list[PythonTypeEvaporationFinding] = []
        args = func.args
        all_args = args.args + args.posonlyargs + args.kwonlyargs

        for arg in all_args:
            if arg.arg in ("self", "cls") or arg.annotation is None:
                continue
            ann_name = self._annotation_name(arg.annotation)
            if ann_name == "Any":
                findings.append(
                    PythonTypeEvaporationFinding(
                        pattern="ANY_TYPE",
                        location=(arg.lineno, arg.col_offset),
                        description=(
                            f"Parameter '{arg.arg}' in '{func.name}' is annotated as "
                            "`Any` — the TS/JS type contract is accepted without "
                            "validation."
                        ),
                        function_name=func.name,
                        parameter_name=arg.arg,
                        code_snippet=self._snippet(source, arg.lineno),
                        severity="high",
                        cwe_id="CWE-20",
                        remediation=(
                            f"Replace `Any` annotation for '{arg.arg}' with a "
                            "Pydantic model or explicit type and add validation."
                        ),
                    )
                )
        return findings

    def _check_variadic_wildcards(
        self,
        func: ast.FunctionDef | ast.AsyncFunctionDef,
        source: str,
    ) -> list[PythonTypeEvaporationFinding]:
        """Flag ``*args`` / ``**kwargs`` parameters in route handlers."""
        findings: list[PythonTypeEvaporationFinding] = []
        args = func.args

        if args.vararg is not None:
            a = args.vararg
            findings.append(
                PythonTypeEvaporationFinding(
                    pattern="ARGS_WILDCARD",
                    location=(a.lineno, a.col_offset),
                    description=(
                        f"Route handler '{func.name}' accepts *{a.arg} — "
                        "positional arguments from the frontend are not typed or validated."
                    ),
                    function_name=func.name,
                    parameter_name=f"*{a.arg}",
                    code_snippet=self._snippet(source, a.lineno),
                    severity="medium",
                    cwe_id="CWE-20",
                    remediation=(
                        "Replace *args with an explicit typed Pydantic model parameter."
                    ),
                )
            )

        if args.kwarg is not None:
            k = args.kwarg
            findings.append(
                PythonTypeEvaporationFinding(
                    pattern="KWARGS_WILDCARD",
                    location=(k.lineno, k.col_offset),
                    description=(
                        f"Route handler '{func.name}' accepts **{k.arg} — "
                        "all keyword arguments from the frontend are absorbed without "
                        "type checking."
                    ),
                    function_name=func.name,
                    parameter_name=f"**{k.arg}",
                    code_snippet=self._snippet(source, k.lineno),
                    severity="medium",
                    cwe_id="CWE-20",
                    remediation=(
                        "Replace **kwargs with an explicit typed Pydantic model "
                        "parameter."
                    ),
                )
            )
        return findings

    def _check_request_data_access(
        self,
        func: ast.FunctionDef | ast.AsyncFunctionDef,
        source: str,
    ) -> list[PythonTypeEvaporationFinding]:
        """Flag dict-style access on ``request.get_json()`` / ``request.json`` result.

        Patterns like ``data["key"]`` or ``data.get("key")`` on a variable that
        is assigned from a JSON request represent type evaporation at the access
        level: no schema or model is enforcing the expected shape.
        """
        findings: list[PythonTypeEvaporationFinding] = []

        # Collect names that receive request JSON data
        json_var_names: set[str] = set()

        for node in ast.walk(func):
            if isinstance(node, ast.Assign):
                # data = request.get_json()  or  data = request.json
                if (
                    isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Attribute)
                    and node.value.func.attr == "get_json"
                ):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            json_var_names.add(target.id)
                elif (
                    isinstance(node.value, ast.Attribute)
                    and node.value.attr in ("json", "data", "form")
                    and isinstance(node.value.value, ast.Name)
                    and node.value.value.id == "request"
                ):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            json_var_names.add(target.id)

        if not json_var_names:
            return findings

        # Detect dict-style subscript access on those variables
        for node in ast.walk(func):
            if isinstance(node, ast.Subscript):
                if isinstance(node.value, ast.Name) and node.value.id in json_var_names:
                    lineno = getattr(node, "lineno", 0)
                    col = getattr(node, "col_offset", 0)
                    snippet = self._snippet(source, lineno)
                    key_repr = ""
                    sl = node.slice
                    if isinstance(sl, ast.Constant):
                        key_repr = repr(sl.value)
                    elif isinstance(sl, ast.Name):
                        key_repr = sl.id
                    findings.append(
                        PythonTypeEvaporationFinding(
                            pattern="DICT_ACCESS_WITHOUT_VALIDATION",
                            location=(lineno, col),
                            description=(
                                f"Unvalidated dict access on request JSON in "
                                f"'{func.name}': `{node.value.id}[{key_repr}]` — "
                                "the TS/JS type contract is not enforced at runtime."
                            ),
                            function_name=func.name,
                            parameter_name=None,
                            code_snippet=snippet,
                            severity="high",
                            cwe_id="CWE-20",
                            remediation=(
                                "Replace dict subscript access with a Pydantic model "
                                "or explicit schema validation (e.g. "
                                "`model = MyModel(**request.get_json())`)."
                            ),
                        )
                    )
        return findings

    def _check_missing_return_type(
        self,
        func: ast.FunctionDef | ast.AsyncFunctionDef,
        source: str,
    ) -> list[PythonTypeEvaporationFinding]:
        """Flag route handlers with no return type annotation."""
        if func.returns is None:
            return [
                PythonTypeEvaporationFinding(
                    pattern="UNTYPED_RETURN",
                    location=(func.lineno, func.col_offset),
                    description=(
                        f"Route handler '{func.name}' has no return type annotation — "
                        "the response shape is opaque to TS/JS callers relying on "
                        "typed API contracts."
                    ),
                    function_name=func.name,
                    parameter_name=None,
                    code_snippet=self._snippet(source, func.lineno),
                    severity="low",
                    cwe_id="CWE-20",
                    remediation=(
                        "Add a return type annotation (e.g. `-> MyResponseModel` or "
                        "`-> dict`) so the response contract is explicit."
                    ),
                )
            ]
        return []

    def _analyze_with_regex(
        self, python_code: str, filename: str
    ) -> list[PythonTypeEvaporationFinding]:
        """Regex-based fallback when ``ast.parse`` fails (e.g. partial code).

        Detects a minimal set of evaporation signals via line-level patterns.
        """
        findings: list[PythonTypeEvaporationFinding] = []
        lines = python_code.splitlines()
        in_route: bool = False
        func_name: str = ""
        route_dec_pattern = re.compile(
            r"@\w+\.(route|get|post|put|delete|patch|head|options|api_route)"
        )
        func_def_pattern = re.compile(r"^(?:async\s+)?def\s+(\w+)\s*\(([^)]*)\)\s*:")
        dict_access_pattern = re.compile(r"\b(\w+)\s*\[\s*['\"](\w+)['\"]\s*\]")

        for i, line in enumerate(lines, 1):
            if route_dec_pattern.search(line):
                in_route = True
                continue

            if in_route:
                m = func_def_pattern.match(line.lstrip())
                if m:
                    func_name = m.group(1)
                    params_str = m.group(2)
                    # Flag params with no type annotation
                    for param in params_str.split(","):
                        param = param.strip().lstrip("*")
                        if param and ":" not in param and "=" not in param:
                            param = param.split("=")[0].strip()
                            if param and param not in ("self", "cls"):
                                findings.append(
                                    PythonTypeEvaporationFinding(
                                        pattern="UNTYPED_PARAMETER",
                                        location=(i, 0),
                                        description=(
                                            f"Parameter '{param}' in route handler "
                                            f"'{func_name}' has no type annotation."
                                        ),
                                        function_name=func_name,
                                        parameter_name=param,
                                        code_snippet=line.strip()[:120],
                                        severity="high",
                                        cwe_id="CWE-20",
                                        remediation=(
                                            f"Annotate '{param}' with an explicit type."
                                        ),
                                    )
                                )
                    in_route = False
                    continue
                in_route = False

            # Dict access pattern anywhere (best-effort in fallback mode)
            if func_name and dict_access_pattern.search(line):
                pass  # skip: without AST we can't be sure this is on json data

        return findings


# =============================================================================
# Cross-File Type Evaporation Analysis
# =============================================================================


@dataclass
class CrossFileTypeEvaporationResult:
    """Result from analyzing TypeScript frontend + Python backend together."""

    frontend_result: TypeEvaporationResult
    backend_vulnerabilities: List[Any]  # From SecurityAnalyzer
    matched_endpoints: List[Tuple[str, int, int]]  # (endpoint, ts_line, py_line)
    cross_file_issues: List[TypeEvaporationVulnerability] = field(default_factory=list)

    def summary(self) -> str:
        lines = ["=== Cross-File Type Evaporation Analysis ==="]
        lines.append(
            f"Frontend vulnerabilities: {len(self.frontend_result.vulnerabilities)}"
        )
        lines.append(f"Backend vulnerabilities: {len(self.backend_vulnerabilities)}")
        lines.append(f"Matched endpoints: {len(self.matched_endpoints)}")
        lines.append(f"Cross-file issues: {len(self.cross_file_issues)}")

        if self.matched_endpoints:
            lines.append("\nEndpoint Correlations:")
            for endpoint, ts_line, py_line in self.matched_endpoints:
                lines.append(
                    f"  - {endpoint}: TS line {ts_line} → Python line {py_line}"
                )

        return "\n".join(lines)


def analyze_type_evaporation_cross_file(
    typescript_code: str,
    python_code: str,
    ts_filename: str = "frontend.ts",
    py_filename: str = "backend.py",
) -> CrossFileTypeEvaporationResult:
    """
    Analyze TypeScript frontend and Python backend together for type evaporation.

    This correlates:
    - TypeScript fetch() endpoints with Python @app.route() decorators
    - Frontend type definitions with backend usage
    - Serialization boundaries with deserialization

    Args:
        typescript_code: TypeScript/JavaScript frontend code
        python_code: Python backend code
        ts_filename: Frontend filename for error messages
        py_filename: Backend filename for error messages

    Returns:
        CrossFileTypeEvaporationResult with correlated findings
    """
    from code_scalpel.security.analyzers import SecurityAnalyzer  # [20251225_BUGFIX]

    # Analyze frontend
    detector = TypeEvaporationDetector()
    frontend_result = detector.analyze(typescript_code, ts_filename)

    # Analyze backend - generic security analysis (SQL injection, XSS, etc.)
    analyzer = SecurityAnalyzer()
    backend_result = analyzer.analyze(python_code)

    # [20260314_FEATURE] Python-specific type evaporation detection
    py_evap_analyzer = PythonBackendAnalyzer()
    py_evap_findings = py_evap_analyzer.analyze(python_code, py_filename)

    # Build map: function_name -> [findings] for fast lookup during endpoint matching
    _py_func_findings: Dict[str, List[PythonTypeEvaporationFinding]] = {}
    for _pf in py_evap_findings:
        _py_func_findings.setdefault(_pf.function_name, []).append(_pf)

    # Extract Python routes (1-based line numbers)
    py_routes: Dict[str, int] = {}
    # Support Flask/FastAPI blueprints/routers (e.g., @bp.route, @router.get, @app.post)
    route_pattern = re.compile(
        r'@\w+\.(route|get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']'
    )
    py_source_lines = python_code.splitlines()
    for i, line in enumerate(py_source_lines, 1):
        match = route_pattern.search(line)
        if match:
            route_path = match.group(2)
            py_routes[route_path] = i

    # [20260314_FEATURE] Map route path -> handler function name (scan for def after decorator)
    _route_handler_names: Dict[str, str] = {}
    for route_path, deco_line in py_routes.items():
        for idx in range(deco_line - 1, min(deco_line + 4, len(py_source_lines))):
            stripped = py_source_lines[idx].strip()
            m = re.match(r"def\s+(\w+)\s*\(", stripped)
            if m:
                _route_handler_names[route_path] = m.group(1)
                break

    # Match endpoints
    matched_endpoints: List[Tuple[str, int, int]] = []

    def _norm_path(s: str) -> str:
        s = (s or "").strip()
        s = re.sub(r"\$\{[^}]+\}", "", s)
        s = s.split("#", 1)[0]
        s = s.split("?", 1)[0]
        if "://" in s:
            parts = s.split("/", 3)
            if len(parts) >= 4:
                s = "/" + parts[3]
        if s and not s.startswith("/") and "/" in s:
            s = "/" + s.lstrip("/")
        if len(s) > 1:
            s = s.rstrip("/")
        return s

    for ts_endpoint, ts_line in frontend_result.fetch_endpoints:
        path = _norm_path(ts_endpoint)
        if not path:
            continue

        # Try to match with Python routes
        for py_route, py_line in py_routes.items():
            py_norm = _norm_path(py_route)
            if not py_norm:
                continue

            # Prefer exact match, then suffix match.
            if path == py_norm or path.endswith(py_norm):
                matched_endpoints.append((py_route, ts_line, py_line))
                continue

            # Fallback: match by final segment (useful for simple test fixtures)
            last_seg = path.split("/")[-1]
            if last_seg and py_norm.split("/")[-1] == last_seg:
                matched_endpoints.append((py_route, ts_line, py_line))

    # Create cross-file issues for matched endpoints
    cross_file_issues: List[TypeEvaporationVulnerability] = []

    for endpoint, ts_line, py_line in matched_endpoints:
        # Check if frontend has type assertions that backend doesn't validate
        for type_name, assert_line, context in frontend_result.type_assertions:
            if type_name not in ("HTMLInputElement", "string", "any"):
                cross_file_issues.append(
                    TypeEvaporationVulnerability(
                        risk_type=TypeEvaporationRisk.CROSS_FILE_TYPE_TRUST,
                        location=(ts_line, 0),
                        description=f"TypeScript type '{type_name}' evaporates at fetch() to {endpoint} (Python line {py_line})",
                        code_snippet=f"Frontend uses `as {type_name}`, backend receives raw JSON",
                        confidence=0.95,
                        remediation=f"Python backend at {endpoint} must validate against allowed values for {type_name}",
                        related_type=type_name,
                        endpoint=endpoint,
                    )
                )

        # [20260314_FEATURE] Generate cross-file issues from Python handler type evaporation
        handler_name = _route_handler_names.get(endpoint)
        if handler_name and handler_name in _py_func_findings:
            for py_finding in _py_func_findings[handler_name]:
                cross_file_issues.append(
                    TypeEvaporationVulnerability(
                        risk_type=TypeEvaporationRisk.CROSS_FILE_TYPE_TRUST,
                        location=(ts_line, 0),
                        description=(
                            f"Python handler '{handler_name}' at {endpoint} has "
                            f"{py_finding.pattern}: {py_finding.description}"
                        ),
                        code_snippet=py_finding.code_snippet,
                        confidence=0.85,
                        remediation=py_finding.remediation,
                        related_type=py_finding.parameter_name or handler_name,
                        endpoint=endpoint,
                    )
                )

    return CrossFileTypeEvaporationResult(
        frontend_result=frontend_result,
        backend_vulnerabilities=list(backend_result.vulnerabilities) + py_evap_findings,
        matched_endpoints=matched_endpoints,
        cross_file_issues=cross_file_issues,
    )
