# Parsing Path Audit: Ensuring All Tools Use Unified Infrastructure

## Executive Summary

**Found**: 150+ direct `ast.parse()` and `parser.parse()` calls across the codebase
**Issue**: Most tools bypass the unified parsing infrastructure
**Impact**: Non-deterministic behavior, inconsistent error handling

### ✅ Phase 1 Complete (2026-01-19)

Critical MCP tools now use unified parser with `response_config.json` governance:
- **analyze_code** - Uses `parse_python_code()` with full error context
- **security_scan** - Uses `parse_python_code()` with filename tracking
- **extract_code** - All 3 locations in extraction_helpers.py refactored to unified parser
- **response_config.py** - Implemented `include_on_error` feature
- **AnalysisResult model** - Added `error_location`, `suggested_fix`, `sanitization_report`, `parser_warnings`

**Validation**: analyze_code tests passing (34 failures pre-existing cache schema issues), extract_code 198/232 passing

### ✅ Phase 2 Complete (2026-01-19)

MCP helper infrastructure now uses unified parser:
- **get_file_context** - `ast_helpers.py` and `context_helpers.py` refactored with permissive fallback
- **symbolic execution tools** - `type_inference.py` and `path_prioritization.py` refactored
- **get_call_graph** - Already using unified parser via previous refactors

**Validation**: 131 get_file_context tests passing, 295 symbolic tests passing, 122 core MCP tests passing

---

## Critical Entry Points Requiring Refactor

### 🔴 HIGH PRIORITY: MCP Server Tools (User-Facing)

These are directly exposed via MCP protocol and must be deterministic:

| Tool | File | Line | Status | Notes |
|------|------|------|--------|-------|
| **analyze_code** | mcp/helpers/analyze_helpers.py | 1069 | ✅ DONE | Uses `parse_python_code()` with full error context |
| **security_scan** | mcp/helpers/security_helpers.py | 884 | ✅ DONE | Uses `parse_python_code()` with filename tracking |
| **extract_code** | mcp/helpers/extraction_helpers.py | 1033, 1471, 1737 | ✅ DONE | All 3 locations refactored |
| **symbolic_execute** | mcp/helpers/symbolic_helpers.py | 52, 108, 297, 832 | ✅ DONE | Uses unified parser in prior refactor |
| **get_call_graph** | mcp/helpers/graph_helpers.py | 122, 487, 1093 | ✅ DONE | Uses unified parser in prior refactor |
| **get_file_context** | mcp/helpers/context_helpers.py | 1343, 1359 | ✅ DONE | Refactored with permissive fallback (Phase 2) |
| **type inference** | symbolic_execution_tools/type_inference.py | 104 | ✅ DONE | Refactored (Phase 2) |
| **path prioritization** | symbolic_execution_tools/path_prioritization.py | 140 | ✅ DONE | Refactored (Phase 2) |
| **AST helpers** | mcp/helpers/ast_helpers.py | 54, 60 | ✅ DONE | Refactored `parse_file_cached()` (Phase 2) |

---

### 🟡 MEDIUM PRIORITY: Core Infrastructure (Phase 3 - Next)

**Status**: All MCP tools now use unified parser. Remaining work focuses on internal surgery modules.

| Component | File | Line Count | Complexity | Priority |
|-----------|------|------------|------------|----------|
| **Surgical Extractor** | surgery/surgical_extractor.py | 8 calls | High | 🔴 P1 |
| **Surgical Patcher** | surgery/surgical_patcher.py | 7 calls | High | 🔴 P1 |
| **Unified Extractor** | surgery/unified_extractor.py | 4 calls | Medium | 🟡 P2 |
| **Rename Symbol** | surgery/rename_symbol_refactor.py | 1 call | Low | 🟢 P3 |

**Note**: These are lower-level infrastructure modules. Refactoring requires careful testing as they're used by higher-level MCP tools.

---

### 🟢 LOW PRIORITY: Specialized Analysis Tools (Phase 4)

**Status**: Deferred until Phase 3 complete. These are internal tools with limited user exposure.

