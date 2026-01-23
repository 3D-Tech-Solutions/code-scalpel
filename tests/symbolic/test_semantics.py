"""
[20251214_TEST] Coverage for PythonSemantics and JavaScriptSemantics branches.
"""

import math

import pytest
from z3 import Bool, BoolVal, IntVal, StringVal

from code_scalpel.ir.semantics import JavaScriptSemantics, PythonSemantics


def test_python_binary_add_string_and_int_raises_type_error():
    semantics = PythonSemantics()

    with pytest.raises(TypeError):
        semantics.binary_add("5", 3)


def test_python_bool_and_short_circuits_and_returns_operand():
    semantics = PythonSemantics()

    assert semantics.bool_and(0, "later") == 0
    assert semantics.bool_or("first", None) == "first"


def test_python_to_number_invalid_string_raises_value_error():
    semantics = PythonSemantics()

    with pytest.raises(ValueError):
        semantics.to_number("not-a-number")


# [20251214_TEST] Cover additional PythonSemantics arithmetic and truthiness branches.
def test_python_binary_mod_and_pow_paths():
    semantics = PythonSemantics()

    assert semantics.binary_mod(-7, 3) == 2
    assert semantics.binary_pow(2, 3) == 8
    with pytest.raises(NotImplementedError):
        semantics.binary_pow("a", "b")


def test_python_bool_not_and_to_boolean():
    semantics = PythonSemantics()

    assert semantics.bool_not(0) is True
    assert semantics.bool_not(1) is False
    assert semantics.to_boolean("non-empty") is True
    assert semantics.to_boolean(0) is False


def test_javascript_binary_add_prefers_string_concat():
    semantics = JavaScriptSemantics()

    assert semantics.binary_add("5", 3) == "53"
    assert semantics.binary_add(5, "3") == "53"


def test_javascript_truthiness_and_not_behavior():
    semantics = JavaScriptSemantics()

    assert semantics.bool_or(0, "fallback") == "fallback"
    assert semantics.bool_not([]) is False


def test_javascript_modulo_sign_matches_dividend():
    semantics = JavaScriptSemantics()

    assert semantics.binary_mod(-7, 3) == -1
    assert math.isnan(semantics.binary_mod("oops", 2))


# [20251214_TEST] Cover JavaScriptSemantics coercion, comparisons, and truthiness.
def test_javascript_to_number_and_truthiness():
    semantics = JavaScriptSemantics()

    assert semantics.to_number(None) == 0
    assert semantics.to_number(True) == 1
    assert math.isnan(semantics.to_number("bad"))
    assert semantics.to_boolean([]) is True
    assert semantics.to_boolean(0) is False


def test_javascript_comparisons_and_bool_ops():
    semantics = JavaScriptSemantics()

    assert semantics.compare_eq(1, "1") is True
    assert semantics.compare_strict_eq(1, "1") is False
    assert semantics.bool_and(0, "later") == 0
    assert semantics.bool_or(0, "later") == "later"
    assert semantics.bool_not([]) is False


