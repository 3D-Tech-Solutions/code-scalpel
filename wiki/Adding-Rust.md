# Adding Rust Language Support

**Difficulty**: High — Rust is the most complex of the four stubs. The language's ownership model, lifetimes, trait system, and generic bounds do not map to IR constructs directly, but the extraction layer only needs to understand the *structure* (functions, types, modules) — not the semantics of borrowing. The core challenges are: `impl` blocks (methods live inside `impl_item`, not directly on structs), trait implementations (`impl Foo for Bar`), macros (`println!`, `vec!`), and the module system (`mod` blocks that can contain nested functions and types).

**Estimated integration points**: 12 files (see [Adding-A-Language.md](Adding-A-Language.md) for the master checklist).

---

## Package

```bash
pip install tree-sitter-rust
python -c "import tree_sitter_rust; print('OK')"
```

Add to `pyproject.toml`:

```toml
"tree-sitter-rust>=0.21.0",  # [FEATURE] Rust language support
```

Add to all three locations: `dependencies`, `[all]`, and `[polyglot]` extras.

---

## Language Enum + Extension Map

```python
# Language enum (both extractor files)
RUST = "rust"

# Extension map
".rs": Language.RUST,
```

---

## Content-Based Detection Heuristics

Place the Rust block **after** C++ and **before** C (Rust shares `#include`-free syntax but has unambiguous keywords):

```python
# Rust indicators — fn/let/use/impl are unambiguous when combined
if any(kw in code for kw in ["fn ", "let mut", "use std::", "impl ", "pub fn", "-> Result<", "-> Option<"]):
    return Language.RUST
```

**Ordering**: C# → Go → Kotlin → Java → C++ → Rust → C → JavaScript → Python.

`"fn "` alone could appear in identifiers, so prefer the combined set. `"use std::"`, `"let mut"`, and `"-> Result<"` are unambiguously Rust.

---

## Key AST Node Mappings

| tree-sitter-rust node | IR node | Notes |
|----------------------|---------|-------|
| `source_file` | `IRModule` | Root |
| `use_declaration` | `IRImport` | `use std::collections::HashMap` → strip to module path |
| `function_item` | `IRFunctionDef` | `fn foo(x: i32) -> i32` |
| `struct_item` | `IRClassDef` | `struct Point { x: f64, y: f64 }` → `_metadata["kind"] = "struct"` |
| `enum_item` | `IRClassDef` | `enum Color { Red, Green, Blue }` → `_metadata["kind"] = "enum"` |
| `trait_item` | `IRClassDef` | `trait Animal { fn speak(&self); }` → `_metadata["kind"] = "trait"` |
| `impl_item` (inherent) | (visit body for `function_item`) | `impl Point { fn distance(&self) -> f64 }` — emit methods directly into IR |
| `impl_item` (trait impl) | (visit body for `function_item`) | `impl Display for Point` — methods stored with `_metadata["trait_impl"] = "Display"` |
| `mod_item` with body | `IRClassDef` | `mod geometry { ... }` — treat as namespace class; `_metadata["kind"] = "module"` |
| `mod_item` without body | `IRImport` | `mod utils;` — external file module declaration |
| `let_declaration` | `IRAssign` | `let x = 42;` and `let mut y: Vec<i32> = vec![];` |
| `assignment_expression` | `IRAssign` | `x = 5;` |
| `return_expression` | `IRReturn` | `return x;` |
| `if_expression` | `IRIf` | |
| `if_let_expression` | `IRIf` | `if let Some(x) = opt { ... }`; `_metadata["kind"] = "if_let"` |
| `while_expression` | `IRFor` | `_metadata["kind"] = "while"` |
| `while_let_expression` | `IRFor` | `while let Some(x) = iter.next()` |
| `loop_expression` | `IRFor` | `loop { ... }` → `_metadata["kind"] = "loop"` |
| `for_expression` | `IRFor` | `for x in collection` |
| `call_expression` | `IRCall` | |
| `method_call_expression` | `IRCall` | `obj.method(args)` |
| `closure_expression` | `IRFunctionDef` | `|x| x + 1`; `_metadata["kind"] = "closure"` |
| `macro_invocation` | `IRCall` | `println!("hi")`; `_metadata["kind"] = "macro"` |
| `match_expression` | `IRIf` | `match x { arm => ... }`; `_metadata["kind"] = "match"` |

