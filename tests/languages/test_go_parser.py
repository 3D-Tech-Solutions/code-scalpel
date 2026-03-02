"""Dedicated Go parser tests.

Validates GoNormalizer + GoVisitor + PolyglotExtractor integration for Go code.
All tests require tree-sitter-go to be installed; they are skipped gracefully otherwise.

[20260302_TEST] Created for Go language support (v2.0.3).
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Shared fixtures / skip guard
# ---------------------------------------------------------------------------

try:
    from code_scalpel.ir.normalizers.go_normalizer import GoNormalizer

    _GO_AVAILABLE = True
except ImportError:
    _GO_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _GO_AVAILABLE, reason="tree-sitter-go not installed"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SIMPLE_PACKAGE = """\
package main

import "fmt"

func Hello() string {
\treturn "hello"
}

func World() {
\tfmt.Println("world")
}
"""

_STRUCT_CODE = """\
package shapes

type Point struct {
\tX float64
\tY float64
}

func (p Point) Distance() float64 {
\treturn p.X + p.Y
}

type Sizer interface {
\tSize() int
}
"""

_IMPORTS_CODE = """\
package main

import (
\t"fmt"
\t"os"
\talias "strings"
)

func run() {
\tfmt.Println(os.Args)
\talias.ToUpper("hi")
}
"""

_VAR_CODE = """\
package main

func demo() {
\tx := 42
\ty := "hello"
\tvar z int = 10
\tx = z + 1
\t_ = y
}
"""

_FOR_CODE = """\
package main