# [20250105_TEST] Cover symbolic and Z3-specific PythonSemantics branches.
def test_python_semantics_symbolic_branches():
    semantics = PythonSemantics()

    seq_concat = semantics.binary_add(StringVal("a"), StringVal("b"))
    assert seq_concat.sexpr() == '(str.++ "a" "b")'

    # [20251214_TEST] Allow non-simplified Z3 arithmetic nodes by checking sexpr variants.
    arith_sum = semantics.binary_add(IntVal(1), IntVal(2))
    assert arith_sum.sexpr() in {"3", "(+ 1 2)"}

    with pytest.raises(TypeError):
        semantics.binary_add(StringVal("a"), IntVal(1))

    arith_diff = semantics.binary_sub(IntVal(5), IntVal(3))
    assert arith_diff.sexpr() in {"2", "(- 5 3)"}

    arith_product = semantics.binary_mul(IntVal(2), IntVal(4))
    assert arith_product.sexpr() in {"8", "(* 2 4)"}

    arith_div = semantics.binary_div(IntVal(5), IntVal(2))
    assert arith_div.sexpr() in {"(/ 5 2)", "(div 5 2)"}

    floor_div_symbolic = semantics.binary_floor_div(IntVal(5), IntVal(2))
    assert floor_div_symbolic.sexpr() in {"(/ 5 2)", "(div 5 2)"}

    floor_div_concrete = semantics.binary_floor_div(5, 2)
    assert floor_div_concrete == 2

    mod_symbolic = semantics.binary_mod(IntVal(7), IntVal(3))
    assert mod_symbolic.sexpr() == "(mod 7 3)"

    eq_symbolic = semantics.compare_eq(IntVal(1), IntVal(1))
    assert eq_symbolic.sexpr() == "(= 1 1)"

    expr_a, expr_b = Bool("a"), Bool("b")
    assert semantics.compare_strict_eq(expr_a, expr_a).sexpr() == "(= a a)"
    assert semantics.bool_and(expr_a, expr_b).sexpr() == "(and a b)"
    assert semantics.bool_or(expr_a, expr_b).sexpr() == "(or a b)"
    assert semantics.bool_not(expr_a).sexpr() == "(not a)"

    symbolic_truth = semantics.to_boolean(BoolVal(True))
    if hasattr(symbolic_truth, "sexpr"):
        assert symbolic_truth.sexpr() == "true"
    else:
        assert symbolic_truth is True

    assert semantics.to_string(StringVal("abc")).sexpr() == '"abc"'
    assert semantics.to_number(IntVal(10)).sexpr() == "10"


# [20250105_TEST] Cover JavaScriptSemantics NaN/inf branches and coercions.
def test_javascript_semantics_error_and_coercion_branches():
    semantics = JavaScriptSemantics()

    concat_symbolic = semantics.binary_add(StringVal("x"), StringVal("y"))
    assert concat_symbolic.sexpr() == '(str.++ "x" "y")'

    assert math.isinf(semantics.binary_div(5, 0))
    assert semantics.binary_div(-5, 0) == float("-inf")

    assert math.isnan(semantics.binary_sub("bad", 3))
    assert math.isnan(semantics.binary_mul("oops", 2))
    assert math.isnan(semantics.binary_pow("oops", 2))

    floor_nan = semantics.binary_floor_div("nan", 2)
    assert math.isnan(floor_nan)

    assert math.isnan(semantics.binary_mod("oops", 0))

    assert semantics.compare_eq("abc", 5) is False
    assert semantics.compare_strict_eq("1", 1) is False

    bool_lhs, bool_rhs = Bool("left"), Bool("right")
    assert semantics.bool_and(bool_lhs, bool_rhs).sexpr() == "(and left right)"
    assert semantics.bool_or(bool_lhs, bool_rhs).sexpr() == "(or left right)"
    assert semantics.bool_not(bool_lhs).sexpr() == "(not left)"

    assert semantics._is_truthy([]) is True
    assert semantics._is_truthy(float("nan")) is False

    # [20251214_TEST] Accept either BoolRef or concrete bool depending on Z3 return type.
    false_coerced = semantics.to_boolean(BoolVal(False))
    if hasattr(false_coerced, "sexpr"):
        assert false_coerced.sexpr() == "false"
    else:
        assert false_coerced is False
    assert semantics.to_string(None) == "null"
    assert semantics.to_string(True) == "true"
    assert semantics.to_string(False) == "false"

    assert semantics.to_number(None) == 0
    assert semantics.to_number(True) == 1
    assert semantics.to_number(False) == 0
    assert semantics.to_number("3.5") == 3.5
    assert math.isnan(semantics.to_number("not-a-number"))
    assert semantics.to_number(7) == 7.0
