# generate_unit_tests Tool Roadmap

**Tool Name:** `generate_unit_tests`  
**Tool Version:** v1.0  
**Code Scalpel Version:** v3.3.0  
**Current Status:** ✅ v1.0 VALIDATED (January 11, 2026)  
**Primary Module:** `src/code_scalpel/generators/test_generator.py`  
**Tier Availability:** All tiers (Community, Pro, Enterprise)

---

## v1.0 Validation Status

> [20260111_DOCS] v1.0 validation complete with metadata fields and bugfix.

| Aspect | Status | Details |
|--------|--------|---------|
| **Tests** | ✅ 64/64 passing | 56 existing + 8 new metadata tests |
| **Output Metadata** | ✅ Added | tier_applied, framework_used, max_test_cases_limit, data_driven_enabled, bug_reproduction_enabled |
| **Config Alignment** | ✅ Verified | limits.toml matches features.py |
| **Tier Enforcement** | ✅ Working | Community/Pro/Enterprise properly gated |
| **Bugfix Applied** | ✅ Fixed | Enterprise tier was missing `data_driven_tests` capability |

### Output Metadata Fields (v1.0)
```python
class TestGenerationResult(BaseModel):
    # ... existing fields ...
    tier_applied: str = "community"           # Tier used for generation
    framework_used: str = "pytest"            # Test framework used
    max_test_cases_limit: int | None = None   # Max limit applied
    data_driven_enabled: bool = False         # Data-driven mode status
    bug_reproduction_enabled: bool = False    # Bug reproduction mode status
```

---

## Overview

The `generate_unit_tests` tool automatically creates unit tests from code using symbolic execution to explore all execution paths and generate test cases.

---

## Polyglot Architecture Definition

> [20260109_DOCS] Added explicit polyglot architecture, current status, gaps, blockers, and acceptance criteria.

Design goal: a language-agnostic test case model with language-specific renderers (templates) and an optional symbolic/CFG path source. The architecture mirrors `symbolic_execute` (front-ends → IR) and adds per-framework template emitters.

- **Front-Ends (Code Under Test):**
  - Python (existing)
  - JavaScript/TypeScript (tree-sitter): model async/await conservatively
  - Java (compiler AST or tree-sitter): primitives + simple objects
  - Go/C/C++/Rust (Enterprise later): minimal CFG extraction for initial cases

- **Common Test Case Model:**
  - Path-derived inputs (`dict[str, Any]`), optional expected output/exception, path conditions metadata
  - Framework-agnostic representation; serializable and stable

- **Path Source:**
  - Preferred: `symbolic_execute` IR → constraints → example inputs (polyglot when available)
  - Fallback: CFG-only heuristic inputs when symbolic is unavailable for a language

- **Template Renderers (Per Framework):**
  - Python: `pytest`, `unittest` (existing)
  - JS/TS: `jest`, `mocha`
  - Java: `junit`
  - Renderers are pure string templates with deterministic ordering/naming

- **Router & Parameters:**
  - `language` (optional, default `python`) + `framework` (required)
  - Future `file_path`/extension detection → selects front-end + renderer

---

## Current Polyglot Status

- Implementation is Python-only at the MCP layer; generates Python tests (`pytest`/`unittest`).
- Crash log parsing can recognize Python/JS/Java shapes, but output is still Python tests.
- No `language` parameter or non-Python renderers/templates are wired.

---

## Known Gaps

- No language router; cannot accept non-Python source for generation
- Missing JS/TS/JUnit/Jest/Mocha renderers and template libraries
- No mapping layer from IR test cases to non-Python framework idioms (param tables, subtests)
- Limited mocking/fixture generation across languages
- Deterministic naming and import resolution rules not defined for non-Python targets

---

## Polyglot Blockers

- Dependency on `symbolic_execute` polyglot IR for high-fidelity inputs
- Async semantics (JS/TS) make path → test scheduling tricky; conservative modeling first
- Java object/field assertions and exception modeling need stable conventions
- Systems languages require bounded memory/pointer abstractions before auto-inputs are reliable