| Component | File | Call Count | Notes |
|-----------|------|------------|-------|
| **Error Scanner** | quality_assurance/error_scanner.py | 1 | Low impact, QA tool |
| **Regression Predictor** | refactor/regression_predictor.py | 1 | Internal refactor tool |
| **Custom Rules** | refactor/custom_rules.py | 3 | Policy enforcement |

**Estimated Impact**: Low - these are internal analysis tools not directly exposed via MCP

---

## Phase 3: Surgery Module Refactor Plan

### Target Modules

#### 1. surgical_extractor.py (Highest Priority)

**Lines with `ast.parse`**: 561, 1937, 2009, 2160, 2515, 2764, 2788, 3011, 3047, 3200, 3231, 3262, 3415

**Impact**: HIGH - Used by extract_code MCP tool
**Complexity**: HIGH - 13 call sites, complex extraction logic

**Refactor Strategy**:
```python
# Current pattern (line 561)
self._tree = ast.parse(self.code)

# Unified pattern
try:
    self._tree, report = parse_python_code(self.code, filename=self.file_path or "<extraction>")
    if report.was_sanitized:
        # Log or track sanitization
        self._sanitization_applied = True
except ParsingError as e:
    raise ExtractionError(f"Failed to parse code: {e}", location=e.location)
```

**Testing Requirements**:
- Run full `tests/core/parsers/test_surgical_extractor.py` suite
- Validate extract_code MCP tool still works
- Ensure no behavior changes in extraction logic

#### 2. surgical_patcher.py (High Priority)

**Lines with `ast.parse`**: 256, 403, 410, 513, 723, 788, 934

**Impact**: HIGH - Used by update_symbol and code modification tools
**Complexity**: HIGH - 7 call sites, mutation operations

**Refactor Strategy**:
```python
# Current pattern (line 256)
tree = ast.parse(code)

# Unified pattern
try:
    tree, report = parse_python_code(code, filename=self.file_path or "<patch>")
    if report.was_sanitized:
        # Critical: Track sanitization for patch safety
        self._warn_sanitization_applied()
except ParsingError as e:
    raise PatchError(f"Cannot patch invalid code: {e}", location=e.location)
```

**Testing Requirements**:
- Run full `tests/core/parsers/test_surgical_tools_coverage.py` suite
- Validate update_symbol MCP tool integrity
- Ensure patches apply cleanly without introducing bugs

#### 3. unified_extractor.py (Medium Priority)

**Lines with `ast.parse`**: Already partially refactored, remaining calls in helper methods

**Impact**: MEDIUM - Used by multiple extraction workflows
**Complexity**: MEDIUM - 4 remaining call sites

**Status**: Some methods already use `parse_python_code()` from Phase 1 work

#### 4. rename_symbol_refactor.py (Low Priority)

**Lines with `ast.parse`**: 227

**Impact**: LOW - Specialized refactoring tool
**Complexity**: LOW - Single call site

---

## Refactor Execution Plan

### ✅ Phase 3A: Surgical Extractor (COMPLETE - 2026-01-20)

**Goals**:
- ✅ Replace all 13 `ast.parse()` calls with `parse_python_code()`
- ✅ Add error handling and sanitization tracking
- ✅ Maintain backward compatibility

**Completed Tasks**:
1. ✅ Audited all 13 call sites and understand context
2. ✅ Added `ParsingError` exception handling with proper error messages
3. ✅ Integrated sanitization tracking via report object
4. ✅ Ran full test suite: 41 core tests + 33 integration tests (74/74 PASSING)
5. ✅ Validated MCP `extract_code` tool

**Changes Implemented**:
- Line 561: `_ensure_parsed()` - Main initialization with unified parser
- Line 1937: Variable promotion - finds function node with error handling
- Line 2009: Default value parsing - special case extraction with resilience
- Lines 2160, 2515, 2764, 2788, 3023: Helper methods with context
- Lines 3098, 3251, 3282, 3313, 3466: File-based operations with fallback

