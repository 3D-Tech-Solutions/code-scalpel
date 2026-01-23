"""
Tests for Feature 13: TypeScript Control-Flow Narrowing.

[20251216_TEST] v2.2.0 - Tests for type narrowing to reduce false positives.

Acceptance Criteria:
- [x] Detect type guards (`typeof`, `instanceof`, `in`)
- [x] Track type narrowing through branches
- [x] Reduce false positives when type is narrowed to safe type
- [x] Handle union type narrowing
- [x] Preserve taint for risky narrowing
"""

from code_scalpel.polyglot.typescript.type_narrowing import (
    BranchState,
    NarrowedType,
    TypeNarrowing,
    analyze_type_narrowing,
)


class TestTypeofDetection:
    """Test typeof type guard detection."""

    def test_detect_typeof_string(self):
        """Detect typeof x === 'string'."""
        code = """
        function process(input: unknown) {
            if (typeof input === 'string') {
                return input.toUpperCase();
            }
        }
        """
        result = analyze_type_narrowing(code)

        assert len(result.type_guards) >= 1
        guard = result.type_guards[0]
        assert guard.guard_type == "typeof"
        assert guard.variable == "input"
        assert guard.narrowed_to == NarrowedType.STRING

    def test_detect_typeof_number(self):
        """Detect typeof x === 'number'."""
        code = """
        function calc(value: unknown) {
            if (typeof value === 'number') {
                return value * 2;
            }
        }
        """
        result = analyze_type_narrowing(code)

        assert len(result.type_guards) >= 1
        guard = result.type_guards[0]
        assert guard.narrowed_to == NarrowedType.NUMBER

    def test_detect_typeof_boolean(self):
        """Detect typeof x === 'boolean'."""
        code = """
        function check(flag: unknown) {
            if (typeof flag === 'boolean') {
                return !flag;
            }
        }
        """
        result = analyze_type_narrowing(code)

        assert len(result.type_guards) >= 1
        assert result.type_guards[0].narrowed_to == NarrowedType.BOOLEAN

    def test_detect_typeof_negated(self):
        """Detect typeof x !== 'string' (negated)."""
        code = """
        function process(input: unknown) {
            if (typeof input !== 'string') {
                return 'not a string';
            }
        }
        """
        result = analyze_type_narrowing(code)

        assert len(result.type_guards) >= 1
        guard = result.type_guards[0]
        assert guard.negated is True


class TestInstanceofDetection:
    """Test instanceof type guard detection."""

    def test_detect_instanceof_date(self):
        """Detect x instanceof Date."""
        code = """
        function formatDate(value: unknown) {
            if (value instanceof Date) {
                return value.toISOString();
            }
        }
        """
        result = analyze_type_narrowing(code)

        assert len(result.type_guards) >= 1
        guard = result.type_guards[0]
        assert guard.guard_type == "instanceof"
        assert guard.narrowed_to == NarrowedType.DATE

    def test_detect_instanceof_array(self):
        """Detect x instanceof Array."""
        code = """
        function process(items: unknown) {
            if (items instanceof Array) {
                return items.length;
            }
        }
        """
        result = analyze_type_narrowing(code)

        assert len(result.type_guards) >= 1
        assert result.type_guards[0].narrowed_to == NarrowedType.ARRAY

    def test_detect_instanceof_regexp(self):
        """Detect x instanceof RegExp."""
        code = """
        function test(pattern: unknown) {
            if (pattern instanceof RegExp) {
                return pattern.test('hello');
            }
        }
        """
        result = analyze_type_narrowing(code)

        assert len(result.type_guards) >= 1
        assert result.type_guards[0].narrowed_to == NarrowedType.REGEXP


class TestInOperatorDetection:
    """Test 'in' operator type guard detection."""

    def test_detect_in_operator(self):
        """Detect 'prop' in obj."""
        code = """
        function process(obj: unknown) {
            if ('name' in obj) {
                return obj.name;
            }
        }
        """
        result = analyze_type_narrowing(code)

        assert len(result.type_guards) >= 1
        guard = result.type_guards[0]
        assert guard.guard_type == "in"
        assert guard.variable == "obj"
        assert guard.narrowed_to == NarrowedType.OBJECT

    def test_detect_in_operator_multiple_props(self):
        """Detect multiple in checks."""
        code = """
        function validate(data: unknown) {
            if ('id' in data) {
                if ('name' in data) {
                    return data.id + data.name;
                }
            }
        }
        """
        result = analyze_type_narrowing(code)

        assert len(result.type_guards) >= 2


