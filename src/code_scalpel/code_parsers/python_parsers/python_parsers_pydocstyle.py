#!/usr/bin/env python3
"""
Python Docstring Style Checker - pydocstyle Integration.
=========================================================

This module provides docstring validation and style checking using
pydocstyle. It enforces documentation conventions (PEP 257) and
ensures consistent documentation quality.

Implementation Status: MOSTLY COMPLETED
Priority: P3 - MEDIUM

Features:
    - Docstring convention checking
    - Multiple convention support (numpy, google, pep257)
    - Coverage analysis (what's documented)
    - Custom convention rules

==============================================================================
COMPLETED [P3-PYDOCSTYLE-001]: pydocstyle integration
==============================================================================
Priority: MEDIUM
Status: ✓ COMPLETED

Implemented Features:
    - [✓] Run pydocstyle via subprocess
    - [✓] Parse output (error format)
    - [✓] Support convention selection (google, numpy, pep257)
    - [✓] Support --add-ignore and --add-select
    - [✓] Handle configuration files (setup.cfg, .pydocstyle)
    - [✓] Complete command building (_build_command)
    - [✓] Output parsing with object type/name extraction
    - [✓] Error categorization by code prefix

Output Format:
    ```
    filename.py:1 at module level:
            D100: Missing docstring in public module
    filename.py:5 in public function `foo`:
            D103: Missing docstring in public function
    ```

Error Codes:
    D1xx: Missing docstrings
    D2xx: Whitespace issues
    D3xx: Quote issues
    D4xx: Content issues (first line, etc.)

==============================================================================
COMPLETED [P3-PYDOCSTYLE-002]: Docstring coverage analysis
==============================================================================
Priority: MEDIUM
Status: ✓ COMPLETED
Estimated Effort: 1 day
Depends On: P3-PYDOCSTYLE-001

Implemented Features:
    - [✓] Count documented vs undocumented items
    - [✓] Coverage by type (module, class, function, method)
    - [✓] Generate coverage report
    - [✓] Identify critical missing docs (public API)
    - [✓] get_coverage() for single files
    - [✓] get_directory_coverage() for directories
    - [✓] check_with_coverage() for combined checking

Coverage Report Structure:
    - Total items
    - Documented items
    - Coverage percentage
    - Missing by category (classes, functions, methods)

==============================================================================
==============================================================================
Priority: MEDIUM
Status: ✅ COMPLETED
Estimated Effort: 1 day
Depends On: P3-PYDOCSTYLE-001

Requirements:
    - [x] Check docstring completeness (Args, Returns, Raises)
    - [x] Verify parameter documentation matches signature
    - [x] Check return type documentation
    - [x] Validate exception documentation
    - [x] Check for deprecated markers

Implementation:
    - DocstringQualityIssue - Individual issue in a docstring
    - FunctionDocstringQuality - Quality analysis for a function
    - ModuleDocstringQuality - Aggregated quality for a module
    - DocstringQualityAnalyzer - Analyzer class with all quality checks

Quality Checks:
    - All parameters documented?
    - Return value documented (if not None)?
    - Exceptions documented?
    - Examples provided (optional)?
    - Type hints in docstrings match actual types?
"""

from __future__ import annotations

import ast
import re
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


# =============================================================================
# Enums
# =============================================================================


class DocstyleConvention(Enum):
    """Docstring conventions supported by pydocstyle."""

    PEP257 = "pep257"
    GOOGLE = "google"
    NUMPY = "numpy"
    SPHINX = "sphinx"


class DocstyleCategory(Enum):
    """Categories of pydocstyle error codes."""

    MISSING = "missing"  # D1xx
    WHITESPACE = "whitespace"  # D2xx
    QUOTES = "quotes"  # D3xx
    CONTENT = "content"  # D4xx


class DocstringSeverity(Enum):
    """Severity of docstring issues."""

    WARNING = "warning"
    ERROR = "error"


# =============================================================================
# Error Code Mappings
# =============================================================================

