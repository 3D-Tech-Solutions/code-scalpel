# Deterministic Parsing: Migration Guide

## Overview

Code-Scalpel now uses **centralized parsing configuration** via `.code-scalpel/response_config.json`. This ensures **deterministic behavior**: same input + same config = same output.

---

## Quick Start

### 1. Configure Parsing Mode

Edit `.code-scalpel/response_config.json`:

```json
{
  "parsing": {
    "mode": "strict",
    "sanitization_policy": {
      "allow_merge_conflicts": false,
      "allow_templates": false,
      "report_modifications": true
    }
  }
}
```

**Modes**:
- `"strict"` - Fail immediately on syntax errors (default, deterministic)
- `"permissive"` - Auto-sanitize with warnings (for IDE/templates)

---

### 2. Refactor Code

**Before** (non-deterministic):
```python
import ast

def analyze_code(code: str):
    tree = ast.parse(code)  # ❌ Crashes on dirty code
    # ... analysis
```

**After** (deterministic):
```python
from code_scalpel.parsing import parse_python_code, ParsingError

def analyze_code(code: str):
    try:
        tree, report = parse_python_code(code)
    except ParsingError as e:
        return {
            "success": False,
            "error": str(e),
            "location": e.location,
            "suggestion": e.suggestion
        }
    
    # Track sanitization
    result = {"success": True, "functions": [...]}
    if report.was_sanitized:
        result["sanitization"] = {
            "changes": report.changes,
            "modified": True
        }
    
    return result
```

---

## Configuration Examples

### Strict Mode (Production)

```json
{
  "parsing": {
    "mode": "strict",
    "sanitization_policy": {
      "allow_merge_conflicts": false,
      "allow_templates": false,
      "report_modifications": true
    }
  }
}
```

**Behavior**:
- Merge conflicts → **Error**
- Jinja2 templates → **Error**
- Invalid syntax → **Error with location + suggestion**

**Use for**: CI/CD, security audits, production code analysis

---

### Permissive Mode (IDE Features)

```json
{
  "parsing": {
    "mode": "permissive",
    "sanitization_policy": {
      "allow_merge_conflicts": true,
      "allow_templates": true,
      "report_modifications": true
    }
  }
}
```

**Behavior**:
- Merge conflicts → **Auto-stripped + warning**
- Jinja2 templates → **Auto-replaced + warning**
- Invalid syntax → **Error (unfixable)**

**Use for**: IDE autocomplete, template analysis, partial code

---

## Profile-Based Configuration

Use profiles for different environments:

```json
{
  "profiles": {
    "strict": {
      "parsing": {
        "mode": "fail_fast",
        "sanitization_policy": {
          "allow_merge_conflicts": false,
          "allow_templates": false
        }
      }
    },
    "permissive": {
      "parsing": {
        "mode": "auto_sanitize",
        "sanitization_policy": {
          "allow_merge_conflicts": true,
          "allow_templates": true,
          "report_modifications": true
        }
      }
    }
  }
}
```

Switch profiles:
```python
from code_scalpel.parsing import ParsingConfig

# Temporarily use permissive mode
config = ParsingConfig(mode="permissive", allow_templates=True)
tree, report = parse_python_code(code, config=config)
```

---

## Entry Point Migration

### 1. PDG Builder

**File**: `src/code_scalpel/pdg_tools/builder.py`

**Before**:
```python
def build(self, code: str) -> tuple[nx.DiGraph, nx.DiGraph]:
    tree = ast.parse(code)  # ❌ Line 82 - No error handling
    self.visit(tree)
    return self.graph, self.call_graph
```

**After**:
```python
from code_scalpel.parsing import parse_python_code, ParsingError

def build(self, code: str) -> tuple[nx.DiGraph, nx.DiGraph]:
    try:
        tree, report = parse_python_code(code)
    except ParsingError as e:
        raise ValueError(
            f"Cannot build PDG: {e}\n"
            f"Location: {e.location}\n" 
            f"Tip: {e.suggestion}"
        ) from e
    
    if report.was_sanitized:
        self._sanitization_report = report
        
    self.visit(tree)
    return self.graph, self.call_graph
```

---

### 2. Surgical Extractor

**File**: `src/code_scalpel/surgery/surgical_extractor.py`

**Before**:
```python
try:
    self._tree = ast.parse(self.code)
except SyntaxError as e:
    raise ValueError(f"Invalid Python code: {e}")  # ⚠️ Line 560
```

**After**:
```python
from code_scalpel.parsing import parse_python_code, ParsingError

try:
    self._tree, report = parse_python_code(self.code)
    self._sanitization_report = report
except ParsingError as e:
    raise ValueError(
        f"Invalid Python code: {e}\n"
        f"Location: {e.location}\n"
        f"Tip: {e.suggestion}"
    ) from e
```