---

## Current Capabilities (v1.0)

### Community Tier
- ✅ Generate `pytest` tests
- ✅ Path-based test generation (via symbolic execution, with fallbacks)
- ✅ Supports Python source input
- ✅ Basic assertion generation
- ⚠️ **Limits (enforced):** max 5 test cases; frameworks: `pytest` only

### Pro Tier
- ✅ All Community features
- ✅ Generate `unittest` tests (in addition to `pytest`)
- ✅ Data-driven / parametrized output (`data_driven=True`)
- ⚠️ **Limits (enforced):** max 20 test cases; frameworks: `pytest`, `unittest`

### Enterprise Tier
- ✅ All Pro features
- ✅ Bug reproduction test generation from `crash_log`
- ⚠️ **Limits (enforced):** unlimited test cases; frameworks: all (tier policy)

---

## Tier Contract (Enforced at MCP Boundary)

This tool enforces tier rules in the MCP handler:

- **Framework gating:** Community allows only `pytest`.
- **Data-driven gating:** `data_driven=True` requires Pro tier (capability: `data_driven_tests`).
- **Bug reproduction gating:** providing `crash_log` requires Enterprise tier (capability: `bug_reproduction`).
- **Output truncation:** `max_test_cases` is applied after generation and returns `truncated` + `truncation_warning` when limits apply.

---

## MCP Request/Response Examples