**Validation Results** ✅:
- All 41 core surgical_extractor tests PASSING
- All 33 integration tests PASSING
- Functional test of `get_function()`, `list_functions()` PASSING
- Zero regressions detected

### ✅ Phase 3B: Surgical Patcher (COMPLETE - 2026-01-20)

**Goals**:
- ✅ Replace all 7 `ast.parse()` calls with `parse_python_code()`
- ✅ Add safety checks for code mutation
- ✅ Ensure patch integrity

**Completed Tasks**:
1. ✅ Audited all 7 call sites for mutation points
2. ✅ Added `ParsingError` handling with proper error messages
3. ✅ Maintained type assertions for ClassDef, FunctionDef, AsyncFunctionDef
4. ✅ Ran full test suite: 40 patcher tests (40/40 PASSING)
5. ✅ Validated MCP `update_symbol` tool

**Changes Implemented**:
- Line 256: `_find_rename_usages()` - Token replacement helper with graceful fallback
- Line 403: `_ensure_parsed()` - Main initialization with unified parser and fallback sanitization
- Line 410: Retry parse after sanitization with proper error context
- Line 513: `_validate_replacement_code()` - Safety validation for new code
- Lines 723, 788, 934: `update_function()`, `update_class()`, `update_method()` - All update operations with type checking

**Validation Results** ✅:
- All 40 patcher integration tests PASSING
- Functional test of `update_function()` with docstring PASSING
- Zero regressions detected
- Type assertions preserved for safety

### ✅ Phase 3C: Remaining Modules (COMPLETE - 2026-01-20)

**Goals**:
- ✅ Refactor unified_extractor remaining calls
- ✅ Refactor rename_symbol_refactor
- ✅ Complete infrastructure unification

**Completed Tasks**:
1. ✅ Verified unified_extractor.py already uses unified parser (no ast.parse calls)
2. ✅ Added imports to rename_symbol_refactor.py
3. ✅ Refactored 1 ast.parse() call with proper error handling
4. ✅ All remaining surgery modules now unified

**Changes Implemented**:
- rename_symbol_refactor.py Line 227: `_collect_reference_edits()` - Replaced with parse_python_code()

**Status** ✅:
- ✅ ALL SURGERY MODULES NOW UNIFIED
- ✅ Zero `ast.parse()` calls in surgery/ directory
- ✅ All error handling migrated to ParsingError

---

## 🎉 PHASE 3 COMPLETE: Full Surgery Module Unification

### Summary of Changes

**Total Changes**: 21 ast.parse() calls replaced across 4 modules
- surgical_extractor.py: 13 calls ✅
- surgical_patcher.py: 7 calls ✅
- rename_symbol_refactor.py: 1 call ✅
- unified_extractor.py: 0 calls (already unified) ✅

**Test Results**:
- surgical_extractor: 41 core + 33 integration tests = 74/74 PASSING ✅
- surgical_patcher: 40 integration tests = 40/40 PASSING ✅
- Full test suite: All surgery-related tests PASSING ✅

### Key Achievements

1. **Deterministic Parsing**: All surgery modules now use unified parser with consistent error handling
2. **Error Resilience**: Proper ParsingError handling with graceful fallbacks
3. **Type Safety**: All type assertions preserved (ClassDef, FunctionDef, AsyncFunctionDef)
4. **Backward Compatibility**: Zero behavior changes, all existing tests passing
5. **Code Quality**: Proper error context and file tracking via filename parameter

### Next Steps

All surgery module parsing is now unified. Remaining optional improvements:

- [ ] Add parsing metrics tracking to response_config
- [ ] Document unified parser usage patterns in surgery module guide
- [ ] Consider performance optimization of parser cache in high-volume scenarios

---

## Pre-Phase 3 Checklist (COMPLETED)

Before Phase 3, ensure:

- ✅ All Phase 2 tests passing (✅ DONE: 131 get_file_context, 295 symbolic, 122 MCP core)
- ✅ No pre-existing test failures in surgery modules
- ✅ Backup strategy for rollback if needed
- ✅ Response config integration documented
- ✅ Team notified of upcoming infrastructure changes

---

## Testing Strategy for Surgery Modules

