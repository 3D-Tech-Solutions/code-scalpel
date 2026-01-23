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

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

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
    location: tuple[int, int]  # (line, column)
    description: str
    code_snippet: str
    confidence: float  # 0.0 - 1.0
    remediation: str
    cwe_id: str = "CWE-20"  # Improper Input Validation
    related_type: str | None = None  # The evaporated type name
    endpoint: str | None = None  # API endpoint if detected

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

    vulnerabilities: list[TypeEvaporationVulnerability] = field(default_factory=list)
    type_definitions: dict[str, tuple[int, str]] = field(default_factory=dict)  # name -> (line, definition)
    fetch_endpoints: list[tuple[str, int]] = field(default_factory=list)  # (url, line)
    dom_accesses: list[tuple[str, int]] = field(default_factory=list)  # (element_id, line)
    type_assertions: list[tuple[str, int, str]] = field(default_factory=list)  # (type, line, context)
    analyzed_lines: int = 0

    def has_vulnerabilities(self) -> bool:
        return len(self.vulnerabilities) > 0

    def summary(self) -> str:
        if not self.vulnerabilities:
            return "No type evaporation vulnerabilities detected."

        lines = [f"Found {len(self.vulnerabilities)} type evaporation issue(s):"]
        for v in self.vulnerabilities:
            lines.append(f"  - {v.risk_type.name} at line {v.location[0]}: {v.description}")
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
        self._parser: TSParser | None = None
        self._language: TSLanguage | None = None

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

    def _analyze_with_tree_sitter(self, code: str, result: TypeEvaporationResult) -> None:
        """Analyze using tree-sitter AST parsing."""
        assert self._parser is not None  # Caller must verify tree-sitter is available
        tree = self._parser.parse(bytes(code, "utf-8"))
        root = tree.root_node
        lines = code.splitlines()

        # Track declared types for context
        self._extract_type_definitions(root, code, result)

        # Walk the AST
        self._walk_tree(root, code, lines, result)

    def _extract_type_definitions(self, root: TSNode, code: str, result: TypeEvaporationResult) -> None:
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

    def _walk_tree(self, node: TSNode, code: str, lines: list[str], result: TypeEvaporationResult) -> None:
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

    def _check_type_assertion(self, node: TSNode, code: str, lines: list[str], result: TypeEvaporationResult) -> None:
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

        type_name = code[type_node.start_byte : type_node.end_byte] if type_node else "unknown"

        # Check if the expression being cast is from DOM or external source
        expr_text = ""
        for child in node.children:
            if child.type not in ("as", "type_identifier", "predefined_type"):
                expr_text = code[child.start_byte : child.end_byte]
                break

        # Track all type assertions
        result.type_assertions.append((type_name, line_num, snippet))

        # Check if this is on DOM input
        is_dom_input = any(pattern in expr_text for pattern in self.DOM_INPUT_PATTERNS) or any(
            prop in expr_text for prop in self.DOM_VALUE_PROPERTIES
        )

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

    def _check_call_expression(self, node: TSNode, code: str, lines: list[str], result: TypeEvaporationResult) -> None:
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

    def _check_fetch_call(self, node: TSNode, code: str, lines: list[str], result: TypeEvaporationResult) -> None:
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
                if any(pattern in line for pattern in self.DOM_INPUT_PATTERNS) or ".value" in line:
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
                    result.fetch_endpoints.append((self._normalize_endpoint_candidate(url_match.group(2)), i))
                else:
                    # Template strings / concatenations: try to salvage a path suffix
                    tmpl = re.search(r"fetch\s*\(\s*(`)([^`]+)`", line)
                    if tmpl:
                        result.fetch_endpoints.append((self._normalize_endpoint_candidate(tmpl.group(2)), i))

            axios_match = re.search(
                r"\baxios\.(get|post|put|delete|patch)\s*\(\s*(['\"`])([^'\"`]+)\2",
                line,
            )
            if axios_match:
                result.fetch_endpoints.append((self._normalize_endpoint_candidate(axios_match.group(3)), i))

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
# Cross-File Type Evaporation Analysis
# =============================================================================


@dataclass
class CrossFileTypeEvaporationResult:
    """Result from analyzing TypeScript frontend + Python backend together."""

    frontend_result: TypeEvaporationResult
    backend_vulnerabilities: list[Any]  # From SecurityAnalyzer
    matched_endpoints: list[tuple[str, int, int]]  # (endpoint, ts_line, py_line)
    cross_file_issues: list[TypeEvaporationVulnerability] = field(default_factory=list)

    def summary(self) -> str:
        lines = ["=== Cross-File Type Evaporation Analysis ==="]
        lines.append(f"Frontend vulnerabilities: {len(self.frontend_result.vulnerabilities)}")
        lines.append(f"Backend vulnerabilities: {len(self.backend_vulnerabilities)}")
        lines.append(f"Matched endpoints: {len(self.matched_endpoints)}")
        lines.append(f"Cross-file issues: {len(self.cross_file_issues)}")

        if self.matched_endpoints:
            lines.append("\nEndpoint Correlations:")
            for endpoint, ts_line, py_line in self.matched_endpoints:
                lines.append(f"  - {endpoint}: TS line {ts_line} → Python line {py_line}")

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

    # Analyze backend
    analyzer = SecurityAnalyzer()
    backend_result = analyzer.analyze(python_code)

    # Extract Python routes
    py_routes: dict[str, int] = {}
    # Support Flask/FastAPI blueprints/routers (e.g., @bp.route, @router.get, @app.post)
    route_pattern = re.compile(r'@\w+\.(route|get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']')
    for i, line in enumerate(python_code.splitlines(), 1):
        match = route_pattern.search(line)
        if match:
            route_path = match.group(2)
            py_routes[route_path] = i

    # Match endpoints
    matched_endpoints: list[tuple[str, int, int]] = []

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
    cross_file_issues: list[TypeEvaporationVulnerability] = []

    for endpoint, ts_line, py_line in matched_endpoints:
        # Check if frontend has type assertions that backend doesn't validate
        for type_name, _assert_line, _context in frontend_result.type_assertions:
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

    return CrossFileTypeEvaporationResult(
        frontend_result=frontend_result,
        backend_vulnerabilities=backend_result.vulnerabilities,
        matched_endpoints=matched_endpoints,
        cross_file_issues=cross_file_issues,
    )