---

## Rust-Specific Implementation Notes

### `impl` blocks — the core challenge

Rust methods do not live directly on the struct/enum definition. They are declared in separate `impl` blocks:

```rust
struct Point { x: f64, y: f64 }

impl Point {
    fn distance(&self) -> f64 {
        (self.x * self.x + self.y * self.y).sqrt()
    }
}
```

The normalizer must:
1. Emit `IRClassDef(name="Point")` when visiting `struct_item`.
2. When visiting `impl_item`, look up the type name from the `type` field and emit `IRFunctionDef` nodes for each `function_item` inside the `impl_item` body. Attach each function to the module's body directly (not nested inside the class), storing `_metadata["impl_of"] = "Point"`.

This approach means extraction tools will find methods alongside the class at the top level of `module.body`, which is consistent with how Go methods are handled.

**Why not nest methods inside the class?** Because `impl` blocks can appear anywhere in the file, even in different modules. Nesting them inside the class at parse time would require a two-pass approach. For the v1 implementation, emit methods at module level with `impl_of` metadata.

### Trait implementations

```rust
impl Display for Point {
    fn fmt(&self, f: &mut Formatter) -> fmt::Result {
        write!(f, "({}, {})", self.x, self.y)
    }
}
```

The `impl_item` has two relevant nodes: the trait name and the implementing type. Store both:

```python
fn._metadata["impl_of"] = "Point"
fn._metadata["trait_impl"] = "Display"
```

### Module system (`mod`)

Rust modules can be inline (with a `{...}` body) or file-based (`mod utils;` with no body):

- **Inline**: `mod geometry { struct Circle {...} fn area(...) {} }` — map to `IRClassDef` with `_metadata["kind"] = "module"` and recurse into the body.
- **File-based**: `mod utils;` — map to `IRImport(module="utils", _metadata={"kind": "mod_declaration"})`.

Inline module bodies are themselves `source_file`-like: they contain function items, struct items, impl items, etc. Recurse using the same visitor dispatch.

### Lifetimes and generics

Lifetime annotations (`'a`, `'static`) and generic parameters (`<T: Clone>`) appear in type signatures. For IR purposes, **strip them** — they are not needed for extraction or analysis. Store the raw signature string in `_metadata["signature"]` if preservation is needed.

```python
# Strip lifetime annotations from parameter types
import re
def _strip_lifetimes(type_str: str) -> str:
    return re.sub(r"'[a-z_]+\s*", "", type_str).strip()
```

### `use` statements

```rust
use std::collections::HashMap;
use std::io::{self, Write};
use crate::models::User;
```

Map all forms to `IRImport`:
- Single: `IRImport(module="std::collections::HashMap")`
- Nested: `use std::io::{self, Write}` → emit two `IRImport` nodes: `"std::io"` and `"std::io::Write"`
- Wildcard: `use std::prelude::*` → `IRImport(module="std::prelude", is_star=True)`

### Closures

```rust
let add = |x: i32, y: i32| -> i32 { x + y };
```

Map to `IRFunctionDef(name="<closure>", _metadata={"kind": "closure"})` and nest it as the right-hand side of the enclosing `let_declaration` / `IRAssign`.

### `match` expressions

Map `match_expression` to `IRIf` with `_metadata["kind"] = "match"`. Each `match_arm` is one branch. Do not try to extract arm patterns as conditions — store the raw arm text in `_metadata["arms"]` for introspection.

---

## Block Structure

Rust function bodies are `block` nodes containing statement nodes directly:

```
function_item
  ├── identifier           ("distance")
  ├── parameters
  │   └── self_parameter   (&self)
  ├── type_identifier      (f64)      ← return type
  └── block
        └── expression_statement
              └── method_call_expression
```

Visit `block.named_children` to iterate statements. Each statement may be an `expression_statement` (an expression followed by `;`) or a bare expression (the last expression in a block is implicitly returned in Rust).

---

## `_parse_rust()` Method

```python
def _parse_rust(self) -> None:
    """Parse Rust code using tree-sitter-rust. [FEATURE]"""
    from code_scalpel.ir.normalizers.rust_normalizer import RustNormalizer

    normalizer = RustNormalizer()
    self._ir_module = normalizer.normalize(self.code)
```

---

## limits.toml

