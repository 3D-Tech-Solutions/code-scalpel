"""Refactor Simulator - Verify Code Changes Before Applying.

This module allows AI Agents to "dry run" their code changes,
verifying that a patch doesn't introduce security vulnerabilities
or break existing functionality.

Example:
    >>> from code_scalpel.generators import RefactorSimulator
    >>> simulator = RefactorSimulator()
    >>> result = simulator.simulate(original_code, patch)
    >>> if result.is_safe:
    ...     print("Safe to apply!")
    ... else:
    ...     print(f"UNSAFE: {result.reason}")

"""

import ast
import difflib
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypedDict


class SecurityIssueDict(TypedDict):
    """Type for serialized security issue."""

    type: str
    severity: str
    line: int | None
    description: str
    cwe: str | None


class RefactorResultDict(TypedDict, total=False):
    """Type-safe dictionary for RefactorSimulationResult.to_dict()."""

    status: str
    is_safe: bool
    reason: str | None
    confidence_score: float
    confidence_factors: dict[str, float]
    security_issues: list[SecurityIssueDict]
    structural_changes: dict[str, Any]
    warnings: list[str]
    test_impact: dict[str, Any]  # Complex nested structure, keep Any for now
    rollback_strategy: dict[str, Any]  # Complex nested structure, keep Any for now


class FileResultDict(TypedDict):
    """Type for individual file simulation result."""

    file_path: str
    status: str
    is_safe: bool
    reason: str | None
    security_issues: list[dict[str, Any]]
    structural_changes: dict[str, Any]
    warnings: list[str]


class MultiFileResultDict(TypedDict):
    """Type-safe dictionary for simulate_multi_file() return value."""

    file_results: list[FileResultDict]
    summary: dict[str, int]
    overall_verdict: str
    is_safe: bool
    cross_file_issues: list[dict[str, Any]]
    dependency_analysis: dict[str, Any]  # Complex nested structure, keep Any for now


class RefactorStatus(Enum):
    """Status of a refactor simulation."""

    SAFE = "safe"
    UNSAFE = "unsafe"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class SecurityIssue:
    """A security issue detected in refactored code."""

    type: str
    severity: str
    line: int | None
    description: str
    cwe: str | None = None


@dataclass
class RefactorResult:
    """Result of simulating a refactor.

    [20251231_FEATURE] v3.3.1 - Added confidence_score, test_impact, rollback_strategy fields.
    """

    status: RefactorStatus
    is_safe: bool
    patched_code: str
    reason: str | None = None
    security_issues: list[SecurityIssue] = field(default_factory=list)
    structural_changes: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    # [20251231_FEATURE] Pro tier: Confidence scoring
    confidence_score: float = 1.0  # 0.0-1.0, higher = more confident in verdict
    confidence_factors: dict[str, float] = field(default_factory=dict)
    # [20251231_FEATURE] Pro tier: Test impact analysis
    test_impact: dict[str, Any] = field(default_factory=dict)
    # [20251231_FEATURE] Enterprise tier: Rollback strategy
    rollback_strategy: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> RefactorResultDict:
        """Convert to dictionary for JSON serialization."""
        return {
            "status": self.status.value,
            "is_safe": self.is_safe,
            "reason": self.reason,
            "confidence_score": self.confidence_score,
            "confidence_factors": self.confidence_factors,
            "security_issues": [
                {
                    "type": issue.type,
                    "severity": issue.severity,
                    "line": issue.line,
                    "description": issue.description,
                    "cwe": issue.cwe,
                }
                for issue in self.security_issues
            ],
            "structural_changes": self.structural_changes,
            "warnings": self.warnings,
            "test_impact": self.test_impact,
            "rollback_strategy": self.rollback_strategy,
        }


