#!/usr/bin/env python3
"""
Flow Parser - Facebook Flow static type checker integration.

Flow is a static type checker for JavaScript developed by Facebook/Meta.
This parser integrates with Flow for type checking and type extraction.


Features:
    Type Extraction:
        - Type alias parsing (type X = ...)
        - Interface declaration parsing
        - Generic type parameter analysis
        - Opaque type detection
        - Variance annotations (+covariant, -contravariant)

    Flow-Specific Types:
        - Maybe types (?T) detection
        - Exact object types ({| |}) detection
        - Utility types ($ReadOnly, $Keys, $Exact, etc.)
        - Type kind classification

    Configuration:
        - .flowconfig parsing
        - Include/ignore pattern extraction
        - Options and lints extraction
        - Library definitions path detection

    Type Checking:
        - Flow CLI integration for type checking
        - Error extraction with locations
        - Type coverage via flow coverage command

    Code Analysis:
        - Suppress comment detection ($FlowFixMe, $FlowIgnore)
        - Type stripping for plain JS output

Future Enhancements:
    - Type-at-position queries
    - Module resolution analysis
    - libdef (.flow) file parsing
    - Flow -> TypeScript migration suggestions
"""

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class FlowSeverity(Enum):
    """Flow error severity levels."""

    ERROR = "error"
    WARNING = "warning"


class FlowTypeKind(Enum):
    """Flow type kinds."""

    PRIMITIVE = "primitive"
    LITERAL = "literal"
    MAYBE = "maybe"  # ?T
    UNION = "union"
    INTERSECTION = "intersection"
    ARRAY = "array"
    TUPLE = "tuple"
    OBJECT = "object"
    EXACT_OBJECT = "exact_object"  # {| |}
    FUNCTION = "function"
    GENERIC = "generic"
    OPAQUE = "opaque"
    UTILITY = "utility"  # $ReadOnly, $Keys, etc.
    TYPEOF = "typeof"
    CLASS = "class"
    INTERFACE = "interface"


class Variance(Enum):
    """Type parameter variance."""

    INVARIANT = "invariant"
    COVARIANT = "covariant"  # +T
    CONTRAVARIANT = "contravariant"  # -T


@dataclass
class FlowTypeAnnotation:
    """A Flow type annotation."""

    text: str
    kind: FlowTypeKind
    line: int
    column: int
    is_nullable: bool = False  # ?T
    is_exact: bool = False  # {| |}
    variance: Variance | None = None


@dataclass
class FlowTypeParameter:
    """A generic type parameter in Flow."""

    name: str
    bound: str | None = None  # T: BoundType
    default: str | None = None
    variance: Variance = Variance.INVARIANT
    line: int = 0


@dataclass
class FlowTypeAlias:
    """A Flow type alias (type X = ...)."""

    name: str
    line: int
    column: int
    type_value: str
    type_kind: FlowTypeKind
    type_parameters: list[FlowTypeParameter] = field(default_factory=list)
    is_exported: bool = False
    is_opaque: bool = False  # opaque type


@dataclass
class FlowInterface:
    """A Flow interface declaration."""

    name: str
    line: int
    column: int
    end_line: int | None = None
    type_parameters: list[FlowTypeParameter] = field(default_factory=list)
    extends: list[str] = field(default_factory=list)
    properties: list[tuple[str, str, bool]] = field(default_factory=list)  # (name, type, optional)
    is_exported: bool = False


@dataclass
class FlowError:
    """A Flow type error."""

    message: str
    severity: FlowSeverity
    line: int
    column: int
    end_line: int
    end_column: int
    file_path: str
    error_code: str | None = None
    context: str | None = None


@dataclass
class FlowCoverage:
    """Flow type coverage information."""

    covered_count: int = 0
    uncovered_count: int = 0
    empty_count: int = 0

    @property
    def total(self) -> int:
        return self.covered_count + self.uncovered_count

    @property
    def percentage(self) -> float:
        if self.total == 0:
            return 100.0
        return (self.covered_count / self.total) * 100


@dataclass
class FlowConfig:
    """Flow configuration from .flowconfig."""

    ignore: list[str] = field(default_factory=list)
    include: list[str] = field(default_factory=list)
    libs: list[str] = field(default_factory=list)
    lints: dict[str, str] = field(default_factory=dict)  # lint_name: severity
    options: dict[str, Any] = field(default_factory=dict)
    version: str | None = None
    strict: bool = False
    all_: bool = False  # all=true


