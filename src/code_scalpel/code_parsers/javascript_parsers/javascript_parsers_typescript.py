#!/usr/bin/env python3
"""
TypeScript Parser - TypeScript-specific code analysis.

Dedicated TypeScript analysis with type system awareness, leveraging the
TypeScript compiler API through subprocess execution.


Features:
    Type Extraction:
        - Interface declaration parsing
        - Type alias parsing
        - Generic type parameter analysis
        - Type kind classification (union, intersection, mapped, etc.)

    Enum Analysis:
        - Enum declaration extraction
        - Const enum detection
        - Member value extraction
        - String/numeric enum differentiation

    Decorator Detection:
        - Class/method/property/parameter decorators
        - Decorator argument extraction
        - Common decorator categorization

    Namespace/Module:
        - Namespace declaration parsing
        - Module declaration parsing
        - Export detection within namespaces

    Type Guards:
        - Type predicate function detection
        - Parameter and return type extraction

    Type Quality:
        - `any` type usage detection
        - Type coverage estimation
        - Explicit vs inferred type analysis

    Type Checking:
        - TypeScript compiler integration (tsc)
        - Error extraction with diagnostics
        - Declaration file (.d.ts) generation

Future Enhancements:
    - tsconfig.json analysis
    - Conditional type analysis
    - Template literal type detection
    - Module augmentation detection
"""

import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class TypeKind(Enum):
    """TypeScript type kinds."""

    PRIMITIVE = "primitive"  # string, number, boolean, etc.
    LITERAL = "literal"  # "hello", 42, true
    UNION = "union"  # A | B
    INTERSECTION = "intersection"  # A & B
    ARRAY = "array"  # T[]
    TUPLE = "tuple"  # [A, B, C]
    OBJECT = "object"  # { key: value }
    FUNCTION = "function"  # (a: A) => B
    GENERIC = "generic"  # T<U>
    CONDITIONAL = "conditional"  # T extends U ? A : B
    MAPPED = "mapped"  # { [K in keyof T]: U }
    INDEXED = "indexed"  # T[K]
    TEMPLATE_LITERAL = "template_literal"  # `hello${string}`
    INFER = "infer"  # infer U
    KEYOF = "keyof"  # keyof T
    TYPEOF = "typeof"  # typeof x
    UNKNOWN = "unknown"


class DecoratorKind(Enum):
    """Common decorator categories."""

    CLASS = "class"
    METHOD = "method"
    PROPERTY = "property"
    PARAMETER = "parameter"
    ACCESSOR = "accessor"


@dataclass
class TypeAnnotation:
    """A TypeScript type annotation."""

    text: str  # Full type text
    kind: TypeKind
    line: int
    column: int
    is_optional: bool = False
    is_readonly: bool = False
    type_arguments: list["TypeAnnotation"] = field(default_factory=list)
    union_members: list["TypeAnnotation"] = field(default_factory=list)
    intersection_members: list["TypeAnnotation"] = field(default_factory=list)


@dataclass
class TypeParameter:
    """A generic type parameter."""

    name: str  # T, U, K, etc.
    constraint: str | None = None  # extends clause
    default: str | None = None  # = DefaultType
    line: int = 0


@dataclass
class InterfaceDeclaration:
    """A TypeScript interface declaration."""

    name: str
    line: int
    column: int
    end_line: int | None = None
    type_parameters: list[TypeParameter] = field(default_factory=list)
    extends: list[str] = field(default_factory=list)
    properties: list["PropertySignature"] = field(default_factory=list)
    methods: list["MethodSignature"] = field(default_factory=list)
    index_signatures: list["IndexSignature"] = field(default_factory=list)
    is_exported: bool = False
    jsdoc: str | None = None


@dataclass
class TypeAliasDeclaration:
    """A TypeScript type alias (type X = ...)."""

    name: str
    line: int
    column: int
    type_value: str  # The actual type definition
    type_kind: TypeKind
    type_parameters: list[TypeParameter] = field(default_factory=list)
    is_exported: bool = False
    jsdoc: str | None = None


@dataclass
class PropertySignature:
    """A property in an interface or type."""

    name: str
    type_annotation: TypeAnnotation | None
    is_optional: bool = False
    is_readonly: bool = False
    line: int = 0


@dataclass
class MethodSignature:
    """A method signature in an interface."""

    name: str
    parameters: list["ParameterDeclaration"] = field(default_factory=list)
    return_type: TypeAnnotation | None = None
    type_parameters: list[TypeParameter] = field(default_factory=list)
    is_optional: bool = False
    line: int = 0