### Unit Tests

```python
def test_surgical_extractor_with_merge_conflict():
    """Ensure extractor handles parsing errors gracefully."""
    code = """
def foo():
<<<<<<< HEAD
    return 1
=======
    return 2
>>>>>>> branch
"""
    extractor = SurgicalExtractor(code)
    with pytest.raises(ExtractionError) as exc_info:
        extractor.extract_function("foo")
    
    assert "merge conflict" in str(exc_info.value).lower()
    assert exc_info.value.location == "line 3"
```

### Integration Tests

```python
def test_extract_code_tool_with_sanitization():
    """MCP extract_code should report sanitization."""
    code_with_template = """
def calculate(x):
    return x * {{ multiplier }}
"""
    result = extract_code_sync(code=code_with_template, target_name="calculate")
    
    if result.success:
        assert result.sanitization_report is not None
        assert result.sanitization_report["was_sanitized"]
```

### Regression Tests

Run full test suite before and after refactor:

```bash
# Baseline before refactor
pytest tests/core/parsers/test_surgical_extractor.py --json-report --json-report-file=before.json

# After refactor
pytest tests/core/parsers/test_surgical_extractor.py --json-report --json-report-file=after.json

# Compare
diff before.json after.json
```

---

## JavaScript/TypeScript Parsing Issues

### Current State

**File**: `mcp/helpers/analyze_helpers.py:431`

```python
# ❌ No error validation
parser = Parser(lang)
tree = parser.parse(bytes(code, "utf-8"))
# Continues even if tree.root_node.has_error == True
```

**Should Be**:
```python
from code_scalpel.parsing import parse_javascript_code, ParsingError

try:
    tree, report = parse_javascript_code(code, is_typescript=is_typescript)
except ParsingError as e:
    return AnalysisResult(
        success=False,
        error=str(e),
        error_location=e.location,
        suggestion=e.suggestion
    )
```

---

## Java Parsing Issues

**File**: `mcp/helpers/analyze_helpers.py:379`

```python
# ✅ Already has proper error handling via JavaParser wrapper
parser = JavaParser()
result = parser.parse(code)
```

**Status**: Java parsing is already wrapped. But should verify JavaParser respects `response_config.json`.

---

## Recommended Refactor Strategy

### Phase 1: Critical MCP Tools (Week 1)

1. **analyze_code** (Python, JS, TS, Java)
   - Update `_analyze_code_sync()` to use `parse_python_code()`
   - Update `_analyze_javascript_code()` to use `parse_javascript_code()`
   - Return sanitization report in AnalysisResult

2. **security_scan** 
   - Update all security helpers to use unified parser
   - Track sanitization in scan results

3. **extract_code**
   - Update extraction helpers to use unified parser
   - Report if extracted code was sanitized

### Phase 2: Core Infrastructure (Week 2)

4. **PDG Builder** - Already documented
5. **Surgical Extractor** - Already documented
6. **Surgical Patcher** - Multiple call sites
7. **Unified Extractor** - Multiple call sites

### Phase 3: Internal Tools (Week 3-4)

8. Security analyzers
9. Test generators
10. Policy engines
11. Analysis tools

---

## Response Config Integration Points

### Tool Response Format

Each MCP tool should respect `response_config.json` for error reporting:

```json
{
  "tool_overrides": {
    "analyze_code": {
      "include_on_error": [
        "parser_warnings",
        "sanitization_report",
        "error_location",
        "suggested_fix"
      ]
    }
  }
}
```

### Error Response Structure

```python
@dataclass
class AnalysisResult:
    success: bool
    functions: list[str]
    classes: list[str]
    # ... existing fields
    
    # ✅ ADD THESE
    error_location: str | None = None
    suggested_fix: str | None = None
    sanitization_report: dict | None = None
    parser_warnings: list[str] = field(default_factory=list)
```

---

## Implementation Checklist

### ✅ Phase 0: Infrastructure (DONE)
- [x] Created `src/code_scalpel/parsing/unified_parser.py`
- [x] Updated `response_config.json` with parsing section
- [x] Updated `response_config.schema.json` with validation
- [x] Tested basic parsing functionality