### MCP Request Format

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "mcp_code-scalpel_generate_unit_tests",
    "arguments": {
      "code": "def calculate_discount(price, is_member):\n    if price > 100:\n        if is_member:\n            return price * 0.8\n        return price * 0.9\n    return price",
      "framework": "pytest"
    }
  },
  "id": 1
}
```

### Community Tier Response

```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "framework": "pytest",
    "pytest_code": "import pytest\n\n\ndef test_calculate_discount_member_high_price():\n    \"\"\"Test: price > 100, is_member = True\"\"\"\n    result = calculate_discount(150, True)\n    assert result == 120.0\n\n\ndef test_calculate_discount_non_member_high_price():\n    \"\"\"Test: price > 100, is_member = False\"\"\"\n    result = calculate_discount(150, False)\n    assert result == 135.0\n\n\ndef test_calculate_discount_low_price():\n    \"\"\"Test: price <= 100\"\"\"\n    result = calculate_discount(50, True)\n    assert result == 50\n",
    "test_cases": [
      {
        "name": "test_calculate_discount_member_high_price",
        "inputs": {"price": 150, "is_member": true},
        "expected_output": 120.0,
        "path_conditions": ["price > 100", "is_member == True"]
      },
      {
        "name": "test_calculate_discount_non_member_high_price",
        "inputs": {"price": 150, "is_member": false},
        "expected_output": 135.0,
        "path_conditions": ["price > 100", "is_member == False"]
      },
      {
        "name": "test_calculate_discount_low_price",
        "inputs": {"price": 50, "is_member": true},
        "expected_output": 50,
        "path_conditions": ["price <= 100"]
      }
    ],
    "coverage_paths": 3,
    "truncated": false,
    "truncation_warning": null
  },
  "id": 1
}
```

### Pro Tier Response (Data-Driven)

```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "framework": "pytest",
    "pytest_code": "import pytest\n\n\n@pytest.mark.parametrize(\n    \"price,is_member,expected\",\n    [\n        (150, True, 120.0),\n        (150, False, 135.0),\n        (50, True, 50),\n        (50, False, 50),\n        (100, True, 100),\n    ],\n    ids=[\n        \"high_price_member\",\n        \"high_price_non_member\",\n        \"low_price_member\",\n        \"low_price_non_member\",\n        \"boundary_price\",\n    ]\n)\ndef test_calculate_discount_parametrized(price, is_member, expected):\n    result = calculate_discount(price, is_member)\n    assert result == expected\n",
    "test_cases": [
      {
        "name": "high_price_member",
        "inputs": {"price": 150, "is_member": true},
        "expected_output": 120.0
      },
      {
        "name": "high_price_non_member",
        "inputs": {"price": 150, "is_member": false},
        "expected_output": 135.0
      },
      {
        "name": "low_price_member",
        "inputs": {"price": 50, "is_member": true},
        "expected_output": 50
      },
      {
        "name": "low_price_non_member",
        "inputs": {"price": 50, "is_member": false},
        "expected_output": 50
      },
      {
        "name": "boundary_price",
        "inputs": {"price": 100, "is_member": true},
        "expected_output": 100
      }
    ],
    "coverage_paths": 5,
    "data_driven": true,
    "truncated": false
  },
  "id": 1
}
```

### Enterprise Tier Response (Bug Reproduction)

```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "framework": "pytest",
    "pytest_code": "import pytest\n\n\ndef test_divide_bug_reproduction():\n    \"\"\"Bug reproduction test for ZeroDivisionError.\n    \n    Original crash log:\n    ZeroDivisionError: division by zero at divide:2\n    \"\"\"\n    a = 10\n    b = 0\n    with pytest.raises(ZeroDivisionError):\n        divide(a=a, b=b)\n\n\ndef test_divide_normal_path_0():\n    result = divide(a=10, b=2)\n    assert result == 5.0\n\n\ndef test_divide_normal_path_1():\n    result = divide(a=-10, b=2)\n    assert result == -5.0\n",
    "test_cases": [
      {
        "name": "test_divide_bug_reproduction",
        "inputs": {"a": 10, "b": 0},
        "expected_exception": "ZeroDivisionError",
        "is_bug_reproduction": true,
        "crash_log_line": 2
      },
      {
        "name": "test_divide_normal_path_0",
        "inputs": {"a": 10, "b": 2},
        "expected_output": 5.0
      },
      {
        "name": "test_divide_normal_path_1",
        "inputs": {"a": -10, "b": 2},
        "expected_output": -5.0
      }
    ],
    "coverage_paths": 3,
    "bug_reproduction_success": true,
    "crash_log_parsed": {
      "exception_type": "ZeroDivisionError",
      "function": "divide",
      "line": 2,
      "inferred_inputs": {"a": 10, "b": 0}
    },
    "truncated": false
  },
  "id": 1
}
```

---

## Roadmap

## Cross-Cutting Research Topics (applies across v1.1–v1.4)

### RQ1 — Test Correctness vs. “Path Coverage”
- When symbolic execution enumerates paths, how often do generated tests actually assert the intended behavior?
- What minimum assertion strategy prevents “always passes” tests without overfitting to implementation details?

### RQ2 — Determinism & Stability
- Are generated tests stable across OS/CPUs/Python versions (ordering, names, parametrization grouping)?
- How do we define and enforce stable “test identity” so diffs are predictable in CI?

### RQ3 — Safe Handling of Unknown/Unsat Paths
- When the symbolic engine can’t solve constraints (timeouts/unsupported constructs), what is the correct fallback semantics?
- How should we label fallbacks so users don’t over-trust coverage?

### RQ4 — Data-Driven Output Value
- Does `data_driven=True` improve readability/maintainability (fewer tests, less duplication) without hiding important distinct paths?
- What grouping strategy yields the best developer experience (by signature, by branch predicate, by exception type)?

### RQ5 — Bug Reproduction Fidelity
- What fraction of crash logs can reliably be converted into a reproducer with inferred inputs?
- What is the “honest uncertainty” model when inputs cannot be inferred (placeholders vs. guided prompts)?

### RQ6 — Tier UX: Limits, Truncation, and Gating
- What wording best explains truncation/gating without upsell messaging?
- What response metadata is sufficient for downstream automation (CI bots, review pipelines)?

### v1.1 (Q1 2026): Enhanced Test Quality

#### Community Tier
- [ ] Better assertion messages
- [ ] Test naming improvements
- [ ] Setup/teardown generation

**Community Research Queries**
- What naming scheme best matches user expectations (function name + path id + intent)?
- Which assertion improvements provide the highest signal with lowest brittleness?

**Community Success Metrics**
- ≥90% of generated tests have descriptive names (measured on benchmark suite)
- ≥80% of generated tests include at least one non-trivial assertion beyond “not None” (where possible)
- <1% of responses contain non-actionable errors (“unknown error”)

#### Pro Tier
- [ ] Behavior-driven test generation
- [ ] Mutation testing integration
- [ ] Test smell detection
- [ ] Test refactoring suggestions

**Pro Research Queries**
- Which “test smell” signals are safe to emit without many false positives (assert-less tests, brittle string matches, over-mocking)?
- Can mutation testing feedback be summarized without running full mutation suites?

**Pro Success Metrics**
- Mutation “smoke” integration can run in <60s on a small benchmark project
- ≥25% reduction in duplicated boilerplate when `data_driven=True` is used (LoC metric)
- ≥90% of suggestions are source-grounded (no hallucinated functions/imports)

#### Enterprise Tier
- [ ] Custom assertion libraries
- [ ] Test compliance checking
- [ ] Automated test review

**Enterprise Research Queries**
- Which compliance rules are actionable for tests (PII redaction, secrets in fixtures, deterministic randomness)?
- What is the safe review surface: annotate, auto-fix, or block?

**Enterprise Success Metrics**
- Compliance checks produce deterministic results and stable rule IDs across runs
- ≥95% of compliance findings link to a concrete line span in generated output (evidence quality)

### v1.2 (Q2 2026): Framework Support

#### All Tiers
- [ ] Router accepts `language` and chooses renderer accordingly
- [ ] Jest test generation (JavaScript)
  - [ ] Deterministic test naming and import resolution
  - [ ] Parametrization via arrays/tables when applicable
- [ ] JUnit test generation (Java)
  - [ ] Gradle/Maven-neutral imports; basic assertions for primitives/strings
  - [ ] Subtests or parameterized tests when applicable
- [ ] Mocha test generation (JavaScript)
  - [ ] Deterministic `describe`/`it` structure with stable ordering

**All-Tiers Research Queries**
- What is the minimum viable “multi-language” contract: language parameter, per-framework templates, or separate tools?
- What is the correct mapping between path-based inputs and each framework’s idioms (parametrize vs tables vs subtests)?

**All-Tiers Success Metrics**
- ≥95% syntactically valid tests on curated fixtures per new framework
- <5s median generation time for a typical function (<200 LOC)

#### Pro Tier
- [ ] React component test generation
  - [ ] Minimal auto-mocking strategy documented; deterministic render
- [ ] API test generation
  - [ ] Safe baseline assertions (status code, shape) without over-mocking
- [ ] E2E test generation
  - [ ] Stable selectors and flake-reduction guidance

**Pro Research Queries**
- What is safe auto-mocking for React/APIs without creating tests that over-mock and miss regressions?
- Which API test baseline is most useful: schema contract, status code invariants, or golden payloads?

**Pro Success Metrics**
- ≥80% of generated React/API tests run without manual edits on benchmark apps
- ≥30% reduction in user-reported “test fails immediately” issues vs v1.0

#### Enterprise Tier
- [ ] Custom test framework support
  - [ ] Template sandboxing + allowlists; deterministic rendering
- [ ] Multi-framework test suites
  - [ ] Single test case model rendered to multiple frameworks predictably

**Enterprise Research Queries**
- How do we support custom templates safely (sandboxing, allowlists, deterministic rendering)?
- What is the best representation of “multi-framework suite” outputs in the MCP schema?

**Enterprise Success Metrics**
- Template engine produces deterministic outputs across environments
- ≥3 enterprise repos adopt multi-framework generation without schema changes

### v1.3 (Q3 2026): AI-Enhanced Generation

#### Pro Tier
- [ ] ML-based test prioritization
- [ ] Intelligent mock generation
- [ ] Natural language test descriptions

**Pro Research Queries**
- Can we prioritize tests using only static information (branch complexity, change frequency) without running coverage?
- What is the lowest-risk mock generation strategy (patch at boundary, dependency injection, minimal stubs)?

**Pro Success Metrics**
- Prioritization correlates with defect discovery on a benchmark dataset (measurable lift)
- Mock generation avoids behavior changes: low regression rate in internal review benchmark

#### Enterprise Tier
- [ ] Custom ML model training
- [ ] Historical test effectiveness analysis
- [ ] Predictive test generation

**Enterprise Research Queries**
- What signals are safe to learn from without capturing sensitive source content?
- How do we evaluate “predictive generation” without encouraging overfitting to historical bugs?

**Enterprise Success Metrics**
- Historical analysis supports stable trend metrics (same inputs → same outputs)
- Predictive generation demonstrates measurable value on a held-out benchmark (no data leakage)

### v1.4 (Q4 2026): Integration & Automation

#### Community Tier
- [ ] CI/CD integration helpers
- [ ] Pre-commit hook support

**Community Research Queries**
- What is the smallest “CI helper” that is actually useful (commands, templates, or docs)?
- Which pre-commit failures should block vs warn (format, syntax, import errors)?

**Community Success Metrics**
- ≥80% of “getting started” users can run generation + tests within 5 minutes (docs-driven benchmark)
- Pre-commit integration has <5% false-positive blocks on a curated fixture set

#### Pro Tier
- [ ] Continuous test generation
- [ ] Test gap analysis
- [ ] Automated test maintenance

**Pro Research Queries**
- What definition of “test gap” is actionable without full coverage data?
- How do we safely propose maintenance edits without changing test intent?

**Pro Success Metrics**
- Gap analysis identifies missing-branch hotspots with measurable precision on fixtures
- Maintenance suggestions preserve behavior (validated by existing tests + diff checks)

#### Enterprise Tier
- [ ] Repository-wide test generation
- [ ] Test orchestration
- [ ] Compliance test automation

**Enterprise Research Queries**
- What is the safe orchestration model (batching, caching, retries) without leaking source or over-consuming CI time?
- How do we represent compliance automation results for audit trails (stable IDs, reproducible runs)?

**Enterprise Success Metrics**
- Repository-wide runs complete within defined SLA on large repos (bounded resources)
- Compliance automation outputs include stable rule IDs and reproducible evidence bundles

---

## Known Issues & Limitations

### Current Limitations
- **Python-only at MCP layer:** The MCP interface currently generates Python tests (`pytest`/`unittest`) from Python source input.
- **Crash log parsing formats:** Bug reproduction parses Python/JS/Java stack traces, but emits Python tests.
- **No mocks/fixtures/templates yet:** Dependency mocking, fixture generation, and custom templates are not implemented.
- **Simple assertions:** Complex assertions may need manual refinement.
- **Crash-log inputs are best-effort:** Bug reproduction currently extracts limited input information from logs.

### Planned Fixes
- v1.2: Multi-language test generation (router + Jest/JUnit/Mocha renderers)
- v1.3: Improved assertion logic
- v1.4: Better dependency handling

---

## Acceptance Criteria

> [20260109_DOCS] Define concrete criteria to validate polyglot generation.

- **Routing & Contract:**
  - `language` param optional (default `python`), `framework` required
  - If unsupported language + `strict_language=True` → structured error; else fallback to CFG-only with warning
  - Result schema stable; renderer-specific code returned in appropriate field (e.g., `jest_code`, `junit_code`) without breaking existing `pytest_code`/`unittest_code`

- **Syntactic Validity:**
  - ≥95% syntactically valid outputs on curated fixtures for each new framework (lint/compile checks)

- **Determinism:**
  - Stable test names and ordering across runs and environments

- **Performance:**
  - <5s median generation time on functions <200 LOC (fixture baseline)

- **Fallback Behavior:**
  - When symbolic inputs unavailable, generator still emits scaffold tests with clear TODOs and non-failing placeholders

## Validation & Test Plan

- **Fixtures per Language:** Curated sets covering branches, loops, exceptions
- **Compile/Run Hooks:**
  - JS/TS: `node --check` or `tsc --noEmit`, run `jest --findRelatedTests` (dry)
  - Java: `javac` compile check or `mvn -q -DskipTests` with test compile phase
- **Determinism Checks:** Compare rendered outputs (hash) across two runs
- **Router Tests:** Matrix over (`language`, `framework`, `file_path`) to ensure correct renderer selection and error paths

---

## Proposed API Additions

> [20260109_DOCS] Concrete MCP examples for language routing and polyglot test generation.

### JavaScript/Jest Example

#### MCP Request

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "mcp_code-scalpel_generate_unit_tests",
    "arguments": {
      "code": "export function calculateDiscount(price, isMember) {\n  if (price > 100) {\n    return isMember ? price * 0.8 : price * 0.9;\n  }\n  return price;\n}",
      "language": "javascript",
      "framework": "jest",
      "function_name": "calculateDiscount"
    }
  },
  "id": 1
}
```