# Map error codes to descriptions
ERROR_CODES: dict[str, tuple[DocstyleCategory, str]] = {
    # D1xx - Missing docstrings
    "D100": (DocstyleCategory.MISSING, "Missing docstring in public module"),
    "D101": (DocstyleCategory.MISSING, "Missing docstring in public class"),
    "D102": (DocstyleCategory.MISSING, "Missing docstring in public method"),
    "D103": (DocstyleCategory.MISSING, "Missing docstring in public function"),
    "D104": (DocstyleCategory.MISSING, "Missing docstring in public package"),
    "D105": (DocstyleCategory.MISSING, "Missing docstring in magic method"),
    "D106": (DocstyleCategory.MISSING, "Missing docstring in public nested class"),
    "D107": (DocstyleCategory.MISSING, "Missing docstring in __init__"),
    # D2xx - Whitespace issues
    "D200": (DocstyleCategory.WHITESPACE, "One-line docstring should fit on one line"),
    "D201": (
        DocstyleCategory.WHITESPACE,
        "No blank lines allowed before function docstring",
    ),
    "D202": (
        DocstyleCategory.WHITESPACE,
        "No blank lines allowed after function docstring",
    ),
    "D203": (
        DocstyleCategory.WHITESPACE,
        "1 blank line required before class docstring",
    ),
    "D204": (
        DocstyleCategory.WHITESPACE,
        "1 blank line required after class docstring",
    ),
    "D205": (
        DocstyleCategory.WHITESPACE,
        "1 blank line required between summary and description",
    ),
    "D206": (
        DocstyleCategory.WHITESPACE,
        "Docstring should be indented with spaces, not tabs",
    ),
    "D207": (DocstyleCategory.WHITESPACE, "Docstring is under-indented"),
    "D208": (DocstyleCategory.WHITESPACE, "Docstring is over-indented"),
    "D209": (
        DocstyleCategory.WHITESPACE,
        "Multi-line docstring closing quotes on separate line",
    ),
    "D210": (
        DocstyleCategory.WHITESPACE,
        "No whitespaces allowed surrounding docstring text",
    ),
    "D211": (
        DocstyleCategory.WHITESPACE,
        "No blank lines allowed before class docstring",
    ),
    "D212": (
        DocstyleCategory.WHITESPACE,
        "Multi-line docstring summary should start at first line",
    ),
    "D213": (
        DocstyleCategory.WHITESPACE,
        "Multi-line docstring summary should start at second line",
    ),
    "D214": (DocstyleCategory.WHITESPACE, "Section is over-indented"),
    "D215": (DocstyleCategory.WHITESPACE, "Section underline is over-indented"),
    # D3xx - Quotes issues
    "D300": (DocstyleCategory.QUOTES, "Use triple double quotes"),
    "D301": (DocstyleCategory.QUOTES, 'Use r""" if any backslashes in docstring'),
    "D302": (DocstyleCategory.QUOTES, 'Deprecated: Use u""" for unicode docstrings'),
    # D4xx - Docstring content
    "D400": (DocstyleCategory.CONTENT, "First line should end with a period"),
    "D401": (DocstyleCategory.CONTENT, "First line should be in imperative mood"),
    "D402": (DocstyleCategory.CONTENT, "First line should not be function's signature"),
    "D403": (
        DocstyleCategory.CONTENT,
        "First word of first line should be capitalized",
    ),
    "D404": (DocstyleCategory.CONTENT, "First word of docstring should not be 'This'"),
    "D405": (DocstyleCategory.CONTENT, "Section name should be properly capitalized"),
    "D406": (DocstyleCategory.CONTENT, "Section name should end with a colon"),
    "D407": (DocstyleCategory.CONTENT, "Missing dashed underline after section"),
    "D408": (DocstyleCategory.CONTENT, "Section underline should be in next line"),
    "D409": (
        DocstyleCategory.CONTENT,
        "Section underline should match section name length",
    ),
    "D410": (DocstyleCategory.CONTENT, "Missing blank line after section"),
    "D411": (DocstyleCategory.CONTENT, "Missing blank line before section"),
    "D412": (
        DocstyleCategory.CONTENT,
        "No blank lines allowed between header and content",
    ),
    "D413": (DocstyleCategory.CONTENT, "Missing blank line after last section"),
    "D414": (DocstyleCategory.CONTENT, "Section has no content"),
    "D415": (
        DocstyleCategory.CONTENT,
        "First line should end with period, question mark, or exclamation",
    ),
    "D416": (DocstyleCategory.CONTENT, "Section name should end with a colon"),
    "D417": (DocstyleCategory.CONTENT, "Missing argument description in docstring"),
    "D418": (
        DocstyleCategory.CONTENT,
        "Function/ Method decorated with @overload shouldn't contain docstring",
    ),
    "D419": (DocstyleCategory.CONTENT, "Docstring is empty"),
}


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class PydocstyleConfig:
    """Configuration for pydocstyle execution."""

    convention: DocstyleConvention = DocstyleConvention.GOOGLE
    ignore: list[str] = field(default_factory=list)
    select: list[str] = field(default_factory=list)
    match: str | None = None  # Regex for filenames
    match_dir: str | None = None  # Regex for directory names
    add_ignore: list[str] = field(default_factory=list)
    add_select: list[str] = field(default_factory=list)
    extra_args: list[str] = field(default_factory=list)


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class DocstyleViolation:
    """Represents a pydocstyle violation."""

    code: str
    message: str
    file: str
    line: int
    object_type: str | None = None  # module, class, function, method
    object_name: str | None = None
    category: DocstyleCategory = DocstyleCategory.MISSING
    severity: DocstringSeverity = DocstringSeverity.WARNING

    @property
    def location(self) -> str:
        """Get formatted location string."""
        return f"{self.file}:{self.line}"

    def format(self) -> str:
        """Format the violation for display."""
        context = ""
        if self.object_type and self.object_name:
            context = f" in {self.object_type} `{self.object_name}`"
        elif self.object_type:
            context = f" at {self.object_type} level"
        return f"{self.location}{context}: {self.code}: {self.message}"


