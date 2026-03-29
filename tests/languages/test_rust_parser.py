"""Tests for Rust language support — Phase 1 IR layer.

[20260305_TEST] Test suite covering Rust normalizer, polyglot extractor,
code_parsers extractor, and adapter integration.

Follows the pattern established by test_swift_parser.py.
"""

import pytest

pytest.importorskip(
    "tree_sitter_rust",
    reason="tree_sitter_rust not installed; skipping Rust parser tests",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RUST_SRC = """
use std::collections::HashMap;
use crate::utils::helper;

struct Point {
    x: f64,
    y: f64,
}

enum Color {
    Red,
    Green,
    Blue(u8),
}

trait Drawable {
    fn draw(&self);
    fn area(&self) -> f64;
}

struct Circle {
    radius: f64,
}

impl Drawable for Circle {
    fn draw(&self) {
        println!("Circle");
    }

    fn area(&self) -> f64 {
        3.14159 * self.radius * self.radius
    }
}

impl Point {
    fn new(x: f64, y: f64) -> Self {
        Point { x, y }
    }

    fn distance(&self, other: &Point) -> f64 {
        let dx = self.x - other.x;
        let dy = self.y - other.y;
        (dx * dx + dy * dy).sqrt()
    }
}

fn add(a: i32, b: i32) -> i32 {
    a + b
}

fn main() {
    let mut map: HashMap<String, i32> = HashMap::new();
    map.insert("key".to_string(), 42);

    for (k, v) in &map {
        println!("{}: {}", k, v);
    }

    let mut i = 0;
    while i < 10 {
        i += 1;
    }

    loop {
        break;
    }

    let result = match i {
        0 => "zero",
        _ => "nonzero",
    };

    let add_fn = |a: i32, b: i32| -> i32 { a + b };
    let _ = add_fn(1, 2);

    if i > 0 {
        return;
    }
}
"""


# ---------------------------------------------------------------------------
# 1. Extension mapping tests (both extractor modules)
# ---------------------------------------------------------------------------


class TestExtensionMap:
    """[20260305_TEST] .rs extension maps to Language.RUST in both extractors."""

    def test_rs_extension_in_polyglot_extractor(self):
        from code_scalpel.polyglot.extractor import EXTENSION_MAP, Language

        assert ".rs" in EXTENSION_MAP
        assert EXTENSION_MAP[".rs"] == Language.RUST

    def test_rs_extension_in_code_parsers_extractor(self):
        from code_scalpel.code_parsers.extractor import EXTENSION_MAP, Language

        assert ".rs" in EXTENSION_MAP
        assert EXTENSION_MAP[".rs"] == Language.RUST

    def test_rust_enum_value_polyglot(self):
        from code_scalpel.polyglot.extractor import Language

        assert Language.RUST.value == "rust"

    def test_rust_enum_value_code_parsers(self):
        from code_scalpel.code_parsers.extractor import Language

        assert Language.RUST.value == "rust"

    def test_rust_in_interface_language(self):
        from code_scalpel.code_parsers.interface import Language

        assert Language.RUST.value == "rust"


# ---------------------------------------------------------------------------
# 2. detect_language tests
# ---------------------------------------------------------------------------


class TestDetectLanguage:
    """[20260305_TEST] Content-based language detection for Rust."""

    def test_detect_use_std(self):
        from code_scalpel.polyglot.extractor import Language, detect_language

        assert detect_language(None, "use std::collections::HashMap;") == Language.RUST

    def test_detect_let_mut(self):
        from code_scalpel.polyglot.extractor import Language, detect_language

        assert detect_language(None, "let mut x = 5;") == Language.RUST

    def test_detect_fn_main(self):
        from code_scalpel.polyglot.extractor import Language, detect_language

        assert detect_language(None, "fn main() { }") == Language.RUST

    def test_detect_use_crate(self):
        from code_scalpel.polyglot.extractor import Language, detect_language

        assert detect_language(None, "use crate::utils::foo;") == Language.RUST

    def test_detect_rs_file_extension(self):
        from code_scalpel.polyglot.extractor import Language, detect_language

        assert detect_language("main.rs") == Language.RUST
        assert detect_language("src/lib.rs") == Language.RUST

    def test_detect_code_parsers(self):
        from code_scalpel.code_parsers.extractor import Language, detect_language

        assert detect_language(None, "use std::io; fn main() {}") == Language.RUST


# ---------------------------------------------------------------------------
# 3. Normalizer unit tests
# ---------------------------------------------------------------------------


class TestRustNormalizer:
    """[20260305_TEST] RustNormalizer produces correct IRModule."""

    @pytest.fixture(autouse=True)
    def normalizer(self):
        from code_scalpel.ir.normalizers.rust_normalizer import RustNormalizer

        self.norm = RustNormalizer()

    def test_language_property(self):
        assert self.norm.language == "rust"

    def test_empty_source(self):
        from code_scalpel.ir.nodes import IRModule

        m = self.norm.normalize("")
        assert isinstance(m, IRModule)
        assert m.body == []

    def test_source_language(self):
        m = self.norm.normalize(_RUST_SRC)
        assert m.source_language == "rust"

    def test_use_declaration(self):
        from code_scalpel.ir.nodes import IRImport

        m = self.norm.normalize("use std::collections::HashMap;")
        imports = [n for n in m.body if isinstance(n, IRImport)]
        assert len(imports) >= 1

    def test_struct_item(self):
        from code_scalpel.ir.nodes import IRClassDef

        m = self.norm.normalize("struct Foo { x: i32 }")
        classes = [n for n in m.body if isinstance(n, IRClassDef)]
        assert any(c.name == "Foo" for c in classes)
        structs = [c for c in classes if c._metadata.get("kind") == "struct"]
        assert len(structs) >= 1

    def test_enum_item(self):
        from code_scalpel.ir.nodes import IRClassDef

        m = self.norm.normalize("enum Color { Red, Green, Blue }")
        classes = [n for n in m.body if isinstance(n, IRClassDef)]
        enums = [c for c in classes if c._metadata.get("kind") == "enum"]
        assert any(e.name == "Color" for e in enums)

    def test_trait_item(self):
        from code_scalpel.ir.nodes import IRClassDef

        m = self.norm.normalize("trait Shape { fn area(&self) -> f64; }")
        classes = [n for n in m.body if isinstance(n, IRClassDef)]
        traits = [c for c in classes if c._metadata.get("kind") == "trait"]
        assert any(t.name == "Shape" for t in traits)

    def test_impl_item(self):
        from code_scalpel.ir.nodes import IRClassDef

        m = self.norm.normalize("impl Foo { fn bar(&self) {} }")
        classes = [n for n in m.body if isinstance(n, IRClassDef)]
        impls = [c for c in classes if c._metadata.get("kind") == "impl"]
        assert len(impls) >= 1

    def test_function_item(self):
        from code_scalpel.ir.nodes import IRFunctionDef

        m = self.norm.normalize("fn add(x: i32, y: i32) -> i32 { x + y }")
        fns = [n for n in m.body if isinstance(n, IRFunctionDef)]
        assert any(f.name == "add" for f in fns)

    def test_function_params(self):
        from code_scalpel.ir.nodes import IRFunctionDef

        m = self.norm.normalize("fn foo(a: i32, b: i32, c: &str) {}")
        fns = [n for n in m.body if isinstance(n, IRFunctionDef)]
        foo = next(f for f in fns if f.name == "foo")
        assert len(foo.params) == 3

    def test_function_return_type(self):
        from code_scalpel.ir.nodes import IRFunctionDef

        m = self.norm.normalize("fn answer() -> i32 { 42 }")
        fns = [n for n in m.body if isinstance(n, IRFunctionDef)]
        answer = next(f for f in fns if f.name == "answer")
        assert answer.return_type is not None

    def test_let_declaration(self):
        from code_scalpel.ir.nodes import IRAssign, IRFunctionDef

        m = self.norm.normalize("fn f() { let mut x: i32 = 5; }")
        fn = next(n for n in m.body if isinstance(n, IRFunctionDef))
        assigns = [n for n in fn.body if isinstance(n, IRAssign)]
        assert len(assigns) >= 1

    def test_if_expression(self):
        from code_scalpel.ir.nodes import IRFunctionDef, IRIf

        m = self.norm.normalize("fn f() { if x > 0 { return; } }")
        fn = next(n for n in m.body if isinstance(n, IRFunctionDef))
        ifs = [n for n in fn.body if isinstance(n, IRIf)]
        assert len(ifs) >= 1

    def test_for_expression(self):
        from code_scalpel.ir.nodes import IRFor, IRFunctionDef

        m = self.norm.normalize('fn f() { for i in items { println!("{}", i); } }')
        fn = next(n for n in m.body if isinstance(n, IRFunctionDef))
        fors = [n for n in fn.body if isinstance(n, IRFor)]
        assert len(fors) >= 1

    def test_while_expression(self):
        from code_scalpel.ir.nodes import IRFunctionDef, IRWhile

        m = self.norm.normalize("fn f() { while x > 0 { x -= 1; } }")
        fn = next(n for n in m.body if isinstance(n, IRFunctionDef))
        whiles = [n for n in fn.body if isinstance(n, IRWhile)]
        assert len(whiles) >= 1

    def test_loop_expression(self):
        from code_scalpel.ir.nodes import IRFunctionDef, IRWhile

        m = self.norm.normalize("fn f() { loop { break; } }")
        fn = next(n for n in m.body if isinstance(n, IRFunctionDef))
        loops = [n for n in fn.body if isinstance(n, IRWhile)]
        loop_nodes = [
            loop_node
            for loop_node in loops
            if loop_node._metadata.get("kind") == "loop"
        ]
        assert len(loop_nodes) >= 1

    def test_match_expression(self):
        from code_scalpel.ir.nodes import IRFunctionDef, IRIf

        m = self.norm.normalize("fn f() { match x { 0 => 0, _ => 1 }; }")
        fn = next(n for n in m.body if isinstance(n, IRFunctionDef))
        ifs = [n for n in fn.body if isinstance(n, IRIf)]
        match_nodes = [i for i in ifs if i._metadata.get("kind") == "match"]
        assert len(match_nodes) >= 1

    def test_return_expression(self):
        from code_scalpel.ir.nodes import IRFunctionDef, IRReturn

        m = self.norm.normalize("fn f() -> i32 { return 42; }")
        fn = next(n for n in m.body if isinstance(n, IRFunctionDef))
        returns = [n for n in fn.body if isinstance(n, IRReturn)]
        assert len(returns) >= 1

    def test_closure_expression(self):
        from code_scalpel.ir.nodes import IRAssign, IRFunctionDef

        m = self.norm.normalize("fn f() { let c = |a: i32| a + 1; }")
        fn = next(n for n in m.body if isinstance(n, IRFunctionDef))
        # closure appears as value of IRAssign
        assigns = [n for n in fn.body if isinstance(n, IRAssign)]
        assert len(assigns) >= 1

    def test_macro_invocation(self):
        from code_scalpel.ir.nodes import IRCall, IRFunctionDef

        m = self.norm.normalize('fn f() { println!("hi"); }')
        fn = next(n for n in m.body if isinstance(n, IRFunctionDef))
        calls = [n for n in fn.body if isinstance(n, IRCall)]
        assert len(calls) >= 1 or any(
            isinstance(getattr(n, "value", None), IRCall) for n in fn.body
        )

    def test_full_source(self):
        from code_scalpel.ir.nodes import IRClassDef, IRFunctionDef, IRImport

        m = self.norm.normalize(_RUST_SRC)
        assert any(isinstance(n, IRImport) for n in m.body)
        assert any(isinstance(n, IRClassDef) for n in m.body)
        assert any(isinstance(n, IRFunctionDef) for n in m.body)

    def test_multiline_whitespace(self):
        m = self.norm.normalize("\n\n   \n")
        assert m.body == []


# ---------------------------------------------------------------------------
# 4. Polyglot extractor parse → IR
# ---------------------------------------------------------------------------


class TestPolyglotExtractorRust:
    """[20260305_TEST] PolyglotExtractor._parse() builds correct IR for Rust."""

    def test_parse_creates_ir_module(self):
        from code_scalpel.polyglot.extractor import Language, PolyglotExtractor

        extractor = PolyglotExtractor(code=_RUST_SRC, language=Language.RUST)
        extractor._parse()
        assert extractor._ir_module is not None
        assert extractor._ir_module.source_language == "rust"

    def test_extract_function(self):
        from code_scalpel.polyglot.extractor import Language, PolyglotExtractor

        extractor = PolyglotExtractor(code=_RUST_SRC, language=Language.RUST)
        result = extractor.extract("function", "add")
        assert result.success
        assert "add" in result.code

    def test_extract_struct(self):
        from code_scalpel.polyglot.extractor import Language, PolyglotExtractor

        extractor = PolyglotExtractor(code=_RUST_SRC, language=Language.RUST)
        result = extractor.extract("class", "Point")
        assert result.success
        assert "Point" in result.code

    def test_detect_from_file_path(self):
        from code_scalpel.polyglot.extractor import Language, PolyglotExtractor

        extractor = PolyglotExtractor(code=_RUST_SRC, file_path="src/main.rs")
        assert extractor.language == Language.RUST


# ---------------------------------------------------------------------------
# 5. code_parsers extractor
# ---------------------------------------------------------------------------


class TestCodeParsersExtractorRust:
    """[20260305_TEST] code_parsers PolyglotExtractor works for Rust."""

    def test_parse_creates_ir_module(self):
        from code_scalpel.code_parsers.extractor import Language, PolyglotExtractor

        extractor = PolyglotExtractor(code=_RUST_SRC, language=Language.RUST)
        extractor._parse()
        assert extractor._ir_module is not None

    def test_extract_function(self):
        from code_scalpel.code_parsers.extractor import Language, PolyglotExtractor

        extractor = PolyglotExtractor(code=_RUST_SRC, language=Language.RUST)
        result = extractor.extract("function", "add")
        assert result.success

    def test_detect_from_file_path(self):
        from code_scalpel.code_parsers.extractor import Language, PolyglotExtractor

        extractor = PolyglotExtractor(code=_RUST_SRC, file_path="main.rs")
        assert extractor.language == Language.RUST


# ---------------------------------------------------------------------------
# 6. Adapter tests
# ---------------------------------------------------------------------------


class TestRustAdapter:
    """[20260305_TEST] RustParserAdapter implements IParser correctly."""

    @pytest.fixture(autouse=True)
    def adapter(self):
        from code_scalpel.code_parsers.adapters.rust_adapter import RustParserAdapter

        self.adapter = RustParserAdapter()

    def test_parse_returns_parse_result(self):
        from code_scalpel.code_parsers.interface import ParseResult

        result = self.adapter.parse(_RUST_SRC)
        assert isinstance(result, ParseResult)

    def test_parse_language(self):
        from code_scalpel.code_parsers.interface import Language

        result = self.adapter.parse(_RUST_SRC)
        assert result.language == Language.RUST

    def test_get_functions(self):
        result = self.adapter.parse(_RUST_SRC)
        fns = self.adapter.get_functions(result.ast)
        assert isinstance(fns, list)
        assert "add" in fns
        assert "main" in fns

    def test_get_classes(self):
        result = self.adapter.parse(_RUST_SRC)
        classes = self.adapter.get_classes(result.ast)
        assert isinstance(classes, list)
        assert "Point" in classes

    def test_no_errors(self):
        result = self.adapter.parse(_RUST_SRC)
        assert result.errors == []


# ---------------------------------------------------------------------------
# 7. Normalizer __init__ exports
# ---------------------------------------------------------------------------


class TestNormalizerInit:
    """[20260305_TEST] RustNormalizer is exported from normalizers __init__."""

    def test_rust_normalizer_exported(self):
        from code_scalpel.ir import normalizers

        assert hasattr(normalizers, "RustNormalizer")

    def test_rust_visitor_exported(self):
        from code_scalpel.ir import normalizers

        assert hasattr(normalizers, "RustVisitor")
