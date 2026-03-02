# Adding a New Language to Code Scalpel

This guide covers every integration point you need to touch when adding support for a new programming language. Follow the checklist in order — later steps depend on earlier ones being complete.

**Target audience**: Contributors extending Code Scalpel's polyglot support.

**Example used throughout**: Go (`go`, `.go` extension, `tree-sitter-go` backend).

**Language-specific guides** (pre-written for the four planned languages):

| Language | Guide | Difficulty |
|----------|-------|------------|
| Kotlin | [Adding-Kotlin.md](Adding-Kotlin.md) | Medium |
| Ruby | [Adding-Ruby.md](Adding-Ruby.md) | Medium-High |
| Rust | [Adding-Rust.md](Adding-Rust.md) | High |
| Swift | [Adding-Swift.md](Adding-Swift.md) | Medium-High |

---

## Prerequisites

Before writing any code:

1. Confirm a tree-sitter grammar exists: `pip show tree-sitter-go` or search PyPI for `tree-sitter-<lang>`.
2. Add the dependency to `pyproject.toml` (Step 1 below).
3. Understand the language's top-level AST node types — run the tree-sitter playground or check the grammar's `grammar.js`.

---

## Integration Checklist

There are **12 distinct integration points** across 3 layers. This table is your at-a-glance checklist:

| # | File | What to add |
|---|------|-------------|
| 1 | `pyproject.toml` | `tree-sitter-go` dependency |
| 2 | `src/code_scalpel/code_parsers/extractor.py` | `Language.GO` enum value + extension map + `detect_language()` heuristics + `_parse()` dispatch case + `_parse_go()` method |
| 3 | `src/code_scalpel/polyglot/extractor.py` | Same Language enum / extension map / detect_language / `_parse()` dispatch (mirror of #2) |
| 4 | `src/code_scalpel/ir/normalizers/go_normalizer.py` | **New file** — `GoNormalizer` + `GoVisitor` |
| 5 | `src/code_scalpel/ir/normalizers/__init__.py` | Conditional import of `GoNormalizer` |
| 6 | `src/code_scalpel/code_parsers/adapters/go_adapter.py` | Implement `GoParserAdapter` (stub already exists) |
| 7 | `src/code_scalpel/code_parsers/adapters/__init__.py` | Already imports `GoParserAdapter` — just make it real |
| 8 | `src/code_scalpel/capabilities/limits.toml` | Add `"go"` to `languages` arrays in all tier sections |
| 9 | `src/code_scalpel/mcp/tools/extraction.py` | Update `language` param docstring |
| 10 | `src/code_scalpel/mcp/tools/oracle.py` (analyze_code) | Update `language` param docstring |
| 11 | `src/code_scalpel/cli.py` | Add `.go` → `"go"` in the local `extension_map` dict |
| 12 | `tests/languages/` | Add tests to `test_polyglot_support.py` + new `test_go_parser.py` |

---

## Step-by-Step Implementation

### Step 1 — Add the tree-sitter dependency

**File**: [pyproject.toml](../pyproject.toml)

Add the tree-sitter grammar package to the `dependencies` list:

```toml
dependencies = [
    ...
    "tree-sitter-go>=0.23.0",
]
```

Verify it installs cleanly:

```bash
pip install tree-sitter-go
python -c "import tree_sitter_go; print('OK')"
```

---

### Step 2 — Register the language in both extractor modules

**Note**: There are two extractor files that both maintain the `Language` enum and `EXTENSION_MAP`. Both must be updated identically.

- [src/code_scalpel/code_parsers/extractor.py](../src/code_scalpel/code_parsers/extractor.py) — primary location
- [src/code_scalpel/polyglot/extractor.py](../src/code_scalpel/polyglot/extractor.py) — kept in sync for backward compatibility

#### 2a. Add the enum value

```python
class Language(Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    C = "c"
    CPP = "cpp"
    CSHARP = "csharp"
    GO = "go"          # ← add this
    AUTO = "auto"
```

#### 2b. Add file extensions

```python
EXTENSION_MAP: dict[str, Language] = {
    ...
    ".go": Language.GO,
}
```

#### 2c. Add content-based detection heuristics

In `detect_language()`, add a Go branch **before** the JavaScript fallback:

```python
# Go indicators (check before JS – 'func' keyword is unambiguous)
if any(
    kw in code
    for kw in [
        "package main",
        "func ",
        "import (",
        ":= ",
    ]
):
    return Language.GO
```

**Ordering matters**: place more specific language checks earlier to avoid misidentification (e.g., C# before Java, C++ before C, Go before JavaScript).

#### 2d. Add the `_parse()` dispatch case

In `PolyglotExtractor._parse()`, add the Go branch immediately before the `else` clause:

```python
elif self.language == Language.GO:
    self._parse_go()
```

#### 2e. Add the `_parse_go()` method

```python
def _parse_go(self) -> None:
    """Parse Go code using tree-sitter-go."""
    from code_scalpel.ir.normalizers.go_normalizer import GoNormalizer

    normalizer = GoNormalizer()
    self._ir_module = normalizer.normalize(self.code, source_file=self.file_path)
```

Follow the same pattern as `_parse_c()`, `_parse_cpp()`, or `_parse_csharp()`.

---

### Step 3 — Write the IR Normalizer

**New file**: [src/code_scalpel/ir/normalizers/go_normalizer.py](../src/code_scalpel/ir/normalizers/go_normalizer.py)

This is the most substantial part of the implementation. The normalizer converts tree-sitter's concrete syntax tree (CST) into Code Scalpel's Unified IR.

#### File structure

```python
"""
Go Normalizer - Converts Go CST (tree-sitter-go) to Unified IR.

Key Mappings:
    source_file           -> IRModule
    function_declaration  -> IRFunctionDef
    method_declaration    -> IRFunctionDef
    type_declaration      -> IRClassDef  (structs/interfaces)
    import_declaration    -> IRImport
    return_statement      -> IRReturn
    if_statement          -> IRIf
    for_statement         -> IRFor
    call_expression       -> IRCall
    ...
"""

from __future__ import annotations
import tree_sitter_go
from tree_sitter import Language, Parser
from ..nodes import (
    IRModule, IRFunctionDef, IRClassDef, IRImport,
    IRReturn, IRIf, IRFor, IRCall, IRName, IRConstant,
    # ... other IR nodes needed
)
from .tree_sitter_visitor import TreeSitterVisitor, VisitorContext
from .base import BaseNormalizer


class GoVisitor(TreeSitterVisitor):
    """Visits Go CST nodes and populates IR."""

    def visit_function_declaration(self, node, ctx: VisitorContext) -> None:
        name_node = node.child_by_field_name("name")
        if name_node:
            func_def = IRFunctionDef(name=name_node.text.decode())
            ctx.current_scope.body.append(func_def)

    def visit_type_declaration(self, node, ctx: VisitorContext) -> None:
        # Struct and interface declarations
        ...


class GoNormalizer(BaseNormalizer):
    """Normalize Go source to Unified IR."""

    def __init__(self) -> None:
        GO_LANGUAGE = Language(tree_sitter_go.language())
        self._parser = Parser()
        self._parser.set_language(GO_LANGUAGE)

    def normalize(self, code: str, source_file: str | None = None) -> IRModule:
        tree = self._parser.parse(code.encode("utf-8"))
        module = IRModule(source_language="go", source_file=source_file or "")
        visitor = GoVisitor()
        visitor.visit(tree.root_node, VisitorContext(module=module))
        return module
```

#### Reference implementations

Look at these existing normalizers for patterns to follow:

- [c_normalizer.py](../src/code_scalpel/ir/normalizers/c_normalizer.py) — simplest tree-sitter normalizer
- [cpp_normalizer.py](../src/code_scalpel/ir/normalizers/cpp_normalizer.py) — classes, templates, namespaces
- [csharp_normalizer.py](../src/code_scalpel/ir/normalizers/csharp_normalizer.py) — generics, async/await

#### Minimum viable node coverage

For the normalizer to support `extract_code` and `analyze_code`, you need at minimum:

| Language construct | IR node |
|-------------------|---------|
| Functions / methods | `IRFunctionDef` |
| Types (structs, interfaces) | `IRClassDef` |
| Import statements | `IRImport` |
| Function calls | `IRCall` |
| Return statements | `IRReturn` |
| Variable assignments | `IRAssign` |

---

### Step 4 — Register the normalizer

**File**: [src/code_scalpel/ir/normalizers/__init__.py](../src/code_scalpel/ir/normalizers/__init__.py)

Add a conditional import following the established pattern:

```python
# Go normalizer — requires tree-sitter-go
try:
    from .go_normalizer import GoNormalizer, GoVisitor
    _HAS_GO = True
except ImportError:
    GoNormalizer = None  # type: ignore[assignment]
    GoVisitor = None  # type: ignore[assignment]
    _HAS_GO = False
```

And add to `__all__`:

```python
if _HAS_GO:
    __all__ += ["GoNormalizer", "GoVisitor"]
```

The `try/except ImportError` pattern means Code Scalpel degrades gracefully if `tree-sitter-go` is not installed — the other languages still work.

---

### Step 5 — Implement the parser adapter

**File**: [src/code_scalpel/code_parsers/adapters/go_adapter.py](../src/code_scalpel/code_parsers/adapters/go_adapter.py)

A stub already exists — replace the `raise NotImplementedError` in `__init__` and implement the `parse()` method:

```python
class GoParserAdapter(IParser):
    """Adapter wrapping GoNormalizer to the IParser interface."""

    def __init__(self):
        from code_scalpel.ir.normalizers.go_normalizer import GoNormalizer
        self._normalizer = GoNormalizer()

    def parse(self, code: str) -> ParseResult:
        ir_module = self._normalizer.normalize(code)
        return ParseResult(
            ast_tree=ir_module,
            language="go",
            success=True,
        )

    def get_functions(self, ast_tree) -> list[str]:
        from code_scalpel.ir.nodes import IRFunctionDef
        return [
            node.name for node in ast_tree.body
            if isinstance(node, IRFunctionDef)
        ]

    def get_classes(self, ast_tree) -> list[str]:
        from code_scalpel.ir.nodes import IRClassDef
        return [
            node.name for node in ast_tree.body
            if isinstance(node, IRClassDef)
        ]
```

**Note**: The `adapters/__init__.py` already has the conditional import for `GoParserAdapter` — once the `raise NotImplementedError` is removed from `__init__`, the import will succeed automatically.

---

### Step 6 — Add Go to the tier capabilities

**File**: [src/code_scalpel/capabilities/limits.toml](../src/code_scalpel/capabilities/limits.toml)

Find every `languages` array in the file (one per tier section) and add `"go"`:

```toml
[community.analyze_code]
languages = [
    "python",
    "javascript",
    "typescript",
    "java",
    "c",
    "cpp",
    "csharp",
    "go",      # ← add here
]
```

Search for all occurrences: there are typically three (community, pro, enterprise). All should be updated.

---

### Step 7 — Update MCP tool docstrings

Two MCP tools explicitly list supported languages in their docstrings. Update both so AI agents know Go is available.

**File**: [src/code_scalpel/mcp/tools/extraction.py](../src/code_scalpel/mcp/tools/extraction.py)

Find the `language` parameter description in `extract_code`'s docstring:

```python
language (str, optional): Programming language. Default: auto-detect.
    Supported: python, javascript, typescript, java, c, cpp, csharp, go.
```

**File**: [src/code_scalpel/mcp/tools/oracle.py](../src/code_scalpel/mcp/tools/oracle.py)

Find the `language` parameter description in `analyze_code`'s docstring and add `go` to the list.

---

### Step 8 — Update the CLI extension map

**File**: [src/code_scalpel/cli.py](../src/code_scalpel/cli.py)

The `analyze_file()` function has a local `extension_map` dict (separate from the one in extractor.py). Add Go:

```python
extension_map = {
    ".py": "python",
    ".js": "javascript",
    ...
    ".java": "java",
    ".go": "go",    # ← add this
}
```

This enables `codescalpel analyze myfile.go` from the command line.

---

### Step 9 — Write tests

#### 9a. Add cases to the shared polyglot test file

**File**: [tests/languages/test_polyglot_support.py](../tests/languages/test_polyglot_support.py)

Add Go to the parametrized language detection and extraction tests. Look for the existing `@pytest.mark.parametrize` blocks and add a Go tuple:

```python
@pytest.mark.parametrize("file_ext,expected_language", [
    ...
    (".go", Language.GO),
])
def test_language_detection_by_extension(file_ext, expected_language):
    ...
```

#### 9b. Create a dedicated Go parser test file

**New file**: `tests/languages/test_go_parser.py`

```python
"""Tests for Go language support."""
import pytest
from code_scalpel.code_parsers.extractor import Language, detect_language, PolyglotExtractor

GO_SNIPPET = '''
package main

import "fmt"

type Point struct {
    X, Y float64
}

func (p Point) Distance() float64 {
    return p.X * p.X + p.Y * p.Y
}

func main() {
    p := Point{X: 3.0, Y: 4.0}
    fmt.Println(p.Distance())
}
'''

def test_detect_go_by_extension():
    assert detect_language("main.go") == Language.GO

def test_detect_go_by_content():
    assert detect_language(None, GO_SNIPPET) == Language.GO

def test_extract_go_function():
    extractor = PolyglotExtractor(GO_SNIPPET, language=Language.GO)
    result = extractor.extract("function", "main")
    assert result.success
    assert "func main()" in result.code

def test_extract_go_method():
    extractor = PolyglotExtractor(GO_SNIPPET, language=Language.GO)
    result = extractor.extract("method", "Distance")
    assert result.success
    assert "func (p Point) Distance()" in result.code

def test_extract_go_struct():
    extractor = PolyglotExtractor(GO_SNIPPET, language=Language.GO)
    result = extractor.extract("class", "Point")
    assert result.success
    assert "type Point struct" in result.code
```

Run with: `pytest tests/languages/test_go_parser.py -v`

---

## Verification Checklist

After completing all steps, confirm end-to-end functionality:

```bash
# 1. Extension detection
python -c "
from code_scalpel.code_parsers.extractor import detect_language, Language
assert detect_language('main.go') == Language.GO
print('Extension detection: OK')
"

# 2. Content detection
python -c "
from code_scalpel.code_parsers.extractor import detect_language, Language
assert detect_language(None, 'package main\nfunc main() {}') == Language.GO
print('Content detection: OK')
"

# 3. Normalizer import
python -c "
from code_scalpel.ir.normalizers import GoNormalizer
print('Normalizer import: OK')
"

# 4. Adapter import
python -c "
from code_scalpel.code_parsers.adapters import GoParserAdapter
print('Adapter import: OK')
"

# 5. Extraction via MCP tool (locally)
python -c "
from code_scalpel.polyglot.extractor import PolyglotExtractor, Language
extractor = PolyglotExtractor('func hello() { return }', language=Language.GO)
result = extractor.extract('function', 'hello')
print('Extraction:', 'OK' if result.success else result.error)
"

# 6. Run test suite
pytest tests/languages/ -v -k go
```

---

## Common Pitfalls

| Problem | Cause | Fix |
|---------|-------|-----|
| `ImportError: No module named tree_sitter_go` | Package not installed | `pip install tree-sitter-go` |
| Language detected as Python | Missing content heuristics | Add keywords to `detect_language()` in both extractor files |
| `ValueError: Unsupported language: Language.GO` | Missing `_parse()` dispatch case | Add `elif self.language == Language.GO: self._parse_go()` |
| `extract_code` returns "language not supported" | Missing from `limits.toml` | Add `"go"` to all `languages` arrays |
| Adapter import silently fails (remains `None`) | `raise NotImplementedError` in `__init__` | Implement `GoParserAdapter.__init__` |
| Content heuristics mis-detect language | Heuristic ordering issue | Move more specific checks earlier in `detect_language()` |

---

## Architecture Notes

### Two extractor files

Code Scalpel has two files that both maintain the `Language` enum and `EXTENSION_MAP`:

- `src/code_scalpel/code_parsers/extractor.py` — the primary, canonical location
- `src/code_scalpel/polyglot/extractor.py` — kept for backward compatibility (aliases into code_parsers)

When adding a language, **update both**. A test will catch any mismatch.

### Graceful degradation

All language-specific imports are wrapped in `try/except ImportError`. If a tree-sitter grammar is not installed, Code Scalpel logs a warning but continues functioning for other languages. This means you can ship an adapter that's "available but requires optional install" without breaking the core package.

### Normalizer vs Adapter

- **Normalizer** (`ir/normalizers/`) — converts raw tree-sitter CST → Unified IR. This is where structural understanding lives.
- **Adapter** (`code_parsers/adapters/`) — wraps the normalizer to implement the `IParser` interface used by the `ParserFactory`. Most new languages can implement the adapter as a thin shim over the normalizer.

### Security scanning for new languages

Security scanning (OWASP patterns, taint tracking) operates on the Unified IR — it is **language-agnostic by design**. Once your normalizer correctly maps source constructs to IR nodes (especially `IRCall`, `IRAssign`, `IRReturn`), the security scanner will work automatically with no additional changes.

Cross-file taint tracking (`cross_file_security_scan`) additionally requires that `IRImport` nodes are populated correctly so the taint engine can follow import chains.

---

## Quick-Reference: Minimum Diff for a New Language

If you want the smallest possible working integration (extraction only, no advanced features):

1. **`pyproject.toml`** — add grammar dependency
2. **`code_parsers/extractor.py`** — enum, extension, `_parse()` case, `_parse_newlang()`
3. **`polyglot/extractor.py`** — same as above
4. **`ir/normalizers/newlang_normalizer.py`** — new file
5. **`ir/normalizers/__init__.py`** — conditional import
6. **`code_parsers/adapters/newlang_adapter.py`** — implement (or fill stub)
7. **`capabilities/limits.toml`** — add to all `languages` arrays
8. **`cli.py`** — add extension mapping

The MCP docstrings (Steps 9–10 above) and tests (Step 12) should be added before merging to main.