Add `"rust"` to the `languages` arrays in all three tier sections of `analyze_code` and `unified_sink_detect`.

---

## Tests to Write

### `tests/languages/test_rust_parser.py`

Cover all of the following scenarios:

1. **Extension detection** — `.rs` maps to `Language.RUST`
2. **Content detection** — `"fn "` + `"let mut"` heuristics identify Rust
3. **Function extraction** — `fn greet(name: &str) -> String`
4. **Struct extraction** — `struct Point { x: f64, y: f64 }`
5. **Enum extraction** — `enum Color { Red, Green, Blue }`
6. **Trait extraction** — `trait Animal { fn speak(&self) -> String; }`
7. **Impl method extraction** — method found via `_metadata["impl_of"]`
8. **Trait impl method extraction** — method found with `_metadata["trait_impl"]`
9. **`use` import extraction** — `use std::collections::HashMap` → `IRImport`
10. **Module (inline) extraction** — `mod geometry { ... }` → `IRClassDef`
11. **`let` declaration** — `let x = 42;` → `IRAssign`
12. **For loop** — `for x in 0..10` → `IRFor`
13. **Closure expression** — `|x| x + 1` → nested `IRFunctionDef`
14. **Missing symbol** — returns graceful failure, not exception
15. **Both extractor modules agree** on `.rs` → `Language.RUST`

### `tests/languages/test_polyglot_support.py`

- Add `"rust"` to `TestAnalyzeCodeLanguageSupport` parametrize
- Add `"rust"` to `TestUnifiedSinkDetectLanguageSupport` parametrize
- Add matrix rows for Rust
- Add `.rs` to `TestLanguageDetection.test_file_extension_detection`
- Update `test_rust_roadmap_documented` → `test_rust_fully_supported`

---

## Verification Commands

```bash
pip install tree-sitter-rust

# 1. Normalizer smoke test
python -c "
from code_scalpel.ir.normalizers.rust_normalizer import RustNormalizer
from code_scalpel.ir.nodes import IRFunctionDef, IRClassDef
n = RustNormalizer()
code = '''
use std::fmt;
struct Point { x: f64, y: f64 }
impl Point {
    fn new(x: f64, y: f64) -> Self { Point { x, y } }
    fn distance(&self) -> f64 { (self.x * self.x + self.y * self.y).sqrt() }
}
'''
m = n.normalize(code)
funcs = [x.name for x in m.body if isinstance(x, IRFunctionDef)]
classes = [x.name for x in m.body if isinstance(x, IRClassDef)]
print('Functions:', funcs)
print('Classes:', classes)
"

# 2. PolyglotExtractor end-to-end
python -c "
from code_scalpel.code_parsers.extractor import PolyglotExtractor, Language
code = 'fn hello() -> &str { \"hi\" }\nfn world() { println!(\"world\"); }'
e = PolyglotExtractor(code, language=Language.RUST)
r = e.extract('function', 'hello')
print('OK' if r.success else r.error)
"

# 3. Run test suite
pytest tests/languages/test_rust_parser.py -v
pytest tests/languages/ -v --tb=short
```

---

## Common Pitfalls

| Problem | Cause | Fix |
|---------|-------|-----|
| Methods not found (returns error) | Methods live in `impl` blocks, not directly on struct | Visit all `impl_item` nodes and emit functions at module level with `_metadata["impl_of"]` |
| Rust detected as C++ | `"::"` appears in both | Add `"fn "` or `"let mut"` as required co-heuristic |
| Lifetime syntax causes parse failure | Normalizer tries to use `'a` as a string literal | Treat lifetime annotations as metadata; strip them from type strings |
| Generic bounds not handled | `<T: Clone + Debug>` causes unexpected node types | Skip unknown child node types gracefully; store raw bounds in `_metadata["generics"]` |
| `mod utils;` (file-based) causes confusion | `mod_item` without a body looks like a declaration | Check for `block` child; if absent, emit `IRImport` instead of `IRClassDef` |
| Macros crash the normalizer | `macro_invocation` node not handled | Add `visit_macro_invocation()` → `IRCall(name=macro_name, _metadata={"kind": "macro"})` |
| `match` arms cause node confusion | `match_arm` patterns are complex patterns, not expressions | Map entire `match_expression` → `IRIf`; store arm text in metadata rather than recursing |