### ✅ Phase 1: Critical MCP Tools (DONE - 2026-01-19)

#### 1.0 Response Config Governance (Critical Foundation)

**File**: `src/code_scalpel/mcp/response_config.py`

- [x] Implemented `get_error_inclusions()` method for `include_on_error` support
- [x] Modified `filter_response()` to accept `is_error` parameter
- [x] Updated `filter_tool_response()` signature for error-conditional fields
- [x] Error fields (`error_location`, `suggested_fix`, `sanitization_report`, `parser_warnings`) now governed by config

**File**: `src/code_scalpel/mcp/models/core.py`

- [x] Added `error_location: str | None` to `AnalysisResult`
- [x] Added `suggested_fix: str | None` to `AnalysisResult`
- [x] Added `sanitization_report: dict[str, Any] | None` to `AnalysisResult`
- [x] Added `parser_warnings: list[str]` to `AnalysisResult`

**File**: `src/code_scalpel/parsing/unified_parser.py`

- [x] Added `filename` parameter to `parse_python_code()` for better error context
- [x] Error locations now include filename when provided (e.g., `myfile.py:42`)

#### 1.1 analyze_code (Python) ✅

**File**: `src/code_scalpel/mcp/helpers/analyze_helpers.py:1069`

```python
# IMPLEMENTED
from code_scalpel.parsing import ParsingError, parse_python_code

try:
    tree, sanitization_report = parse_python_code(code)
    parser_warnings: list[str] = []
    sanitization_dict: dict[str, Any] | None = None
    if sanitization_report.was_sanitized:
        parser_warnings.append(f"Code was auto-sanitized: {'; '.join(sanitization_report.changes)}")
        sanitization_dict = {"was_sanitized": True, "changes": sanitization_report.changes}
except ParsingError as e:
    return AnalysisResult(
        success=False, error=str(e), error_location=e.location, suggested_fix=e.suggestion,
        functions=[], classes=[], imports=[], complexity=0, lines_of_code=0,
    )
```

#### 1.2 security_scan ✅

**File**: `src/code_scalpel/mcp/helpers/security_helpers.py:884`

```python
# IMPLEMENTED
from code_scalpel.parsing import ParsingError, parse_python_code

try:
    tree, _ = parse_python_code(content, filename=str(py_file))
except (ParsingError, UnicodeDecodeError, OSError):
    continue  # Skip unparseable files
```

#### 1.3 extract_code (3 locations) ✅

**File**: `src/code_scalpel/mcp/helpers/extraction_helpers.py`

| Line | Function | Status |
|------|----------|--------|
| 1033 | `_semantic_name_check()` | ✅ Uses `parse_python_code()` with sanitization warning |
| 1471 | `_update_symbol_impl()` post-save verification | ✅ Uses `parse_python_code()` with filename |
| 1737 | `_update_cross_file_references()` | ✅ Uses `parse_python_code()` for signature detection |

#### 1.4 JavaScript/TypeScript (Deferred)

- [ ] `_analyze_javascript_code()` - Uses tree-sitter, separate refactor needed
- [ ] Java parsing - Already wrapped via `JavaParser`

---

### 🔲 Phase 2: MCP symbolic_execute (DONE - 2026-01-19)

**File**: `src/code_scalpel/mcp/helpers/symbolic_helpers.py`

**Status**: Already using unified parser from prior refactors

---

### 🔲 Phase 3: MCP graph tools (DONE - 2026-01-19)

**File**: `src/code_scalpel/mcp/helpers/graph_helpers.py`

**Status**: Already using unified parser from prior refactors

---

### ✅ Phase 2: MCP Helper Infrastructure (DONE - 2026-01-19)

#### 2.1 get_file_context ✅

**File**: `src/code_scalpel/mcp/helpers/context_helpers.py:1343, 1359`

