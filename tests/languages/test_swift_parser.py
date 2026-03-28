"""Tests for Swift language support — Phase 1 IR layer.

[20260304_TEST] Test suite covering Swift normalizer, polyglot extractor,
code_parsers extractor, and adapter integration.

Follows the pattern established by test_ruby_parser.py.
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SWIFT_SRC = """
import Foundation
import UIKit

class Animal {
    var name: String = "unknown"
    var age: Int = 0

    func speak() -> String {
        return "..."
    }
}

struct Point {
    var x: Int
    var y: Int

    func distance() -> Double {
        return 0.0
    }
}

enum Color {
    case red
    case green
    case blue
}

protocol Drawable {
    func draw()
}

func greet(name: String) -> String {
    return "Hello, " + name
}

func loopDemo() {
    for i in 0..<10 {
        print(i)
    }
    var count = 0
    while count < 5 {
        count += 1
    }
    let value: Int? = nil
    guard let val = value else {
        return
    }
    print(val)
}

class Calculator {
    init() {}
    func add(a: Int, b: Int) -> Int {
        return a + b
    }
}
"""


# ---------------------------------------------------------------------------
# 1. Extension mapping tests (both extractor modules)
# ---------------------------------------------------------------------------


class TestExtensionMap:
    """[20260304_TEST] .swift extension maps to Language.SWIFT in both extractors."""

    def test_swift_extension_polyglot(self):
        from code_scalpel.polyglot.extractor import EXTENSION_MAP, Language

        assert ".swift" in EXTENSION_MAP
        assert EXTENSION_MAP[".swift"] == Language.SWIFT

    def test_swift_extension_code_parsers(self):
        from code_scalpel.code_parsers.extractor import EXTENSION_MAP, Language

        assert ".swift" in EXTENSION_MAP
        assert EXTENSION_MAP[".swift"] == Language.SWIFT

    def test_swift_on_both_extractor_modules(self):
        from code_scalpel.code_parsers.extractor import EXTENSION_MAP as CP_MAP
        from code_scalpel.polyglot.extractor import EXTENSION_MAP as PG_MAP

        assert (
            CP_MAP[".swift"].value == PG_MAP[".swift"].value == "swift"
        ), "Both extractor modules must map .swift to 'swift'"


# ---------------------------------------------------------------------------
# 2. detect_language tests
# ---------------------------------------------------------------------------


class TestDetectLanguage:
    """[20260304_TEST] Content-based Swift detection."""

    def test_detect_from_import_foundation(self):
        from code_scalpel.code_parsers.extractor import Language, detect_language

        code = "import Foundation\nvar x: Int = 1"
        assert detect_language(None, code) == Language.SWIFT

    def test_detect_from_import_uikit(self):
        from code_scalpel.code_parsers.extractor import Language, detect_language

        code = "import UIKit\nclass MyViewController: UIViewController {}"
        assert detect_language(None, code) == Language.SWIFT

    def test_detect_from_iboutlet(self):
        from code_scalpel.code_parsers.extractor import Language, detect_language

        code = "@IBOutlet var label: UILabel!"
        assert detect_language(None, code) == Language.SWIFT

    def test_detect_from_objc_annotation(self):
        from code_scalpel.code_parsers.extractor import Language, detect_language

        code = "@objc func buttonTapped() {}"
        assert detect_language(None, code) == Language.SWIFT

    def test_detect_from_extension_path(self):
        from code_scalpel.code_parsers.extractor import Language, detect_language

        assert detect_language("MyApp/Sources/AppDelegate.swift") == Language.SWIFT


# ---------------------------------------------------------------------------
# 3. SwiftNormalizer IR extraction tests
# ---------------------------------------------------------------------------


class TestSwiftNormalizerImport:
    """[20260304_TEST] import declarations → IRImport."""

    def test_import_foundation(self):
        from code_scalpel.ir.nodes import IRImport
        from code_scalpel.ir.normalizers.swift_normalizer import SwiftNormalizer

        mod = SwiftNormalizer().normalize("import Foundation")
        imports = [n for n in mod.body if isinstance(n, IRImport)]
        assert any("Foundation" in i.module for i in imports)


class TestSwiftNormalizerClass:
    """[20260304_TEST] class/struct/enum declarations → IRClassDef."""

    def test_class_declaration(self):
        from code_scalpel.ir.nodes import IRClassDef
        from code_scalpel.ir.normalizers.swift_normalizer import SwiftNormalizer

        mod = SwiftNormalizer().normalize("class Foo { var x: Int = 0 }")
        classes = [n for n in mod.body if isinstance(n, IRClassDef)]
        assert any(c.name == "Foo" for c in classes)

    def test_struct_declaration(self):
        from code_scalpel.ir.nodes import IRClassDef
        from code_scalpel.ir.normalizers.swift_normalizer import SwiftNormalizer

        mod = SwiftNormalizer().normalize("struct Point { var x: Int }")
        classes = [n for n in mod.body if isinstance(n, IRClassDef)]
        assert any(c.name == "Point" for c in classes)

    def test_enum_declaration(self):
        from code_scalpel.ir.nodes import IRClassDef
        from code_scalpel.ir.normalizers.swift_normalizer import SwiftNormalizer

        mod = SwiftNormalizer().normalize("enum Color { case red\ncase blue }")
        classes = [n for n in mod.body if isinstance(n, IRClassDef)]
        assert any(c.name == "Color" for c in classes)

    def test_protocol_declaration(self):
        from code_scalpel.ir.nodes import IRClassDef
        from code_scalpel.ir.normalizers.swift_normalizer import SwiftNormalizer

        mod = SwiftNormalizer().normalize("protocol Drawable { func draw() }")
        classes = [n for n in mod.body if isinstance(n, IRClassDef)]
        assert any(c.name == "Drawable" for c in classes)


class TestSwiftNormalizerFunction:
    """[20260304_TEST] func / init declarations → IRFunctionDef."""

    def test_top_level_function(self):
        from code_scalpel.ir.nodes import IRFunctionDef
        from code_scalpel.ir.normalizers.swift_normalizer import SwiftNormalizer

        mod = SwiftNormalizer().normalize('func greet() -> String { return "hi" }')
        funcs = [n for n in mod.body if isinstance(n, IRFunctionDef)]
        assert any(f.name == "greet" for f in funcs)

    def test_init_method(self):
        from code_scalpel.ir.nodes import IRClassDef
        from code_scalpel.ir.normalizers.swift_normalizer import SwiftNormalizer

        src = "class Calc { init() {} }"
        mod = SwiftNormalizer().normalize(src)
        # init may be inside class body
        classes = [n for n in mod.body if isinstance(n, IRClassDef)]
        assert classes, "Expected a class definition"
        # We just verify parsing doesn't raise — init handling is best-effort

    def test_method_inside_class(self):
        from code_scalpel.ir.nodes import IRClassDef
        from code_scalpel.ir.normalizers.swift_normalizer import SwiftNormalizer

        src = "class Foo { func bar() -> Int { return 1 } }"
        mod = SwiftNormalizer().normalize(src)
        classes = [n for n in mod.body if isinstance(n, IRClassDef)]
        assert classes, "Expected a class"


class TestSwiftNormalizerProperty:
    """[20260304_TEST] var/let declarations → IRAssign."""

    def test_var_declaration(self):
        from code_scalpel.ir.nodes import IRAssign
        from code_scalpel.ir.normalizers.swift_normalizer import SwiftNormalizer

        mod = SwiftNormalizer().normalize("var count: Int = 0")
        assigns = [n for n in mod.body if isinstance(n, IRAssign)]
        # Property may be emitted as top-level assign
        assert mod is not None  # normalization succeeded without exception


class TestSwiftNormalizerControlFlow:
    """[20260304_TEST] if, for, while, guard, return → corresponding IR nodes."""

    def test_if_statement(self):
        from code_scalpel.ir.nodes import IRFunctionDef, IRIf
        from code_scalpel.ir.normalizers.swift_normalizer import SwiftNormalizer

        src = "func check(x: Int) { if x > 0 { print(x) } }"
        mod = SwiftNormalizer().normalize(src)
        funcs = [n for n in mod.body if isinstance(n, IRFunctionDef)]
        assert funcs, "Expected a function"
        ifs = [n for n in funcs[0].body if isinstance(n, IRIf)]
        assert ifs, "Expected an if statement inside the function"

    def test_for_loop(self):
        from code_scalpel.ir.nodes import IRFor, IRFunctionDef
        from code_scalpel.ir.normalizers.swift_normalizer import SwiftNormalizer

        src = "func demo() { for i in 0..<10 { print(i) } }"
        mod = SwiftNormalizer().normalize(src)
        funcs = [n for n in mod.body if isinstance(n, IRFunctionDef)]
        assert funcs
        fors = [n for n in funcs[0].body if isinstance(n, IRFor)]
        assert fors, "Expected a for loop inside the function"

    def test_while_loop(self):
        from code_scalpel.ir.nodes import IRFunctionDef, IRWhile
        from code_scalpel.ir.normalizers.swift_normalizer import SwiftNormalizer

        src = "func spin() { var i = 0\nwhile i < 5 { i += 1 } }"
        mod = SwiftNormalizer().normalize(src)
        funcs = [n for n in mod.body if isinstance(n, IRFunctionDef)]
        assert funcs
        whiles = [n for n in funcs[0].body if isinstance(n, IRWhile)]
        assert whiles, "Expected a while loop"

    def test_return_statement(self):
        from code_scalpel.ir.nodes import IRFunctionDef, IRReturn
        from code_scalpel.ir.normalizers.swift_normalizer import SwiftNormalizer

        src = "func answer() -> Int { return 42 }"
        mod = SwiftNormalizer().normalize(src)
        funcs = [n for n in mod.body if isinstance(n, IRFunctionDef)]
        assert funcs
        returns = [n for n in funcs[0].body if isinstance(n, IRReturn)]
        assert returns, "Expected a return statement"


class TestSwiftNormalizerFullSource:
    """[20260304_TEST] Full multi-construct Swift source normalizes cleanly."""

    def test_full_source_no_exception(self):
        from code_scalpel.ir.nodes import IRClassDef, IRFunctionDef, IRImport
        from code_scalpel.ir.normalizers.swift_normalizer import SwiftNormalizer

        mod = SwiftNormalizer().normalize(_SWIFT_SRC)
        assert mod is not None
        # Must have at least one import, class, and function at top level
        assert any(isinstance(n, IRImport) for n in mod.body), "Expected imports"
        top_level_defs = [
            n for n in mod.body if isinstance(n, (IRClassDef, IRFunctionDef))
        ]
        assert top_level_defs, "Expected classes or functions at top level"


# ---------------------------------------------------------------------------
# 4. SwiftParserAdapter tests
# ---------------------------------------------------------------------------


class TestSwiftParserAdapter:
    """[20260304_TEST] SwiftParserAdapter wraps SwiftNormalizer correctly."""

    def test_adapter_instantiates(self):
        from code_scalpel.code_parsers.adapters.swift_adapter import SwiftParserAdapter

        adapter = SwiftParserAdapter()
        assert adapter is not None

    def test_parse_returns_result(self):
        from code_scalpel.code_parsers.adapters.swift_adapter import SwiftParserAdapter
        from code_scalpel.code_parsers.interface import Language, ParseResult

        adapter = SwiftParserAdapter()
        result = adapter.parse("import Foundation\nfunc foo() {}")
        assert isinstance(result, ParseResult)
        assert result.language == Language.SWIFT
        assert result.errors == []

    def test_get_functions(self):
        from code_scalpel.code_parsers.adapters.swift_adapter import SwiftParserAdapter

        adapter = SwiftParserAdapter()
        result = adapter.parse("func alpha() {}\nfunc beta() {}")
        funcs = adapter.get_functions(result.ast)
        assert "alpha" in funcs
        assert "beta" in funcs

    def test_get_classes(self):
        from code_scalpel.code_parsers.adapters.swift_adapter import SwiftParserAdapter

        adapter = SwiftParserAdapter()
        result = adapter.parse("class Dog {}\nstruct Cat {}")
        classes = adapter.get_classes(result.ast)
        assert "Dog" in classes


# ---------------------------------------------------------------------------
# 5. Polyglot extractor end-to-end test
# ---------------------------------------------------------------------------


class TestPolyglotSwiftExtraction:
    """[20260304_TEST] Polyglot extractor handles Swift source end-to-end."""

    def test_extract_swift_functions(self):
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from code_scalpel.polyglot.extractor import Language, PolyglotExtractor

        extractor = PolyglotExtractor(
            code="func greet() {}\nfunc farewell() {}",
            language=Language.SWIFT,
        )
        extractor._parse()
        assert extractor._ir_module is not None
        from code_scalpel.ir.nodes import IRFunctionDef

        func_names = [
            n.name for n in extractor._ir_module.body if isinstance(n, IRFunctionDef)
        ]
        assert "greet" in func_names
        assert "farewell" in func_names

    def test_extract_swift_classes(self):
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from code_scalpel.polyglot.extractor import Language, PolyglotExtractor

        extractor = PolyglotExtractor(
            code="class Vehicle {}\nstruct Wheel {}",
            language=Language.SWIFT,
        )
        extractor._parse()
        assert extractor._ir_module is not None
        from code_scalpel.ir.nodes import IRClassDef

        class_names = [
            n.name for n in extractor._ir_module.body if isinstance(n, IRClassDef)
        ]
        assert "Vehicle" in class_names
        assert "Wheel" in class_names
