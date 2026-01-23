from code_scalpel.polyglot.typescript.type_narrowing import NarrowedType, TypeNarrowing

# [20251216_TEST] Cover regex fallback and negated guard branches


def test_regex_fallback_truthiness_negated() -> None:
    analyzer = TypeNarrowing()
    analyzer._parser = None  # Force regex path
    code = "if (!input) { return; }"
    result = analyzer.analyze(code)

    assert result.type_guards[0].guard_type == "truthiness"
    assert result.type_guards[0].negated is True
    assert result.taint_eliminated.get("input") is False
    assert analyzer.get_narrowed_type("input", result, at_line=1) == {NarrowedType.UNKNOWN}


def test_reduced_risk_instanceof_date() -> None:
    analyzer = TypeNarrowing()
    analyzer._parser = None  # Force regex path
    code = "if (value instanceof Date) { call(value); }"
    result = analyzer.analyze(code)

    assert analyzer.is_taint_reduced("value", result, at_line=1) is True
    assert result.type_guards[0].narrowed_to == NarrowedType.DATE


def test_array_predicate_detection() -> None:
    analyzer = TypeNarrowing()
    analyzer._parser = None
    code = "if (Array.isArray(items)) { items.push(1); }"
    result = analyzer.analyze(code)

    assert result.type_guards[0].guard_type == "predicate"
    assert result.type_guards[0].narrowed_to == NarrowedType.ARRAY
    assert analyzer.is_taint_eliminated("items", result, at_line=1) is False
    assert analyzer.is_taint_reduced("items", result, at_line=1) is False