#### MCP Response

```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "function_name": "calculateDiscount",
    "test_count": 3,
    "test_cases": [
      {
        "path_id": 1,
        "function_name": "calculateDiscount",
        "inputs": {"price": 150, "isMember": true},
        "description": "price > 100 and isMember = true",
        "path_conditions": ["price > 100", "isMember === true"]
      },
      {
        "path_id": 2,
        "function_name": "calculateDiscount",
        "inputs": {"price": 150, "isMember": false},
        "description": "price > 100 and isMember = false",
        "path_conditions": ["price > 100", "isMember === false"]
      },
      {
        "path_id": 3,
        "function_name": "calculateDiscount",
        "inputs": {"price": 50, "isMember": true},
        "description": "price <= 100",
        "path_conditions": ["price <= 100"]
      }
    ],
    "total_test_cases": 3,
    "jest_code": "describe('calculateDiscount', () => {\n  it('should apply 20% discount for high-price members', () => {\n    const result = calculateDiscount(150, true);\n    expect(result).toBe(120);\n  });\n\n  it('should apply 10% discount for high-price non-members', () => {\n    const result = calculateDiscount(150, false);\n    expect(result).toBe(135);\n  });\n\n  it('should return original price for low-price purchases', () => {\n    const result = calculateDiscount(50, true);\n    expect(result).toBe(50);\n  });\n});\n",
    "truncated": false,
    "truncation_warning": null
  },
  "id": 1
}
```