class TestEqualityDetection:
    """Test null/undefined equality type guards."""

    def test_detect_null_check(self):
        """Detect x === null."""
        code = """
        function process(value: string | null) {
            if (value === null) {
                return 'empty';
            }
            return value.toUpperCase();
        }
        """
        result = analyze_type_narrowing(code)

        assert len(result.type_guards) >= 1
        guard = result.type_guards[0]
        assert guard.guard_type == "equality"
        assert guard.narrowed_to == NarrowedType.NULL

    def test_detect_undefined_check(self):
        """Detect x === undefined."""
        code = """
        function process(value: string | undefined) {
            if (value === undefined) {
                return 'missing';
            }
            return value.length;
        }
        """
        result = analyze_type_narrowing(code)

        assert len(result.type_guards) >= 1
        assert result.type_guards[0].narrowed_to == NarrowedType.UNDEFINED

    def test_detect_not_null_check(self):
        """Detect x !== null (negated)."""
        code = """
        function process(value: string | null) {
            if (value !== null) {
                return value.length;
            }
        }
        """
        result = analyze_type_narrowing(code)

        assert len(result.type_guards) >= 1
        assert result.type_guards[0].negated is True


class TestTypePredicateDetection:
    """Test custom type predicate function detection."""

    def test_detect_isstring_predicate(self):
        """Detect isString(x) type predicate."""
        code = """
        function process(value: unknown) {
            if (isString(value)) {
                return value.toUpperCase();
            }
        }
        """
        result = analyze_type_narrowing(code)

        assert len(result.type_guards) >= 1
        guard = result.type_guards[0]
        assert guard.guard_type == "predicate"
        assert guard.narrowed_to == NarrowedType.STRING

    def test_detect_array_isarray(self):
        """Detect Array.isArray(x) predicate."""
        code = """
        function process(items: unknown) {
            if (Array.isArray(items)) {
                return items.map(x => x);
            }
        }
        """
        result = analyze_type_narrowing(code)

        assert len(result.type_guards) >= 1
        assert result.type_guards[0].narrowed_to == NarrowedType.ARRAY

    def test_detect_isvalid_predicate(self):
        """Detect isValid(x) validation predicate."""
        code = """
        function process(input: unknown) {
            if (isValid(input)) {
                return saveToDb(input);
            }
        }
        """
        result = analyze_type_narrowing(code)

        assert len(result.type_guards) >= 1
        assert result.type_guards[0].narrowed_to == NarrowedType.VALIDATED


class TestBranchTracking:
    """Test type narrowing through branches."""

    def test_branch_state_created(self):
        """Branch state is created for type guards."""
        code = """
        function process(value: unknown) {
            if (typeof value === 'number') {
                return value * 2;
            }
        }
        """
        result = analyze_type_narrowing(code)

        # Should have at least one branch state
        assert len(result.branch_states) >= 1

    def test_branch_state_narrow(self):
        """BranchState.narrow() correctly updates types."""
        branch = BranchState()
        branch.narrow("x", NarrowedType.STRING)

        assert NarrowedType.STRING in branch.get_types("x")

    def test_branch_state_multiple_narrows(self):
        """Multiple narrows create union of types."""
        branch = BranchState()
        branch.narrow("x", NarrowedType.STRING)
        branch.narrow("x", NarrowedType.NUMBER)

        types = branch.get_types("x")
        assert NarrowedType.STRING in types
        assert NarrowedType.NUMBER in types

    def test_unknown_variable_returns_unknown(self):
        """Unknown variable returns UNKNOWN type."""
        branch = BranchState()
        types = branch.get_types("nonexistent")
        assert NarrowedType.UNKNOWN in types


class TestTaintElimination:
    """Test taint elimination for safe types."""

    def test_number_eliminates_taint(self):
        """Number type narrowing eliminates taint."""
        code = """
        function process(input: unknown) {
            if (typeof input === 'number') {
                return db.query(`SELECT * FROM users WHERE id = ${input}`);
            }
        }
        """
        result = analyze_type_narrowing(code)

        assert result.taint_eliminated.get("input", False) is True

    def test_boolean_eliminates_taint(self):
        """Boolean type narrowing eliminates taint."""
        code = """
        function process(flag: unknown) {
            if (typeof flag === 'boolean') {
                return db.query(`SELECT * FROM users WHERE active = ${flag}`);
            }
        }
        """
        result = analyze_type_narrowing(code)

        assert result.taint_eliminated.get("flag", False) is True

    def test_null_eliminates_taint(self):
        """Null check eliminates taint."""
        code = """
        function process(value: string | null) {
            if (value === null) {
                return 'empty';
            }
        }
        """
        result = analyze_type_narrowing(code)

        # Null narrowing should eliminate taint
        assert result.taint_eliminated.get("value", False) is True

    def test_string_does_not_eliminate_taint(self):
        """String type narrowing does NOT eliminate taint (still risky)."""
        code = """
        function process(input: unknown) {
            if (typeof input === 'string') {
                return db.query(`SELECT * FROM users WHERE name = '${input}'`);
            }
        }
        """
        result = analyze_type_narrowing(code)

        # String is still risky for SQL injection
        assert result.taint_eliminated.get("input", False) is False


