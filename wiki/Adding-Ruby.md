# Adding Ruby Language Support

**Difficulty**: Medium-High — Ruby's grammar is clean but the language has several constructs that have no direct parallel in the existing IR: mixins (`include`/`extend`), singleton methods (`def self.foo`), open classes (the same class can be reopened and extended), blocks/procs/lambdas (three distinct callable objects), and method aliases. The `module` construct is used both as a namespace and as a mixin container, requiring careful disambiguation.

**Estimated integration points**: 12 files (see [Adding-A-Language.md](Adding-A-Language.md) for the master checklist).

---

## Package

```bash
pip install tree-sitter-ruby
python -c "import tree_sitter_ruby; print('OK')"
```

Add to `pyproject.toml`:

```toml
"tree-sitter-ruby>=0.21.0",  # [FEATURE] Ruby language support
```

Add to all three locations: `dependencies`, `[all]`, and `[polyglot]` extras.

---

## Language Enum + Extension Map

```python
# Language enum (both extractor files)
RUBY = "ruby"

# Extension map
".rb":   Language.RUBY,
".rake": Language.RUBY,   # Rake build files
".gemspec": Language.RUBY,
```

---

## Content-Based Detection Heuristics

Place the Ruby block **after** Java and **before** JavaScript (Ruby's `end` keyword and `def` are distinctive):

```python
# Ruby indicators — "def " + "end" combination is unambiguous
if "def " in code and "end" in code:
    return Language.RUBY
if any(kw in code for kw in ["require ", "attr_accessor", "attr_reader", "module ", "include "]):
    return Language.RUBY
```

**Note**: `def` alone appears in JavaScript's class syntax (`def` is not a keyword there, but watch for false positives). The `def ... end` pair is the reliable signal. `require ` with a space distinguishes from `requires` as a word.

---

## Key AST Node Mappings

| tree-sitter-ruby node | IR node | Notes |
|----------------------|---------|-------|
| `program` | `IRModule` | Root |
| `call` with `require` / `require_relative` | `IRImport` | `require "json"` → `IRImport(module="json")` |
| `call` with `include` / `extend` | `IRImport` | `include Enumerable` → `IRImport(module="Enumerable", _metadata={"kind": "mixin"})` |
| `method` | `IRFunctionDef` | `def greet(name)` |
| `singleton_method` | `IRFunctionDef` | `def self.create()` → `_metadata["singleton"] = True` |
| `class` | `IRClassDef` | `class Foo < Bar` |
| `module` | `IRClassDef` | `module Enumerable` → `_metadata["kind"] = "module"` |
| `assignment` | `IRAssign` | `x = 42` |
| `operator_assignment` | `IRAssign` | `x += 1` |
| `return` | `IRReturn` | |
| `if` / `unless` | `IRIf` | `unless` → negate condition; `_metadata["kind"] = "unless"` |
| `while` / `until` | `IRFor` | `until` → negate; `_metadata["kind"] = "until"` |
| `for` | `IRFor` | `for x in collection` |
| `call` | `IRCall` | Method calls |
| `block` | `IRFunctionDef` | `do |x| ... end`; `_metadata["kind"] = "block"` |
| `lambda` | `IRFunctionDef` | `-> (x) { x + 1 }`; `_metadata["kind"] = "lambda"` |
| `proc` (via `Proc.new`) | `IRFunctionDef` | Captured at `IRCall` level; `_metadata["kind"] = "proc"` |
| `method_add_block` | (visit both sides) | Call with a trailing block argument |

---

## Ruby-Specific Implementation Notes

### `module` as both namespace and mixin

Ruby `module` serves two roles:

1. **Namespace**: `module MyApp; class Foo; end; end` — the module wraps classes.
2. **Mixin**: `include Enumerable` inside a class — pulls in module methods.

For the normalizer, treat all `module` nodes as `IRClassDef` with `_metadata["kind"] = "module"`. The mixin relationship is recorded via `IRImport` nodes with `_metadata["kind"] = "mixin"` inside the receiving class's body.

### Singleton methods (`def self.foo`)

```ruby
class MyClass
  def self.create(attrs)
    new(attrs)
  end
end
```

The tree-sitter node is `singleton_method` with fields `object` (`self`) and `name`. Map to `IRFunctionDef` with `_metadata["singleton"] = True`. This is effectively a class method (equivalent to Java's `static`).

### Open classes

Ruby allows reopening any class:

```ruby
class String
  def shout
    upcase + "!"
  end
end
```

This is a second `class` node with the same name. The normalizer should not deduplicate — emit a new `IRClassDef` for each class body. The extraction tools can query by name and will find the first match. Store `_metadata["reopened"] = True` on subsequent definitions if you can detect them.

### Blocks

Ruby blocks (`do...end` or `{...}`) are closures passed as the last argument to a method call:

```ruby
[1, 2, 3].each do |x|
  puts x
end
```

The `block` node is a child of `method_add_block`. Map it to `IRFunctionDef(name="<block>", _metadata={"kind": "block"})` and attach it as the last element of the call's `args`. For most extraction purposes, you can skip deep block traversal and just record the block's presence.

### `attr_accessor` / `attr_reader` / `attr_writer`

These are method-call macros that define getter/setter methods:

```ruby
class User
  attr_accessor :name, :email
end
```

The tree-sitter node is a `call` with the method name `attr_accessor` and symbol arguments. For IR purposes, emit `IRAssign` nodes for each attribute name with `_metadata["kind"] = "attr_accessor"`.

### `require` vs `include`

- `require "json"` → file-level import; map to `IRImport(module="json")`
- `include Enumerable` → mixin inside a class; map to `IRImport(module="Enumerable", _metadata={"kind": "mixin"})`

Distinguish by checking whether you are inside a `class` or `module` body.

---

## Block Structure

Ruby uses `body_statement` inside methods and `then` inside conditionals:

```
method
  ├── identifier          ("greet")
  ├── method_parameters
  │   └── identifier      ("name")
  └── body_statement
        ├── call            (puts name)
        └── return
```

The `body_statement` node directly contains statement nodes. Iterate `body_statement.named_children` to visit statements.

For class bodies:

```
class
  ├── constant            ("Greeter")
  ├── superclass          (< Base)
  └── body_statement
        ├── method        (def greet)
        └── singleton_method (def self.create)
```

---

## `_parse_ruby()` Method

```python
def _parse_ruby(self) -> None:
    """Parse Ruby code using tree-sitter-ruby. [FEATURE]"""
    from code_scalpel.ir.normalizers.ruby_normalizer import RubyNormalizer

    normalizer = RubyNormalizer()
    self._ir_module = normalizer.normalize(self.code)
```

---

## limits.toml

Add `"ruby"` to the `languages` arrays in all three tier sections of `analyze_code` and `unified_sink_detect`.

---

## Tests to Write

### `tests/languages/test_ruby_parser.py`

Cover all of the following scenarios:

1. **Extension detection** — `.rb`, `.rake`, `.gemspec` map to `Language.RUBY`
2. **Content detection** — `def ... end` heuristic identifies Ruby
3. **Function extraction** — `def greet(name)`
4. **Singleton method extraction** — `def self.create` with `_metadata["singleton"] = True`
5. **Class extraction** — `class User < ActiveRecord::Base`
6. **Module extraction** — `module Enumerable` with `_metadata["kind"] = "module"`
7. **`require` import extraction** — `require "json"` → `IRImport(module="json")`
8. **Mixin import** — `include Enumerable` → `IRImport` with `_metadata["kind"] = "mixin"`
9. **`attr_accessor` attributes** — produce `IRAssign` nodes with metadata
10. **Instance variable assignment** — `@name = name` maps to `IRAssign`
11. **Block attached to method call** — captured as `IRFunctionDef` with `_metadata["kind"] = "block"`
12. **Lambda expression** — `-> (x) { x + 1 }` with `_metadata["kind"] = "lambda"`
13. **Missing symbol** — returns graceful failure, not exception
14. **Both extractor modules agree** on `.rb` → `Language.RUBY`

### `tests/languages/test_polyglot_support.py`

- Add `"ruby"` to `TestAnalyzeCodeLanguageSupport` parametrize
- Add `"ruby"` to `TestUnifiedSinkDetectLanguageSupport` parametrize
- Add matrix rows for Ruby
- Add `.rb` to `TestLanguageDetection.test_file_extension_detection`

---

## Verification Commands

```bash
pip install tree-sitter-ruby

# 1. Normalizer smoke test
python -c "
from code_scalpel.ir.normalizers.ruby_normalizer import RubyNormalizer
from code_scalpel.ir.nodes import IRFunctionDef, IRClassDef
n = RubyNormalizer()
code = '''
require 'json'
class User
  attr_accessor :name
  def initialize(name)
    @name = name
  end
  def self.create(name)
    new(name)
  end
end
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
code = 'def hello\n  puts \"hi\"\nend\ndef world\n  puts \"world\"\nend'
e = PolyglotExtractor(code, language=Language.RUBY)
r = e.extract('function', 'hello')
print('OK' if r.success else r.error)
"

# 3. Run test suite
pytest tests/languages/test_ruby_parser.py -v
pytest tests/languages/ -v --tb=short
```

---

## Common Pitfalls

| Problem | Cause | Fix |
|---------|-------|-----|
| Ruby detected as Python | `"def "` and `"import "` also appear in Python | Add `"end"` as a required co-heuristic; check `"def " in code and "end" in code` |
| Singleton methods missing | `singleton_method` node not handled | Add `visit_singleton_method()` in addition to `visit_method()` |
| Module methods not extracted | Module body not recursed | Treat `module` like a class — recurse `body_statement` for methods |
| `require` not mapped | `call` node with identifier `require` not detected | Check `call.function_name == "require"` and emit `IRImport` |
| Blocks cause infinite recursion | Block body recursed without depth guard | Track recursion depth; skip deep block traversal for extraction use case |
| `attr_accessor` names missing | Macro call not parsed | Visit `call` nodes and check for `attr_accessor`/`attr_reader`/`attr_writer` identifiers |
| Open class definitions create duplicate entries | Same class name appears twice | Expected behavior — emit separate `IRClassDef`; mark `_metadata["reopened"] = True` on subsequent ones |