@dataclass
class FlowAnalysis:
    """Complete Flow analysis results."""

    type_aliases: list[FlowTypeAlias] = field(default_factory=list)
    interfaces: list[FlowInterface] = field(default_factory=list)
    errors: list[FlowError] = field(default_factory=list)
    coverage: FlowCoverage | None = None
    config: FlowConfig | None = None
    utility_types_used: list[str] = field(default_factory=list)
    maybe_types: list[tuple[int, int]] = field(default_factory=list)  # (line, col) of ?T usages
    exact_objects: list[tuple[int, int]] = field(default_factory=list)  # {| |} usages
    suppress_comments: list[tuple[int, str]] = field(default_factory=list)  # (line, type)


class FlowParser:
    """
    Parser for Flow type checker integration.

    Flow provides static type checking for JavaScript with features like:
    - Type inference
    - Nullable types (?T)
    - Exact object types ({| |})
    - Opaque types
    - Utility types ($ReadOnly, $Keys, etc.)

    Example usage:
        parser = FlowParser()

        # Analyze Flow-typed code
        analysis = parser.analyze(code)

        # Check types
        errors = parser.check(code)

        # Get coverage
        coverage = parser.get_coverage(file_path)
    """

    # Flow utility types
    UTILITY_TYPES = {
        "$Keys",
        "$Values",
        "$ReadOnly",
        "$Exact",
        "$Diff",
        "$Rest",
        "$PropertyType",
        "$ElementType",
        "$NonMaybeType",
        "$ObjMap",
        "$ObjMapi",
        "$ObjMapConst",
        "$TupleMap",
        "$Call",
        "$Class",
        "$Shape",
        "$Exports",
        "$Supertype",
        "$Subtype",
        "$CharSet",
    }

    # Regex patterns
    _TYPE_ALIAS_PATTERN = re.compile(
        r"(?:export\s+)?(?:opaque\s+)?type\s+(\w+)(?:<([^>]+)>)?\s*(?::\s*(\w+))?\s*=\s*([^;]+);",
        re.MULTILINE,
    )
    _INTERFACE_PATTERN = re.compile(
        r"(?:export\s+)?interface\s+(\w+)(?:<([^>]+)>)?(?:\s+extends\s+([^{]+))?\s*\{",
        re.MULTILINE,
    )
    _MAYBE_TYPE_PATTERN = re.compile(r"\?\w+")
    _EXACT_OBJECT_PATTERN = re.compile(r"\{\|")
    _SUPPRESS_PATTERN = re.compile(r"//\s*\$FlowFixMe|\$FlowIgnore|\$FlowIssue")
    _VARIANCE_PATTERN = re.compile(r"([+-])(\w+)")

    def __init__(self, flow_path: str | None = None):
        """
        Initialize Flow parser.

        :param flow_path: Path to Flow binary.
        """
        self._flow_path = flow_path or self._find_flow()

    def _find_flow(self) -> str | None:
        """Find Flow binary."""
        flow = shutil.which("flow")
        if flow:
            return flow

        local = Path("node_modules/.bin/flow")
        if local.exists():
            return str(local)

        if shutil.which("npx"):
            return "npx flow"

        return None

    def analyze(self, code: str, filename: str = "input.js") -> FlowAnalysis:
        """
        Analyze Flow-typed JavaScript code.

        :param code: JavaScript source code with Flow types.
        :param filename: Virtual filename.
        :return: FlowAnalysis with extracted type information.
        """
        analysis = FlowAnalysis()

        # Extract type aliases
        analysis.type_aliases = self._extract_type_aliases(code)

        # Extract interfaces
        analysis.interfaces = self._extract_interfaces(code)

        # Find utility type usages
        analysis.utility_types_used = self._find_utility_types(code)

        # Find maybe types (?T)
        analysis.maybe_types = self._find_maybe_types(code)

        # Find exact objects ({| |})
        analysis.exact_objects = self._find_exact_objects(code)

        # Find suppress comments
        analysis.suppress_comments = self._find_suppress_comments(code)

        return analysis

    def analyze_file(self, file_path: str) -> FlowAnalysis:
        """
        Analyze a Flow-typed file.

        :param file_path: Path to JavaScript file.
        :return: FlowAnalysis.
        """
        path = Path(file_path)
        code = path.read_text(encoding="utf-8")
        return self.analyze(code, path.name)

    def _extract_type_aliases(self, code: str) -> list[FlowTypeAlias]:
        """Extract Flow type aliases."""
        aliases: list[FlowTypeAlias] = []

        for match in self._TYPE_ALIAS_PATTERN.finditer(code):
            name = match.group(1)
            type_params_str = match.group(2)
            match.group(3)  # For opaque types
            type_value = match.group(4).strip()

            line = code[: match.start()].count("\n") + 1
            column = match.start() - code.rfind("\n", 0, match.start()) - 1

            type_parameters = self._parse_type_parameters(type_params_str) if type_params_str else []
            is_exported = "export" in code[max(0, match.start() - 20) : match.start()]
            is_opaque = "opaque" in code[max(0, match.start() - 20) : match.start()]

            type_kind = self._determine_type_kind(type_value)

            aliases.append(
                FlowTypeAlias(
                    name=name,
                    line=line,
                    column=column,
                    type_value=type_value,
                    type_kind=type_kind,
                    type_parameters=type_parameters,
                    is_exported=is_exported,
                    is_opaque=is_opaque,
                )
            )

        return aliases

    def _extract_interfaces(self, code: str) -> list[FlowInterface]:
        """Extract Flow interfaces."""
        interfaces: list[FlowInterface] = []

        for match in self._INTERFACE_PATTERN.finditer(code):
            name = match.group(1)
            type_params_str = match.group(2)
            extends_str = match.group(3)

            line = code[: match.start()].count("\n") + 1
            column = match.start() - code.rfind("\n", 0, match.start()) - 1

            type_parameters = self._parse_type_parameters(type_params_str) if type_params_str else []
            extends = [e.strip() for e in extends_str.split(",")] if extends_str else []
            is_exported = "export" in code[max(0, match.start() - 20) : match.start()]

            interfaces.append(
                FlowInterface(
                    name=name,
                    line=line,
                    column=column,
                    type_parameters=type_parameters,
                    extends=extends,
                    is_exported=is_exported,
                )
            )

        return interfaces

    def _parse_type_parameters(self, params_str: str) -> list[FlowTypeParameter]:
        """Parse Flow type parameters with variance."""
        params: list[FlowTypeParameter] = []

        if not params_str:
            return params

        for param in params_str.split(","):
            param = param.strip()

            variance = Variance.INVARIANT
            if param.startswith("+"):
                variance = Variance.COVARIANT
                param = param[1:]
            elif param.startswith("-"):
                variance = Variance.CONTRAVARIANT
                param = param[1:]

            name = param
            bound = None
            default = None

            if ":" in param:
                parts = param.split(":", 1)
                name = parts[0].strip()
                bound = parts[1].strip()

            if "=" in name:
                name, default = name.split("=", 1)
                name = name.strip()
                default = default.strip()

            params.append(
                FlowTypeParameter(
                    name=name,
                    bound=bound,
                    default=default,
                    variance=variance,
                )
            )

        return params

    def _determine_type_kind(self, type_value: str) -> FlowTypeKind:
        """Determine the kind of a Flow type."""
        type_value = type_value.strip()

        # Check for utility types first
        for util in self.UTILITY_TYPES:
            if util in type_value:
                return FlowTypeKind.UTILITY

        if type_value.startswith("?"):
            return FlowTypeKind.MAYBE
        if "|" in type_value and "{|" not in type_value:
            return FlowTypeKind.UNION
        if "&" in type_value:
            return FlowTypeKind.INTERSECTION
        if type_value.startswith("{|"):
            return FlowTypeKind.EXACT_OBJECT
        if type_value.startswith("{"):
            return FlowTypeKind.OBJECT
        if type_value.startswith("["):
            return FlowTypeKind.TUPLE
        if "Array<" in type_value or type_value.endswith("[]"):
            return FlowTypeKind.ARRAY
        if "=>" in type_value:
            return FlowTypeKind.FUNCTION
        if "<" in type_value:
            return FlowTypeKind.GENERIC
        if "typeof" in type_value:
            return FlowTypeKind.TYPEOF
        if type_value in (
            "string",
            "number",
            "boolean",
            "null",
            "void",
            "mixed",
            "any",
            "empty",
        ):
            return FlowTypeKind.PRIMITIVE
        if type_value.startswith('"') or type_value.startswith("'") or type_value.isdigit():
            return FlowTypeKind.LITERAL

        return FlowTypeKind.CLASS

    def _find_utility_types(self, code: str) -> list[str]:
        """Find Flow utility types used in code."""
        found: list[str] = []
        for util in self.UTILITY_TYPES:
            if util in code:
                found.append(util)
        return found

    def _find_maybe_types(self, code: str) -> list[tuple[int, int]]:
        """Find maybe type (?T) usages."""
        usages: list[tuple[int, int]] = []
        for match in self._MAYBE_TYPE_PATTERN.finditer(code):
            line = code[: match.start()].count("\n") + 1
            column = match.start() - code.rfind("\n", 0, match.start()) - 1
            usages.append((line, column))
        return usages

    def _find_exact_objects(self, code: str) -> list[tuple[int, int]]:
        """Find exact object type ({| |}) usages."""
        usages: list[tuple[int, int]] = []
        for match in self._EXACT_OBJECT_PATTERN.finditer(code):
            line = code[: match.start()].count("\n") + 1
            column = match.start() - code.rfind("\n", 0, match.start()) - 1
            usages.append((line, column))
        return usages

    def _find_suppress_comments(self, code: str) -> list[tuple[int, str]]:
        """Find Flow suppress comments."""
        comments: list[tuple[int, str]] = []
        for match in self._SUPPRESS_PATTERN.finditer(code):
            line = code[: match.start()].count("\n") + 1
            comment_type = match.group(0).split("$Flow")[1]
            comments.append((line, comment_type))
        return comments

    def check(self, file_path: str) -> list[FlowError]:
        """
        Run Flow type checking on a file.

        :param file_path: Path to file.
        :return: List of Flow errors.
        """
        if not self._flow_path:
            raise RuntimeError("Flow not found. Install with: npm install flow-bin")

        cmd = self._flow_path.split() if " " in self._flow_path else [self._flow_path]
        cmd.extend(["check", "--json", file_path])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            errors: list[FlowError] = []
            try:
                data = json.loads(result.stdout)
                for error in data.get("errors", []):
                    for message in error.get("message", []):
                        loc = message.get("loc", {})
                        errors.append(
                            FlowError(
                                message=message.get("descr", ""),
                                severity=FlowSeverity.ERROR,
                                line=loc.get("start", {}).get("line", 0),
                                column=loc.get("start", {}).get("column", 0),
                                end_line=loc.get("end", {}).get("line", 0),
                                end_column=loc.get("end", {}).get("column", 0),
                                file_path=loc.get("source", file_path),
                            )
                        )
            except json.JSONDecodeError:
                pass

            return errors
        except subprocess.TimeoutExpired:
            raise TimeoutError("Flow timed out")

    def get_coverage(self, file_path: str) -> FlowCoverage:
        """
        Get type coverage for a file.

        :param file_path: Path to file.
        :return: FlowCoverage object.
        """
        if not self._flow_path:
            raise RuntimeError("Flow not found")

        cmd = self._flow_path.split() if " " in self._flow_path else [self._flow_path]
        cmd.extend(["coverage", "--json", file_path])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            try:
                data = json.loads(result.stdout)
                expressions = data.get("expressions", {})
                return FlowCoverage(
                    covered_count=expressions.get("covered_count", 0),
                    uncovered_count=expressions.get("uncovered_count", 0),
                    empty_count=expressions.get("empty_count", 0),
                )
            except json.JSONDecodeError:
                return FlowCoverage()
        except subprocess.TimeoutExpired:
            raise TimeoutError("Flow coverage timed out")

    def parse_config(self, config_path: str = ".flowconfig") -> FlowConfig:
        """
        Parse a .flowconfig file.

        :param config_path: Path to .flowconfig.
        :return: FlowConfig object.
        """
        path = Path(config_path)

        if not path.exists():
            raise FileNotFoundError(f"Flow config not found: {config_path}")

        config = FlowConfig()
        current_section = None

        with open(path) as f:
            for line in f:
                line = line.strip()

                if not line or line.startswith("#"):
                    continue

                if line.startswith("[") and line.endswith("]"):
                    current_section = line[1:-1]
                    continue

                if current_section == "ignore":
                    config.ignore.append(line)
                elif current_section == "include":
                    config.include.append(line)
                elif current_section == "libs":
                    config.libs.append(line)
                elif current_section == "lints":
                    if "=" in line:
                        key, value = line.split("=", 1)
                        config.lints[key.strip()] = value.strip()
                elif current_section == "options":
                    if "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip()

                        # Parse common options
                        if key == "all":
                            config.all_ = value.lower() == "true"
                        elif key == "strict":
                            config.strict = value.lower() == "true"
                        else:
                            config.options[key] = value
                elif current_section == "version":
                    config.version = line

        return config

    def strip_flow_types(self, code: str) -> str:
        """
        Strip Flow type annotations from code.

        :param code: JavaScript code with Flow types.
        :return: Plain JavaScript without types.
        """
        # Remove type annotations after colons
        code = re.sub(r":\s*\??\w+(?:<[^>]+>)?(?:\[\])?", "", code)

        # Remove type imports
        code = re.sub(r"import\s+type\s+\{[^}]+\}\s+from\s+['\"][^'\"]+['\"];?", "", code)
        code = re.sub(r"import\s+type\s+\w+\s+from\s+['\"][^'\"]+['\"];?", "", code)

        # Remove type exports
        code = re.sub(r"export\s+type\s+\{[^}]+\};?", "", code)

        # Remove type aliases
        code = re.sub(
            r"(?:export\s+)?(?:opaque\s+)?type\s+\w+(?:<[^>]+>)?(?:\s*:\s*\w+)?\s*=[^;]+;",
            "",
            code,
        )

        # Remove interfaces
        code = re.sub(r"(?:export\s+)?interface\s+\w+[^{]*\{[^}]+\}", "", code)

        # Remove flow pragma
        code = re.sub(r"/\*\s*@flow\s*\*/", "", code)
        code = re.sub(r"//\s*@flow", "", code)

        return code