class RefactorSimulator:
    """Simulate code refactors and verify safety.

    This class allows AI Agents to test their code changes in a
    sandboxed environment before actually applying them. It:

    1. Applies the patch to get the new code
    2. Runs security analysis on the patched code
    3. Compares structural changes (added/removed functions, etc.)
    4. Returns a verdict: SAFE, UNSAFE, WARNING, or ERROR

    Example:
        >>> simulator = RefactorSimulator()
        >>> result = simulator.simulate(
        ...     original_code='def foo(x): return x',
        ...     patch='@@ -1 +1 @@\\n-def foo(x): return x\\n+def foo(x): return eval(x)'
        ... )
        >>> result.is_safe
        False
        >>> result.reason
        'Introduced Code Injection vulnerability'
    """

    def __init__(self, strict_mode: bool = False):
        """Initialize the refactor simulator.

        Args:
            strict_mode: If True, treat warnings as unsafe
        """
        self.strict_mode = strict_mode

    def simulate(
        self,
        original_code: str,
        patch: str | None = None,
        new_code: str | None = None,
        language: str = "python",
        enable_type_checking: bool = False,
        enable_regression_prediction: bool = False,
        enable_test_impact: bool = False,
        enable_rollback_strategy: bool = False,
        project_root: str | None = None,
        file_path: str | None = None,
    ) -> RefactorResult:
        """Simulate applying a patch and check for safety.

        Provide either a unified diff patch OR the new code directly.

        [20251231_FEATURE] v3.3.1 - Added Pro/Enterprise tier parameters.

        Args:
            original_code: The original source code
            patch: Unified diff patch to apply (optional)
            new_code: New code to compare against (optional)
            language: Source language ("python", "javascript", "java")
            enable_type_checking: Enable Pro tier type checking (default: False)
            enable_regression_prediction: Enable Enterprise tier regression prediction (default: False)
            enable_test_impact: Enable Pro tier test impact analysis (default: False)
            enable_rollback_strategy: Enable Enterprise tier rollback strategy (default: False)
            project_root: Project root for regression/test analysis (optional)
            file_path: Path to the file being refactored (for test discovery)

        Returns:
            RefactorResult with safety verdict and details

        Raises:
            ValueError: If neither patch nor new_code provided
        """
        if patch is None and new_code is None:
            raise ValueError("Must provide either 'patch' or 'new_code'")

        # Apply patch to get new code
        patch_text = patch
        if new_code is None:
            try:
                new_code = self._apply_patch(original_code, patch)  # type: ignore[arg-type]
            except Exception as e:
                return RefactorResult(
                    status=RefactorStatus.ERROR,
                    is_safe=False,
                    patched_code="",
                    reason=f"Failed to apply patch: {str(e)}",
                )

        patch_security_issues: list[SecurityIssue] = []
        if patch_text:
            patch_security_issues = self._scan_patch_added_lines_for_security(patch_text, original_code)

        # Validate syntax
        syntax_error = self._check_syntax(new_code, language)
        if syntax_error:
            return RefactorResult(
                status=RefactorStatus.ERROR,
                is_safe=False,
                patched_code=new_code,
                reason=f"Syntax error in patched code: {syntax_error}",
                security_issues=patch_security_issues,
            )

        # Run security scan
        security_issues = self._scan_security(new_code, original_code, language)
        if patch_security_issues:
            security_issues.extend(patch_security_issues)

        # [20251230_FEATURE] Pro tier: Type checking
        if enable_type_checking and language == "python":
            type_errors = self._check_types_with_mypy(new_code)
            if type_errors:
                security_issues.extend(type_errors)

        # Check structural changes
        structural_changes = self._analyze_structural_changes(original_code, new_code, language)

        # [20251230_FEATURE] Enterprise tier: Regression prediction
        if enable_regression_prediction:
            regression_analysis = self._predict_regression_impact(original_code, new_code, project_root)
            structural_changes["regression_prediction"] = regression_analysis

        # Generate warnings
        warnings = self._generate_warnings(structural_changes)

        # Add regression warnings if applicable
        if enable_regression_prediction:
            regression = structural_changes.get("regression_prediction", {})
            if regression.get("risk_score", 0) > 0.5:
                warnings.append(regression.get("impact_summary", ""))

        # [20251231_FEATURE] Pro tier: Test impact analysis
        test_impact: dict[str, Any] = {}
        if enable_test_impact:
            test_impact = self._analyze_test_impact(
                original_code, new_code, structural_changes, project_root, file_path
            )
            if test_impact.get("affected_tests"):
                warnings.append(f"Test impact: {len(test_impact['affected_tests'])} tests may need updates")

        # [20251231_FEATURE] Enterprise tier: Rollback strategy generation
        rollback_strategy: dict[str, Any] = {}
        if enable_rollback_strategy:
            rollback_strategy = self._generate_rollback_strategy(original_code, new_code, structural_changes, file_path)

        # [20251231_FEATURE] Pro tier: Calculate confidence score
        confidence_score, confidence_factors = self._calculate_confidence(
            language,
            security_issues,
            structural_changes,
            enable_type_checking,
            enable_regression_prediction,
        )

        # Determine verdict
        status, is_safe, reason = self._determine_verdict(security_issues, structural_changes, warnings)

        return RefactorResult(
            status=status,
            is_safe=is_safe,
            patched_code=new_code,
            reason=reason,
            security_issues=security_issues,
            structural_changes=structural_changes,
            warnings=warnings,
            confidence_score=confidence_score,
            confidence_factors=confidence_factors,
            test_impact=test_impact,
            rollback_strategy=rollback_strategy,
        )

    def _scan_patch_added_lines_for_security(self, patch: str, original_code: str) -> list[SecurityIssue]:
        """Scan patch-added lines for obviously dangerous introductions.

        This is intentionally conservative: it only considers lines starting with '+'
        (excluding file headers like '+++') and only flags patterns not already
        present in the original code.
        """
        added_lines: list[str] = []
        for raw in patch.splitlines():
            stripped = raw.lstrip(" \t")
            if stripped.startswith("+++") or stripped.startswith("@@"):
                continue
            if stripped.startswith("+") and not stripped.startswith("+++"):
                added_lines.append(stripped[1:])

        added_text = "\n".join(added_lines)
        if not added_text.strip():
            return []

        issues: list[SecurityIssue] = []
        dangerous_patterns = [
            (
                "eval(",
                "Code Injection",
                "CWE-94",
                "high",
                "Introduced eval() via patch",
            ),
            (
                "exec(",
                "Code Injection",
                "CWE-94",
                "high",
                "Introduced exec() via patch",
            ),
            (
                "os.system(",
                "Command Injection",
                "CWE-78",
                "high",
                "Introduced os.system() via patch",
            ),
            (
                "subprocess.Popen(",
                "Command Injection",
                "CWE-78",
                "medium",
                "Introduced subprocess.Popen() via patch",
            ),
            (
                "pickle.loads(",
                "Deserialization",
                "CWE-502",
                "high",
                "Introduced pickle.loads() via patch",
            ),
        ]

        for pattern, vuln_type, cwe, severity, desc in dangerous_patterns:
            if pattern in added_text and pattern not in original_code:
                issues.append(
                    SecurityIssue(
                        type=vuln_type,
                        severity=severity,
                        line=None,
                        description=desc,
                        cwe=cwe,
                    )
                )

        return issues

    def simulate_inline(
        self,
        original_code: str,
        new_code: str,
        language: str = "python",
    ) -> RefactorResult:
        """Simulate by comparing original and new code directly.

        This is a convenience method when you have both versions.

        Args:
            original_code: Original source code
            new_code: New/modified source code
            language: Source language

        Returns:
            RefactorResult with safety analysis
        """
        return self.simulate(
            original_code=original_code,
            new_code=new_code,
            language=language,
        )

    def _apply_patch(self, original: str, patch: str) -> str:
        """Apply a unified diff patch to the original code."""
        # Parse the patch
        original_lines = original.splitlines(keepends=True)
        patched_lines = list(original_lines)

        # Simple unified diff parser
        hunk_pattern = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

        lines = patch.splitlines(keepends=True)
        i = 0
        offset = 0

        while i < len(lines):
            line = lines[i]

            # Find hunk header
            match = hunk_pattern.match(line)
            if match:
                old_start = int(match.group(1)) - 1  # 0-indexed
                i += 1

                # Process hunk
                current_old = old_start + offset
                deletions = []
                additions = []

                while i < len(lines) and not lines[i].startswith("@@"):
                    hunk_line = lines[i]
                    if hunk_line.startswith("-") and not hunk_line.startswith("---"):
                        deletions.append(current_old)
                        current_old += 1
                    elif hunk_line.startswith("+") and not hunk_line.startswith("+++"):
                        additions.append(hunk_line[1:])
                    elif hunk_line.startswith(" ") or hunk_line == "\n":
                        current_old += 1
                    i += 1

                # Apply deletions (in reverse to preserve indices)
                for del_idx in reversed(deletions):
                    if del_idx < len(patched_lines):
                        patched_lines.pop(del_idx)

                # Apply additions
                insert_point = old_start + offset
                for j, add_line in enumerate(additions):
                    patched_lines.insert(insert_point + j, add_line)

                offset += len(additions) - len(deletions)
            else:
                i += 1

        return "".join(patched_lines)

    def _check_syntax(self, code: str, language: str) -> str | None:
        """Check if code has valid syntax. Returns error message or None.

        [20251231_FEATURE] v3.3.1 - Added JavaScript/TypeScript syntax validation.
        """
        if language == "python":
            try:
                ast.parse(code)
                return None
            except SyntaxError as e:
                return f"Line {e.lineno}: {e.msg}"

        # [20251231_FEATURE] JavaScript/TypeScript syntax validation
        if language in ("javascript", "typescript"):
            try:
                # Try tree-sitter first (most accurate)
                from tree_sitter_languages import get_parser  # type: ignore[import]

                parser_lang = "typescript" if language == "typescript" else "javascript"
                parser = get_parser(parser_lang)  # type: ignore[call-arg]
                tree = parser.parse(code.encode("utf-8"))  # type: ignore[union-attr]

                # Check for ERROR nodes in the tree
                if tree.root_node.has_error:
                    # Find first error node for line number
                    error_node = self._find_first_error_node(tree.root_node)
                    if error_node:
                        line = error_node.start_point[0] + 1
                        return f"Line {line}: Syntax error"
                    return "Syntax error in code"
                return None
            except ImportError:
                # Fall back to regex-based heuristic validation
                return self._check_js_syntax_heuristic(code, language)
            except Exception as e:
                return f"Parser error: {str(e)}"

        # Java - try tree-sitter
        if language == "java":
            try:
                from tree_sitter_languages import get_parser  # type: ignore[import]

                parser = get_parser("java")  # type: ignore[call-arg]
                tree = parser.parse(code.encode("utf-8"))  # type: ignore[union-attr]

                if tree.root_node.has_error:
                    error_node = self._find_first_error_node(tree.root_node)
                    if error_node:
                        line = error_node.start_point[0] + 1
                        return f"Line {line}: Syntax error"
                    return "Syntax error in code"
                return None
            except ImportError:
                return None  # Can't validate without tree-sitter
            except Exception as e:
                return f"Parser error: {str(e)}"

        return None

    def _find_first_error_node(self, node: Any) -> Any:
        """Find the first ERROR node in a tree-sitter parse tree."""
        if node.type == "ERROR":
            return node
        for child in node.children:
            error = self._find_first_error_node(child)
            if error:
                return error
        return None

    def _check_js_syntax_heuristic(self, code: str, language: str) -> str | None:
        """Heuristic-based JavaScript/TypeScript syntax validation.

        [20251231_FEATURE] Fallback when tree-sitter is not available.
        Checks for common syntax errors without full parsing.
        """
        lines = code.splitlines()

        # Check for balanced braces, brackets, and parentheses
        brace_count = 0
        bracket_count = 0
        paren_count = 0

        # Track string literals to avoid counting braces inside strings
        in_string = False
        string_char = None
        in_template = False
        in_multiline_comment = False

        for line_num, line in enumerate(lines, 1):
            i = 0
            while i < len(line):
                char = line[i]

                # Handle multiline comments
                if in_multiline_comment:
                    if char == "*" and i + 1 < len(line) and line[i + 1] == "/":
                        in_multiline_comment = False
                        i += 1
                    i += 1
                    continue

                # Check for multiline comment start
                if char == "/" and i + 1 < len(line) and line[i + 1] == "*":
                    in_multiline_comment = True
                    i += 2
                    continue

                # Check for single-line comment
                if char == "/" and i + 1 < len(line) and line[i + 1] == "/":
                    break  # Rest of line is comment

                # Handle string literals
                if char in ('"', "'", "`"):
                    if not in_string:
                        in_string = True
                        string_char = char
                        if char == "`":
                            in_template = True
                    elif char == string_char:
                        # Check for escape
                        escape_count = 0
                        j = i - 1
                        while j >= 0 and line[j] == "\\":
                            escape_count += 1
                            j -= 1
                        if escape_count % 2 == 0:
                            in_string = False
                            in_template = False
                            string_char = None
                    i += 1
                    continue

                # Skip template literal expressions ${...}
                if in_template and char == "$" and i + 1 < len(line) and line[i + 1] == "{":
                    # Count nested braces in template
                    i += 2
                    template_brace = 1
                    while i < len(line) and template_brace > 0:
                        if line[i] == "{":
                            template_brace += 1
                        elif line[i] == "}":
                            template_brace -= 1
                        i += 1
                    continue

                if in_string:
                    i += 1
                    continue

                # Count braces
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count < 0:
                        return f"Line {line_num}: Unexpected '}}'"
                elif char == "[":
                    bracket_count += 1
                elif char == "]":
                    bracket_count -= 1
                    if bracket_count < 0:
                        return f"Line {line_num}: Unexpected ']'"
                elif char == "(":
                    paren_count += 1
                elif char == ")":
                    paren_count -= 1
                    if paren_count < 0:
                        return f"Line {line_num}: Unexpected ')'"

                i += 1

        # Check for unbalanced at end
        if brace_count > 0:
            return f"Unclosed '{{' - {brace_count} unclosed"
        if bracket_count > 0:
            return f"Unclosed '[' - {bracket_count} unclosed"
        if paren_count > 0:
            return f"Unclosed '(' - {paren_count} unclosed"
        if in_string:
            return "Unclosed string literal"
        if in_multiline_comment:
            return "Unclosed multiline comment"

        # Check for obvious syntax errors
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()

            # Empty or comment lines
            if not stripped or stripped.startswith("//") or stripped.startswith("/*"):
                continue

            # Check for incomplete statements (very basic)
            # Comma at end of object/array is OK in JS, so skip that check

            # Check for double operators
            if re.search(r"[+\-*/=<>!&|]{3,}(?!==)", stripped):
                # Allow === and !==
                if "===" not in stripped and "!==" not in stripped:
                    return f"Line {line_num}: Invalid operator sequence"

        return None

    def _scan_security(self, new_code: str, original_code: str, language: str) -> list[SecurityIssue]:
        """Scan for security vulnerabilities in the new code.

        [20251231_FEATURE] v3.3.1 - Added language-aware security scanning.
        """
        issues = []

        # For Python, prefer the built-in security analyzer (AST + taint + dangerous patterns).
        # For other languages, use pattern-based detection.
        if language == "python":
            try:
                from code_scalpel.security.analyzers import SecurityAnalyzer
                from code_scalpel.security.analyzers.taint_tracker import SecuritySink

                analyzer = SecurityAnalyzer()

                new_result = analyzer.analyze(new_code)
                old_result = analyzer.analyze(original_code)

                old_vulns = {(v.sink_type, v.sink_location) for v in getattr(old_result, "vulnerabilities", [])}

                severity_by_sink = {
                    SecuritySink.SHELL_COMMAND: "high",
                    SecuritySink.SQL_QUERY: "high",
                    SecuritySink.EVAL: "high",
                    SecuritySink.DESERIALIZATION: "high",
                    SecuritySink.SSRF: "high",
                    SecuritySink.WEAK_CRYPTO: "medium",
                    SecuritySink.HARDCODED_SECRET: "medium",
                    SecuritySink.HTML_OUTPUT: "medium",
                    SecuritySink.DOM_XSS: "medium",
                    SecuritySink.SSTI: "high",
                    SecuritySink.XXE: "high",
                }

                for vuln in getattr(new_result, "vulnerabilities", []):
                    vuln_key = (vuln.sink_type, vuln.sink_location)
                    if vuln_key in old_vulns:
                        continue

                    line = vuln.sink_location[0] if vuln.sink_location else None
                    issues.append(
                        SecurityIssue(
                            type=vuln.vulnerability_type,
                            severity=severity_by_sink.get(vuln.sink_type, "medium"),
                            line=line,
                            description=vuln.vulnerability_type,
                            cwe=vuln.cwe_id,
                        )
                    )
                return issues

            except Exception:
                # Fallback to pattern-based detection for Python
                pass

        # [20251231_FEATURE] Use pattern-based detection for all non-Python languages
        # or as fallback when SecurityAnalyzer fails
        issues.extend(self._pattern_security_scan(new_code, original_code, language))

        return issues

    def _pattern_security_scan(
        self, new_code: str, original_code: str, language: str = "python"
    ) -> list[SecurityIssue]:
        """Pattern-based security scan fallback.

        [20251231_FEATURE] v3.3.1 - Added JavaScript/TypeScript patterns.
        """
        issues = []

        # Common dangerous patterns across languages
        dangerous_patterns = [
            # Python patterns
            (
                "eval(",
                "Code Injection",
                "CWE-94",
                "high",
                "eval() can execute arbitrary code",
            ),
            (
                "exec(",
                "Code Injection",
                "CWE-94",
                "high",
                "exec() can execute arbitrary code",
            ),
            (
                "os.system(",
                "Command Injection",
                "CWE-78",
                "high",
                "os.system() can execute shell commands",
            ),
            (
                "subprocess.call(",
                "Command Injection",
                "CWE-78",
                "medium",
                "subprocess with shell=True is dangerous",
            ),
            (
                "cursor.execute(",
                "SQL Injection",
                "CWE-89",
                "high",
                "SQL query may be injectable",
            ),
            (
                "render_template_string(",
                "XSS",
                "CWE-79",
                "medium",
                "Template injection risk",
            ),
            (
                "pickle.loads(",
                "Deserialization",
                "CWE-502",
                "high",
                "Insecure deserialization",
            ),
            (
                "yaml.load(",
                "Deserialization",
                "CWE-502",
                "medium",
                "yaml.load() is unsafe, use safe_load()",
            ),
        ]

        # [20251231_FEATURE] JavaScript/TypeScript specific patterns
        if language in ("javascript", "typescript"):
            dangerous_patterns.extend(
                [
                    # XSS patterns
                    (
                        "innerHTML",
                        "XSS",
                        "CWE-79",
                        "high",
                        "innerHTML can introduce XSS vulnerabilities",
                    ),
                    (
                        "document.write(",
                        "XSS",
                        "CWE-79",
                        "high",
                        "document.write() can introduce XSS vulnerabilities",
                    ),
                    (
                        "outerHTML",
                        "XSS",
                        "CWE-79",
                        "high",
                        "outerHTML can introduce XSS vulnerabilities",
                    ),
                    # Code injection
                    (
                        "new Function(",
                        "Code Injection",
                        "CWE-94",
                        "high",
                        "new Function() can execute arbitrary code",
                    ),
                    (
                        'setTimeout("',
                        "Code Injection",
                        "CWE-94",
                        "high",
                        "setTimeout with string argument can execute arbitrary code",
                    ),
                    (
                        'setInterval("',
                        "Code Injection",
                        "CWE-94",
                        "high",
                        "setInterval with string argument can execute arbitrary code",
                    ),
                    # Command injection (Node.js)
                    (
                        "child_process.exec(",
                        "Command Injection",
                        "CWE-78",
                        "high",
                        "child_process.exec() can execute shell commands",
                    ),
                    (
                        "execSync(",
                        "Command Injection",
                        "CWE-78",
                        "high",
                        "execSync() can execute shell commands",
                    ),
                    # SQL injection
                    (
                        ".query(",
                        "SQL Injection",
                        "CWE-89",
                        "medium",
                        "SQL query may be injectable - use parameterized queries",
                    ),
                    # Prototype pollution
                    (
                        "__proto__",
                        "Prototype Pollution",
                        "CWE-1321",
                        "high",
                        "Prototype pollution vulnerability",
                    ),
                ]
            )

        for line_num, line in enumerate(new_code.splitlines(), 1):
            for pattern, vuln_type, cwe, severity, desc in dangerous_patterns:
                if pattern in line and pattern not in original_code:
                    issues.append(
                        SecurityIssue(
                            type=vuln_type,
                            severity=severity,
                            line=line_num,
                            description=f"Introduced {desc}",
                            cwe=cwe,
                        )
                    )

        return issues

    def _analyze_structural_changes(self, original: str, new_code: str, language: str) -> dict[str, Any]:
        """Analyze structural changes between versions.

        [20251231_FEATURE] v3.3.1 - Added JavaScript/TypeScript structural analysis.
        """
        changes = {
            "functions_added": [],
            "functions_removed": [],
            "functions_modified": [],
            "classes_added": [],
            "classes_removed": [],
            "imports_added": [],
            "imports_removed": [],
            "lines_added": 0,
            "lines_removed": 0,
        }

        if language == "python":
            try:
                old_tree = ast.parse(original)
                new_tree = ast.parse(new_code)

                old_funcs = {n.name for n in ast.walk(old_tree) if isinstance(n, ast.FunctionDef)}
                new_funcs = {n.name for n in ast.walk(new_tree) if isinstance(n, ast.FunctionDef)}

                old_classes = {n.name for n in ast.walk(old_tree) if isinstance(n, ast.ClassDef)}
                new_classes = {n.name for n in ast.walk(new_tree) if isinstance(n, ast.ClassDef)}

                old_imports = set()
                new_imports = set()

                for node in ast.walk(old_tree):
                    if isinstance(node, ast.Import):
                        old_imports.update(a.name for a in node.names)
                    elif isinstance(node, ast.ImportFrom):
                        old_imports.update(f"{node.module}.{a.name}" for a in node.names)

                for node in ast.walk(new_tree):
                    if isinstance(node, ast.Import):
                        new_imports.update(a.name for a in node.names)
                    elif isinstance(node, ast.ImportFrom):
                        new_imports.update(f"{node.module}.{a.name}" for a in node.names)

                changes["functions_added"] = list(new_funcs - old_funcs)
                changes["functions_removed"] = list(old_funcs - new_funcs)
                changes["classes_added"] = list(new_classes - old_classes)
                changes["classes_removed"] = list(old_classes - new_classes)
                changes["imports_added"] = list(new_imports - old_imports)
                changes["imports_removed"] = list(old_imports - new_imports)

            except SyntaxError:
                pass

        # [20251231_FEATURE] JavaScript/TypeScript structural analysis
        elif language in ("javascript", "typescript"):
            old_structure = self._extract_js_structure(original)
            new_structure = self._extract_js_structure(new_code)

            changes["functions_added"] = list(new_structure["functions"] - old_structure["functions"])
            changes["functions_removed"] = list(old_structure["functions"] - new_structure["functions"])
            changes["classes_added"] = list(new_structure["classes"] - old_structure["classes"])
            changes["classes_removed"] = list(old_structure["classes"] - new_structure["classes"])
            changes["imports_added"] = list(new_structure["imports"] - old_structure["imports"])
            changes["imports_removed"] = list(old_structure["imports"] - new_structure["imports"])

        # Count line changes
        diff = list(difflib.unified_diff(original.splitlines(), new_code.splitlines(), lineterm=""))

        for line in diff:
            if line.startswith("+") and not line.startswith("+++"):
                changes["lines_added"] += 1
            elif line.startswith("-") and not line.startswith("---"):
                changes["lines_removed"] += 1

        return changes

    def _extract_js_structure(self, code: str) -> dict[str, set]:
        """Extract structural information from JavaScript/TypeScript code.

        [20251231_FEATURE] v3.3.1 - JavaScript/TypeScript structure extraction.
        Uses tree-sitter if available, falls back to regex patterns.
        """
        structure = {
            "functions": set(),
            "classes": set(),
            "imports": set(),
        }

        try:
            # Try tree-sitter first
            from tree_sitter_languages import get_parser  # type: ignore[import]

            parser = get_parser("typescript")  # type: ignore[call-arg]  # TypeScript parser handles JS too
            tree = parser.parse(code.encode("utf-8"))  # type: ignore[union-attr]

            self._extract_js_symbols_from_tree(tree.root_node, structure)  # type: ignore[union-attr]
            return structure
        except ImportError:
            pass
        except Exception:
            pass

        # Fallback to regex-based extraction
        return self._extract_js_structure_regex(code)

    def _extract_js_symbols_from_tree(self, node, structure: dict[str, set]) -> None:
        """Extract symbols from tree-sitter parse tree.

        [20251231_FEATURE] Tree-sitter based JS/TS symbol extraction.
        """
        # Function declarations
        if node.type in (
            "function_declaration",
            "method_definition",
            "arrow_function",
            "function_expression",
        ):
            # Find the function name
            for child in node.children:
                if child.type == "identifier":
                    structure["functions"].add(child.text.decode("utf-8"))
                    break
                # For methods, look in property_identifier
                if child.type == "property_identifier":
                    structure["functions"].add(child.text.decode("utf-8"))
                    break

        # Variable declarations with arrow functions
        if node.type == "variable_declarator":
            name_node = None
            has_function = False
            for child in node.children:
                if child.type == "identifier":
                    name_node = child
                if child.type == "arrow_function" or child.type == "function_expression":
                    has_function = True
            if name_node and has_function:
                structure["functions"].add(name_node.text.decode("utf-8"))

        # Class declarations
        if node.type == "class_declaration":
            for child in node.children:
                if child.type == "type_identifier" or child.type == "identifier":
                    structure["classes"].add(child.text.decode("utf-8"))
                    break

        # Import statements
        if node.type in ("import_statement", "import_declaration"):
            # Extract the module being imported
            for child in node.children:
                if child.type == "string" or child.type == "string_fragment":
                    module = child.text.decode("utf-8").strip("'\"")
                    structure["imports"].add(module)

        # Recurse into children
        for child in node.children:
            self._extract_js_symbols_from_tree(child, structure)

    def _extract_js_structure_regex(self, code: str) -> dict[str, set]:
        """Regex-based fallback for JS/TS structure extraction.

        [20251231_FEATURE] v3.3.1 - Fallback when tree-sitter unavailable.
        """
        structure = {
            "functions": set(),
            "classes": set(),
            "imports": set(),
        }

        # Function declarations: function name(...) or async function name(...)
        func_pattern = r"\b(?:async\s+)?function\s+(\w+)\s*\("
        for match in re.finditer(func_pattern, code):
            structure["functions"].add(match.group(1))

        # Arrow functions assigned to const/let/var (handles TypeScript typed params)
        # Matches: const add = (a: number, b: number): number => ...
        # Matches: const add = async (a, b) => ...
        # Matches: const add = x => ...
        arrow_pattern = r"\b(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[a-zA-Z_]\w*)\s*(?::\s*\w+)?\s*=>"
        for match in re.finditer(arrow_pattern, code):
            structure["functions"].add(match.group(1))

        # Function expressions assigned to const/let/var
        func_expr_pattern = r"\b(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?function\s*\("
        for match in re.finditer(func_expr_pattern, code):
            structure["functions"].add(match.group(1))

        # Class declarations
        class_pattern = r"\bclass\s+(\w+)"
        for match in re.finditer(class_pattern, code):
            structure["classes"].add(match.group(1))

        # Import statements: import ... from 'module' or import 'module'
        import_pattern = r"""import\s+.*?from\s+['"]([^'"]+)['"]|import\s+['"]([^'"]+)['"]"""
        for match in re.finditer(import_pattern, code):
            module = match.group(1) or match.group(2)
            if module:
                structure["imports"].add(module)

        # Require statements: require('module')
        require_pattern = r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)"""
        for match in re.finditer(require_pattern, code):
            structure["imports"].add(match.group(1))

        return structure

    def _generate_warnings(self, structural_changes: dict[str, Any]) -> list[str]:
        """Generate warnings based on structural changes."""
        warnings = []

        if structural_changes.get("functions_removed"):
            funcs = ", ".join(structural_changes["functions_removed"])
            warnings.append(f"Removed functions: {funcs}")

        if structural_changes.get("classes_removed"):
            classes = ", ".join(structural_changes["classes_removed"])
            warnings.append(f"Removed classes: {classes}")

        lines_added = structural_changes.get("lines_added", 0)
        lines_removed = structural_changes.get("lines_removed", 0)

        if lines_removed > lines_added * 2:
            warnings.append(f"Large deletion: {lines_removed} lines removed vs {lines_added} added")

        if lines_added > 100:
            warnings.append(f"Large addition: {lines_added} new lines")

        return warnings

    def _determine_verdict(
        self,
        security_issues: list[SecurityIssue],
        structural_changes: dict[str, Any],
        warnings: list[str],
    ) -> tuple[RefactorStatus, bool, str | None]:
        """Determine the final verdict."""
        # High severity security issues = UNSAFE
        high_severity = [i for i in security_issues if i.severity == "high"]
        if high_severity:
            issue = high_severity[0]
            return (
                RefactorStatus.UNSAFE,
                False,
                f"Introduced {issue.type} vulnerability: {issue.description}",
            )

        # Medium severity = UNSAFE in strict mode, WARNING otherwise
        medium_severity = [i for i in security_issues if i.severity == "medium"]
        if medium_severity:
            issue = medium_severity[0]
            if self.strict_mode:
                return (
                    RefactorStatus.UNSAFE,
                    False,
                    f"Introduced {issue.type} vulnerability: {issue.description}",
                )
            return (
                RefactorStatus.WARNING,
                True,  # Still safe but with warning
                f"Potential {issue.type} issue: {issue.description}",
            )

        # Warnings without security issues
        if warnings and self.strict_mode:
            return (
                RefactorStatus.WARNING,
                True,
                warnings[0],
            )

        # All clear
        return (RefactorStatus.SAFE, True, None)

    def _calculate_confidence(
        self,
        language: str,
        security_issues: list[SecurityIssue],
        structural_changes: dict[str, Any],
        type_checking_enabled: bool,
        regression_enabled: bool,
    ) -> tuple[float, dict[str, float]]:
        """
        Pro tier: Calculate confidence score for the safety verdict.

        [20251231_FEATURE] v3.3.1 - Pro tier confidence scoring.

        Args:
            language: Source language
            security_issues: Detected security issues
            structural_changes: Structural analysis results
            type_checking_enabled: Whether type checking was run
            regression_enabled: Whether regression analysis was run

        Returns:
            Tuple of (confidence_score, confidence_factors)
        """
        factors: dict[str, float] = {}

        # Base confidence by language (AST-based languages higher)
        language_confidence = {
            "python": 0.95,
            "javascript": 0.80,
            "typescript": 0.85,
            "java": 0.90,
        }
        factors["language_support"] = language_confidence.get(language, 0.5)

        # Syntax validation factor (always 1.0 if we got here - no syntax error)
        factors["syntax_validation"] = 1.0

        # Security analysis factor
        if security_issues:
            # Lower confidence if we detected issues (they might be false positives)
            high_severity = len([i for i in security_issues if i.severity == "high"])
            medium_severity = len([i for i in security_issues if i.severity == "medium"])
            # More issues = less confident in the "unsafe" verdict (could be FPs)
            factors["security_analysis"] = max(0.6, 1.0 - (high_severity * 0.1 + medium_severity * 0.05))
        else:
            factors["security_analysis"] = 0.9  # No issues found

        # Structural analysis factor
        has_structural_data = bool(
            structural_changes.get("functions_added")
            or structural_changes.get("functions_removed")
            or structural_changes.get("classes_added")
            or structural_changes.get("classes_removed")
        )
        factors["structural_analysis"] = 0.95 if has_structural_data else 0.7

        # Type checking bonus (Pro tier)
        if type_checking_enabled:
            factors["type_checking"] = 0.95
        else:
            factors["type_checking"] = 0.0  # Not enabled

        # Regression analysis bonus (Enterprise tier)
        if regression_enabled:
            regression = structural_changes.get("regression_prediction", {})
            risk_score = regression.get("risk_score", 0.5)
            # Higher risk = lower confidence in "safe" verdict
            factors["regression_analysis"] = max(0.5, 1.0 - risk_score)
        else:
            factors["regression_analysis"] = 0.0  # Not enabled

        # Calculate weighted average (exclude 0 values)
        active_factors = {k: v for k, v in factors.items() if v > 0}
        if active_factors:
            confidence = sum(active_factors.values()) / len(active_factors)
        else:
            confidence = 0.5  # Fallback

        return round(confidence, 3), factors

    def _analyze_test_impact(
        self,
        original_code: str,
        new_code: str,
        structural_changes: dict[str, Any],
        project_root: str | None,
        file_path: str | None,
    ) -> dict[str, Any]:
        """
        Pro tier: Analyze which tests would be impacted by the refactor.

        [20251231_FEATURE] v3.3.1 - Pro tier test impact analysis.

        Args:
            original_code: Original source code
            new_code: Refactored source code
            structural_changes: Structural analysis results
            project_root: Project root for test discovery
            file_path: Path to the file being refactored

        Returns:
            Dictionary with affected tests and recommendations
        """
        from pathlib import Path

        impact = {
            "affected_tests": [],
            "test_files_to_check": [],
            "coverage_impact": "unknown",
            "recommendations": [],
        }

        # Get changed function/class names
        changed_symbols = set()
        changed_symbols.update(structural_changes.get("functions_added", []))
        changed_symbols.update(structural_changes.get("functions_removed", []))
        changed_symbols.update(structural_changes.get("classes_added", []))
        changed_symbols.update(structural_changes.get("classes_removed", []))

        if not changed_symbols:
            impact["recommendations"].append("No structural changes detected - tests likely unaffected")
            return impact

        # If we have project_root, search for related tests
        if project_root:
            root = Path(project_root)
            if root.exists():
                # Find test files
                test_patterns = ["**/test_*.py", "**/tests/*.py", "**/*_test.py"]
                test_files: list[Path] = []

                for pattern in test_patterns:
                    test_files.extend(root.glob(pattern))

                # Search test files for references to changed symbols
                for test_file in test_files[:50]:  # Limit to 50 files
                    try:
                        content = test_file.read_text(encoding="utf-8", errors="ignore")
                        for symbol in changed_symbols:
                            if symbol in content:
                                rel_path = str(test_file.relative_to(root))
                                if rel_path not in impact["test_files_to_check"]:
                                    impact["test_files_to_check"].append(rel_path)

                                # Try to find specific test functions
                                test_funcs = re.findall(
                                    rf"\bdef\s+(test_\w*{re.escape(symbol)}\w*)\s*\(",
                                    content,
                                    re.IGNORECASE,
                                )
                                for func in test_funcs:
                                    impact["affected_tests"].append(
                                        {
                                            "test_name": func,
                                            "file": rel_path,
                                            "reason": f"References changed symbol '{symbol}'",
                                        }
                                    )
                    except Exception:
                        continue

        # If file_path provided, derive test file names
        if file_path:
            file_name = Path(file_path).stem
            potential_test_files = [
                f"test_{file_name}.py",
                f"{file_name}_test.py",
                f"tests/test_{file_name}.py",
            ]
            impact["recommendations"].append(f"Check these test files: {', '.join(potential_test_files)}")

        # Generate recommendations
        if impact["affected_tests"]:
            impact["recommendations"].append(f"Run {len(impact['affected_tests'])} affected tests before merging")

        if structural_changes.get("functions_removed"):
            impact["recommendations"].append(
                "Removed functions may cause test failures - update or remove related tests"
            )

        if structural_changes.get("functions_added"):
            impact["recommendations"].append("New functions should have corresponding tests")

        return impact

    def _generate_rollback_strategy(
        self,
        original_code: str,
        new_code: str,
        structural_changes: dict[str, Any],
        file_path: str | None,
    ) -> dict[str, Any]:
        """
        Enterprise tier: Generate a rollback strategy for the refactor.

        [20251231_FEATURE] v3.3.1 - Enterprise tier rollback strategy generation.

        Args:
            original_code: Original source code
            new_code: Refactored source code
            structural_changes: Structural analysis results
            file_path: Path to the file being refactored

        Returns:
            Dictionary with rollback steps and recommendations
        """
        import hashlib
        from datetime import datetime, timezone

        strategy = {
            "rollback_type": "single_file",
            "original_checksum": hashlib.sha256(original_code.encode()).hexdigest()[:12],
            "new_checksum": hashlib.sha256(new_code.encode()).hexdigest()[:12],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "steps": [],
            "verification_commands": [],
            "estimated_risk": "low",
        }

        # Determine risk level based on structural changes
        removed_funcs = len(structural_changes.get("functions_removed", []))
        removed_classes = len(structural_changes.get("classes_removed", []))
        lines_removed = structural_changes.get("lines_removed", 0)

        if removed_funcs > 3 or removed_classes > 1:
            strategy["estimated_risk"] = "high"
        elif removed_funcs > 0 or lines_removed > 50:
            strategy["estimated_risk"] = "medium"

        # Generate rollback steps
        file_name = file_path or "file"

        strategy["steps"] = [
            {
                "step": 1,
                "action": "Create backup of current state",
                "command": f"cp {file_name} {file_name}.rollback_backup",
            },
            {
                "step": 2,
                "action": "Restore original code",
                "command": f"git checkout HEAD~1 -- {file_name}",
                "alternative": "Restore from backup or apply reverse patch",
            },
            {
                "step": 3,
                "action": "Verify restoration",
                "command": f"git diff {file_name}",
            },
            {
                "step": 4,
                "action": "Run tests to confirm rollback",
                "command": "pytest tests/ -x",
            },
        ]

        # Add verification commands
        strategy["verification_commands"] = [
            f"sha256sum {file_name}  # Should match: {strategy['original_checksum']}...",
            "git status  # Check for uncommitted changes",
            "python -m py_compile {file_name}  # Verify syntax",
        ]

        # Generate reverse patch
        reverse_diff = list(
            difflib.unified_diff(
                new_code.splitlines(keepends=True),
                original_code.splitlines(keepends=True),
                fromfile=f"a/{file_name}",
                tofile=f"b/{file_name}",
            )
        )
        strategy["reverse_patch"] = "".join(reverse_diff)

        # Add warnings for high-risk rollbacks
        if strategy["estimated_risk"] == "high":
            strategy["warnings"] = [
                "High-risk rollback: Multiple functions/classes affected",
                "Ensure all dependent code is also rolled back",
                "Consider incremental rollback instead of full revert",
            ]

        return strategy

    def simulate_multi_file(
        self,
        file_changes: list[dict[str, str]],
        language: str = "python",
        enable_type_checking: bool = False,
        enable_regression_prediction: bool = False,
        project_root: str | None = None,
    ) -> MultiFileResultDict:
        """
        Enterprise tier: Simulate refactors across multiple files.

        [20251231_FEATURE] v3.3.1 - Enterprise tier multi-file refactor simulation.

        Args:
            file_changes: List of dicts with 'file_path', 'original_code', 'new_code'
            language: Source language
            enable_type_checking: Enable Pro tier type checking
            enable_regression_prediction: Enable Enterprise regression prediction
            project_root: Project root for analysis

        Returns:
            TypedDict with per-file results and aggregated summary
        """
        results: MultiFileResultDict = {
            "file_results": [],
            "summary": {
                "total_files": len(file_changes),
                "safe_count": 0,
                "unsafe_count": 0,
                "warning_count": 0,
                "error_count": 0,
            },
            "overall_verdict": RefactorStatus.SAFE.value,
            "is_safe": True,
            "cross_file_issues": [],
            "dependency_analysis": {},
        }

        # Track all changed symbols across files for cross-file analysis
        all_removed_functions: set[str] = set()
        all_added_functions: set[str] = set()
        all_removed_classes: set[str] = set()
        all_added_classes: set[str] = set()

        # Simulate each file
        for change in file_changes:
            file_path = change.get("file_path", "unknown")
            original = change.get("original_code", "")
            new = change.get("new_code", "")

            result = self.simulate(
                original_code=original,
                new_code=new,
                language=language,
                enable_type_checking=enable_type_checking,
                enable_regression_prediction=enable_regression_prediction,
                project_root=project_root,
                file_path=file_path,
            )

            # Track per-file result
            file_result: FileResultDict = {
                "file_path": file_path,
                "status": result.status.value,
                "is_safe": result.is_safe,
                "reason": result.reason,
                "security_issues": [
                    # [20260101_BUGFIX] Safe attribute access for SecurityIssue objects
                    (
                        getattr(
                            i,
                            "to_dict",
                            lambda: {
                                "type": getattr(i, "type", "unknown"),
                                "severity": getattr(i, "severity", "unknown"),
                                "line": getattr(i, "line", 0),
                                "description": getattr(i, "description", ""),
                                "cwe": getattr(i, "cwe", ""),
                            },
                        )()
                        if callable(getattr(i, "to_dict", None))
                        else {
                            "type": getattr(i, "type", "unknown"),
                            "severity": getattr(i, "severity", "unknown"),
                            "line": getattr(i, "line", 0),
                            "description": getattr(i, "description", ""),
                            "cwe": getattr(i, "cwe", ""),
                        }
                    )
                    for i in result.security_issues
                ],
                "structural_changes": result.structural_changes,
                "warnings": result.warnings,
            }
            results["file_results"].append(file_result)

            # Update summary counts
            if result.status == RefactorStatus.SAFE:
                results["summary"]["safe_count"] += 1
            elif result.status == RefactorStatus.UNSAFE:
                results["summary"]["unsafe_count"] += 1
            elif result.status == RefactorStatus.WARNING:
                results["summary"]["warning_count"] += 1
            else:
                results["summary"]["error_count"] += 1

            # Collect symbols for cross-file analysis
            sc = result.structural_changes
            all_removed_functions.update(sc.get("functions_removed", []))
            all_added_functions.update(sc.get("functions_added", []))
            all_removed_classes.update(sc.get("classes_removed", []))
            all_added_classes.update(sc.get("classes_added", []))

        # Cross-file dependency analysis
        # Check if removed symbols are used in other files
        for change in file_changes:
            new_code = change.get("new_code", "")
            file_path = change.get("file_path", "unknown")

            # Check if this file uses any removed functions from other files
            for func in all_removed_functions:
                if func in new_code and func not in all_added_functions:
                    results["cross_file_issues"].append(
                        {
                            "type": "missing_dependency",
                            "file": file_path,
                            "symbol": func,
                            "description": f"File uses function '{func}' which is removed in another file",
                        }
                    )

        # Determine overall verdict
        if results["summary"]["unsafe_count"] > 0:
            results["overall_verdict"] = RefactorStatus.UNSAFE.value
            results["is_safe"] = False
        elif results["summary"]["error_count"] > 0:
            results["overall_verdict"] = RefactorStatus.ERROR.value
            results["is_safe"] = False
        elif results["summary"]["warning_count"] > 0 or results["cross_file_issues"]:
            results["overall_verdict"] = RefactorStatus.WARNING.value
            results["is_safe"] = True  # Warnings are still "safe" unless in strict mode

        # Add cross-file dependency summary
        results["dependency_analysis"] = {
            "removed_functions_total": list(all_removed_functions),
            "added_functions_total": list(all_added_functions),
            "removed_classes_total": list(all_removed_classes),
            "added_classes_total": list(all_added_classes),
            "potential_broken_imports": len(results["cross_file_issues"]),
        }

        return results

    def _check_types_with_mypy(self, code: str) -> list[SecurityIssue]:
        """
        Pro tier: Run mypy type checking on the code.

        [20251230_FEATURE] v3.5.0 - Pro tier build check with type validation.

        Args:
            code: Python source code to type check

        Returns:
            List of type errors as SecurityIssue objects
        """
        import subprocess
        import tempfile
        from pathlib import Path

        type_errors: list[SecurityIssue] = []

        try:
            # Write code to temporary file for mypy
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                temp_path = Path(f.name)
                f.write(code)

            try:
                # Run mypy on the file
                result = subprocess.run(
                    [
                        "mypy",
                        "--no-error-summary",
                        "--show-column-numbers",
                        str(temp_path),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                # Parse mypy output
                for line in result.stdout.splitlines():
                    # Format: filename:line:col: error: message
                    match = re.match(r".+:(\d+):(\d+): error: (.+)", line)
                    if match:
                        line_no = int(match.group(1))
                        message = match.group(3)

                        type_errors.append(
                            SecurityIssue(
                                type="Type Error",
                                severity="medium",
                                line=line_no,
                                description=f"Type checking error: {message}",
                                cwe=None,
                            )
                        )

            finally:
                # Clean up temp file
                temp_path.unlink(missing_ok=True)

        except FileNotFoundError:
            # mypy not installed - skip type checking
            pass
        except subprocess.TimeoutExpired:
            # Timeout - skip
            pass
        except Exception:
            # Any other error - skip gracefully
            pass

        return type_errors

    def _predict_regression_impact(
        self, original_code: str, new_code: str, project_root: str | None = None
    ) -> dict[str, Any]:
        """
        Enterprise tier: Predict which features might break using call graph analysis.

        [20251230_FEATURE] v3.5.0 - Enterprise tier regression prediction with AI+Graph.

        Args:
            original_code: Original source code
            new_code: Refactored source code
            project_root: Project root for call graph analysis

        Returns:
            Dictionary with regression predictions and risk assessment
        """
        from pathlib import Path

        predictions = {
            "at_risk_functions": [],
            "breaking_changes": [],
            "risk_score": 0.0,
            "impact_summary": "",
            "recommended_tests": [],
        }

        try:
            # Parse both versions to identify changed functions
            old_tree = ast.parse(original_code)
            new_tree = ast.parse(new_code)

            # Extract function signatures
            old_sigs = self._extract_function_signatures(old_tree)
            new_sigs = self._extract_function_signatures(new_tree)

            # Identify signature changes
            changed_functions = []
            for func_name in old_sigs.keys():
                if func_name in new_sigs:
                    if old_sigs[func_name] != new_sigs[func_name]:
                        changed_functions.append(func_name)
                else:
                    # Function removed
                    changed_functions.append(func_name)
                    predictions["breaking_changes"].append(
                        {
                            "type": "function_removed",
                            "name": func_name,
                            "severity": "high",
                        }
                    )

            # If project_root provided, analyze call graph
            if project_root and changed_functions:
                try:
                    from code_scalpel.ast_tools.call_graph import CallGraphBuilder

                    root_path = Path(project_root)
                    if root_path.exists():
                        builder = CallGraphBuilder(root_path)
                        graph = builder.build_with_details(entry_point=None, depth=5, max_nodes=500)

                        # Find callers of changed functions
                        for func_name in changed_functions:
                            callers = self._find_callers_in_graph(func_name, graph)
                            if callers:
                                predictions["at_risk_functions"].extend(
                                    [
                                        {
                                            "name": caller,
                                            "reason": f"Calls changed function '{func_name}'",
                                            "risk": "medium",
                                        }
                                        for caller in callers
                                    ]
                                )

                                # Recommend tests
                                predictions["recommended_tests"].append(f"test_{func_name}_integration")

                except ImportError:
                    # Call graph not available - use simpler analysis
                    pass
                except Exception:
                    # Error in graph analysis - skip
                    pass

            # Calculate risk score
            num_breaking = len(predictions["breaking_changes"])
            num_at_risk = len(predictions["at_risk_functions"])
            num_changed = len(changed_functions)

            # Risk formula: (breaking * 0.5) + (at_risk * 0.3) + (changed * 0.2)
            predictions["risk_score"] = min(1.0, (num_breaking * 0.5 + num_at_risk * 0.3 + num_changed * 0.2) / 10)

            # Generate summary
            if predictions["risk_score"] > 0.7:
                predictions["impact_summary"] = "HIGH RISK: Significant breaking changes detected"
            elif predictions["risk_score"] > 0.4:
                predictions["impact_summary"] = "MEDIUM RISK: Some functions may be affected"
            elif predictions["risk_score"] > 0:
                predictions["impact_summary"] = "LOW RISK: Minor changes detected"
            else:
                predictions["impact_summary"] = "SAFE: No breaking changes detected"

        except Exception as e:
            predictions["impact_summary"] = f"Analysis error: {str(e)}"

        return predictions

    def _extract_function_signatures(self, tree: ast.AST) -> dict[str, str]:
        """Extract function signatures from AST."""
        signatures = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Build signature string: name(arg1: type1, arg2: type2) -> return_type
                args_parts = []
                for arg in node.args.args:
                    arg_str = arg.arg
                    if arg.annotation:
                        arg_str += f": {ast.unparse(arg.annotation)}"
                    args_parts.append(arg_str)

                sig = f"{node.name}({', '.join(args_parts)})"

                if node.returns:
                    sig += f" -> {ast.unparse(node.returns)}"

                signatures[node.name] = sig

        return signatures

    def _find_callers_in_graph(self, func_name: str, graph: Any) -> list[str]:
        """Find all functions that call the specified function in the call graph."""
        callers = []

        try:
            # Search for edges that target func_name
            for edge in graph.edges:
                if func_name in edge.callee:
                    caller_name = edge.caller.split(":")[-1]
                    if caller_name not in callers:
                        callers.append(caller_name)
        except AttributeError:
            # Graph structure different - skip
            pass

        return callers
