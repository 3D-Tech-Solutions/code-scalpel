#!/usr/bin/env python3
"""
JavaScript Code Quality Analyzer - Comprehensive code quality and pattern detection.

Implements advanced code quality checks, anti-pattern detection, and
code smell identification for JavaScript/TypeScript code.
Features:
    Code Smell Detection:
        - Callback hell / deep nesting detection
        - Magic number/string detection
        - Long function detection (configurable threshold)
        - Too many parameters detection
        - Empty catch block detection
        - Console.log/debugger statement detection
        - Nested ternary detection
        - Complex boolean condition detection

    Anti-Pattern Detection:
        - Promise executor async (anti-pattern)
        - Unnecessary return await
        - Duplicate code similarity hashing

    Comment Extraction:
        - Author and priority extraction

    Framework Detection:
        - React (components, hooks, JSX)
        - Vue (Options API, Composition API)
        - Angular (components, decorators)
        - Express.js / Next.js / NestJS
        - jQuery, Redux, Lodash

    Module Analysis:
        - CommonJS vs ES6 module detection
        - Import/export counting
        - Dynamic import detection
"""

import hashlib
import re
from dataclasses import dataclass, field
from enum import Enum


class CodeSmellType(Enum):
    """Types of code smells detected."""

    CALLBACK_HELL = "callback_hell"
    MAGIC_NUMBER = "magic_number"
    MAGIC_STRING = "magic_string"
    LONG_FUNCTION = "long_function"
    LONG_FILE = "long_file"
    TOO_MANY_PARAMS = "too_many_params"
    EMPTY_CATCH = "empty_catch"
    CONSOLE_LOG = "console_log"
    DEBUGGER = "debugger"
    DEEP_NESTING = "deep_nesting"
    DEAD_CODE = "dead_code"
    UNREACHABLE_CODE = "unreachable_code"
    TODO_COMMENT = "todo_comment"
    FIXME_COMMENT = "fixme_comment"
    HACK_COMMENT = "hack_comment"
    UNUSED_VARIABLE = "unused_variable"
    UNUSED_IMPORT = "unused_import"
    DUPLICATE_CODE = "duplicate_code"
    COMPLEX_CONDITION = "complex_condition"
    NESTED_TERNARY = "nested_ternary"
    PROMISE_EXECUTOR_ASYNC = "promise_executor_async"
    FLOATING_PROMISE = "floating_promise"
    THIS_IN_ARROW = "this_in_arrow"
    NO_RETURN_AWAIT = "no_return_await"