---

### 3. JavaScript/TypeScript Analyzer

**File**: `src/code_scalpel/mcp/helpers/analyze_helpers.py`

**Before**:
```python
parser = Parser(lang)
tree = parser.parse(bytes(code, "utf-8"))  # ⚠️ Line 431 - No error check
```

**After**:
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

## Error Reporting

### Enhanced Error Objects

```python
class ParsingError(ValueError):
    """Deterministic parsing error with context."""
    
    def __init__(self, message: str, *, location: str | None, suggestion: str | None):
        self.location = location      # "line 5, column 12"
        self.suggestion = suggestion  # "Resolve merge conflicts..."
```

### Tool Response Format

Controlled by `response_config.json`:

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

**Minimal Mode** (default):
```json
{
  "success": false,
  "error": "Code contains merge conflict markers",
  "location": "line 3",
  "suggestion": "Resolve conflicts or use permissive mode"
}
```

**Verbose Mode** (debug):
```json
{
  "success": false,
  "error": "Code contains merge conflict markers",
  "location": "line 3, column 0",
  "suggestion": "Resolve merge conflicts before analysis",
  "sanitization_attempted": false,
  "parser_warnings": ["SyntaxError: expected indent"],
  "original_code_snippet": "<<<<<<< HEAD"
}
```

---

## Testing

### Test Deterministic Behavior

```python
def test_deterministic_parsing():
    """Same input + same config = same output."""
    code_with_conflict = """
def foo():
<<<<<<< HEAD
    return 1
=======
    return 2
>>>>>>> branch
"""
    
    # Test 1: Strict mode
    config = ParsingConfig(mode="strict")
    try:
        tree1, _ = parse_python_code(code_with_conflict, config=config)
        assert False, "Should have raised ParsingError"
    except ParsingError as e1:
        # Same error every time
        assert "merge conflict" in str(e1).lower()
        assert e1.location == "line 3"
    
    # Test 2: Permissive mode
    config = ParsingConfig(mode="permissive", allow_merge_conflicts=True)
    tree1, report1 = parse_python_code(code_with_conflict, config=config)
    tree2, report2 = parse_python_code(code_with_conflict, config=config)
    
    # Deterministic sanitization
    assert report1.was_sanitized == report2.was_sanitized
    assert report1.changes == report2.changes
    assert ast.dump(tree1) == ast.dump(tree2)
```

---

## Rollback Plan

If you need to revert to old behavior:

1. **Keep old imports** working:
   ```python
   # Old code still works
   import ast
   tree = ast.parse(code)
   ```

2. **Set permissive mode globally**:
   ```json
   {"parsing": {"mode": "permissive"}}
   ```

3. **Disable warnings**:
   ```json
   {
     "parsing": {
       "sanitization_policy": {
         "report_modifications": false
       }
     }
   }
   ```

---

## FAQ

### Q: Why did my code start failing?

**A**: Strict mode is now default. Code with merge conflicts or templates will fail explicitly instead of silently corrupting analysis.

**Fix**: Either:
1. Clean your code (resolve conflicts, extract templates)
2. Use permissive mode: `{"parsing": {"mode": "permissive"}}`

---

### Q: How do I get the old behavior back?

**A**: Set permissive mode + disable warnings:
```json
{
  "parsing": {
    "mode": "permissive",
    "sanitization_policy": {
      "allow_merge_conflicts": true,
      "allow_templates": true,
      "report_modifications": false
    }
  }
}
```

---

### Q: What's the performance impact?

**A**: Minimal:
- Config loaded once at startup
- Parsing logic identical (just wrapped)
- Error handling adds <1ms overhead

---

### Q: Can I use different modes per tool?

**A**: Yes, via profiles:
```json
{
  "tool_overrides": {
    "analyze_code": "permissive",
    "security_scan": "strict"
  }
}
```

---

## Timeline

- **v1.0.0**: Current non-deterministic behavior
- **v1.1.0**: Add `parsing` module + config (permissive default for compatibility)
- **v1.2.0**: Deprecation warnings for direct `ast.parse()` usage
- **v2.0.0**: Change default to strict mode (**BREAKING CHANGE**)

---

## Related Documents

- [Architect's Final Report](ARCHITECT_FINAL_REPORT.md) - Full analysis
- [Parsing Flow Architecture](architecture/PARSING_FLOW_ARCHITECTURE.md) - Diagrams
- [response_config.json](../.code-scalpel/response_config.json) - Configuration reference