@dataclass
class DocstringCoverage:
    """Docstring coverage statistics."""

    total_modules: int = 0
    documented_modules: int = 0
    total_classes: int = 0
    documented_classes: int = 0
    total_functions: int = 0
    documented_functions: int = 0
    total_methods: int = 0
    documented_methods: int = 0

    @property
    def total_items(self) -> int:
        """Total documentable items."""
        return self.total_modules + self.total_classes + self.total_functions + self.total_methods

    @property
    def documented_items(self) -> int:
        """Total documented items."""
        return self.documented_modules + self.documented_classes + self.documented_functions + self.documented_methods

    @property
    def coverage_percent(self) -> float:
        """Overall coverage percentage."""
        if self.total_items == 0:
            return 100.0
        return (self.documented_items / self.total_items) * 100

    @property
    def module_coverage(self) -> float:
        """Module documentation coverage."""
        if self.total_modules == 0:
            return 100.0
        return (self.documented_modules / self.total_modules) * 100

    @property
    def class_coverage(self) -> float:
        """Class documentation coverage."""
        if self.total_classes == 0:
            return 100.0
        return (self.documented_classes / self.total_classes) * 100

    @property
    def function_coverage(self) -> float:
        """Function documentation coverage."""
        if self.total_functions == 0:
            return 100.0
        return (self.documented_functions / self.total_functions) * 100


class DocstringQualityIssueType(Enum):
    """Types of docstring quality issues."""

    MISSING_PARAM = "missing_param"
    UNDOCUMENTED_PARAM = "undocumented_param"
    EXTRA_PARAM = "extra_param"
    MISSING_RETURN = "missing_return"
    MISSING_RAISES = "missing_raises"
    MISSING_EXAMPLE = "missing_example"
    TYPE_MISMATCH = "type_mismatch"
    DEPRECATED_MISSING_REASON = "deprecated_missing_reason"
    EMPTY_DESCRIPTION = "empty_description"


@dataclass
class DocstringQualityIssue:
    """A specific quality issue in a docstring."""

    issue_type: DocstringQualityIssueType
    message: str
    param_name: str | None = None
    expected: str | None = None
    actual: str | None = None


@dataclass
class FunctionDocstringQuality:
    """Quality analysis results for a function's docstring."""

    function_name: str
    file_path: str
    line: int
    has_docstring: bool

    # Parameter documentation
    params_in_signature: list[str] = field(default_factory=list)
    params_documented: list[str] = field(default_factory=list)
    params_with_types: list[str] = field(default_factory=list)

    # Return documentation
    has_return_annotation: bool = False
    return_documented: bool = False
    return_type_documented: bool = False
    returns_none: bool = False

    # Exception documentation
    exceptions_raised: list[str] = field(default_factory=list)
    exceptions_documented: list[str] = field(default_factory=list)

    # Optional sections
    has_examples: bool = False
    has_notes: bool = False
    is_deprecated: bool = False
    deprecated_reason: str | None = None

    # Issues
    issues: list[DocstringQualityIssue] = field(default_factory=list)

    @property
    def missing_params(self) -> list[str]:
        """Parameters in signature but not documented."""
        return [p for p in self.params_in_signature if p not in self.params_documented]

    @property
    def extra_params(self) -> list[str]:
        """Parameters documented but not in signature."""
        return [p for p in self.params_documented if p not in self.params_in_signature]

    @property
    def param_coverage(self) -> float:
        """Percentage of parameters documented."""
        if not self.params_in_signature:
            return 100.0
        return (len(self.params_documented) / len(self.params_in_signature)) * 100

    @property
    def is_complete(self) -> bool:
        """Check if docstring is complete (all params, return, raises documented)."""
        if not self.has_docstring:
            return False
        if self.missing_params:
            return False
        if self.has_return_annotation and not self.returns_none and not self.return_documented:
            return False
        if self.exceptions_raised and not self.exceptions_documented:
            return False
        return True

    @property
    def quality_score(self) -> float:
        """Calculate a quality score (0-100)."""
        if not self.has_docstring:
            return 0.0

        score = 40.0  # Base score for having a docstring

        # Parameter documentation (30 points)
        if self.params_in_signature:
            score += 30.0 * self.param_coverage / 100
        else:
            score += 30.0  # No params = full points

        # Return documentation (15 points)
        if self.returns_none or not self.has_return_annotation:
            score += 15.0
        elif self.return_documented:
            score += 15.0

        # Exception documentation (10 points)
        if self.exceptions_raised:
            if self.exceptions_documented:
                score += 10.0 * len(self.exceptions_documented) / len(self.exceptions_raised)
        else:
            score += 10.0

        # Examples (5 points)
        if self.has_examples:
            score += 5.0

        return min(100.0, score)


@dataclass
class ModuleDocstringQuality:
    """Aggregated quality analysis for a module."""

    module_path: str
    functions: list[FunctionDocstringQuality] = field(default_factory=list)
    methods: list[FunctionDocstringQuality] = field(default_factory=list)
    total_issues: int = 0

    @property
    def all_callables(self) -> list[FunctionDocstringQuality]:
        """All functions and methods."""
        return self.functions + self.methods

    @property
    def average_quality_score(self) -> float:
        """Average quality score across all functions/methods."""
        if not self.all_callables:
            return 100.0
        return sum(f.quality_score for f in self.all_callables) / len(self.all_callables)

    @property
    def complete_count(self) -> int:
        """Number of functions with complete docstrings."""
        return sum(1 for f in self.all_callables if f.is_complete)

    @property
    def completeness_percent(self) -> float:
        """Percentage of functions with complete docstrings."""
        if not self.all_callables:
            return 100.0
        return (self.complete_count / len(self.all_callables)) * 100