### Java/JUnit Example

#### MCP Request

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "mcp_code-scalpel_generate_unit_tests",
    "arguments": {
      "code": "public class Calculator {\n  public static double calculateDiscount(double price, boolean isMember) {\n    if (price > 100) {\n      return isMember ? price * 0.8 : price * 0.9;\n    }\n    return price;\n  }\n}",
      "language": "java",
      "framework": "junit",
      "function_name": "calculateDiscount"
    }
  },
  "id": 2
}
```

#### MCP Response

```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "function_name": "calculateDiscount",
    "test_count": 3,
    "test_cases": [
      {
        "path_id": 1,
        "function_name": "calculateDiscount",
        "inputs": {"price": 150.0, "isMember": true},
        "description": "price > 100 and isMember = true",
        "path_conditions": ["price > 100.0", "isMember == true"]
      },
      {
        "path_id": 2,
        "function_name": "calculateDiscount",
        "inputs": {"price": 150.0, "isMember": false},
        "description": "price > 100 and isMember = false",
        "path_conditions": ["price > 100.0", "isMember == false"]
      },
      {
        "path_id": 3,
        "function_name": "calculateDiscount",
        "inputs": {"price": 50.0, "isMember": true},
        "description": "price <= 100",
        "path_conditions": ["price <= 100.0"]
      }
    ],
    "total_test_cases": 3,
    "junit_code": "import static org.junit.jupiter.api.Assertions.assertEquals;\nimport org.junit.jupiter.api.Test;\n\npublic class CalculatorTest {\n  @Test\n  public void testCalculateDiscountMemberHighPrice() {\n    double result = Calculator.calculateDiscount(150.0, true);\n    assertEquals(120.0, result, 0.01);\n  }\n\n  @Test\n  public void testCalculateDiscountNonMemberHighPrice() {\n    double result = Calculator.calculateDiscount(150.0, false);\n    assertEquals(135.0, result, 0.01);\n  }\n\n  @Test\n  public void testCalculateDiscountLowPrice() {\n    double result = Calculator.calculateDiscount(50.0, true);\n    assertEquals(50.0, result, 0.01);\n  }\n}\n",
    "truncated": false,
    "truncation_warning": null
  },
  "id": 2
}
```

### TypeScript/Jest Example (with Data-Driven, Pro Tier)

#### MCP Request

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "mcp_code-scalpel_generate_unit_tests",
    "arguments": {
      "code": "export function validate(age: number): 'invalid' | 'minor' | 'adult' {\n  if (age < 0) return 'invalid';\n  if (age < 18) return 'minor';\n  return 'adult';\n}",
      "language": "typescript",
      "framework": "jest",
      "function_name": "validate",
      "data_driven": true
    }
  },
  "id": 3
}
```