class TestTaintReduction:
    """Test taint reduction for medium-risk types."""

    def test_validated_reduces_taint(self):
        """Validated type reduces taint risk."""
        code = """
        function process(input: unknown) {
            if (isValid(input)) {
                return db.query(`SELECT * FROM users WHERE id = ${input}`);
            }
        }
        """
        result = analyze_type_narrowing(code)

        assert result.taint_reduced.get("input", False) is True

    def test_date_reduces_taint(self):
        """Date type reduces taint risk."""
        code = """
        function process(value: unknown) {
            if (value instanceof Date) {
                return db.query(`SELECT * FROM logs WHERE timestamp = '${value}'`);
            }
        }
        """
        result = analyze_type_narrowing(code)

        assert result.taint_reduced.get("value", False) is True


class TestPreserveTaintForRiskyNarrowing:
    """Test that taint is preserved for risky type narrowing."""

    def test_string_preserves_taint(self):
        """String narrowing preserves taint (still dangerous for SQL/XSS)."""
        code = """
        function process(input: unknown) {
            if (typeof input === 'string') {
                return `<div>${input}</div>`;
            }
        }
        """
        result = analyze_type_narrowing(code)

        # Taint should NOT be eliminated
        assert result.taint_eliminated.get("input", True) is False

    def test_object_preserves_taint(self):
        """Object narrowing preserves taint."""
        code = """
        function process(data: unknown) {
            if (typeof data === 'object') {
                return JSON.stringify(data);
            }
        }
        """
        result = analyze_type_narrowing(code)

        assert result.taint_eliminated.get("data", True) is False


class TestUnionTypeNarrowing:
    """Test union type narrowing scenarios."""

    def test_union_narrowed_by_typeof(self):
        """Union type narrowed by typeof."""
        code = """
        function format(value: string | number) {
            if (typeof value === 'string') {
                return value.toUpperCase();
            }
            return value.toFixed(2);
        }
        """
        result = analyze_type_narrowing(code)

        assert len(result.type_guards) >= 1
        assert result.type_guards[0].narrowed_to == NarrowedType.STRING

    def test_multiple_union_branches(self):
        """Multiple branches narrow union type."""
        code = """
        function process(input: string | number | boolean) {
            if (typeof input === 'string') {
                return input.length;
            }
            if (typeof input === 'number') {
                return input * 2;
            }
            return !input;
        }
        """
        result = analyze_type_narrowing(code)

        # Should detect multiple guards
        assert len(result.type_guards) >= 2


class TestAnalyzerAPI:
    """Test the TypeNarrowing analyzer API."""

    def test_is_taint_eliminated(self):
        """Test is_taint_eliminated() method."""
        analyzer = TypeNarrowing()
        code = """
        function process(x: unknown) {
            if (typeof x === 'number') {
                return x;
            }
        }
        """
        result = analyzer.analyze(code)

        assert analyzer.is_taint_eliminated("x", result) is True

    def test_is_taint_reduced(self):
        """Test is_taint_reduced() method."""
        analyzer = TypeNarrowing()
        code = """
        function process(x: unknown) {
            if (x instanceof Date) {
                return x;
            }
        }
        """
        result = analyzer.analyze(code)

        assert analyzer.is_taint_reduced("x", result) is True

    def test_get_narrowed_type(self):
        """Test get_narrowed_type() method."""
        analyzer = TypeNarrowing()
        code = """
        function process(value: unknown) {
            if (typeof value === 'boolean') {
                return value;
            }
        }
        """
        result = analyzer.analyze(code)

        # Get the line of the guard
        guard_line = result.type_guards[0].line if result.type_guards else 3

        types = analyzer.get_narrowed_type("value", result, guard_line)
        assert NarrowedType.BOOLEAN in types


