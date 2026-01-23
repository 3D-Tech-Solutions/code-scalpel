"""
TypeScript Control-Flow Type Narrowing Analysis.

[20251216_FEATURE] v2.2.0 - Type narrowing to reduce false positives in taint tracking.

This module analyzes TypeScript/JavaScript control flow to detect type guards
and track type narrowing through branches. This reduces false positives by
recognizing when a variable has been narrowed to a safe type.

Supported Type Guards:
- typeof checks: `typeof x === 'string'`
- instanceof checks: `x instanceof Date`
- in operator: `'prop' in obj`
- Truthiness checks: `if (x)`
- Equality checks: `x === null`, `x !== undefined`
- Custom type predicates: `isString(x)`

Example:
    ```typescript
    function process(input: unknown) {
        if (typeof input === 'string') {
            // input narrowed to string - safer for SQL
            return db.query(`SELECT * FROM users WHERE name = '${input}'`);
        }
    }
    ```
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tree_sitter import Node as TSNode

try:
    import tree_sitter
    from tree_sitter import Node as TSNode

    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    TSNode = Any  # type: ignore


class NarrowedType(Enum):
    """Types that a variable can be narrowed to."""

    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    OBJECT = "object"
    FUNCTION = "function"
    UNDEFINED = "undefined"
    NULL = "null"
    SYMBOL = "symbol"
    BIGINT = "bigint"
    # Special narrowed types
    ARRAY = "array"
    DATE = "date"
    REGEXP = "regexp"
    # Custom validated types
    VALIDATED = "validated"
    # Unknown (not narrowed)
    UNKNOWN = "unknown"


# [20251216_FEATURE] Safe types that eliminate taint risk
SAFE_PRIMITIVE_TYPES = {
    NarrowedType.NUMBER,
    NarrowedType.BOOLEAN,
    NarrowedType.NULL,
    NarrowedType.UNDEFINED,
    NarrowedType.BIGINT,
}

# Types that reduce but don't eliminate risk
REDUCED_RISK_TYPES = {
    NarrowedType.DATE,
    NarrowedType.REGEXP,
    NarrowedType.VALIDATED,
}


@dataclass
class TypeGuard:
    """Represents a detected type guard in code."""

    variable: str
    guard_type: str  # 'typeof', 'instanceof', 'in', 'equality', 'truthiness', 'predicate'
    narrowed_to: NarrowedType
    condition_text: str
    line: int
    negated: bool = False  # True if guard is in else branch


@dataclass
class BranchState:
    """Type state within a specific branch."""

    variable_types: dict[str, set[NarrowedType]] = field(default_factory=dict)
    is_else_branch: bool = False

    def narrow(self, variable: str, to_type: NarrowedType) -> None:
        """Narrow a variable to a specific type."""
        if variable not in self.variable_types:
            self.variable_types[variable] = set()
        self.variable_types[variable].add(to_type)

    def get_types(self, variable: str) -> set[NarrowedType]:
        """Get the narrowed types for a variable."""
        return self.variable_types.get(variable, {NarrowedType.UNKNOWN})


@dataclass
class NarrowingResult:
    """Result of type narrowing analysis."""

    type_guards: list[TypeGuard]
    branch_states: dict[int, BranchState]  # line -> state
    taint_eliminated: dict[str, bool]  # variable -> is eliminated
    taint_reduced: dict[str, bool]  # variable -> is reduced
    analysis_summary: dict[str, Any]


class TypeNarrowing:
    """
    Analyze TypeScript control flow for type narrowing.

    [20251216_FEATURE] Detects type guards and tracks narrowing through branches
    to reduce false positives in taint analysis.
    """

    # typeof result mappings
    TYPEOF_MAPPINGS = {
        "string": NarrowedType.STRING,
        "number": NarrowedType.NUMBER,
        "boolean": NarrowedType.BOOLEAN,
        "object": NarrowedType.OBJECT,
        "function": NarrowedType.FUNCTION,
        "undefined": NarrowedType.UNDEFINED,
        "symbol": NarrowedType.SYMBOL,
        "bigint": NarrowedType.BIGINT,
    }

    # instanceof class mappings
    INSTANCEOF_MAPPINGS = {
        "Array": NarrowedType.ARRAY,
        "Date": NarrowedType.DATE,
        "RegExp": NarrowedType.REGEXP,
        "String": NarrowedType.STRING,
        "Number": NarrowedType.NUMBER,
        "Boolean": NarrowedType.BOOLEAN,
    }

    # Custom type predicate patterns
    TYPE_PREDICATES = {
        "isString": NarrowedType.STRING,
        "isNumber": NarrowedType.NUMBER,
        "isBoolean": NarrowedType.BOOLEAN,
        "isArray": NarrowedType.ARRAY,
        "isObject": NarrowedType.OBJECT,
        "isValid": NarrowedType.VALIDATED,
        "isValidated": NarrowedType.VALIDATED,
        "isSafe": NarrowedType.VALIDATED,
        "isSanitized": NarrowedType.VALIDATED,
    }

    def __init__(self) -> None:
        """Initialize the type narrowing analyzer."""
        self._parser: Any = None
        if TREE_SITTER_AVAILABLE:
            try:
                import tree_sitter_typescript

                # Create Language object from the PyCapsule
                typescript_lang = tree_sitter.Language(tree_sitter_typescript.language_typescript())
                self._parser = tree_sitter.Parser(typescript_lang)
            except Exception:
                pass

    def analyze(self, code: str) -> NarrowingResult:
        """
        Analyze code for type narrowing patterns.

        Args:
            code: TypeScript/JavaScript source code

        Returns:
            NarrowingResult with detected guards and narrowing information
        """
        type_guards: list[TypeGuard] = []
        branch_states: dict[int, BranchState] = {}
        taint_eliminated: dict[str, bool] = {}
        taint_reduced: dict[str, bool] = {}

        if self._parser:
            try:
                tree = self._parser.parse(code.encode())
                if not tree or not tree.root_node:
                    raise ValueError("Parsing failed: tree or root_node is None")
            except Exception as e:
                raise ValueError(f"Parsing failed: {str(e)}")

            self._analyze_tree(
                tree.root_node,
                code,
                type_guards,
                branch_states,
                taint_eliminated,
                taint_reduced,
            )
        else:
            # Fallback: regex-based detection
            self._analyze_regex(code, type_guards, branch_states, taint_eliminated, taint_reduced)

        return NarrowingResult(
            type_guards=type_guards,
            branch_states=branch_states,
            taint_eliminated=taint_eliminated,
            taint_reduced=taint_reduced,
            analysis_summary={
                "total_guards": len(type_guards),
                "variables_narrowed": len(set(g.variable for g in type_guards)),
                "taint_eliminated_count": sum(taint_eliminated.values()),
                "taint_reduced_count": sum(taint_reduced.values()),
            },
        )

    def _analyze_tree(
        self,
        node: Any,
        code: str,
        type_guards: list[TypeGuard],
        branch_states: dict[int, BranchState],
        taint_eliminated: dict[str, bool],
        taint_reduced: dict[str, bool],
        current_branch: BranchState | None = None,
    ) -> None:
        """Recursively analyze AST for type guards."""
        if current_branch is None:
            current_branch = BranchState()

        # Check for if statements
        if node.type == "if_statement":
            self._analyze_if_statement(
                node,
                code,
                type_guards,
                branch_states,
                taint_eliminated,
                taint_reduced,
                current_branch,
            )

        # Recurse into children
        for child in node.children:
            self._analyze_tree(
                child,
                code,
                type_guards,
                branch_states,
                taint_eliminated,
                taint_reduced,
                current_branch,
            )

    def _analyze_if_statement(
        self,
        node: Any,
        code: str,
        type_guards: list[TypeGuard],
        branch_states: dict[int, BranchState],
        taint_eliminated: dict[str, bool],
        taint_reduced: dict[str, bool],
        parent_branch: BranchState,
    ) -> None:
        """Analyze an if statement for type guards."""
        # Find the condition
        condition = None
        consequence = None

        for child in node.children:
            if child.type == "parenthesized_expression":
                condition = child
            elif child.type == "statement_block" and consequence is None:
                consequence = child
            # Note: else_clause handled in future branch analysis

        if condition is None:
            return

        condition_text = code[condition.start_byte : condition.end_byte]
        line = condition.start_point[0] + 1

        # Detect type guards in condition
        guards = self._detect_type_guards(condition_text, line, code, condition)

        for guard in guards:
            type_guards.append(guard)

            # Create branch state for the if block
            if_branch = BranchState()
            if_branch.narrow(guard.variable, guard.narrowed_to)
            branch_states[line] = if_branch

            # Update taint status
            self._update_taint_status(
                guard.variable,
                guard.narrowed_to,
                taint_eliminated,
                taint_reduced,
            )

    def _detect_type_guards(
        self,
        condition_text: str,
        line: int,
        code: str,
        node: Any | None = None,
    ) -> list[TypeGuard]:
        """Detect type guards in a condition expression."""
        guards = []

        # Check for typeof
        guard = self._detect_typeof(condition_text, line)
        if guard:
            guards.append(guard)

        # Check for instanceof
        guard = self._detect_instanceof(condition_text, line)
        if guard:
            guards.append(guard)

        # Check for 'in' operator
        guard = self._detect_in_operator(condition_text, line)
        if guard:
            guards.append(guard)

        # Check for equality checks (null/undefined)
        guard = self._detect_equality(condition_text, line)
        if guard:
            guards.append(guard)

        # Check for type predicates
        guard = self._detect_type_predicate(condition_text, line)
        if guard:
            guards.append(guard)

        # Check for truthiness
        if not guards:
            guard = self._detect_truthiness(condition_text, line)
            if guard:
                guards.append(guard)

        return guards

    def _detect_typeof(self, condition: str, line: int) -> TypeGuard | None:
        """Detect typeof type guards."""
        import re

        # Pattern: typeof x === 'string' or typeof x !== 'string'
        pattern = r"typeof\s+(\w+)\s*(===?|!==?)\s*['\"](\w+)['\"]"
        match = re.search(pattern, condition)

        if match:
            variable = match.group(1)
            operator = match.group(2)
            type_str = match.group(3)
            negated = "!" in operator

            narrowed_to = self.TYPEOF_MAPPINGS.get(type_str, NarrowedType.UNKNOWN)

            return TypeGuard(
                variable=variable,
                guard_type="typeof",
                narrowed_to=narrowed_to,
                condition_text=condition,
                line=line,
                negated=negated,
            )

        return None

    def _detect_instanceof(self, condition: str, line: int) -> TypeGuard | None:
        """Detect instanceof type guards."""
        import re

        # Pattern: x instanceof Date
        pattern = r"(\w+)\s+instanceof\s+(\w+)"
        match = re.search(pattern, condition)

        if match:
            variable = match.group(1)
            class_name = match.group(2)
            negated = condition.strip().startswith("!")

            narrowed_to = self.INSTANCEOF_MAPPINGS.get(class_name, NarrowedType.OBJECT)

            return TypeGuard(
                variable=variable,
                guard_type="instanceof",
                narrowed_to=narrowed_to,
                condition_text=condition,
                line=line,
                negated=negated,
            )

        return None

    def _detect_in_operator(self, condition: str, line: int) -> TypeGuard | None:
        """Detect 'in' operator type guards."""
        import re

        # Pattern: 'prop' in obj
        pattern = r"['\"](\w+)['\"]\s+in\s+(\w+)"
        match = re.search(pattern, condition)

        if match:
            # match.group(1) is the property name, group(2) is the object
            variable = match.group(2)

            return TypeGuard(
                variable=variable,
                guard_type="in",
                narrowed_to=NarrowedType.OBJECT,
                condition_text=condition,
                line=line,
                negated=False,
            )

        return None

    def _detect_equality(self, condition: str, line: int) -> TypeGuard | None:
        """Detect null/undefined equality checks."""
        import re

        # Pattern: x === null, x !== undefined, x == null
        pattern = r"(\w+)\s*(===?|!==?)\s*(null|undefined)"
        match = re.search(pattern, condition)

        if match:
            variable = match.group(1)
            operator = match.group(2)
            value = match.group(3)
            negated = "!" in operator

            if value == "null":
                narrowed_to = NarrowedType.NULL
            else:
                narrowed_to = NarrowedType.UNDEFINED

            return TypeGuard(
                variable=variable,
                guard_type="equality",
                narrowed_to=narrowed_to,
                condition_text=condition,
                line=line,
                negated=negated,
            )

        return None

    def _detect_type_predicate(self, condition: str, line: int) -> TypeGuard | None:
        """Detect custom type predicate functions."""
        import re

        # Pattern: isString(x), Array.isArray(x)
        for predicate, narrowed_to in self.TYPE_PREDICATES.items():
            pattern = rf"{predicate}\s*\(\s*(\w+)\s*\)"
            match = re.search(pattern, condition)

            if match:
                variable = match.group(1)
                negated = condition.strip().startswith("!")

                return TypeGuard(
                    variable=variable,
                    guard_type="predicate",
                    narrowed_to=narrowed_to,
                    condition_text=condition,
                    line=line,
                    negated=negated,
                )

        # Array.isArray special case
        pattern = r"Array\.isArray\s*\(\s*(\w+)\s*\)"
        match = re.search(pattern, condition)
        if match:
            return TypeGuard(
                variable=match.group(1),
                guard_type="predicate",
                narrowed_to=NarrowedType.ARRAY,
                condition_text=condition,
                line=line,
                negated=condition.strip().startswith("!"),
            )

        return None

    def _detect_truthiness(self, condition: str, line: int) -> TypeGuard | None:
        """Detect simple truthiness checks."""
        import re

        # Pattern: if (x) or if (!x)
        condition = condition.strip()
        if condition.startswith("("):
            condition = condition[1:]
        if condition.endswith(")"):
            condition = condition[:-1]
        condition = condition.strip()

        negated = condition.startswith("!")
        if negated:
            condition = condition[1:].strip()

        # Simple identifier
        if re.match(r"^\w+$", condition):
            return TypeGuard(
                variable=condition,
                guard_type="truthiness",
                narrowed_to=NarrowedType.UNKNOWN,  # Narrows to truthy but type unknown
                condition_text=condition,
                line=line,
                negated=negated,
            )

        return None

    def _update_taint_status(
        self,
        variable: str,
        narrowed_to: NarrowedType,
        taint_eliminated: dict[str, bool],
        taint_reduced: dict[str, bool],
    ) -> None:
        """Update taint elimination/reduction status based on narrowing."""
        if narrowed_to in SAFE_PRIMITIVE_TYPES:
            taint_eliminated[variable] = True
            taint_reduced[variable] = True
        elif narrowed_to in REDUCED_RISK_TYPES:
            taint_eliminated[variable] = False
            taint_reduced[variable] = True
        else:
            # String or object - still risky
            if variable not in taint_eliminated:
                taint_eliminated[variable] = False
            if variable not in taint_reduced:
                taint_reduced[variable] = False

    def _analyze_regex(
        self,
        code: str,
        type_guards: list[TypeGuard],
        branch_states: dict[int, BranchState],
        taint_eliminated: dict[str, bool],
        taint_reduced: dict[str, bool],
    ) -> None:
        """Fallback regex-based analysis when tree-sitter unavailable."""
        import re

        lines = code.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Look for if statements with type guards
            if "if" in line and "(" in line:
                # Extract condition
                match = re.search(r"if\s*\((.*)\)", line)
                if match:
                    condition = match.group(1)
                    guards = self._detect_type_guards(condition, line_num, code, None)

                    for guard in guards:
                        type_guards.append(guard)

                        branch = BranchState()
                        branch.narrow(guard.variable, guard.narrowed_to)
                        branch_states[line_num] = branch

                        self._update_taint_status(
                            guard.variable,
                            guard.narrowed_to,
                            taint_eliminated,
                            taint_reduced,
                        )

    def is_taint_eliminated(self, variable: str, result: NarrowingResult, at_line: int | None = None) -> bool:
        """
        Check if taint is eliminated for a variable.

        Args:
            variable: Variable name to check
            result: NarrowingResult from analyze()
            at_line: Optional line number to check branch-specific state

        Returns:
            True if taint is eliminated by type narrowing
        """
        # Check if variable was narrowed to a safe type
        if result.taint_eliminated.get(variable, False):
            return True

        # Check branch-specific state
        if at_line and at_line in result.branch_states:
            branch = result.branch_states[at_line]
            types = branch.get_types(variable)
            return any(t in SAFE_PRIMITIVE_TYPES for t in types)

        return False

    def is_taint_reduced(self, variable: str, result: NarrowingResult, at_line: int | None = None) -> bool:
        """
        Check if taint risk is reduced (but not eliminated) for a variable.

        Args:
            variable: Variable name to check
            result: NarrowingResult from analyze()
            at_line: Optional line number to check branch-specific state

        Returns:
            True if taint risk is reduced by type narrowing
        """
        if result.taint_reduced.get(variable, False):
            return True

        if at_line and at_line in result.branch_states:
            branch = result.branch_states[at_line]
            types = branch.get_types(variable)
            return any(t in REDUCED_RISK_TYPES for t in types)

        return False

    def get_narrowed_type(self, variable: str, result: NarrowingResult, at_line: int) -> set[NarrowedType]:
        """
        Get the narrowed type(s) for a variable at a specific line.

        Args:
            variable: Variable name
            result: NarrowingResult from analyze()
            at_line: Line number to check

        Returns:
            Set of narrowed types (may include UNKNOWN if not narrowed)
        """
        # Find the most recent type guard for this variable before the line
        relevant_guards = [g for g in result.type_guards if g.variable == variable and g.line <= at_line]

        if not relevant_guards:
            return {NarrowedType.UNKNOWN}

        # Get the most recent guard
        latest_guard = max(relevant_guards, key=lambda g: g.line)

        # Check if we're in the narrowed branch
        if at_line in result.branch_states:
            return result.branch_states[at_line].get_types(variable)

        # If negated, the narrowing applies to else branch
        if latest_guard.negated:
            return {NarrowedType.UNKNOWN}

        return {latest_guard.narrowed_to}


def analyze_type_narrowing(code: str) -> NarrowingResult:
    """
    Convenience function to analyze type narrowing in code.

    [20251216_FEATURE] Entry point for type narrowing analysis.

    Args:
        code: TypeScript/JavaScript source code

    Returns:
        NarrowingResult with detected type guards and narrowing information

    Example:
        >>> result = analyze_type_narrowing('''
        ...     function process(input: unknown) {
        ...         if (typeof input === 'number') {
        ...             return input * 2;  // safe - number
        ...         }
        ...     }
        ... ''')
        >>> len(result.type_guards)
        1
        >>> result.type_guards[0].narrowed_to
        <NarrowedType.NUMBER: 'number'>
    """
    analyzer = TypeNarrowing()
    return analyzer.analyze(code)