@dataclass
class IndexSignature:
    """An index signature [key: KeyType]: ValueType."""

    key_name: str
    key_type: str
    value_type: str
    is_readonly: bool = False
    line: int = 0


@dataclass
class ParameterDeclaration:
    """A function/method parameter."""

    name: str
    type_annotation: TypeAnnotation | None = None
    is_optional: bool = False
    is_rest: bool = False  # ...args
    default_value: str | None = None
    line: int = 0


@dataclass
class EnumDeclaration:
    """A TypeScript enum declaration."""

    name: str
    line: int
    column: int
    members: list["EnumMember"] = field(default_factory=list)
    is_const: bool = False  # const enum
    is_exported: bool = False


@dataclass
class EnumMember:
    """An enum member."""

    name: str
    value: str | int | None = None
    is_computed: bool = False
    line: int = 0


@dataclass
class DecoratorUsage:
    """A decorator usage (@Decorator)."""

    name: str
    kind: DecoratorKind
    line: int
    column: int
    arguments: list[str] = field(default_factory=list)
    target_name: str | None = None  # Name of decorated element


@dataclass
class NamespaceDeclaration:
    """A TypeScript namespace/module declaration."""

    name: str
    line: int
    column: int
    end_line: int | None = None
    is_exported: bool = False
    is_ambient: bool = False  # declare namespace
    nested_namespaces: list["NamespaceDeclaration"] = field(default_factory=list)
    exports: list[str] = field(default_factory=list)


@dataclass
class TypeGuard:
    """A type guard function/expression."""

    parameter_name: str
    guarded_type: str
    function_name: str | None = None
    line: int = 0
    is_assertion: bool = False  # asserts x is T


@dataclass
class TypeScriptAnalysis:
    """Complete TypeScript analysis results."""

    interfaces: list[InterfaceDeclaration] = field(default_factory=list)
    type_aliases: list[TypeAliasDeclaration] = field(default_factory=list)
    enums: list[EnumDeclaration] = field(default_factory=list)
    decorators: list[DecoratorUsage] = field(default_factory=list)
    namespaces: list[NamespaceDeclaration] = field(default_factory=list)
    type_guards: list[TypeGuard] = field(default_factory=list)
    type_parameters: list[TypeParameter] = field(default_factory=list)
    any_usages: list[tuple[int, int]] = field(default_factory=list)  # (line, column)
    type_coverage: float = 0.0  # Percentage of typed declarations
    has_strict_null_checks: bool = False