class TestAnalysisSummary:
    """Test analysis summary output."""

    def test_summary_fields_present(self):
        """Analysis summary has required fields."""
        code = """
        function process(x: unknown, y: unknown) {
            if (typeof x === 'number') {
                if (typeof y === 'string') {
                    return x + y.length;
                }
            }
        }
        """
        result = analyze_type_narrowing(code)

        assert "total_guards" in result.analysis_summary
        assert "variables_narrowed" in result.analysis_summary
        assert "taint_eliminated_count" in result.analysis_summary
        assert "taint_reduced_count" in result.analysis_summary

    def test_summary_counts_correct(self):
        """Summary counts are accurate."""
        code = """
        function process(a: unknown, b: unknown) {
            if (typeof a === 'number') {
                if (typeof b === 'boolean') {
                    return a + (b ? 1 : 0);
                }
            }
        }
        """
        result = analyze_type_narrowing(code)

        assert result.analysis_summary["total_guards"] >= 2
        assert result.analysis_summary["variables_narrowed"] >= 2
        # Both number and boolean eliminate taint
        assert result.analysis_summary["taint_eliminated_count"] >= 2


class TestAcceptanceCriteria:
    """Verify all acceptance criteria are met."""

    def test_criterion_1_detect_type_guards(self):
        """AC1: Detect type guards (typeof, instanceof, in)."""
        code = """
        function test(a: unknown, b: unknown, c: unknown) {
            if (typeof a === 'string') { /* typeof */ }
            if (b instanceof Date) { /* instanceof */ }
            if ('prop' in c) { /* in */ }
        }
        """
        result = analyze_type_narrowing(code)

        guard_types = {g.guard_type for g in result.type_guards}
        assert "typeof" in guard_types
        assert "instanceof" in guard_types
        assert "in" in guard_types

    def test_criterion_2_track_narrowing_through_branches(self):
        """AC2: Track type narrowing through branches."""
        code = """
        function process(value: unknown) {
            if (typeof value === 'number') {
                // value is narrowed to number here
                const doubled = value * 2;
            }
        }
        """
        result = analyze_type_narrowing(code)

        # Branch state should exist
        assert len(result.branch_states) >= 1

        # Check that narrowing is tracked
        for _line, state in result.branch_states.items():
            if "value" in state.variable_types:
                assert NarrowedType.NUMBER in state.get_types("value")
                break

    def test_criterion_3_reduce_false_positives_safe_type(self):
        """AC3: Reduce false positives when type is narrowed to safe type."""
        code = """
        function query(id: unknown) {
            if (typeof id === 'number') {
                // Number is safe - no SQL injection possible
                return db.query(`SELECT * FROM users WHERE id = ${id}`);
            }
        }
        """
        result = analyze_type_narrowing(code)

        # Number narrowing should eliminate taint
        assert result.taint_eliminated.get("id", False) is True

    def test_criterion_4_handle_union_type_narrowing(self):
        """AC4: Handle union type narrowing."""
        code = """
        function format(value: string | number | null) {
            if (value === null) {
                return 'N/A';
            }
            if (typeof value === 'string') {
                return value.trim();
            }
            return value.toFixed(2);
        }
        """
        result = analyze_type_narrowing(code)

        # Should detect multiple guards for union type
        assert len(result.type_guards) >= 2

        # Should have guards for null and string
        guard_types = {g.narrowed_to for g in result.type_guards}
        assert NarrowedType.NULL in guard_types
        assert NarrowedType.STRING in guard_types

    def test_criterion_5_preserve_taint_for_risky_narrowing(self):
        """AC5: Preserve taint for risky narrowing."""
        code = """
        function render(input: unknown) {
            if (typeof input === 'string') {
                // String is STILL risky for XSS!
                return `<div>${input}</div>`;
            }
        }
        """
        result = analyze_type_narrowing(code)

        # String should NOT eliminate taint
        assert result.taint_eliminated.get("input", True) is False


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_code(self):
        """Handle empty code gracefully."""
        result = analyze_type_narrowing("")
        assert result.type_guards == []
        assert result.taint_eliminated == {}

    def test_no_type_guards(self):
        """Handle code with no type guards."""
        code = """
        function add(a: number, b: number) {
            return a + b;
        }
        """
        result = analyze_type_narrowing(code)
        assert len(result.type_guards) == 0

    def test_complex_condition(self):
        """Handle complex conditions."""
        code = """
        function process(x: unknown) {
            if (typeof x === 'string' && x.length > 0) {
                return x;
            }
        }
        """
        result = analyze_type_narrowing(code)

        # Should still detect the typeof guard
        assert len(result.type_guards) >= 1
        assert result.type_guards[0].narrowed_to == NarrowedType.STRING

    def test_nested_if_statements(self):
        """Handle nested if statements."""
        code = """
        function process(a: unknown, b: unknown) {
            if (typeof a === 'string') {
                if (typeof b === 'number') {
                    return a.length + b;
                }
            }
        }
        """
        result = analyze_type_narrowing(code)

        # Should detect both guards
        assert len(result.type_guards) >= 2
