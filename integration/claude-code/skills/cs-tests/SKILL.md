---
name: cs-tests
description: |
  Generate unit tests from code paths. Uses symbolic execution to explore branches,
  identify edge cases, and auto-generate pytest/unittest test cases.
allowed-tools:
  - mcp__codescalpel__extract_code
  - mcp__codescalpel__symbolic_execute
  - mcp__codescalpel__generate_unit_tests
preamble-tier: 1
---

# /cs-tests — Generate Tests from Code Paths

Auto-generate unit tests by analyzing execution paths through a function.
Finds edge cases, branches, and error conditions automatically.

## Usage

```bash
/cs-tests src/utils.py function calculate_tax
/cs-tests src/validation.py function validate_email
/cs-tests src/api.py function handle_request
```

## How It Works

1. **Extract** — Get the function you want to test
2. **Symbolic Execute** — Run the code symbolically to explore all branches
   - Finds path conditions (if/else, loops, exceptions)
   - Identifies edge cases and dead code
3. **Generate Tests** — Create pytest test cases for each path
   - Happy path (normal inputs)
   - Error cases (invalid inputs)
   - Edge cases (boundary values)
   - Dead code detection

## What You Get

A test file with:
- ✅ One test per execution path
- ✅ Different input types (valid, invalid, boundary)
- ✅ Exception handling tests
- ✅ pytest or unittest format (you choose)

## Test Generation Framework

Supports:
- `pytest` (recommended, modern)
- `unittest` (legacy, standard library)

## Example Output

```python
def test_calculate_tax_normal():
    assert calculate_tax(100) == 10.0

def test_calculate_tax_zero():
    assert calculate_tax(0) == 0.0

def test_calculate_tax_negative_raises():
    with pytest.raises(ValueError):
        calculate_tax(-100)
```

## Next Steps

1. Review the generated tests
2. Run them: `pytest test_*.py`
3. Adjust assertions if needed
4. Commit to your test suite

## Pro Tip

Generate tests BEFORE refactoring to create a safety baseline:

```bash
/cs-tests src/legacy_code.py function complex_function
# Now safe to refactor—tests will catch breakage
/cs-refactor src/legacy_code.py function complex_function
```

See `CLAUDE.md` for the full test generation workflow.