class TypeScriptParser:
    """
    Parser for TypeScript-specific features.

    Analyzes TypeScript code for type information, interfaces, type aliases,
    enums, decorators, and other TypeScript-specific constructs.

    Example usage:
        parser = TypeScriptParser()

        # Analyze TypeScript code
        analysis = parser.analyze(code)

        # Get all interfaces
        interfaces = analysis.interfaces

        # Check type coverage
        coverage = analysis.type_coverage
    """

    # Regex patterns for TypeScript constructs
    _INTERFACE_PATTERN = re.compile(
        r"(?:export\s+)?interface\s+(\w+)(?:<([^>]+)>)?(?:\s+extends\s+([^{]+))?\s*\{",
        re.MULTILINE,
    )
    _TYPE_ALIAS_PATTERN = re.compile(r"(?:export\s+)?type\s+(\w+)(?:<([^>]+)>)?\s*=\s*([^;]+);", re.MULTILINE)
    _ENUM_PATTERN = re.compile(r"(?:export\s+)?(?:const\s+)?enum\s+(\w+)\s*\{([^}]+)\}", re.MULTILINE)
    _DECORATOR_PATTERN = re.compile(
        r"@(\w+)(?:\(([^)]*)\))?\s*(?:(?:export\s+)?(?:class|function|get|set|async)|\w+\s*[:(])",
        re.MULTILINE,
    )
    _NAMESPACE_PATTERN = re.compile(r"(?:export\s+)?(?:declare\s+)?(?:namespace|module)\s+(\w+)\s*\{", re.MULTILINE)
    _TYPE_GUARD_PATTERN = re.compile(r"(\w+)\s+is\s+(\w+(?:\[\])?(?:<[^>]+>)?)", re.MULTILINE)
    _ANY_USAGE_PATTERN = re.compile(r":\s*any\b|<any>|as\s+any\b", re.MULTILINE)

    def __init__(self, tsc_path: str | None = None):
        """
        Initialize TypeScript parser.

        :param tsc_path: Path to TypeScript compiler (tsc).
        """
        self._tsc_path = tsc_path or self._find_tsc()

    def _find_tsc(self) -> str | None:
        """Find TypeScript compiler."""
        tsc = shutil.which("tsc")
        if tsc:
            return tsc

        local = Path("node_modules/.bin/tsc")
        if local.exists():
            return str(local)

        if shutil.which("npx"):
            return "npx tsc"

        return None

    def analyze(self, code: str, filename: str = "input.ts") -> TypeScriptAnalysis:
        """
        Analyze TypeScript code.

        :param code: TypeScript source code.
        :param filename: Virtual filename for error reporting.
        :return: TypeScriptAnalysis with extracted type information.
        """
        analysis = TypeScriptAnalysis()

        # Extract interfaces
        analysis.interfaces = self._extract_interfaces(code)

        # Extract type aliases
        analysis.type_aliases = self._extract_type_aliases(code)

        # Extract enums
        analysis.enums = self._extract_enums(code)

        # Extract decorators
        analysis.decorators = self._extract_decorators(code)

        # Extract namespaces
        analysis.namespaces = self._extract_namespaces(code)

        # Extract type guards
        analysis.type_guards = self._extract_type_guards(code)

        # Find any usages
        analysis.any_usages = self._find_any_usages(code)

        # Calculate type coverage
        analysis.type_coverage = self._calculate_type_coverage(code)

        return analysis

    def analyze_file(self, file_path: str) -> TypeScriptAnalysis:
        """
        Analyze a TypeScript file.

        :param file_path: Path to TypeScript file.
        :return: TypeScriptAnalysis.
        """
        path = Path(file_path)
        code = path.read_text(encoding="utf-8")
        return self.analyze(code, path.name)

    def _extract_interfaces(self, code: str) -> list[InterfaceDeclaration]:
        """Extract interface declarations."""
        interfaces: list[InterfaceDeclaration] = []
        code.split("\n")

        for match in self._INTERFACE_PATTERN.finditer(code):
            name = match.group(1)
            type_params_str = match.group(2)
            extends_str = match.group(3)

            # Calculate line number
            line = code[: match.start()].count("\n") + 1
            column = match.start() - code.rfind("\n", 0, match.start()) - 1

            # Parse type parameters
            type_parameters = self._parse_type_parameters(type_params_str) if type_params_str else []

            # Parse extends clause
            extends = [e.strip() for e in extends_str.split(",")] if extends_str else []

            # Check if exported
            is_exported = "export" in code[max(0, match.start() - 20) : match.start()]

            # Find end of interface (simple brace matching)
            end_line = self._find_closing_brace(code, match.end() - 1)

            interfaces.append(
                InterfaceDeclaration(
                    name=name,
                    line=line,
                    column=column,
                    end_line=end_line,
                    type_parameters=type_parameters,
                    extends=extends,
                    is_exported=is_exported,
                )
            )

        return interfaces

    def _extract_type_aliases(self, code: str) -> list[TypeAliasDeclaration]:
        """Extract type alias declarations."""
        aliases: list[TypeAliasDeclaration] = []

        for match in self._TYPE_ALIAS_PATTERN.finditer(code):
            name = match.group(1)
            type_params_str = match.group(2)
            type_value = match.group(3).strip()

            line = code[: match.start()].count("\n") + 1
            column = match.start() - code.rfind("\n", 0, match.start()) - 1

            type_parameters = self._parse_type_parameters(type_params_str) if type_params_str else []
            is_exported = "export" in code[max(0, match.start() - 20) : match.start()]

            # Determine type kind
            type_kind = self._determine_type_kind(type_value)

            aliases.append(
                TypeAliasDeclaration(
                    name=name,
                    line=line,
                    column=column,
                    type_value=type_value,
                    type_kind=type_kind,
                    type_parameters=type_parameters,
                    is_exported=is_exported,
                )
            )

        return aliases

    def _extract_enums(self, code: str) -> list[EnumDeclaration]:
        """Extract enum declarations."""
        enums: list[EnumDeclaration] = []

        for match in self._ENUM_PATTERN.finditer(code):
            name = match.group(1)
            body = match.group(2)

            line = code[: match.start()].count("\n") + 1
            column = match.start() - code.rfind("\n", 0, match.start()) - 1

            is_const = "const" in code[max(0, match.start() - 10) : match.start()]
            is_exported = "export" in code[max(0, match.start() - 20) : match.start()]

            # Parse members
            members: list[EnumMember] = []
            for member_match in re.finditer(r"(\w+)(?:\s*=\s*([^,}]+))?", body):
                member_name = member_match.group(1)
                member_value = member_match.group(2)

                if member_value:
                    member_value = member_value.strip()
                    # Try to parse as number
                    try:
                        parsed_value: str | int | None = int(member_value)
                    except ValueError:
                        parsed_value = member_value.strip("\"'")
                else:
                    parsed_value = None

                members.append(
                    EnumMember(
                        name=member_name,
                        value=parsed_value,
                    )
                )

            enums.append(
                EnumDeclaration(
                    name=name,
                    line=line,
                    column=column,
                    members=members,
                    is_const=is_const,
                    is_exported=is_exported,
                )
            )

        return enums

    def _extract_decorators(self, code: str) -> list[DecoratorUsage]:
        """Extract decorator usages."""
        decorators: list[DecoratorUsage] = []

        for match in self._DECORATOR_PATTERN.finditer(code):
            name = match.group(1)
            args_str = match.group(2)

            line = code[: match.start()].count("\n") + 1
            column = match.start() - code.rfind("\n", 0, match.start()) - 1

            # Determine decorator kind from context
            following = code[match.end() : match.end() + 50]
            if "class" in following[:20]:
                kind = DecoratorKind.CLASS
            elif any(kw in following[:20] for kw in ("get ", "set ")):
                kind = DecoratorKind.ACCESSOR
            elif "(" in following[:30]:
                kind = DecoratorKind.METHOD
            else:
                kind = DecoratorKind.PROPERTY

            arguments = [a.strip() for a in args_str.split(",")] if args_str else []

            decorators.append(
                DecoratorUsage(
                    name=name,
                    kind=kind,
                    line=line,
                    column=column,
                    arguments=arguments,
                )
            )

        return decorators

    def _extract_namespaces(self, code: str) -> list[NamespaceDeclaration]:
        """Extract namespace/module declarations."""
        namespaces: list[NamespaceDeclaration] = []

        for match in self._NAMESPACE_PATTERN.finditer(code):
            name = match.group(1)

            line = code[: match.start()].count("\n") + 1
            column = match.start() - code.rfind("\n", 0, match.start()) - 1

            is_exported = "export" in code[max(0, match.start() - 20) : match.start()]
            is_ambient = "declare" in code[max(0, match.start() - 20) : match.start()]

            end_line = self._find_closing_brace(code, match.end() - 1)

            namespaces.append(
                NamespaceDeclaration(
                    name=name,
                    line=line,
                    column=column,
                    end_line=end_line,
                    is_exported=is_exported,
                    is_ambient=is_ambient,
                )
            )

        return namespaces

    def _extract_type_guards(self, code: str) -> list[TypeGuard]:
        """Extract type guard expressions."""
        guards: list[TypeGuard] = []

        for match in self._TYPE_GUARD_PATTERN.finditer(code):
            param_name = match.group(1)
            guarded_type = match.group(2)

            line = code[: match.start()].count("\n") + 1

            # Check for assertion form
            is_assertion = "asserts" in code[max(0, match.start() - 20) : match.start()]

            guards.append(
                TypeGuard(
                    parameter_name=param_name,
                    guarded_type=guarded_type,
                    line=line,
                    is_assertion=is_assertion,
                )
            )

        return guards

    def _find_any_usages(self, code: str) -> list[tuple[int, int]]:
        """Find all usages of 'any' type."""
        usages: list[tuple[int, int]] = []

        for match in self._ANY_USAGE_PATTERN.finditer(code):
            line = code[: match.start()].count("\n") + 1
            column = match.start() - code.rfind("\n", 0, match.start()) - 1
            usages.append((line, column))

        return usages

    def _calculate_type_coverage(self, code: str) -> float:
        """Calculate percentage of declarations with explicit types."""
        # Count declarations
        declarations = len(re.findall(r"\b(?:let|const|var)\s+\w+", code))
        declarations += len(re.findall(r"function\s+\w+\s*\([^)]*\)", code))
        declarations += len(re.findall(r"=>", code))  # Arrow functions

        if declarations == 0:
            return 100.0

        # Count typed declarations
        typed = len(re.findall(r":\s*\w+(?:<[^>]+>)?(?:\[\])?\s*[=;,)]", code))
        typed += len(re.findall(r"\)\s*:\s*\w+", code))  # Return types

        return min(100.0, (typed / declarations) * 100)

    def _parse_type_parameters(self, params_str: str) -> list[TypeParameter]:
        """Parse generic type parameters."""
        params: list[TypeParameter] = []

        if not params_str:
            return params

        # Simple parsing (doesn't handle all edge cases)
        for param in params_str.split(","):
            param = param.strip()

            name = param
            constraint = None
            default = None

            if " extends " in param:
                parts = param.split(" extends ", 1)
                name = parts[0].strip()
                rest = parts[1]
                if " = " in rest:
                    constraint, default = rest.split(" = ", 1)
                    constraint = constraint.strip()
                    default = default.strip()
                else:
                    constraint = rest.strip()
            elif " = " in param:
                name, default = param.split(" = ", 1)
                name = name.strip()
                default = default.strip()

            params.append(
                TypeParameter(
                    name=name,
                    constraint=constraint,
                    default=default,
                )
            )

        return params

    def _determine_type_kind(self, type_value: str) -> TypeKind:
        """Determine the kind of a type from its string representation."""
        type_value = type_value.strip()

        if "|" in type_value:
            return TypeKind.UNION
        if "&" in type_value:
            return TypeKind.INTERSECTION
        if type_value.endswith("[]"):
            return TypeKind.ARRAY
        if type_value.startswith("[") and type_value.endswith("]"):
            return TypeKind.TUPLE
        if type_value.startswith("{"):
            return TypeKind.OBJECT
        if "=>" in type_value or type_value.startswith("("):
            return TypeKind.FUNCTION
        if "<" in type_value and ">" in type_value:
            return TypeKind.GENERIC
        if " extends " in type_value and "?" in type_value:
            return TypeKind.CONDITIONAL
        if "keyof" in type_value:
            return TypeKind.KEYOF
        if "typeof" in type_value:
            return TypeKind.TYPEOF
        if type_value in (
            "string",
            "number",
            "boolean",
            "null",
            "undefined",
            "void",
            "never",
            "unknown",
            "any",
            "object",
            "symbol",
            "bigint",
        ):
            return TypeKind.PRIMITIVE
        if type_value.startswith('"') or type_value.startswith("'") or type_value.isdigit():
            return TypeKind.LITERAL

        return TypeKind.UNKNOWN

    def _find_closing_brace(self, code: str, start: int) -> int:
        """Find the line number of the closing brace."""
        depth = 1
        i = start + 1

        while i < len(code) and depth > 0:
            if code[i] == "{":
                depth += 1
            elif code[i] == "}":
                depth -= 1
            i += 1

        return code[:i].count("\n") + 1

    def check_types(
        self,
        file_path: str,
        strict: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Run TypeScript type checking on a file.

        :param file_path: Path to TypeScript file.
        :param strict: Whether to use strict mode.
        :return: List of type errors.
        """
        if not self._tsc_path:
            raise RuntimeError("TypeScript compiler not found. Install with: npm install typescript")

        cmd = self._tsc_path.split() if " " in self._tsc_path else [self._tsc_path]
        cmd.extend(["--noEmit", "--pretty", "false"])

        if strict:
            cmd.extend(["--strict"])

        cmd.append(file_path)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            errors: list[dict[str, Any]] = []
            for line in result.stdout.split("\n"):
                if line and "(" in line:
                    # Parse error line: file.ts(line,col): error TS1234: message
                    match = re.match(
                        r"(.+)\((\d+),(\d+)\):\s*(error|warning)\s+(TS\d+):\s*(.+)",
                        line,
                    )
                    if match:
                        errors.append(
                            {
                                "file": match.group(1),
                                "line": int(match.group(2)),
                                "column": int(match.group(3)),
                                "severity": match.group(4),
                                "code": match.group(5),
                                "message": match.group(6),
                            }
                        )

            return errors
        except subprocess.TimeoutExpired:
            raise TimeoutError("TypeScript compiler timed out")

    def get_declaration_file(self, code: str) -> str:
        """
        Generate a .d.ts declaration file from TypeScript code.

        :param code: TypeScript source code.
        :return: Declaration file content.
        """
        if not self._tsc_path:
            raise RuntimeError("TypeScript compiler not found")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".ts", delete=False) as f:
            f.write(code)
            temp_path = f.name

        try:
            cmd = self._tsc_path.split() if " " in self._tsc_path else [self._tsc_path]
            cmd.extend(
                [
                    "--declaration",
                    "--emitDeclarationOnly",
                    "--outDir",
                    tempfile.gettempdir(),
                    temp_path,
                ]
            )

            subprocess.run(cmd, capture_output=True, timeout=30)

            dts_path = Path(temp_path).with_suffix(".d.ts")
            dts_path = Path(tempfile.gettempdir()) / dts_path.name

            if dts_path.exists():
                return dts_path.read_text()
            return ""
        finally:
            Path(temp_path).unlink(missing_ok=True)
