from code_scalpel.code_parsers.python_parser import PythonParser


# [20251214_TEST] Cover PythonParser error handling and complexity helpers.
# [20251214_REFACTOR] Remove unused pytest import flagged by ruff.
def test_parse_reports_syntax_error_details():
    parser = PythonParser()
    result = parser.parse("def bad(:\n    pass")

    assert result.ast is None
    assert result.errors and result.errors[0]["type"] == "SyntaxError"


def test_get_functions_and_classes_guard_invalid_ast():
    parser = PythonParser()
    assert parser.get_functions("not-an-ast") == []
    assert parser.get_classes(123) == []


def test_complexity_counts_control_and_bool_ops():
    parser = PythonParser()
    code = """
def sample(x):
    if x and (x or 3):
        for i in range(2):
            while i:
                pass
    try:
        raise ValueError()
    except ValueError:
        return x
"""
    result = parser.parse(code)
    assert result.metrics["complexity"] >= 6