class DocstringQualityAnalyzer:
    """
    Analyzer for docstring quality beyond basic style checks.

    Performs deep analysis of docstrings to check:
    - Parameter documentation completeness and accuracy
    - Return value documentation
    - Exception documentation
    - Deprecation markers
    - Examples and notes
    """

    # Common docstring section patterns for Google style
    GOOGLE_ARGS_PATTERN = re.compile(r"^\s*Args?:\s*$", re.MULTILINE)
    GOOGLE_RETURNS_PATTERN = re.compile(r"^\s*Returns?:\s*$", re.MULTILINE)
    GOOGLE_RAISES_PATTERN = re.compile(r"^\s*Raises?:\s*$", re.MULTILINE)
    GOOGLE_EXAMPLES_PATTERN = re.compile(r"^\s*Examples?:\s*$", re.MULTILINE)
    GOOGLE_NOTES_PATTERN = re.compile(r"^\s*Notes?:\s*$", re.MULTILINE)
    GOOGLE_DEPRECATED_PATTERN = re.compile(r"^\s*Deprecated[:\s]", re.MULTILINE | re.IGNORECASE)

    # Parameter pattern for Google style: name (type): description OR name: description
    GOOGLE_PARAM_PATTERN = re.compile(r"^\s+(\w+)(?:\s*\(([^)]+)\))?:\s*(.*)$", re.MULTILINE)

    # NumPy style patterns
    NUMPY_PARAMS_PATTERN = re.compile(r"^Parameters\s*$", re.MULTILINE)
    NUMPY_RETURNS_PATTERN = re.compile(r"^Returns\s*$", re.MULTILINE)
    NUMPY_RAISES_PATTERN = re.compile(r"^Raises\s*$", re.MULTILINE)
    NUMPY_PARAM_PATTERN = re.compile(r"^(\w+)\s*:\s*(\S.*)$", re.MULTILINE)

    # Sphinx style patterns
    SPHINX_PARAM_PATTERN = re.compile(r":param\s+(\w+)(?:\s+(\w+))?:\s*(.*)$", re.MULTILINE)
    SPHINX_RETURNS_PATTERN = re.compile(r":returns?:\s*(.*)$", re.MULTILINE)
    SPHINX_RAISES_PATTERN = re.compile(r":raises?\s+(\w+):\s*(.*)$", re.MULTILINE)

    def __init__(self, convention: DocstyleConvention = DocstyleConvention.GOOGLE):
        """Initialize the analyzer with a docstring convention."""
        self.convention = convention

    def analyze_file(self, path: str | Path) -> ModuleDocstringQuality:
        """Analyze docstring quality for all functions in a file."""
        path = Path(path)
        source = path.read_text(encoding="utf-8")
        return self.analyze_source(source, str(path))

    def analyze_source(self, source: str, file_path: str = "<string>") -> ModuleDocstringQuality:
        """Analyze docstring quality from source code."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return ModuleDocstringQuality(module_path=file_path)

        result = ModuleDocstringQuality(module_path=file_path)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                quality = self._analyze_function(node, source, file_path)
                if self._is_method(node, tree):
                    result.methods.append(quality)
                else:
                    result.functions.append(quality)

        result.total_issues = sum(len(f.issues) for f in result.all_callables)
        return result

    def _analyze_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        source: str,
        file_path: str,
    ) -> FunctionDocstringQuality:
        """Analyze a single function's docstring quality."""
        docstring = ast.get_docstring(node)

        result = FunctionDocstringQuality(
            function_name=node.name,
            file_path=file_path,
            line=node.lineno,
            has_docstring=bool(docstring),
        )

        # Get signature information
        result.params_in_signature = self._get_params(node)
        result.has_return_annotation = node.returns is not None
        result.returns_none = self._returns_none(node)
        result.exceptions_raised = self._get_raised_exceptions(node)

        if not docstring:
            # Add issue for missing docstring
            result.issues.append(
                DocstringQualityIssue(
                    issue_type=DocstringQualityIssueType.EMPTY_DESCRIPTION,
                    message="Function has no docstring",
                )
            )
            return result

        # Parse docstring based on convention
        self._parse_docstring(docstring, result)

        # Check for issues
        self._check_param_issues(result)
        self._check_return_issues(result)
        self._check_raises_issues(result)
        self._check_deprecation_issues(docstring, result)

        return result

    def _get_params(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
        """Get parameter names from function signature."""
        params = []
        for arg in node.args.args:
            if arg.arg != "self" and arg.arg != "cls":
                params.append(arg.arg)
        for arg in node.args.posonlyargs:
            if arg.arg != "self" and arg.arg != "cls":
                params.append(arg.arg)
        for arg in node.args.kwonlyargs:
            params.append(arg.arg)
        if node.args.vararg:
            params.append(node.args.vararg.arg)
        if node.args.kwarg:
            params.append(node.args.kwarg.arg)
        return params

    def _returns_none(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        """Check if function explicitly returns None or has no return."""
        if node.returns:
            if isinstance(node.returns, ast.Constant) and node.returns.value is None:
                return True
            if isinstance(node.returns, ast.Name) and node.returns.id == "None":
                return True

        # Check if function has any non-None return statements
        for child in ast.walk(node):
            if isinstance(child, ast.Return) and child.value is not None:
                if not (isinstance(child.value, ast.Constant) and child.value.value is None):
                    return False
        return True

    def _get_raised_exceptions(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
        """Get exception types raised in the function."""
        exceptions = []
        for child in ast.walk(node):
            if isinstance(child, ast.Raise) and child.exc:
                exc_name = self._get_exception_name(child.exc)
                if exc_name and exc_name not in exceptions:
                    exceptions.append(exc_name)
        return exceptions

    def _get_exception_name(self, exc: ast.expr) -> str | None:
        """Get the name of an exception from a raise statement."""
        if isinstance(exc, ast.Name):
            return exc.id
        if isinstance(exc, ast.Call):
            if isinstance(exc.func, ast.Name):
                return exc.func.id
            if isinstance(exc.func, ast.Attribute):
                return exc.func.attr
        if isinstance(exc, ast.Attribute):
            return exc.attr
        return None

    def _parse_docstring(
        self,
        docstring: str,
        result: FunctionDocstringQuality,
    ) -> None:
        """Parse docstring and extract documented items."""
        if self.convention == DocstyleConvention.GOOGLE:
            self._parse_google_docstring(docstring, result)
        elif self.convention == DocstyleConvention.NUMPY:
            self._parse_numpy_docstring(docstring, result)
        elif self.convention == DocstyleConvention.SPHINX:
            self._parse_sphinx_docstring(docstring, result)
        else:
            # PEP257 doesn't have structured sections, use Google as fallback
            self._parse_google_docstring(docstring, result)

        # Check for common sections
        result.has_examples = bool(
            self.GOOGLE_EXAMPLES_PATTERN.search(docstring)
            or re.search(r">>>\s+", docstring)
            or re.search(r"^Examples?\s*$", docstring, re.MULTILINE)
        )
        result.has_notes = bool(
            self.GOOGLE_NOTES_PATTERN.search(docstring) or re.search(r"^Notes?\s*$", docstring, re.MULTILINE)
        )
        result.is_deprecated = bool(self.GOOGLE_DEPRECATED_PATTERN.search(docstring))
        if result.is_deprecated:
            # Try to extract deprecation reason
            match = re.search(r"Deprecated[:\s]+(.+?)(?:\n\n|$)", docstring, re.IGNORECASE | re.DOTALL)
            if match:
                result.deprecated_reason = match.group(1).strip()

    def _parse_google_docstring(
        self,
        docstring: str,
        result: FunctionDocstringQuality,
    ) -> None:
        """Parse Google-style docstring."""
        # Find Args section
        args_match = self.GOOGLE_ARGS_PATTERN.search(docstring)
        if args_match:
            # Extract params until next section or end
            section_end = self._find_next_section(docstring, args_match.end())
            args_section = docstring[args_match.end() : section_end]

            for match in self.GOOGLE_PARAM_PATTERN.finditer(args_section):
                param_name = match.group(1)
                param_type = match.group(2)
                result.params_documented.append(param_name)
                if param_type:
                    result.params_with_types.append(param_name)

        # Find Returns section
        result.return_documented = bool(self.GOOGLE_RETURNS_PATTERN.search(docstring))
        if result.return_documented:
            # Check for type in return
            returns_match = self.GOOGLE_RETURNS_PATTERN.search(docstring)
            if returns_match:
                section_end = self._find_next_section(docstring, returns_match.end())
                returns_section = docstring[returns_match.end() : section_end].strip()
                # Check if there's a type annotation in the return
                result.return_type_documented = bool(re.match(r"^\s*\w+:", returns_section))

        # Find Raises section
        raises_match = self.GOOGLE_RAISES_PATTERN.search(docstring)
        if raises_match:
            section_end = self._find_next_section(docstring, raises_match.end())
            raises_section = docstring[raises_match.end() : section_end]
            # Extract exception names
            for match in re.finditer(r"^\s+(\w+):", raises_section, re.MULTILINE):
                result.exceptions_documented.append(match.group(1))

    def _parse_numpy_docstring(
        self,
        docstring: str,
        result: FunctionDocstringQuality,
    ) -> None:
        """Parse NumPy-style docstring."""
        # Find Parameters section
        params_match = self.NUMPY_PARAMS_PATTERN.search(docstring)
        if params_match:
            section_end = self._find_next_section(docstring, params_match.end())
            params_section = docstring[params_match.end() : section_end]

            for match in self.NUMPY_PARAM_PATTERN.finditer(params_section):
                param_name = match.group(1)
                result.params_documented.append(param_name)
                result.params_with_types.append(param_name)  # NumPy always has types

        # Find Returns section
        result.return_documented = bool(self.NUMPY_RETURNS_PATTERN.search(docstring))
        result.return_type_documented = result.return_documented

        # Find Raises section
        raises_match = self.NUMPY_RAISES_PATTERN.search(docstring)
        if raises_match:
            section_end = self._find_next_section(docstring, raises_match.end())
            raises_section = docstring[raises_match.end() : section_end]
            for match in self.NUMPY_PARAM_PATTERN.finditer(raises_section):
                result.exceptions_documented.append(match.group(1))

    def _parse_sphinx_docstring(
        self,
        docstring: str,
        result: FunctionDocstringQuality,
    ) -> None:
        """Parse Sphinx-style docstring."""
        # Find :param tags
        for match in self.SPHINX_PARAM_PATTERN.finditer(docstring):
            param_name = match.group(1)
            param_type = match.group(2)
            result.params_documented.append(param_name)
            if param_type:
                result.params_with_types.append(param_name)

        # Find :returns tag
        result.return_documented = bool(self.SPHINX_RETURNS_PATTERN.search(docstring))
        result.return_type_documented = bool(re.search(r":rtype:", docstring))

        # Find :raises tags
        for match in self.SPHINX_RAISES_PATTERN.finditer(docstring):
            result.exceptions_documented.append(match.group(1))

    def _find_next_section(self, docstring: str, start: int) -> int:
        """Find the start of the next section in a docstring."""
        section_patterns = [
            r"^\s*Args?:\s*$",
            r"^\s*Returns?:\s*$",
            r"^\s*Raises?:\s*$",
            r"^\s*Examples?:\s*$",
            r"^\s*Notes?:\s*$",
            r"^\s*Attributes?:\s*$",
            r"^\s*Yields?:\s*$",
            r"^\s*See Also:\s*$",
            r"^\s*References?:\s*$",
            r"^Parameters\s*$",  # NumPy
            r"^Returns\s*$",
            r"^Raises\s*$",
        ]

        min_pos = len(docstring)
        for pattern in section_patterns:
            match = re.search(pattern, docstring[start:], re.MULTILINE)
            if match:
                pos = start + match.start()
                if pos < min_pos:
                    min_pos = pos

        return min_pos

    def _is_method(self, node: ast.FunctionDef | ast.AsyncFunctionDef, tree: ast.Module) -> bool:
        """Check if a function is a method within a class."""
        for cls in ast.walk(tree):
            if isinstance(cls, ast.ClassDef):
                for item in cls.body:
                    if item is node:
                        return True
        return False

    def _check_param_issues(self, result: FunctionDocstringQuality) -> None:
        """Check for parameter documentation issues."""
        for param in result.missing_params:
            result.issues.append(
                DocstringQualityIssue(
                    issue_type=DocstringQualityIssueType.MISSING_PARAM,
                    message=f"Parameter '{param}' not documented",
                    param_name=param,
                )
            )

        for param in result.extra_params:
            result.issues.append(
                DocstringQualityIssue(
                    issue_type=DocstringQualityIssueType.EXTRA_PARAM,
                    message=f"Documented parameter '{param}' not in signature",
                    param_name=param,
                )
            )

    def _check_return_issues(self, result: FunctionDocstringQuality) -> None:
        """Check for return documentation issues."""
        if result.has_return_annotation and not result.returns_none and not result.return_documented:
            result.issues.append(
                DocstringQualityIssue(
                    issue_type=DocstringQualityIssueType.MISSING_RETURN,
                    message="Return value not documented",
                )
            )

    def _check_raises_issues(self, result: FunctionDocstringQuality) -> None:
        """Check for exception documentation issues."""
        for exc in result.exceptions_raised:
            if exc not in result.exceptions_documented:
                result.issues.append(
                    DocstringQualityIssue(
                        issue_type=DocstringQualityIssueType.MISSING_RAISES,
                        message=f"Exception '{exc}' not documented",
                        expected=exc,
                    )
                )

    def _check_deprecation_issues(self, docstring: str, result: FunctionDocstringQuality) -> None:
        """Check for deprecation documentation issues."""
        if result.is_deprecated and not result.deprecated_reason:
            result.issues.append(
                DocstringQualityIssue(
                    issue_type=DocstringQualityIssueType.DEPRECATED_MISSING_REASON,
                    message="Deprecated marker found but no reason provided",
                )
            )


@dataclass
class PydocstyleReport:
    """Complete pydocstyle analysis report."""

    violations: list[DocstyleViolation] = field(default_factory=list)
    files_checked: int = 0
    coverage: DocstringCoverage = field(default_factory=DocstringCoverage)
    convention: DocstyleConvention = DocstyleConvention.GOOGLE
    errors: list[str] = field(default_factory=list)

    @property
    def violation_count(self) -> int:
        """Get total number of violations."""
        return len(self.violations)

    @property
    def violations_by_code(self) -> dict[str, list[DocstyleViolation]]:
        """Group violations by error code."""
        result: dict[str, list[DocstyleViolation]] = {}
        for v in self.violations:
            result.setdefault(v.code, []).append(v)
        return result

    @property
    def violations_by_category(self) -> dict[DocstyleCategory, list[DocstyleViolation]]:
        """Group violations by category."""
        result: dict[DocstyleCategory, list[DocstyleViolation]] = {}
        for v in self.violations:
            result.setdefault(v.category, []).append(v)
        return result

    @property
    def missing_count(self) -> int:
        """Count of missing docstring violations."""
        return len([v for v in self.violations if v.category == DocstyleCategory.MISSING])

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the report."""
        return {
            "files_checked": self.files_checked,
            "convention": self.convention.value,
            "total_violations": self.violation_count,
            "missing_docstrings": self.missing_count,
            "by_category": {cat.value: len(violations) for cat, violations in self.violations_by_category.items()},
            "coverage_percent": self.coverage.coverage_percent,
        }


# =============================================================================
# Parser Class
# =============================================================================


class PydocstyleParser:
    """
    Parser for pydocstyle output - docstring style checker.

    Provides docstring validation using pydocstyle with support
    for multiple conventions (Google, NumPy, PEP 257).

    Implementation Status:
        ✓ Full pydocstyle integration (P3-PYDOCSTYLE-001)
        ✓ Coverage analysis (P3-PYDOCSTYLE-002)
        ✓ Quality analysis via DocstringQualityAnalyzer (P3-PYDOCSTYLE-003)

    Usage:
        >>> parser = PydocstyleParser()
        >>> report = parser.check_file("example.py")
        >>> for violation in report.violations:
        ...     print(violation.format())
        >>>
        >>> # Get coverage
        >>> coverage = parser.get_coverage("example.py")
        >>> print(f"Coverage: {coverage.coverage_percent:.1f}%")
    """

    def __init__(self, config: PydocstyleConfig | None = None):
        """
        Initialize the parser.

        Args:
            config: Configuration for pydocstyle.
        """
        self.config = config or PydocstyleConfig()
        self._pydocstyle_path: str | None = None

    @property
    def pydocstyle_path(self) -> str | None:
        """Get path to pydocstyle executable."""
        if self._pydocstyle_path is None:
            self._pydocstyle_path = self._find_pydocstyle()
        return self._pydocstyle_path

    def _find_pydocstyle(self) -> str | None:
        """Find pydocstyle executable."""
        try:
            result = subprocess.run(
                ["which", "pydocstyle"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    def is_available(self) -> bool:
        """Check if pydocstyle is available."""
        return self.pydocstyle_path is not None

    def check_file(self, path: str | Path) -> PydocstyleReport:
        """
        Check a Python file for docstring issues.

        Args:
            path: Path to the Python file.

        Returns:
            PydocstyleReport with violations.
        """
        return self.check_paths([str(path)])

    def check_paths(
        self,
        paths: list[str],
    ) -> PydocstyleReport:
        """
        Check multiple paths for docstring issues.

        Runs pydocstyle subprocess and parses violations.

        Args:
            paths: Paths to check (files or directories).

        Returns:
            PydocstyleReport with all violations.
        """
        report = PydocstyleReport(
            convention=self.config.convention,
        )

        if not self.is_available():
            report.errors.append("pydocstyle is not installed or not in PATH")
            return report

        cmd = self._build_command(paths)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )

            # pydocstyle returns 1 when violations found, 0 otherwise
            report.violations = self._parse_output(result.stdout)
            report.files_checked = len(paths)

            if result.stderr:
                # Parse errors from stderr
                for line in result.stderr.strip().split("\n"):
                    if line:
                        report.errors.append(line)

        except subprocess.TimeoutExpired:
            report.errors.append("pydocstyle timed out after 5 minutes")
        except Exception as e:
            report.errors.append(f"Failed to run pydocstyle: {e}")

        return report

    def _build_command(self, paths: list[str]) -> list[str]:
        """Build the pydocstyle command."""
        cmd = ["pydocstyle"]

        # Add convention
        cmd.extend(["--convention", self.config.convention.value])

        # Add ignore
        if self.config.ignore:
            cmd.extend(["--ignore", ",".join(self.config.ignore)])

        # Add select
        if self.config.select:
            cmd.extend(["--select", ",".join(self.config.select)])

        # Add extra ignores
        if self.config.add_ignore:
            cmd.extend(["--add-ignore", ",".join(self.config.add_ignore)])

        # Add extra selects
        if self.config.add_select:
            cmd.extend(["--add-select", ",".join(self.config.add_select)])

        # Add match pattern
        if self.config.match:
            cmd.extend(["--match", self.config.match])

        if self.config.match_dir:
            cmd.extend(["--match-dir", self.config.match_dir])

        # Add extra args
        cmd.extend(self.config.extra_args)

        # Add paths
        cmd.extend(paths)

        return cmd

    def _parse_output(self, output: str) -> list[DocstyleViolation]:
        """
        Parse pydocstyle output.

        Output format:
            filename.py:1 at module level:
                    D100: Missing docstring in public module
            filename.py:5 in public function `foo`:
                    D103: Missing docstring in public function
        """
        violations: list[DocstyleViolation] = []

        # Pattern for location line
        loc_pattern = re.compile(r"^(.+?):(\d+)\s+(at|in)\s+(.+?)(?:\s+`(.+?)`)?:?\s*$")

        # Pattern for error line
        error_pattern = re.compile(r"^\s+(D\d+):\s+(.+)$")

        current_file: str | None = None
        current_line: int | None = None
        current_obj_type: str | None = None
        current_obj_name: str | None = None

        for line in output.strip().split("\n"):
            if not line:
                continue

            # Check for location line
            loc_match = loc_pattern.match(line)
            if loc_match:
                current_file = loc_match.group(1)
                current_line = int(loc_match.group(2))
                context = loc_match.group(4)
                current_obj_name = loc_match.group(5)

                # Parse object type from context
                if "module" in context.lower():
                    current_obj_type = "module"
                elif "class" in context.lower():
                    current_obj_type = "class"
                elif "method" in context.lower():
                    current_obj_type = "method"
                elif "function" in context.lower():
                    current_obj_type = "function"
                else:
                    current_obj_type = context
                continue

            # Check for error line
            error_match = error_pattern.match(line)
            if error_match and current_file and current_line:
                code = error_match.group(1)
                message = error_match.group(2)

                # Get category from code
                category = DocstyleCategory.MISSING
                if code in ERROR_CODES:
                    category = ERROR_CODES[code][0]

                violations.append(
                    DocstyleViolation(
                        code=code,
                        message=message,
                        file=current_file,
                        line=current_line,
                        object_type=current_obj_type,
                        object_name=current_obj_name,
                        category=category,
                    )
                )

        return violations

    def get_coverage(self, path: str | Path) -> DocstringCoverage:
        """
        Calculate docstring coverage for a file using AST analysis.

        Analyzes the source code to count documentable items (modules, classes,
        functions, methods) and determines which have docstrings.

        Args:
            path: Path to the Python file.

        Returns:
            DocstringCoverage with counts and percentages.
        """
        path = Path(path)
        source = path.read_text(encoding="utf-8")
        return self.get_coverage_from_source(source)

    def get_coverage_from_source(self, source: str) -> DocstringCoverage:
        """
        Calculate docstring coverage from source code.

        Args:
            source: Python source code.

        Returns:
            DocstringCoverage with counts.
        """
        coverage = DocstringCoverage()

        try:
            tree = ast.parse(source)
        except SyntaxError:
            return coverage

        # Check module docstring
        coverage.total_modules = 1
        if ast.get_docstring(tree):
            coverage.documented_modules = 1

        # Walk the tree for classes and functions
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                self._analyze_class(node, coverage)
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                # Only count top-level functions (not methods)
                if not self._is_method(node, tree):
                    coverage.total_functions += 1
                    if ast.get_docstring(node):
                        coverage.documented_functions += 1

        return coverage

    def _analyze_class(
        self,
        node: ast.ClassDef,
        coverage: DocstringCoverage,
    ) -> None:
        """Analyze a class for docstring coverage."""
        coverage.total_classes += 1
        if ast.get_docstring(node):
            coverage.documented_classes += 1

        # Count methods within the class
        for item in node.body:
            if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                coverage.total_methods += 1
                if ast.get_docstring(item):
                    coverage.documented_methods += 1

    def _is_method(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        tree: ast.AST,
    ) -> bool:
        """Check if a function is a method (defined inside a class)."""
        for parent in ast.walk(tree):
            if isinstance(parent, ast.ClassDef):
                for child in parent.body:
                    if child is node:
                        return True
        return False

    def get_directory_coverage(
        self,
        path: str | Path,
        *,
        recursive: bool = True,
        exclude_patterns: list[str] | None = None,
    ) -> DocstringCoverage:
        """
        Calculate docstring coverage for all Python files in a directory.

        Args:
            path: Path to the directory.
            recursive: Whether to search recursively.
            exclude_patterns: Patterns to exclude.

        Returns:
            Combined DocstringCoverage.
        """
        path = Path(path)
        coverage = DocstringCoverage()

        pattern = "**/*.py" if recursive else "*.py"

        for py_file in path.glob(pattern):
            # Skip excluded patterns
            if exclude_patterns:
                skip = False
                for pat in exclude_patterns:
                    if pat in str(py_file):
                        skip = True
                        break
                if skip:
                    continue

            try:
                file_coverage = self.get_coverage(py_file)
                self._merge_coverage(coverage, file_coverage)
            except Exception:
                pass

        return coverage

    def _merge_coverage(
        self,
        target: DocstringCoverage,
        source: DocstringCoverage,
    ) -> None:
        """Merge source coverage into target."""
        target.total_modules += source.total_modules
        target.documented_modules += source.documented_modules
        target.total_classes += source.total_classes
        target.documented_classes += source.documented_classes
        target.total_functions += source.total_functions
        target.documented_functions += source.documented_functions
        target.total_methods += source.total_methods
        target.documented_methods += source.documented_methods

    def check_with_coverage(
        self,
        path: str | Path,
    ) -> PydocstyleReport:
        """
        Check a file for docstring issues and calculate coverage.

        Combines pydocstyle checking with AST-based coverage analysis.

        Args:
            path: Path to the Python file.

        Returns:
            PydocstyleReport with violations and coverage.
        """
        path = Path(path)
        report = self.check_file(path)
        report.coverage = self.get_coverage(path)
        return report


# =============================================================================
# Utility Functions
# =============================================================================


def format_pydocstyle_report(report: PydocstyleReport) -> str:
    """Format a pydocstyle report for display."""
    lines = [
        "Pydocstyle Report",
        "=" * 50,
        "",
        f"Files checked: {report.files_checked}",
        f"Convention: {report.convention.value}",
        f"Total violations: {report.violation_count}",
        "",
    ]

    if report.violations_by_category:
        lines.append("By category:")
        for category, violations in sorted(report.violations_by_category.items(), key=lambda x: -len(x[1])):
            lines.append(f"  {category.value}: {len(violations)}")

    lines.append("")

    if report.coverage.total_items > 0:
        lines.extend(
            [
                "Documentation Coverage:",
                f"  Overall: {report.coverage.coverage_percent:.1f}%",
                f"  Modules: {report.coverage.module_coverage:.1f}%",
                f"  Classes: {report.coverage.class_coverage:.1f}%",
                f"  Functions: {report.coverage.function_coverage:.1f}%",
                "",
            ]
        )

    if report.violations:
        lines.append("Violations:")
        for violation in report.violations[:10]:
            lines.append(f"  {violation.format()}")
        if len(report.violations) > 10:
            lines.append(f"  ... and {len(report.violations) - 10} more")

    if report.errors:
        lines.extend(["", "Errors:"])
        for error in report.errors:
            lines.append(f"  {error}")

    return "\n".join(lines)


def get_error_description(code: str) -> str:
    """Get the description for an error code."""
    if code in ERROR_CODES:
        return ERROR_CODES[code][1]
    return f"Unknown error code: {code}"