#### MCP Response (Parametrized)

```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "function_name": "validate",
    "test_count": 3,
    "test_cases": [
      {
        "path_id": 1,
        "function_name": "validate",
        "inputs": {"age": -1},
        "expected_output": "invalid",
        "description": "age < 0"
      },
      {
        "path_id": 2,
        "function_name": "validate",
        "inputs": {"age": 10},
        "expected_output": "minor",
        "description": "age < 18"
      },
      {
        "path_id": 3,
        "function_name": "validate",
        "inputs": {"age": 25},
        "expected_output": "adult",
        "description": "age >= 18"
      }
    ],
    "total_test_cases": 3,
    "jest_code": "describe('validate', () => {\n  it.each([\n    [-1, 'invalid'],\n    [10, 'minor'],\n    [25, 'adult'],\n  ])('returns %s for age %d', (age, expected) => {\n    expect(validate(age)).toBe(expected);\n  });\n});\n",
    "data_driven": true,
    "truncated": false
  },
  "id": 3
}
```

---

## Success Metrics

### Performance Targets
- **Generation time:** <5s per function
- **Test quality:** >80% tests pass without modification
- **Coverage:** Generated tests achieve >90% coverage

### Reliability Targets
- **Tier enforcement correctness:** 100% of requests honor tier gating + framework limits (unit tests)
- **Truncation correctness:** 100% of truncation events set `truncated=true` and include `truncation_warning`
- **Serialization safety:** 0 MCP transport failures due to non-JSON-serializable test inputs
- **Determinism:** Stable ordering + naming for identical inputs (bit-identical output on benchmark suite)

### Adoption Metrics
- **Usage:** 50K+ test generations per month by Q4 2026
- **Developer satisfaction:** >4.0/5 average rating

---

## Dependencies

### Internal Dependencies
- `src/code_scalpel/generators/test_generator.py` - Test suite generation
- `src/code_scalpel/symbolic_execution_tools/engine.py` - Symbolic path exploration (when available)

### External Dependencies
- `pytest` - Test framework (optional)

---

## Breaking Changes

None planned for v1.x series.

**API Stability Promise:**
- Tool signature stable
- Test format backward compatible

---

**Last Updated:** December 30, 2025  
**Next Review:** March 31, 2026