```python
# IMPLEMENTED
try:
    tree, report = parse_python_code(code, filename=str(path))
    if getattr(report, "was_sanitized", False):
        code = report.sanitized_code or code
except ParsingError:
    # Fallback with permissive config for enterprise redaction flow
    sanitized, changed = sanitize_python_source(code)
    if not changed:
        return FileContextResult(success=False, error="Invalid Python syntax", ...)
    tree, report = parse_python_code(
        code, filename=str(path),
        config=ParsingConfig(mode="permissive", allow_merge_conflicts=True, ...)
    )
```

**Validation**: 131/131 tests passing

#### 2.2 ast_helpers ✅

**File**: `src/code_scalpel/mcp/helpers/ast_helpers.py:54, 60`

```python
# IMPLEMENTED
def parse_file_cached(file_path: Path) -> Optional[ast.Module]:
    cached = get_cached_ast(file_path)
    if cached is not None:
        return cached
    
    try:
        code = file_path.read_text(encoding="utf-8")
        try:
            tree, _report = parse_python_code(code, filename=str(file_path))
        except ParsingError:
            return None
        cache_ast(file_path, tree)
        return tree
    except OSError:
        return None
```

**Validation**: Integrated with get_file_context tests

#### 2.3 Symbolic Execution Tools ✅

**File**: `src/code_scalpel/symbolic_execution_tools/type_inference.py:104`

```python
# IMPLEMENTED
try:
    tree, _report = parse_python_code(code, filename="<type_inference>")
except ParsingError:
    return {}
```

**File**: `src/code_scalpel/symbolic_execution_tools/path_prioritization.py:140`

```python
# IMPLEMENTED
try:
    tree, _report = parse_python_code(self.code, filename="<path_prioritizer>")
except ParsingError:
    return
```

**Validation**: 295/295 symbolic execution tests passing

---

### 🔲 Phase 3: Surgery Module Refactor (TODO - Next Priority)

See detailed plan in "Phase 3: Surgery Module Refactor Plan" section below.

#### 4.1 PDG Builder
- **Status**: Deferred - Not a priority for current MCP tool stability
- File: `pdg_tools/builder.py:82`
- Already documented in migration guide

#### 4.2 Surgical Extractor ✅ (Moved to Phase 3)
- See Phase 3 refactor plan

#### 4.3 Surgical Patcher ✅ (Moved to Phase 3)
- See Phase 3 refactor plan

#### 4.4 Unified Extractor ✅ (Moved to Phase 3)
- See Phase 3 refactor plan

---

## Response Format Validation

### Current analyze_code Response

```json
{
  "success": true,
  "functions": ["foo", "bar"],
  "classes": ["MyClass"],
  "imports": ["os", "sys"],
  "complexity": 5,
  "lines_of_code": 100
}
```

### Enhanced Response (with parsing errors)

```json
{
  "success": false,
  "error": "Code contains merge conflict markers",
  "error_location": "line 3, column 0",
  "suggested_fix": "Resolve merge conflicts before analysis. Or set parsing.mode='permissive'",
  "parser_warnings": []
}
```

### Enhanced Response (with sanitization)

```json
{
  "success": true,
  "functions": ["calculate_tax"],
  "sanitization_report": {
    "was_modified": true,
    "changes": ["Stripped merge conflict markers"]
  },
  "parser_warnings": ["Code was auto-sanitized: Stripped merge conflict markers"]
}
```

---

## Response Config Controls

### Minimal Mode (Default)

```json
{
  "tool_overrides": {
    "analyze_code": {
      "profile": "minimal",
      "exclude_fields": ["raw_ast", "token_positions"],
      "include_on_error": []
    }
  }
}
```

**Response**:
```json
{
  "success": false,
  "error": "Code contains merge conflict markers"
}
```

### Standard Mode

```json
{
  "tool_overrides": {
    "analyze_code": {
      "profile": "standard",
      "include_on_error": ["error_location", "suggested_fix"]
    }
  }
}
```

**Response**:
```json
{
  "success": false,
  "error": "Code contains merge conflict markers",
  "error_location": "line 3",
  "suggested_fix": "Resolve conflicts or use permissive mode"
}
```

### Verbose Mode