func loops() {
\tfor i := 0; i < 10; i++ {
\t}
\tfor _, v := range []int{1, 2} {
\t\t_ = v
\t}
\tfor true {
\t}
}
"""


# ---------------------------------------------------------------------------
# Language / extension detection
# ---------------------------------------------------------------------------


class TestGoLanguageDetection:
    """Go should be detected by file extension and content heuristics."""

    def test_go_extension_detected(self):
        """`.go` maps to Language.GO."""
        from code_scalpel.code_parsers.extractor import EXTENSION_MAP, Language

        assert EXTENSION_MAP[".go"] is Language.GO

    def test_go_language_enum_value(self):
        """Language.GO should have value 'go'."""
        from code_scalpel.code_parsers.extractor import Language

        assert Language.GO.value == "go"

    def test_content_detection_package_main(self):
        """'package main' heuristic should return Language.GO."""
        from code_scalpel.code_parsers.extractor import Language, detect_language

        result = detect_language(None, "package main\nfunc Hello() {}\n")
        assert result is Language.GO

    def test_content_detection_func_keyword(self):
        """'func ' heuristic should return Language.GO."""
        from code_scalpel.code_parsers.extractor import Language, detect_language

        result = detect_language(None, "func Add(a, b int) int { return a + b }")
        assert result is Language.GO

    def test_go_extension_on_both_extractor_modules(self):
        """Both code_parsers and polyglot extractor must agree."""
        from code_scalpel.code_parsers.extractor import EXTENSION_MAP as CP_MAP
        from code_scalpel.code_parsers.extractor import Language as CP_Lang
        from code_scalpel.polyglot.extractor import EXTENSION_MAP as PG_MAP
        from code_scalpel.polyglot.extractor import Language as PG_Lang

        assert CP_MAP[".go"] is CP_Lang.GO
        assert PG_MAP[".go"] is PG_Lang.GO


# ---------------------------------------------------------------------------
# GoNormalizer — IR structure
# ---------------------------------------------------------------------------


class TestGoNormalizerFunctions:
    """GoNormalizer should map Go functions to IRFunctionDef nodes."""

    def test_simple_functions_extracted(self):
        """Top-level functions appear in module.body."""
        from code_scalpel.ir.nodes import IRFunctionDef

        normalizer = GoNormalizer()
        module = normalizer.normalize(_SIMPLE_PACKAGE)
        names = [n.name for n in module.body if isinstance(n, IRFunctionDef)]
        assert "Hello" in names
        assert "World" in names

    def test_function_has_location(self):
        """IRFunctionDef nodes should carry line location info."""
        from code_scalpel.ir.nodes import IRFunctionDef

        normalizer = GoNormalizer()
        module = normalizer.normalize(_SIMPLE_PACKAGE)
        func = next(
            n for n in module.body if isinstance(n, IRFunctionDef) and n.name == "Hello"
        )
        assert func.loc is not None
        assert func.loc.line > 0


class TestGoNormalizerMethods:
    """Methods (with receivers) should be mapped to IRFunctionDef."""

    def test_method_with_receiver_extracted(self):
        """Method declarations are IRFunctionDef nodes in module.body."""
        from code_scalpel.ir.nodes import IRFunctionDef

        normalizer = GoNormalizer()
        module = normalizer.normalize(_STRUCT_CODE)
        names = [n.name for n in module.body if isinstance(n, IRFunctionDef)]
        assert "Distance" in names

    def test_method_receiver_in_metadata(self):
        """Receiver info should be stored in IRFunctionDef.metadata."""
        from code_scalpel.ir.nodes import IRFunctionDef

        normalizer = GoNormalizer()
        module = normalizer.normalize(_STRUCT_CODE)
        dist = next(
            n
            for n in module.body
            if isinstance(n, IRFunctionDef) and n.name == "Distance"
        )
        # _metadata["receiver"] should be present and non-empty
        receiver = dist._metadata.get("receiver", "")
        assert "Point" in receiver


class TestGoNormalizerStructsInterfaces:
    """Struct and interface type declarations map to IRClassDef."""

    def test_struct_extracted(self):
        from code_scalpel.ir.nodes import IRClassDef

        normalizer = GoNormalizer()
        module = normalizer.normalize(_STRUCT_CODE)
        names = [n.name for n in module.body if isinstance(n, IRClassDef)]
        assert "Point" in names

    def test_interface_extracted(self):
        from code_scalpel.ir.nodes import IRClassDef

        normalizer = GoNormalizer()
        module = normalizer.normalize(_STRUCT_CODE)
        names = [n.name for n in module.body if isinstance(n, IRClassDef)]
        assert "Sizer" in names


class TestGoNormalizerImports:
    """Grouped and single imports map to IRImport nodes."""

    def test_grouped_imports_normalized(self):
        from code_scalpel.ir.nodes import IRImport

        normalizer = GoNormalizer()
        module = normalizer.normalize(_IMPORTS_CODE)
        imported = [n.module for n in module.body if isinstance(n, IRImport)]
        assert "fmt" in imported
        assert "os" in imported

    def test_import_alias_captured(self):
        from code_scalpel.ir.nodes import IRImport

        normalizer = GoNormalizer()
        module = normalizer.normalize(_IMPORTS_CODE)
        aliases = {
            n.module: n.alias
            for n in module.body
            if isinstance(n, IRImport) and n.alias
        }
        assert aliases.get("strings") == "alias"


class TestGoNormalizerVariables:
    """Short var declarations and assignments produce IRAssign nodes."""

    def test_short_var_decl_produces_ir_assign(self):
        from code_scalpel.ir.nodes import IRAssign, IRFunctionDef

        normalizer = GoNormalizer()
        module = normalizer.normalize(_VAR_CODE)
        func = next(
            n for n in module.body if isinstance(n, IRFunctionDef) and n.name == "demo"
        )
        assigns = [n for n in func.body if isinstance(n, IRAssign)]
        assert len(assigns) >= 1


class TestGoNormalizerLoops:
    """All Go for-loop forms should map to IRFor."""

    def test_for_loops_produce_ir_for(self):
        from code_scalpel.ir.nodes import IRFor, IRFunctionDef

        normalizer = GoNormalizer()
        module = normalizer.normalize(_FOR_CODE)
        func = next(
            n for n in module.body if isinstance(n, IRFunctionDef) and n.name == "loops"
        )
        for_nodes = [n for n in func.body if isinstance(n, IRFor)]
        # Expect at least 2 for-loops (classic + range)
        assert len(for_nodes) >= 2


# ---------------------------------------------------------------------------
# PolyglotExtractor — end-to-end extraction
# ---------------------------------------------------------------------------


class TestPolyglotExtractorGo:
    """PolyglotExtractor with Language.GO should extract functions and structs."""

    def test_extract_function_by_name(self):
        from code_scalpel.code_parsers.extractor import Language, PolyglotExtractor

        extractor = PolyglotExtractor(_SIMPLE_PACKAGE, language=Language.GO)
        result = extractor.extract("function", "Hello")
        assert result.success, f"Expected success, got: {result.error}"
        assert "Hello" in result.code

    def test_extract_second_function(self):
        from code_scalpel.code_parsers.extractor import Language, PolyglotExtractor

        extractor = PolyglotExtractor(_SIMPLE_PACKAGE, language=Language.GO)
        result = extractor.extract("function", "World")
        assert result.success, f"Expected success, got: {result.error}"
        assert "World" in result.code

    def test_extract_struct_as_class(self):
        from code_scalpel.code_parsers.extractor import Language, PolyglotExtractor

        extractor = PolyglotExtractor(_STRUCT_CODE, language=Language.GO)
        result = extractor.extract("class", "Point")
        assert result.success, f"Expected success, got: {result.error}"
        assert "Point" in result.code

    def test_extract_method_from_struct(self):
        from code_scalpel.code_parsers.extractor import Language, PolyglotExtractor

        extractor = PolyglotExtractor(_STRUCT_CODE, language=Language.GO)
        result = extractor.extract("function", "Distance")
        assert result.success, f"Expected success, got: {result.error}"
        assert "Distance" in result.code

    def test_extract_missing_symbol_returns_error(self):
        from code_scalpel.code_parsers.extractor import Language, PolyglotExtractor

        extractor = PolyglotExtractor(_SIMPLE_PACKAGE, language=Language.GO)
        result = extractor.extract("function", "NonExistent")
        assert not result.success
        assert result.error is not None

    def test_extract_reports_language_as_go(self):
        from code_scalpel.code_parsers.extractor import Language, PolyglotExtractor

        extractor = PolyglotExtractor(_SIMPLE_PACKAGE, language=Language.GO)
        result = extractor.extract("function", "Hello")
        assert result.language == "go"

    def test_extract_reports_line_numbers(self):
        from code_scalpel.code_parsers.extractor import Language, PolyglotExtractor

        extractor = PolyglotExtractor(_SIMPLE_PACKAGE, language=Language.GO)
        result = extractor.extract("function", "Hello")
        assert result.success
        assert result.start_line > 0
        assert result.end_line >= result.start_line

    def test_auto_detect_via_file_path(self):
        """When file_path ends in .go, language is auto-detected as GO."""
        from code_scalpel.code_parsers.extractor import Language, PolyglotExtractor

        extractor = PolyglotExtractor(
            _SIMPLE_PACKAGE, file_path="main.go", language=Language.AUTO
        )
        assert extractor.language is Language.GO
        result = extractor.extract("function", "Hello")
        assert result.success