class CodeSmellSeverity(Enum):
    """Severity levels for code smells."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FrameworkType(Enum):
    """Detected JavaScript frameworks."""

    REACT = "react"
    REACT_NATIVE = "react_native"
    VUE = "vue"
    ANGULAR = "angular"
    SVELTE = "svelte"
    EXPRESS = "express"
    NEXTJS = "nextjs"
    NUXT = "nuxt"
    NESTJS = "nestjs"
    FASTIFY = "fastify"
    KOA = "koa"
    JQUERY = "jquery"
    LODASH = "lodash"
    REDUX = "redux"
    MOBX = "mobx"
    GRAPHQL = "graphql"
    ELECTRON = "electron"
    DENO = "deno"


class ModuleType(Enum):
    """JavaScript module system type."""

    COMMONJS = "commonjs"
    ES6 = "es6"
    AMD = "amd"
    UMD = "umd"
    MIXED = "mixed"
    UNKNOWN = "unknown"


@dataclass
class CodeSmell:
    """Represents a detected code smell."""

    smell_type: CodeSmellType
    severity: CodeSmellSeverity
    message: str
    line: int
    column: int = 0
    end_line: int | None = None
    end_column: int | None = None
    code_snippet: str | None = None
    recommendation: str | None = None
    auto_fixable: bool = False


@dataclass
class TodoComment:

    comment_type: str  # "TODO", "FIXME", "HACK", "XXX", "NOTE"
    message: str
    line: int
    author: str | None = None
    priority: str | None = None


@dataclass
class DuplicateCodeBlock:
    """Represents a detected duplicate code block."""

    hash_signature: str
    lines_start: list[int]  # Starting lines of each duplicate
    lines_end: list[int]  # Ending lines of each duplicate
    line_count: int
    similarity: float  # 0.0 to 1.0


@dataclass
class FrameworkDetection:
    """Framework detection result."""

    framework: FrameworkType
    confidence: float  # 0.0 to 1.0
    indicators: list[str]  # What triggered detection
    version_hint: str | None = None


@dataclass
class ModuleAnalysis:
    """Module system analysis result."""

    module_type: ModuleType
    commonjs_requires: int = 0
    commonjs_exports: int = 0
    es6_imports: int = 0
    es6_exports: int = 0
    dynamic_imports: int = 0


@dataclass
class CodeQualityResult:
    """Comprehensive code quality analysis result."""

    code_smells: list[CodeSmell] = field(default_factory=list)
    todo_comments: list[TodoComment] = field(default_factory=list)
    duplicate_blocks: list[DuplicateCodeBlock] = field(default_factory=list)
    frameworks: list[FrameworkDetection] = field(default_factory=list)
    module_analysis: ModuleAnalysis | None = None
    max_nesting_depth: int = 0
    avg_function_length: float = 0.0
    total_code_smells: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    info_count: int = 0


class CodeQualityAnalyzer:
    """
    Comprehensive JavaScript code quality analyzer.

    Detects code smells, anti-patterns, and provides quality metrics.
    Works with raw source code (no AST required) for maximum compatibility.

    Example usage:
        analyzer = CodeQualityAnalyzer()
        result = analyzer.analyze(source_code)

        for smell in result.code_smells:
            print(f"{smell.smell_type.value}: {smell.message} at line {smell.line}")
    """

    # Configurable thresholds
    DEFAULT_MAX_FUNCTION_LINES = 50
    DEFAULT_MAX_PARAMS = 5
    DEFAULT_MAX_NESTING = 4
    DEFAULT_MAX_FILE_LINES = 500
    DEFAULT_MIN_DUPLICATE_LINES = 6

    # Acceptable magic numbers (commonly used constants)
    ACCEPTABLE_NUMBERS = {0, 1, -1, 2, 10, 100, 1000, 24, 60, 365}

    def __init__(
        self,
        max_function_lines: int = DEFAULT_MAX_FUNCTION_LINES,
        max_params: int = DEFAULT_MAX_PARAMS,
        max_nesting: int = DEFAULT_MAX_NESTING,
        max_file_lines: int = DEFAULT_MAX_FILE_LINES,
        min_duplicate_lines: int = DEFAULT_MIN_DUPLICATE_LINES,
    ):
        """
        Initialize the code quality analyzer.

        :param max_function_lines: Maximum lines before flagging long function.
        :param max_params: Maximum parameters before flagging.
        :param max_nesting: Maximum nesting depth before flagging.
        :param max_file_lines: Maximum file lines before flagging.
        :param min_duplicate_lines: Minimum lines for duplicate detection.
        """
        self.max_function_lines = max_function_lines
        self.max_params = max_params
        self.max_nesting = max_nesting
        self.max_file_lines = max_file_lines
        self.min_duplicate_lines = min_duplicate_lines

    def analyze(self, code: str, filename: str = "input.js") -> CodeQualityResult:
        """
        Analyze JavaScript code for quality issues.

        :param code: JavaScript/TypeScript source code.
        :param filename: Name of the file being analyzed.
        :return: CodeQualityResult with all findings.
        """
        result = CodeQualityResult()
        lines = code.split("\n")

        # Run all detections
        result.code_smells.extend(self._detect_callback_hell(code, lines))
        result.code_smells.extend(self._detect_magic_numbers(code, lines))
        result.code_smells.extend(self._detect_magic_strings(code, lines))
        result.code_smells.extend(self._detect_long_functions(code, lines))
        result.code_smells.extend(self._detect_too_many_params(code, lines))
        result.code_smells.extend(self._detect_empty_catch(code, lines))
        result.code_smells.extend(self._detect_console_statements(code, lines))
        result.code_smells.extend(self._detect_debugger(code, lines))
        result.code_smells.extend(self._detect_nested_ternary(code, lines))
        result.code_smells.extend(self._detect_complex_conditions(code, lines))
        result.code_smells.extend(self._detect_promise_issues(code, lines))

        # Long file check
        if len(lines) > self.max_file_lines:
            result.code_smells.append(
                CodeSmell(
                    smell_type=CodeSmellType.LONG_FILE,
                    severity=CodeSmellSeverity.MEDIUM,
                    message=f"File has {len(lines)} lines (max: {self.max_file_lines})",
                    line=1,
                    recommendation="Consider splitting into smaller modules",
                )
            )

        result.todo_comments = self._extract_todo_comments(code, lines)
        for todo in result.todo_comments:
            smell_type = {
                "TODO": CodeSmellType.TODO_COMMENT,
                "FIXME": CodeSmellType.FIXME_COMMENT,
                "HACK": CodeSmellType.HACK_COMMENT,
            }.get(todo.comment_type, CodeSmellType.TODO_COMMENT)
            result.code_smells.append(
                CodeSmell(
                    smell_type=smell_type,
                    severity=CodeSmellSeverity.INFO,
                    message=f"{todo.comment_type}: {todo.message}",
                    line=todo.line,
                )
            )

        # Detect frameworks
        result.frameworks = self._detect_frameworks(code)

        # Analyze module system
        result.module_analysis = self._analyze_module_system(code)

        # Detect duplicate code blocks
        result.duplicate_blocks = self._detect_duplicate_blocks(code, lines)
        for dup in result.duplicate_blocks:
            result.code_smells.append(
                CodeSmell(
                    smell_type=CodeSmellType.DUPLICATE_CODE,
                    severity=CodeSmellSeverity.MEDIUM,
                    message=f"Duplicate code block ({dup.line_count} lines, {dup.similarity:.0%} similar)",
                    line=dup.lines_start[0] if dup.lines_start else 0,
                    recommendation="Consider extracting to a shared function",
                )
            )

        # Calculate max nesting
        result.max_nesting_depth = self._calculate_max_nesting(code)

        # Count severities
        result.total_code_smells = len(result.code_smells)
        result.critical_count = sum(1 for s in result.code_smells if s.severity == CodeSmellSeverity.CRITICAL)
        result.high_count = sum(1 for s in result.code_smells if s.severity == CodeSmellSeverity.HIGH)
        result.medium_count = sum(1 for s in result.code_smells if s.severity == CodeSmellSeverity.MEDIUM)
        result.low_count = sum(1 for s in result.code_smells if s.severity == CodeSmellSeverity.LOW)
        result.info_count = sum(1 for s in result.code_smells if s.severity == CodeSmellSeverity.INFO)

        return result

    def _detect_callback_hell(self, code: str, lines: list[str]) -> list[CodeSmell]:
        """Detect callback hell (deeply nested callbacks)."""
        smells: list[CodeSmell] = []

        # Track callback nesting via indentation and callback patterns
        callback_pattern = re.compile(r"(function\s*\(|=>\s*{|\(\s*function)")

        for i, line in enumerate(lines, 1):
            # Count leading whitespace
            stripped = line.lstrip()
            if not stripped:
                continue

            indent = len(line) - len(stripped)
            # Approximate nesting by indentation (assuming 2 or 4 space indent)
            nesting = indent // 2

            if nesting > self.max_nesting and callback_pattern.search(line):
                smells.append(
                    CodeSmell(
                        smell_type=CodeSmellType.CALLBACK_HELL,
                        severity=CodeSmellSeverity.HIGH,
                        message=f"Callback hell detected - nesting depth {nesting}",
                        line=i,
                        code_snippet=line.strip()[:80],
                        recommendation="Use async/await or Promise chains",
                    )
                )

        return smells

    def _detect_magic_numbers(self, code: str, lines: list[str]) -> list[CodeSmell]:
        """Detect magic numbers (unexplained numeric literals)."""
        smells: list[CodeSmell] = []

        # Pattern for numeric literals (excluding common acceptable values)
        number_pattern = re.compile(r"\b(\d+\.?\d*)\b")

        # Skip patterns (array indices, common values)
        skip_contexts = [
            r"for\s*\(\s*\w+\s*=",  # Loop initializers
            r"\[\s*\d+\s*\]",  # Array indices
            r":\s*\d+",  # Object property values (often port numbers, etc.)
            r"setTimeout|setInterval",  # Timeouts
            r"Math\.",  # Math operations
            r"new\s+Date",  # Date constructor
        ]

        for i, line in enumerate(lines, 1):
            # Skip comment lines
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue

            # Skip if line matches skip contexts
            if any(re.search(ctx, line) for ctx in skip_contexts):
                continue

            for match in number_pattern.finditer(line):
                num_str = match.group(1)
                try:
                    num = float(num_str) if "." in num_str else int(num_str)
                    if num not in self.ACCEPTABLE_NUMBERS and abs(num) > 2:
                        # Check if it's in a const/let/var declaration
                        if not re.search(
                            r"const\s+\w+\s*=|let\s+\w+\s*=|var\s+\w+\s*=",
                            line[: match.start()],
                        ):
                            smells.append(
                                CodeSmell(
                                    smell_type=CodeSmellType.MAGIC_NUMBER,
                                    severity=CodeSmellSeverity.LOW,
                                    message=f"Magic number {num_str} - consider using a named constant",
                                    line=i,
                                    column=match.start() + 1,
                                    auto_fixable=True,
                                    recommendation=f"Extract to: const SOME_CONSTANT = {num_str};",
                                )
                            )
                except ValueError:
                    pass

        return smells

    def _detect_magic_strings(self, code: str, lines: list[str]) -> list[CodeSmell]:
        """Detect magic strings (hardcoded string literals)."""
        smells: list[CodeSmell] = []

        # Pattern for string literals
        string_pattern = re.compile(r"""(['"`])(?:(?!\1)[^\\]|\\.)*\1""")

        # Skip common acceptable strings
        skip_strings = {
            "",
            " ",
            ".",
            ",",
            ":",
            ";",
            "-",
            "_",
            "/",
            "\\",
            "use strict",
            "utf-8",
            "utf8",
            "ascii",
            "GET",
            "POST",
            "PUT",
            "DELETE",
            "PATCH",
            "click",
            "change",
            "submit",
            "load",
            "error",
            "true",
            "false",
            "null",
            "undefined",
        }

        for i, line in enumerate(lines, 1):
            # Skip comment lines
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue

            # Skip import/require statements
            if "import" in line or "require(" in line:
                continue

            # Skip console.log statements (likely debug)
            if "console." in line:
                continue

            for match in string_pattern.finditer(line):
                content = match.group()[1:-1]  # Remove quotes
                if len(content) > 10 and content.lower() not in skip_strings:
                    # Check if it looks like a URL, path, or message
                    if not content.startswith(("http://", "https://", "/", "./")):
                        # Check if it's in a const declaration
                        before = line[: match.start()]
                        if not re.search(r"const\s+\w+\s*=", before):
                            smells.append(
                                CodeSmell(
                                    smell_type=CodeSmellType.MAGIC_STRING,
                                    severity=CodeSmellSeverity.LOW,
                                    message="Magic string detected - consider using a constant",
                                    line=i,
                                    column=match.start() + 1,
                                    code_snippet=content[:30] + ("..." if len(content) > 30 else ""),
                                    auto_fixable=True,
                                )
                            )

        return smells

    def _detect_long_functions(self, code: str, lines: list[str]) -> list[CodeSmell]:
        """Detect functions that are too long."""
        smells: list[CodeSmell] = []

        # Pattern to match function declarations
        func_patterns = [
            re.compile(r"function\s+(\w+)\s*\("),
            re.compile(r"(\w+)\s*[=:]\s*(?:async\s+)?function\s*\("),
            re.compile(r"(\w+)\s*[=:]\s*(?:async\s+)?\([^)]*\)\s*=>"),
            re.compile(r"(\w+)\s*\([^)]*\)\s*{"),  # Method shorthand
        ]

        i = 0
        while i < len(lines):
            line = lines[i]

            for pattern in func_patterns:
                match = pattern.search(line)
                if match:
                    func_name = match.group(1)
                    start_line = i + 1

                    # Count function length by tracking braces
                    brace_count = line.count("{") - line.count("}")
                    func_lines = 1
                    j = i + 1

                    while j < len(lines) and brace_count > 0:
                        brace_count += lines[j].count("{") - lines[j].count("}")
                        func_lines += 1
                        j += 1

                    if func_lines > self.max_function_lines:
                        smells.append(
                            CodeSmell(
                                smell_type=CodeSmellType.LONG_FUNCTION,
                                severity=CodeSmellSeverity.MEDIUM,
                                message=f"Function '{func_name}' has {func_lines} lines (max: {self.max_function_lines})",
                                line=start_line,
                                end_line=start_line + func_lines - 1,
                                recommendation="Break down into smaller, focused functions",
                            )
                        )
                    break
            i += 1

        return smells

    def _detect_too_many_params(self, code: str, lines: list[str]) -> list[CodeSmell]:
        """Detect functions with too many parameters."""
        smells: list[CodeSmell] = []

        # Pattern to match function parameters
        func_pattern = re.compile(r"(?:function\s+\w+|(?:async\s+)?(?:function|\w+)\s*[=:]?\s*)\s*\(([^)]*)\)")

        for i, line in enumerate(lines, 1):
            for match in func_pattern.finditer(line):
                params_str = match.group(1).strip()
                if params_str:
                    # Count parameters (split by comma, accounting for default values and destructuring)
                    params = self._count_params(params_str)

                    if params > self.max_params:
                        smells.append(
                            CodeSmell(
                                smell_type=CodeSmellType.TOO_MANY_PARAMS,
                                severity=CodeSmellSeverity.MEDIUM,
                                message=f"Function has {params} parameters (max: {self.max_params})",
                                line=i,
                                recommendation="Use an options object pattern: function(options) {...}",
                            )
                        )

        return smells

    def _count_params(self, params_str: str) -> int:
        """Count parameters accounting for destructuring."""
        # Remove destructuring patterns
        params_str = re.sub(r"\{[^}]*\}", "DESTRUCTURED", params_str)
        params_str = re.sub(r"\[[^\]]*\]", "DESTRUCTURED", params_str)

        # Split by comma and count non-empty
        params = [p.strip() for p in params_str.split(",") if p.strip()]
        return len(params)

    def _detect_empty_catch(self, code: str, lines: list[str]) -> list[CodeSmell]:
        """Detect empty catch blocks."""
        smells: list[CodeSmell] = []

        # Pattern for empty catch blocks
        empty_catch_pattern = re.compile(r"catch\s*\([^)]*\)\s*\{\s*\}")

        # Multi-line detection
        i = 0
        while i < len(lines):
            line = lines[i]

            # Single line empty catch
            if empty_catch_pattern.search(line):
                smells.append(
                    CodeSmell(
                        smell_type=CodeSmellType.EMPTY_CATCH,
                        severity=CodeSmellSeverity.HIGH,
                        message="Empty catch block - errors are silently ignored",
                        line=i + 1,
                        recommendation="Log the error or handle it appropriately",
                        auto_fixable=True,
                    )
                )

            # Multi-line empty catch
            if re.search(r"catch\s*\([^)]*\)\s*\{\s*$", line):
                # Check if next non-whitespace line is just }
                j = i + 1
                while j < len(lines) and not lines[j].strip():
                    j += 1
                if j < len(lines) and lines[j].strip() == "}":
                    smells.append(
                        CodeSmell(
                            smell_type=CodeSmellType.EMPTY_CATCH,
                            severity=CodeSmellSeverity.HIGH,
                            message="Empty catch block - errors are silently ignored",
                            line=i + 1,
                            recommendation="Log the error or handle it appropriately",
                        )
                    )

            i += 1

        return smells

    def _detect_console_statements(self, code: str, lines: list[str]) -> list[CodeSmell]:
        """Detect console.log and debug statements."""
        smells: list[CodeSmell] = []

        console_pattern = re.compile(r"console\.(log|debug|info|warn|error|trace|dir|table)\s*\(")

        for i, line in enumerate(lines, 1):
            # Skip comments
            stripped = line.strip()
            if stripped.startswith("//"):
                continue

            match = console_pattern.search(line)
            if match:
                method = match.group(1)
                severity = CodeSmellSeverity.LOW if method in ("error", "warn") else CodeSmellSeverity.INFO
                smells.append(
                    CodeSmell(
                        smell_type=CodeSmellType.CONSOLE_LOG,
                        severity=severity,
                        message=f"console.{method}() found - remove before production",
                        line=i,
                        auto_fixable=True,
                        recommendation="Use a proper logging library or remove debug statements",
                    )
                )

        return smells

    def _detect_debugger(self, code: str, lines: list[str]) -> list[CodeSmell]:
        """Detect debugger statements."""
        smells: list[CodeSmell] = []

        debugger_pattern = re.compile(r"\bdebugger\b")

        for i, line in enumerate(lines, 1):
            if debugger_pattern.search(line):
                smells.append(
                    CodeSmell(
                        smell_type=CodeSmellType.DEBUGGER,
                        severity=CodeSmellSeverity.HIGH,
                        message="debugger statement found - must remove before production",
                        line=i,
                        auto_fixable=True,
                    )
                )

        return smells

    def _detect_nested_ternary(self, code: str, lines: list[str]) -> list[CodeSmell]:
        """Detect nested ternary operators."""
        smells: list[CodeSmell] = []

        # Pattern for nested ternary (simplified - matches ? ... ? pattern)
        nested_ternary = re.compile(r"\?[^:]*\?")

        for i, line in enumerate(lines, 1):
            if nested_ternary.search(line):
                smells.append(
                    CodeSmell(
                        smell_type=CodeSmellType.NESTED_TERNARY,
                        severity=CodeSmellSeverity.MEDIUM,
                        message="Nested ternary operator - difficult to read",
                        line=i,
                        recommendation="Use if-else statements or extract to helper function",
                    )
                )

        return smells

    def _detect_complex_conditions(self, code: str, lines: list[str]) -> list[CodeSmell]:
        """Detect overly complex boolean conditions."""
        smells: list[CodeSmell] = []

        for i, line in enumerate(lines, 1):
            # Count logical operators in the line
            and_count = len(re.findall(r"&&", line))
            or_count = len(re.findall(r"\|\|", line))

            total_ops = and_count + or_count

            if total_ops >= 4:
                smells.append(
                    CodeSmell(
                        smell_type=CodeSmellType.COMPLEX_CONDITION,
                        severity=CodeSmellSeverity.MEDIUM,
                        message=f"Complex condition with {total_ops} logical operators",
                        line=i,
                        recommendation="Extract condition parts to named variables or functions",
                    )
                )

        return smells

    def _detect_promise_issues(self, code: str, lines: list[str]) -> list[CodeSmell]:
        """Detect common Promise anti-patterns."""
        smells: list[CodeSmell] = []

        # Async function in Promise executor
        async_executor = re.compile(r"new\s+Promise\s*\(\s*async")

        # Return await inside async function (usually unnecessary)
        return_await = re.compile(r"return\s+await\s+")

        for i, line in enumerate(lines, 1):
            if async_executor.search(line):
                smells.append(
                    CodeSmell(
                        smell_type=CodeSmellType.PROMISE_EXECUTOR_ASYNC,
                        severity=CodeSmellSeverity.MEDIUM,
                        message="Async function in Promise executor is an anti-pattern",
                        line=i,
                        recommendation="Use async/await directly without wrapping in Promise",
                    )
                )

            if return_await.search(line):
                smells.append(
                    CodeSmell(
                        smell_type=CodeSmellType.NO_RETURN_AWAIT,
                        severity=CodeSmellSeverity.LOW,
                        message="return await is usually unnecessary",
                        line=i,
                        recommendation="Just return the promise directly (except in try blocks)",
                    )
                )

        return smells

    def _extract_todo_comments(self, code: str, lines: list[str]) -> list[TodoComment]:
        todos: list[TodoComment] = []

        # Pattern: TODO/FIXME/HACK with optional (author) or priority
        todo_pattern = re.compile(
            r"//\s*(TODO|FIXME|HACK|XXX|NOTE)\s*(?:\(([^)]+)\))?\s*:?\s*(.+?)$",
            re.IGNORECASE,
        )

        for i, line in enumerate(lines, 1):
            match = todo_pattern.search(line)
            if match:
                comment_type = match.group(1).upper()
                author_or_priority = match.group(2)
                message = match.group(3).strip()

                todos.append(
                    TodoComment(
                        comment_type=comment_type,
                        message=message,
                        line=i,
                        author=(
                            author_or_priority if author_or_priority and not author_or_priority.isdigit() else None
                        ),
                        priority=(author_or_priority if author_or_priority and author_or_priority.isdigit() else None),
                    )
                )

        return todos

    def _detect_frameworks(self, code: str) -> list[FrameworkDetection]:
        """Detect JavaScript frameworks used."""
        detections: list[FrameworkDetection] = []

        framework_indicators = {
            FrameworkType.REACT: [
                (r'import\s+.*\s+from\s+[\'"]react[\'"]', 0.9),
                (r'require\([\'"]react[\'"]\)', 0.9),
                (r"React\.createElement", 0.8),
                (r"useState|useEffect|useContext|useReducer", 0.85),
                (r"<\w+[^>]*\/>", 0.5),  # JSX self-closing tags
            ],
            FrameworkType.VUE: [
                (r'import\s+.*\s+from\s+[\'"]vue[\'"]', 0.9),
                (r"new\s+Vue\s*\(", 0.9),
                (r"export\s+default\s*\{[^}]*data\s*\(\)", 0.7),
                (r"defineComponent|ref\(|reactive\(|computed\(", 0.85),
            ],
            FrameworkType.ANGULAR: [
                (r"@Component\s*\(", 0.9),
                (r"@Injectable\s*\(", 0.85),
                (r"@NgModule\s*\(", 0.9),
                (r'import\s+.*\s+from\s+[\'"]@angular', 0.95),
            ],
            FrameworkType.EXPRESS: [
                (r'require\([\'"]express[\'"]\)', 0.9),
                (r'import\s+.*\s+from\s+[\'"]express[\'"]', 0.9),
                (r"app\.(get|post|put|delete|patch|use)\s*\(", 0.6),
                (r"express\s*\(\)", 0.85),
            ],
            FrameworkType.NEXTJS: [
                (r'import\s+.*\s+from\s+[\'"]next', 0.9),
                (r"getServerSideProps|getStaticProps|getStaticPaths", 0.95),
                (r"useRouter\s*\(\)", 0.7),
            ],
            FrameworkType.REDUX: [
                (r'import\s+.*\s+from\s+[\'"]redux[\'"]', 0.9),
                (r"createStore|combineReducers|applyMiddleware", 0.85),
                (r"useSelector|useDispatch", 0.8),
            ],
            FrameworkType.JQUERY: [
                (r'\$\s*\(\s*[\'"]', 0.8),
                (r"jQuery\s*\(", 0.9),
                (r"\$\.(ajax|get|post)\s*\(", 0.85),
            ],
            FrameworkType.LODASH: [
                (r'import\s+.*\s+from\s+[\'"]lodash[\'"]', 0.9),
                (r'require\([\'"]lodash[\'"]\)', 0.9),
                (r"_\.(map|filter|reduce|find|forEach)", 0.7),
            ],
        }

        for framework, patterns in framework_indicators.items():
            indicators: list[str] = []
            max_confidence = 0.0

            for pattern, confidence in patterns:
                if re.search(pattern, code):
                    indicators.append(pattern)
                    max_confidence = max(max_confidence, confidence)

            if indicators:
                detections.append(
                    FrameworkDetection(
                        framework=framework,
                        confidence=max_confidence,
                        indicators=indicators,
                    )
                )

        return detections

    def _analyze_module_system(self, code: str) -> ModuleAnalysis:
        """Analyze the module system used."""
        commonjs_requires = len(re.findall(r'require\s*\([\'"]', code))
        commonjs_exports = len(re.findall(r"module\.exports|exports\.", code))
        es6_imports = len(re.findall(r'import\s+.+\s+from\s+[\'"]', code))
        es6_exports = len(re.findall(r"export\s+(default\s+)?(?:const|let|var|function|class|{)", code))
        dynamic_imports = len(re.findall(r'import\s*\([\'"]', code))

        # Determine module type
        has_commonjs = commonjs_requires > 0 or commonjs_exports > 0
        has_es6 = es6_imports > 0 or es6_exports > 0

        if has_commonjs and has_es6:
            module_type = ModuleType.MIXED
        elif has_es6:
            module_type = ModuleType.ES6
        elif has_commonjs:
            module_type = ModuleType.COMMONJS
        else:
            module_type = ModuleType.UNKNOWN

        return ModuleAnalysis(
            module_type=module_type,
            commonjs_requires=commonjs_requires,
            commonjs_exports=commonjs_exports,
            es6_imports=es6_imports,
            es6_exports=es6_exports,
            dynamic_imports=dynamic_imports,
        )

    def _detect_duplicate_blocks(self, code: str, lines: list[str]) -> list[DuplicateCodeBlock]:
        """Detect duplicate code blocks using line hashing."""
        duplicates: list[DuplicateCodeBlock] = []

        # Skip if file is too small
        if len(lines) < self.min_duplicate_lines * 2:
            return duplicates

        # Create normalized line hashes
        line_hashes: list[tuple[int, str]] = []
        for i, line in enumerate(lines):
            normalized = self._normalize_line(line)
            if normalized:  # Skip empty/whitespace lines
                line_hash = hashlib.sha256(normalized.encode()).hexdigest()[:8]
                line_hashes.append((i, line_hash))

        # Find duplicate sequences
        seen_sequences: dict[str, list[int]] = {}

        for start_idx in range(len(line_hashes)):
            # Create sequence hash for minimum duplicate lines
            if start_idx + self.min_duplicate_lines > len(line_hashes):
                break

            sequence = tuple(h[1] for h in line_hashes[start_idx : start_idx + self.min_duplicate_lines])
            seq_hash = hashlib.sha256("".join(sequence).encode()).hexdigest()

            actual_line = line_hashes[start_idx][0] + 1  # 1-indexed

            if seq_hash in seen_sequences:
                seen_sequences[seq_hash].append(actual_line)
            else:
                seen_sequences[seq_hash] = [actual_line]

        # Report duplicates
        for seq_hash, line_starts in seen_sequences.items():
            if len(line_starts) > 1:
                duplicates.append(
                    DuplicateCodeBlock(
                        hash_signature=seq_hash,
                        lines_start=line_starts,
                        # [20251222_BUGFIX] Avoid ambiguous variable name (E741).
                        lines_end=[start_line + self.min_duplicate_lines - 1 for start_line in line_starts],
                        line_count=self.min_duplicate_lines,
                        similarity=1.0,
                    )
                )

        return duplicates

    def _normalize_line(self, line: str) -> str:
        """Normalize a line for comparison (remove whitespace, comments)."""
        # Remove leading/trailing whitespace
        normalized = line.strip()

        # Remove single-line comments
        comment_idx = normalized.find("//")
        if comment_idx >= 0:
            normalized = normalized[:comment_idx].strip()

        # Normalize whitespace
        normalized = re.sub(r"\s+", " ", normalized)

        return normalized

    def _calculate_max_nesting(self, code: str) -> int:
        """Calculate maximum nesting depth."""
        max_depth = 0
        current_depth = 0

        for char in code:
            if char == "{":
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif char == "}":
                current_depth = max(0, current_depth - 1)

        return max_depth

    def get_smell_summary(self, result: CodeQualityResult) -> dict[str, int]:
        """Get a summary count of each smell type."""
        summary: dict[str, int] = {}
        for smell in result.code_smells:
            key = smell.smell_type.value
            summary[key] = summary.get(key, 0) + 1
        return summary

    def filter_by_severity(self, result: CodeQualityResult, min_severity: CodeSmellSeverity) -> list[CodeSmell]:
        """Filter code smells by minimum severity."""
        severity_order = [
            CodeSmellSeverity.INFO,
            CodeSmellSeverity.LOW,
            CodeSmellSeverity.MEDIUM,
            CodeSmellSeverity.HIGH,
            CodeSmellSeverity.CRITICAL,
        ]

        min_idx = severity_order.index(min_severity)
        return [smell for smell in result.code_smells if severity_order.index(smell.severity) >= min_idx]