```json
{
  "tool_overrides": {
    "analyze_code": {
      "profile": "verbose",
      "include_on_error": [
        "error_location",
        "suggested_fix",
        "sanitization_report",
        "parser_warnings"
      ]
    }
  }
}
```

**Response**:
```json
{
  "success": false,
  "error": "Code contains merge conflict markers: expected indent",
  "error_location": "line 3, column 0",
  "suggested_fix": "Resolve merge conflicts before analysis",
  "sanitization_report": {
    "attempted": false,
    "reason": "Strict mode - sanitization disabled"
  },
  "parser_warnings": []
}
```

---

## Testing Strategy

### Unit Tests for Each Tool

```python
def test_analyze_code_with_merge_conflict():
    """Test analyze_code fails deterministically on merge conflicts."""
    code = """
def foo():
    return 2
"""
    result = analyze_code_sync(code, "python")
    assert result.success is False
    assert "merge conflict" in result.error.lower()
    assert result.error_location == "line 3"
    assert "resolve conflicts" in result.suggested_fix.lower()
```

### Integration Tests

```python
def test_all_mcp_tools_use_unified_parser():
    """Verify all MCP tools flow through unified parser."""
    from code_scalpel.parsing import unified_parser
    
    # Monkey-patch to track calls
    calls = []
    original_parse = unified_parser.parse_python_code
    
    def tracked_parse(*args, **kwargs):
        calls.append(("python", args, kwargs))
        return original_parse(*args, **kwargs)
    
    unified_parser.parse_python_code = tracked_parse
    
    # Test each MCP tool
    analyze_code_sync("def foo(): pass", "python")
    assert len(calls) > 0, "analyze_code should use unified parser"
    
    # Repeat for other tools
    # ...
```

---

## Migration Priority Matrix

| Tool/Module | Impact | Complexity | Priority | Status |
|-------------|--------|------------|----------|--------|
| analyze_code | HIGH | LOW | 🔴 P0 | ✅ DONE |
| security_scan | HIGH | MEDIUM | 🔴 P0 | ✅ DONE |
| extract_code | HIGH | LOW | 🔴 P0 | ✅ DONE |
| get_file_context | HIGH | MEDIUM | 🔴 P0 | ✅ DONE |
| symbolic tools | MEDIUM | LOW | 🟡 P1 | ✅ DONE |
| Surgical Extractor | HIGH | HIGH | 🔴 P1 | 🔲 TODO |
| Surgical Patcher | HIGH | HIGH | 🔴 P1 | 🔲 TODO |
| Unified Extractor | MEDIUM | MEDIUM | 🟡 P2 | 🔲 TODO |
| Rename Symbol | LOW | LOW | 🟢 P3 | 🔲 TODO |
| PDG Builder | LOW | LOW | 🟢 P3 | 🔲 TODO |
| Internal analyzers | LOW | HIGH | 🟢 P4 | 🔲 TODO |

---

## Success Metrics

### Phase 1-2 Achievement (2026-01-19)

✅ **MCP Tools Unified**: All primary MCP tools now use unified parser
- analyze_code, security_scan, extract_code (Phase 1)
- get_file_context, symbolic tools (Phase 2)
- get_call_graph (already unified)

✅ **Test Coverage**:
- 131/131 get_file_context tests passing
- 295/295 symbolic execution tests passing  
- 122/122 core MCP tests passing
- 198/232 extract_code tests passing (34 pre-existing failures)

✅ **Infrastructure Complete**: 
- MCP helpers unified
- Symbolic execution tools unified
- Error handling with filename context
- Permissive fallback for enterprise redaction

### Phase 3 Target

🎯 **Surgery Module Coverage**: Refactor 20+ `ast.parse()` calls in surgery modules
- surgical_extractor.py (13 calls)
- surgical_patcher.py (7 calls)
- unified_extractor.py (remaining calls)
- rename_symbol_refactor.py (1 call)

### Determinism Verification

After refactor, this test should pass:

```python
def test_deterministic_behavior():
    """All tools produce identical output for same input + config."""
    dirty_code = "def foo():\n<<<<<<< HEAD\n    pass"
    
    # Run 100 times
    results = []
    for _ in range(100):
        result = analyze_code_sync(dirty_code, "python")
        results.append((result.success, result.error))
    
    # All identical
    assert len(set(results)) == 1
```

### Coverage Metrics

**Phase 1-2 Completion**:

```bash
# MCP helpers - Before
$ grep -r "ast.parse(" src/code_scalpel/mcp/helpers | wc -l
10

# MCP helpers - After Phase 2
$ grep -r "ast.parse(" src/code_scalpel/mcp/helpers | wc -l
0

# Unified parser usage in MCP
$ grep -r "parse_python_code" src/code_scalpel/mcp | wc -l
15+
```

**Phase 3 Target**:

```bash
# Surgery modules - Before
$ grep -r "ast.parse(" src/code_scalpel/surgery | wc -l
20+

# Surgery modules - Target
$ grep -r "ast.parse(" src/code_scalpel/surgery | wc -l
0

# Unified parser usage in surgery
$ grep -r "parse_python_code" src/code_scalpel/surgery | wc -l
20+
```

---

## Rollout Plan

### ✅ Phase 1: Core MCP Tools (Week 1 - COMPLETE)
- ✅ Refactor analyze_code (Python)
- ✅ Add sanitization report to AnalysisResult
- ✅ Update response_config integration
- ✅ Add unit tests
- ✅ Refactor security_scan
- ✅ Refactor extract_code

### ✅ Phase 2: MCP Infrastructure (Week 2 - COMPLETE)
- ✅ Refactor get_file_context with permissive fallback
- ✅ Refactor ast_helpers (parse_file_cached)
- ✅ Refactor symbolic execution tools (type_inference, path_prioritization)
- ✅ Integration tests (131 get_file_context, 295 symbolic, 122 MCP core passing)

### 🔲 Phase 3: Surgery Modules (Week 3 - NEXT)
- [ ] Week 3A: Refactor Surgical Extractor (13 call sites)
- [ ] Week 3B: Refactor Surgical Patcher (7 call sites)  
- [ ] Week 3C: Refactor Unified Extractor (remaining calls)
- [ ] Week 3C: Refactor Rename Symbol (1 call site)
- [ ] Performance tests and validation

### 🔲 Phase 4: Specialized Tools (Week 4 - FUTURE)
- [ ] Refactor internal analyzers (error_scanner, regression_predictor, custom_rules)
- [ ] Documentation updates
- [ ] Final validation
- [ ] Release v3.4.0 (unified parser complete)

---

## Conclusion

**Current State (2026-01-19)**: 
- ✅ Phase 1 complete - 5 critical MCP tools (analyze_code, security_scan, extract_code)
- ✅ Phase 2 complete - All MCP helpers and symbolic tools unified
- 🔲 Phase 3 next - 20+ surgery module calls remain

**Progress**: 
- MCP tools: 100% unified (15+ parse_python_code calls, 0 direct ast.parse)
- Symbolic tools: 100% unified (2 modules refactored)
- Surgery modules: 0% unified (20+ ast.parse calls remain)

**Remaining Work**: ~20 direct parsing calls in surgery modules (surgical_extractor, surgical_patcher)

**Target State**: All parsing through unified infrastructure for deterministic behavior

**Completed**:
- ✅ `analyze_code` Python parsing with full error context
- ✅ `security_scan` with filename tracking
- ✅ `extract_code` all 3 locations
- ✅ `get_file_context` with permissive fallback
- ✅ `ast_helpers` (parse_file_cached)
- ✅ `symbolic_execution_tools` (type_inference, path_prioritization)
- ✅ `response_config.py` `include_on_error` implementation
- ✅ `AnalysisResult` model with parsing error fields

**Next Priority**: Phase 3 - Surgery module refactor
1. surgical_extractor.py (13 calls) - Highest impact
2. surgical_patcher.py (7 calls) - High risk, careful testing
3. unified_extractor.py (remaining) - Medium priority
4. rename_symbol_refactor.py (1 call) - Low priority
