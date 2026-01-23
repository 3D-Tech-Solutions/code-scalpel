from __future__ import annotations

from textwrap import dedent

from code_scalpel.polyglot.typescript.type_narrowing import (
    NarrowedType,
    NarrowingResult,
    TypeNarrowing,
)

# [20251216_TEST] Cover regex fallback and taint helpers


def test_regex_fallback_tracks_negated_predicates_and_truthy_guards() -> None:
    code = dedent("""
        if (!isValid(value)) {
          doThing(value);
        }
        if (typeof value === 'number') {
          return value + 1;
        }
        """)

    narrowing = TypeNarrowing()
    result = narrowing.analyze(code)

    # First guard is negated predicate; narrowing should not apply in else branch
    unknown_types = narrowing.get_narrowed_type("value", result, at_line=1)
    assert NarrowedType.UNKNOWN in unknown_types

    # Second guard narrows to number and should mark taint eliminated
    assert narrowing.is_taint_eliminated("value", result, at_line=4)
    assert narrowing.is_taint_reduced("value", result, at_line=4)


def test_manual_tree_analysis_creates_branch_state() -> None:
    """[20251216_TEST] Drive _analyze_tree with fake nodes to cover tree path."""

    class FakeNode:
        def __init__(
            self,
            node_type: str,
            children=None,
            start_byte: int = 0,
            end_byte: int = 0,
            line: int = 0,
        ):
            self.type = node_type
            self.children = children or []
            self.start_byte = start_byte
            self.end_byte = end_byte
            self.start_point = (line, 0)

    condition_text = "(typeof foo === 'number')"
    condition_node = FakeNode(
        "parenthesized_expression",
        start_byte=0,
        end_byte=len(condition_text),
        line=0,
    )
    if_node = FakeNode("if_statement", children=[condition_node])

    analyzer = TypeNarrowing()
    type_guards: list = []
    branch_states: dict = {}
    taint_eliminated: dict = {}
    taint_reduced: dict = {}

    analyzer._analyze_tree(
        if_node,
        condition_text,
        type_guards,
        branch_states,
        taint_eliminated,
        taint_reduced,
    )

    assert type_guards
    assert branch_states
    assert analyzer.is_taint_eliminated(
        "foo",
        NarrowingResult(type_guards, branch_states, taint_eliminated, taint_reduced, {}),
        at_line=1,
    )


def test_get_narrowed_type_with_negated_guard_returns_unknown() -> None:
    """[20251216_TEST] Negated guard should not narrow in else branch."""
    analyzer = TypeNarrowing()
    result = analyzer.analyze("if (typeof value !== 'string') { call(value); }")

    narrowed = analyzer.get_narrowed_type("value", result, at_line=2)
    assert NarrowedType.UNKNOWN in narrowed


def test_analyze_tree_with_statement_block_child() -> None:
    """[20251217_TEST] _analyze_tree recursively processes statement blocks."""

    class FakeNode:
        def __init__(
            self,
            node_type: str,
            children=None,
            start_byte: int = 0,
            end_byte: int = 0,
            line: int = 0,
        ):
            self.type = node_type
            self.children = children or []
            self.start_byte = start_byte
            self.end_byte = end_byte
            self.start_point = (line, 0)

    condition_text = "(typeof foo === 'number')"
    condition_node = FakeNode(
        "parenthesized_expression",
        start_byte=0,
        end_byte=len(condition_text),
        line=0,
    )
    stmt_block = FakeNode("statement_block", line=0)
    if_node = FakeNode("if_statement", children=[condition_node, stmt_block])

    analyzer = TypeNarrowing()
    type_guards: list = []
    branch_states: dict = {}
    taint_eliminated: dict = {}
    taint_reduced: dict = {}

    analyzer._analyze_tree(
        if_node,
        condition_text,
        type_guards,
        branch_states,
        taint_eliminated,
        taint_reduced,
    )

    assert type_guards
    assert branch_states


def test_detect_in_operator_negative() -> None:
    """[20251217_TEST] Condition without 'in' operator returns None."""
    analyzer = TypeNarrowing()
    guard = analyzer._detect_in_operator("x === 5", line=1)
    assert guard is None


def test_detect_equality_negative() -> None:
    """[20251217_TEST] Condition without null/undefined returns None."""
    analyzer = TypeNarrowing()
    guard = analyzer._detect_equality("x === 5", line=1)
    assert guard is None


def test_detect_type_predicate_negative() -> None:
    """[20251217_TEST] Condition without known predicates returns None."""
    analyzer = TypeNarrowing()
    guard = analyzer._detect_type_predicate("customCheck(x)", line=1)
    assert guard is None


def test_detect_truthiness_complex_expression_returns_none() -> None:
    """[20251217_TEST] Complex expressions don't match truthiness pattern."""
    analyzer = TypeNarrowing()
    guard = analyzer._detect_truthiness("x && y || z", line=1)
    assert guard is None
