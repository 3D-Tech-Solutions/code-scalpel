"""
C and C++ language parser tests.

[20260224_TEST] Comprehensive tests for CNormalizer, CppNormalizer, and
PolyglotExtractor C/C++ integration.

Covers:
- CNormalizer: function defs, structs, unions, enums, includes, defines, control flow
- CppNormalizer: classes, namespaces, templates, qualified methods, using declarations
- PolyglotExtractor: end-to-end function/class/method extraction from C and C++ source
- Language detection: extension map, content-based heuristics

3D-project-relevant patterns are tested explicitly (Vec3, Mesh, AABB, etc.).
"""

from __future__ import annotations

import pytest

pytest.importorskip("tree_sitter_c", reason="tree_sitter_c not installed; skipping C/C++ parser tests")

from code_scalpel.ir.nodes import (
    IRAssign,
    IRClassDef,
    IRFunctionDef,
    IRImport,
    IRModule,
    IRName,
    IRReturn,
)
from code_scalpel.ir.normalizers.c_normalizer import CNormalizer
from code_scalpel.ir.normalizers.cpp_normalizer import CppNormalizer
from code_scalpel.code_parsers.extractor import (
    EXTENSION_MAP,
    Language,
    PolyglotExtractor,
)

# =============================================================================
# Helpers
# =============================================================================


def _c(source: str) -> IRModule:
    return CNormalizer().normalize(source)


def _cpp(source: str) -> IRModule:
    return CppNormalizer().normalize(source)


def _find(module: IRModule, kind, name: str):
    for node in module.body:
        if isinstance(node, kind) and getattr(node, "name", None) == name:
            return node
    return None


# =============================================================================
# Extension Map Tests
# =============================================================================


class TestExtensionMap:
    """File extension to Language mapping correctness."""

    @pytest.mark.parametrize("ext", [".c", ".h"])
    def test_c_extensions(self, ext):
        assert EXTENSION_MAP[ext] == Language.C

    @pytest.mark.parametrize(
        "ext", [".cpp", ".cc", ".cxx", ".c++", ".hpp", ".hxx", ".hh", ".h++", ".inl"]
    )
    def test_cpp_extensions(self, ext):
        assert EXTENSION_MAP[ext] == Language.CPP

    def test_c_language_enum_value(self):
        assert Language.C.value == "c"

    def test_cpp_language_enum_value(self):
        assert Language.CPP.value == "cpp"


# =============================================================================
# C Normalizer — Functions
# =============================================================================


class TestCNormalizerFunctions:
    """CNormalizer function definition handling."""

    def test_simple_int_function(self):
        m = _c("int add(int a, int b) { return a + b; }")
        fn = _find(m, IRFunctionDef, "add")
        assert fn is not None
        assert fn.name == "add"
        assert fn.source_language == "c"

    def test_function_return_type(self):
        m = _c("float dot(float x, float y) { return x * y; }")
        fn = _find(m, IRFunctionDef, "dot")
        assert fn.return_type == "float"

    def test_void_function(self):
        m = _c("void reset(int *buf, int n) { }")
        fn = _find(m, IRFunctionDef, "reset")
        assert fn is not None
        assert fn.return_type == "void"

    def test_function_parameters(self):
        m = _c("int lerp(int a, int b, float t) { return a; }")
        fn = _find(m, IRFunctionDef, "lerp")
        assert len(fn.params) == 3
        assert fn.params[0].name == "a"
        assert fn.params[1].name == "b"
        assert fn.params[2].name == "t"

    def test_function_param_type_annotation(self):
        m = _c("int foo(float x) { return 0; }")
        fn = _find(m, IRFunctionDef, "foo")
        assert fn.params[0].type_annotation == "float"

    def test_function_body_has_return(self):
        m = _c("int id(int x) { return x; }")
        fn = _find(m, IRFunctionDef, "id")
        assert any(isinstance(s, IRReturn) for s in fn.body)

    def test_function_location_tracked(self):
        m = _c("int f(void) { return 0; }")
        fn = _find(m, IRFunctionDef, "f")
        assert fn.loc is not None
        assert fn.loc.line >= 1

    def test_multiple_functions(self):
        m = _c("int a(void){return 1;}\nfloat b(void){return 2.0f;}")
        names = {n.name for n in m.body if isinstance(n, IRFunctionDef)}
        assert "a" in names
        assert "b" in names

    def test_pointer_return_type(self):
        m = _c("char *name(void) { return 0; }")
        fn = _find(m, IRFunctionDef, "name")
        assert fn is not None  # name extracted despite pointer declarator

    def test_variadic_function(self):
        m = _c("int printf(const char *fmt, ...) { return 0; }")
        fn = _find(m, IRFunctionDef, "printf")
        assert fn is not None
        # Last param should be the variadic indicator
        assert any(p.name == "..." for p in fn.params)

    def test_main_function(self):
        m = _c("int main(int argc, char *argv[]) { return 0; }")
        fn = _find(m, IRFunctionDef, "main")
        assert fn is not None
        assert fn.params[0].name == "argc"


# =============================================================================
# C Normalizer — Structs / Unions / Enums
# =============================================================================


class TestCNormalizerStructs:
    """CNormalizer struct/union/enum handling."""

    def test_named_struct(self):
        m = _c("struct Point { int x; int y; };")
        cls = _find(m, IRClassDef, "Point")
        assert cls is not None
        assert cls.source_language == "c"

    def test_struct_fields(self):
        m = _c("struct Vec3 { float x; float y; float z; };")
        cls = _find(m, IRClassDef, "Vec3")
        assert cls is not None
        field_names = {n.targets[0].id for n in cls.body if isinstance(n, IRAssign)}
        assert "x" in field_names
        assert "y" in field_names
        assert "z" in field_names

    def test_typedef_struct(self):
        m = _c("typedef struct { float x; float y; } Vec2;")
        cls = _find(m, IRClassDef, "Vec2")
        assert cls is not None
        assert cls._metadata.get("kind") == "struct"

    def test_typedef_struct_with_named_struct(self):
        m = _c("typedef struct _Point { int x; int y; } Point;")
        cls = _find(m, IRClassDef, "Point")
        assert cls is not None
        assert cls._metadata.get("struct_name") == "_Point"

    def test_union(self):
        m = _c("union Value { int i; float f; };")
        cls = _find(m, IRClassDef, "Value")
        assert cls is not None
        assert cls._metadata.get("kind") == "union"

    def test_enum(self):
        m = _c("enum Color { RED, GREEN, BLUE };")
        cls = _find(m, IRClassDef, "Color")
        assert cls is not None
        assert cls._metadata.get("kind") == "enum"

    def test_enum_with_values(self):
        m = _c("enum Axis { X=0, Y=1, Z=2 };")
        cls = _find(m, IRClassDef, "Axis")
        assert cls is not None
        assigns = [n for n in cls.body if isinstance(n, IRAssign)]
        assert len(assigns) == 3


# =============================================================================
# C Normalizer — Preprocessor
# =============================================================================


class TestCNormalizerPreprocessor:
    """#include and #define handling."""

    def test_system_include(self):
        m = _c("#include <stdio.h>")
        imports = [n for n in m.body if isinstance(n, IRImport)]
        assert any("stdio.h" in i.module for i in imports)

    def test_local_include(self):
        m = _c('#include "mesh.h"')
        imports = [n for n in m.body if isinstance(n, IRImport)]
        assert any("mesh.h" in i.module for i in imports)

    def test_define_integer(self):
        m = _c("#define MAX_VERTS 65535")
        assigns = [n for n in m.body if isinstance(n, IRAssign)]
        node = next((a for a in assigns if a.targets[0].id == "MAX_VERTS"), None)
        assert node is not None
        assert node.value.value == 65535

    def test_define_float(self):
        m = _c("#define PI 3.14159")
        assigns = [n for n in m.body if isinstance(n, IRAssign)]
        node = next((a for a in assigns if a.targets[0].id == "PI"), None)
        assert node is not None
        assert abs(node.value.value - 3.14159) < 1e-5

    def test_define_hex(self):
        m = _c("#define FLAG 0xFF")
        assigns = [n for n in m.body if isinstance(n, IRAssign)]
        node = next((a for a in assigns if a.targets[0].id == "FLAG"), None)
        assert node is not None
        assert node.value.value == 255


# =============================================================================
# C Normalizer — Module structure
# =============================================================================


class TestCNormalizerModule:
    """IRModule output from CNormalizer."""

    def test_returns_irmodule(self):
        m = _c("int x;")
        assert isinstance(m, IRModule)

    def test_source_language(self):
        m = _c("void f(void) {}")
        assert m.source_language == "c"

    def test_realistic_3d_header(self):
        """Smoke-test a realistic 3D-style C header.

        Note: forward declarations (no body) are NOT emitted as IRFunctionDef;
        only full function definitions are.  The header mainly tests struct and
        include extraction.
        """
        src = """
#ifndef VEC3_H
#define VEC3_H

#include <math.h>

#define VEC3_ZERO 0

typedef struct {
    float x;
    float y;
    float z;
} Vec3;

/* forward declarations — no body, so no IRFunctionDef produced */
float vec3_length(Vec3 v);
float vec3_dot(Vec3 a, Vec3 b);

#endif
"""
        m = _c(src)
        assert isinstance(m, IRModule)
        # Should have Vec3 struct from typedef
        cls = _find(m, IRClassDef, "Vec3")
        assert cls is not None
        # Should have math.h import
        imports = [n for n in m.body if isinstance(n, IRImport)]
        assert any("math.h" in i.module for i in imports)
        # Should have VEC3_ZERO define
        assigns = [n for n in m.body if isinstance(n, IRAssign)]
        assert any(a.targets[0].id == "VEC3_ZERO" for a in assigns)


# =============================================================================
# C++ Normalizer — Classes
# =============================================================================


class TestCppNormalizerClasses:
    """CppNormalizer class handling."""

    def test_simple_class(self):
        m = _cpp("class Foo {};")
        cls = _find(m, IRClassDef, "Foo")
        assert cls is not None
        assert cls.source_language == "cpp"

    def test_class_with_fields(self):
        m = _cpp("class Vec3 { public: float x, y, z; };")
        cls = _find(m, IRClassDef, "Vec3")
        assert cls is not None

    def test_class_with_method_stub(self):
        m = _cpp("class Mesh { public: int vertex_count() const; };")
        cls = _find(m, IRClassDef, "Mesh")
        assert cls is not None
        methods = [n for n in cls.body if isinstance(n, IRFunctionDef)]
        assert any(fn.name == "vertex_count" for fn in methods)

    def test_class_method_stub_is_declaration(self):
        m = _cpp("class A { void foo(); };")
        cls = _find(m, IRClassDef, "A")
        stubs = [n for n in cls.body if isinstance(n, IRFunctionDef)]
        assert stubs[0]._metadata.get("is_declaration") is True

    def test_class_inline_method(self):
        m = _cpp("class Foo { int val() const { return 42; } };")
        cls = _find(m, IRClassDef, "Foo")
        fns = [n for n in cls.body if isinstance(n, IRFunctionDef)]
        assert any(fn.name == "val" for fn in fns)

    def test_class_location(self):
        m = _cpp("class Bar {};\n")
        cls = _find(m, IRClassDef, "Bar")
        assert cls.loc is not None
        assert cls.loc.line == 1

    def test_class_base_class(self):
        m = _cpp("class Derived : public Base {};")
        cls = _find(m, IRClassDef, "Derived")
        assert cls is not None
        base_names = [b.id for b in cls.bases if isinstance(b, IRName)]
        assert "Base" in base_names


# =============================================================================
# C++ Normalizer — Namespaces
# =============================================================================


class TestCppNormalizerNamespaces:
    """Namespace declarations fold into parent scope."""

    def test_namespace_children_visible(self):
        m = _cpp("namespace geom { class Vec3 {}; }")
        # Vec3 should be folded into module body
        cls = _find(m, IRClassDef, "Vec3")
        assert cls is not None

    def test_namespace_metadata_tagged(self):
        m = _cpp("namespace geom { class Vec3 {}; }")
        cls = _find(m, IRClassDef, "Vec3")
        assert cls._metadata.get("namespace") == "geom"

    def test_nested_namespaces(self):
        m = _cpp("namespace a { namespace b { void f(){} } }")
        fn = _find(m, IRFunctionDef, "f")
        assert fn is not None

    def test_namespace_function(self):
        m = _cpp("namespace math { float sqrt2() { return 1.414f; } }")
        fn = _find(m, IRFunctionDef, "sqrt2")
        assert fn is not None
        assert fn._metadata.get("namespace") == "math"


# =============================================================================
# C++ Normalizer — Templates
# =============================================================================


class TestCppNormalizerTemplates:
    """Template declarations unwrap the inner entity."""

    def test_template_function_visible(self):
        m = _cpp("template<typename T> T clamp(T v, T lo, T hi) { return v; }")
        fn = _find(m, IRFunctionDef, "clamp")
        assert fn is not None

    def test_template_function_params_tagged(self):
        m = _cpp("template<typename T> T clamp(T v, T lo, T hi) { return v; }")
        fn = _find(m, IRFunctionDef, "clamp")
        assert "T" in fn._metadata.get("template_params", [])

    def test_template_class_visible(self):
        m = _cpp("template<typename T> class AABB { T min_pt; T max_pt; };")
        cls = _find(m, IRClassDef, "AABB")
        assert cls is not None

    def test_template_class_params_tagged(self):
        m = _cpp("template<typename T> class Vec { T x; T y; };")
        cls = _find(m, IRClassDef, "Vec")
        assert "T" in cls._metadata.get("template_params", [])

    def test_template_lerp_3d(self):
        """Common 3D template pattern."""
        src = """
template<typename T>
T lerp(T a, T b, float t) {
    return a + (b - a) * t;
}
"""
        m = _cpp(src)
        fn = _find(m, IRFunctionDef, "lerp")
        assert fn is not None
        assert fn.params[0].name == "a"
        assert fn.params[2].name == "t"


# =============================================================================
# C++ Normalizer — Using / Qualified names
# =============================================================================


class TestCppNormalizerUsing:
    """using declarations become IRImport."""

    def test_using_namespace(self):
        m = _cpp("using namespace std;")
        imports = [n for n in m.body if isinstance(n, IRImport)]
        assert any("std" in i.module for i in imports)

    def test_using_specific_name(self):
        m = _cpp("using std::vector;")
        imports = [n for n in m.body if isinstance(n, IRImport)]
        match = next((i for i in imports if "std" in i.module), None)
        assert match is not None
        assert "vector" in match.names


class TestCppQualifiedMethods:
    """Qualified method definitions (Vec3::dot) get dotted names."""

    def test_qualified_method_name(self):
        src = """
class Vec3 { public: float dot(const Vec3& o) const; };
float Vec3::dot(const Vec3& o) const { return x*o.x + y*o.y + z*o.z; }
"""
        m = _cpp(src)
        fns = [n for n in m.body if isinstance(n, IRFunctionDef)]
        # The out-of-line definition should have a dotted name
        qualified = [f for f in fns if "." in f.name]
        assert qualified, "Expected qualified method name like 'Vec3.dot'"
        assert qualified[0].name == "Vec3.dot"


# =============================================================================
# C++ Normalizer — Lambda
# =============================================================================


class TestCppLambda:
    def test_lambda_in_function(self):
        src = """
void process(float* arr, int n) {
    auto square = [](float x) { return x * x; };
}
"""
        m = _cpp(src)
        fn = _find(m, IRFunctionDef, "process")
        assert fn is not None  # outer function found


# =============================================================================
# PolyglotExtractor — C
# =============================================================================


class TestPolyglotExtractorC:
    """PolyglotExtractor end-to-end extraction from C source."""

    C_SOURCE = """\
#include <math.h>

#define MAX_VERTS 65535

struct Vertex {
    float x;
    float y;
    float z;
};

float length(float x, float y, float z) {
    return sqrtf(x*x + y*y + z*z);
}

float dot(float ax, float ay, float az,
          float bx, float by, float bz) {
    return ax*bx + ay*by + az*bz;
}
"""

    def _extractor(self):
        return PolyglotExtractor(self.C_SOURCE, language=Language.C)

    def test_extract_function_by_name(self):
        r = self._extractor().extract("function", "length")
        assert r.success
        assert "length" in r.code

    def test_extract_second_function(self):
        r = self._extractor().extract("function", "dot")
        assert r.success
        assert "dot" in r.code

    def test_extract_struct(self):
        r = self._extractor().extract("class", "Vertex")
        assert r.success
        assert "Vertex" in r.code

    def test_extract_missing_function_fails(self):
        r = self._extractor().extract("function", "nonexistent")
        assert not r.success

    def test_extract_language_reported(self):
        r = self._extractor().extract("function", "length")
        assert r.language == "c"

    def test_extract_location_reported(self):
        r = self._extractor().extract("function", "length")
        assert r.start_line >= 1
        assert r.end_line >= r.start_line

    def test_from_file_extension_auto_detect(self, tmp_path):
        f = tmp_path / "geom.c"
        f.write_text(self.C_SOURCE)
        ext = PolyglotExtractor.from_file(str(f))
        assert ext.language == Language.C

    def test_header_extension_auto_detect(self, tmp_path):
        f = tmp_path / "geom.h"
        f.write_text(self.C_SOURCE)
        ext = PolyglotExtractor.from_file(str(f))
        assert ext.language == Language.C


# =============================================================================
# PolyglotExtractor — C++ (3D project patterns)
# =============================================================================


class TestPolyglotExtractorCpp:
    """PolyglotExtractor end-to-end extraction from C++ source."""

    CPP_SOURCE = """\
#include <cmath>

namespace geom {

class Vec3 {
public:
    float x, y, z;

    Vec3(float x, float y, float z);
    float length() const;
    float dot(const Vec3& o) const;
    Vec3  cross(const Vec3& o) const;
};

template<typename T>
T lerp(T a, T b, float t) {
    return a + (b - a) * t;
}

} // namespace geom
"""

    def _extractor(self):
        return PolyglotExtractor(self.CPP_SOURCE, language=Language.CPP)

    def test_extract_cpp_class(self):
        r = self._extractor().extract("class", "Vec3")
        assert r.success
        assert "Vec3" in r.code

    def test_extract_template_function(self):
        r = self._extractor().extract("function", "lerp")
        assert r.success
        assert "lerp" in r.code

    def test_extract_language_reported_cpp(self):
        r = self._extractor().extract("class", "Vec3")
        assert r.language == "cpp"

    def test_from_file_cpp_extension(self, tmp_path):
        f = tmp_path / "vec3.cpp"
        f.write_text(self.CPP_SOURCE)
        ext = PolyglotExtractor.from_file(str(f))
        assert ext.language == Language.CPP

    def test_from_file_hpp_extension(self, tmp_path):
        f = tmp_path / "vec3.hpp"
        f.write_text(self.CPP_SOURCE)
        ext = PolyglotExtractor.from_file(str(f))
        assert ext.language == Language.CPP

    def test_extract_missing_class_fails(self):
        r = self._extractor().extract("class", "Quaternion")
        assert not r.success

    def test_aabb_template_class(self):
        src = """
template<typename T>
class AABB {
public:
    T min_pt;
    T max_pt;
    bool contains(T p) const;
};
"""
        ext = PolyglotExtractor(src, language=Language.CPP)
        r = ext.extract("class", "AABB")
        assert r.success
        assert "AABB" in r.code

    def test_mesh_class_extraction(self):
        src = """
class Mesh {
public:
    int vertex_count;
    int index_count;
    void upload_to_gpu();
    void draw() const;
};
"""
        ext = PolyglotExtractor(src, language=Language.CPP)
        r = ext.extract("class", "Mesh")
        assert r.success
        assert "Mesh" in r.code


# =============================================================================
# Language detection heuristics
# =============================================================================


class TestLanguageDetection:
    """Content-based language detection for C/C++."""

    def test_detect_cpp_from_namespace(self):
        from code_scalpel.code_parsers.extractor import detect_language

        lang = detect_language(None, "namespace geom { class Vec3{}; }")
        assert lang == Language.CPP

    def test_detect_cpp_from_std_scope(self):
        from code_scalpel.code_parsers.extractor import detect_language

        lang = detect_language(None, "std::vector<float> verts;")
        assert lang == Language.CPP

    def test_detect_cpp_from_nullptr(self):
        from code_scalpel.code_parsers.extractor import detect_language

        lang = detect_language(None, "void* p = nullptr;")
        assert lang == Language.CPP

    def test_detect_c_from_include(self):
        from code_scalpel.code_parsers.extractor import detect_language

        lang = detect_language(None, "#include <stdio.h>\nint main(){}")
        assert lang in (Language.C, Language.CPP)  # either is acceptable

    def test_detect_from_c_extension(self):
        from code_scalpel.code_parsers.extractor import detect_language

        lang = detect_language("mesh.c")
        assert lang == Language.C

    def test_detect_from_cpp_extension(self):
        from code_scalpel.code_parsers.extractor import detect_language

        lang = detect_language("renderer.cpp")
        assert lang == Language.CPP

    def test_detect_from_hpp_extension(self):
        from code_scalpel.code_parsers.extractor import detect_language

        lang = detect_language("scene.hpp")
        assert lang == Language.CPP


# =============================================================================
# Cache behavior
# =============================================================================


class TestNormalizerCache:
    """Parse tree caching doesn't break correctness."""

    def test_c_cache_same_result(self):
        src = "int f(void) { return 1; }"
        n = CNormalizer()
        m1 = n.normalize(src)
        m2 = n.normalize(src)
        fn1 = _find(m1, IRFunctionDef, "f")
        fn2 = _find(m2, IRFunctionDef, "f")
        assert fn1.name == fn2.name

    def test_cpp_cache_same_result(self):
        src = "class A {};"
        n = CppNormalizer()
        m1 = n.normalize(src)
        m2 = n.normalize(src)
        c1 = _find(m1, IRClassDef, "A")
        c2 = _find(m2, IRClassDef, "A")
        assert c1.name == c2.name


# =============================================================================
# Real-World C Patterns
# =============================================================================


class TestCRealWorldPatterns:
    """C patterns drawn from real codebases: callbacks, bitfields, Win32, etc.

    [20260224_TEST] Extended coverage for edge-case C constructs.
    """

    def test_function_with_function_pointer_param(self):
        """Function pointer as parameter — outer function must be found."""
        m = _c(
            "void qsort_ex(void* base, int n, int (*cmp)(const void*, const void*)) {}"
        )
        fn = _find(m, IRFunctionDef, "qsort_ex")
        assert fn is not None

    def test_function_pointer_typedef_parses(self):
        """Typedef of a function pointer — module must parse without error."""
        m = _c("typedef int (*CompareFunc)(const void* a, const void* b);")
        assert isinstance(m, IRModule)

    def test_bitfield_struct(self):
        """Struct with bitfields — struct must be found as IRClassDef."""
        m = _c(
            "struct Flags { unsigned int dirty:1; unsigned int visible:1; unsigned int cast_shadow:1; };"
        )
        cls = _find(m, IRClassDef, "Flags")
        assert cls is not None

    def test_array_parameter(self):
        """C array parameter syntax `float arr[]` — param name preserved."""
        m = _c("void fill(float arr[], int n) {}")
        fn = _find(m, IRFunctionDef, "fill")
        assert fn is not None
        assert fn.params[0].name == "arr"

    def test_double_pointer_param(self):
        """char **argv — function found, second param name preserved."""
        m = _c("int main(int argc, char **argv) { return 0; }")
        fn = _find(m, IRFunctionDef, "main")
        assert fn is not None
        assert fn.params[1].name == "argv"

    def test_static_function(self):
        """static storage-class qualifier does not suppress IRFunctionDef."""
        m = _c(
            "static float clamp(float v, float lo, float hi) { return v < lo ? lo : v > hi ? hi : v; }"
        )
        fn = _find(m, IRFunctionDef, "clamp")
        assert fn is not None

    def test_define_string_value_parses(self):
        """#define with string literal — module parses without error."""
        m = _c('#define SHADER_PATH "assets/basic.glsl"')
        assert isinstance(m, IRModule)

    def test_define_functional_macro_parses(self):
        """Functional macro — module parses without error."""
        m = _c("#define MAX(a,b) ((a)>(b)?(a):(b))")
        assert isinstance(m, IRModule)

    def test_nested_struct(self):
        """Struct containing another struct type."""
        src = """
struct AABB {
    float min[3];
    float max[3];
};
struct BVHNode {
    struct AABB bounds;
    int left;
    int right;
};
"""
        m = _c(src)
        assert _find(m, IRClassDef, "BVHNode") is not None
        assert _find(m, IRClassDef, "AABB") is not None

    def test_anonymous_union_in_struct_parses(self):
        """D3D-style anonymous union inside a struct — outer struct must be found."""
        src = """
struct Vec4 {
    union {
        struct { float x, y, z, w; };
        float v[4];
    };
};
"""
        m = _c(src)
        assert isinstance(m, IRModule)
        # At minimum the outer type should surface (possibly as unnamed union child)
        assert any(isinstance(n, IRClassDef) for n in m.body)

    def test_extern_function_declaration_parses(self):
        """extern declaration — module parses, no crash on missing body."""
        m = _c("extern int snprintf(char* buf, int n, const char* fmt, ...);")
        assert isinstance(m, IRModule)

    def test_const_pointer_return(self):
        """const-qualified pointer return type — function found."""
        m = _c('const char* get_name(void) { return "mesh"; }')
        fn = _find(m, IRFunctionDef, "get_name")
        assert fn is not None

    def test_win32_style_header_smoke(self):
        """Smoke-test a Win32-style C header with typedefs, callbacks, prototypes."""
        src = """
#include <stdint.h>

typedef void*          HANDLE;
typedef uint32_t       DWORD;
typedef int            BOOL;

typedef BOOL (*WNDENUMPROC)(HANDLE hwnd, long lParam);

BOOL EnumWindows(WNDENUMPROC callback, long lParam);
HANDLE CreateFile(
    const char* name, DWORD access, DWORD share,
    void* security, DWORD creation, DWORD flags, HANDLE tmpl
);
"""
        m = _c(src)
        assert isinstance(m, IRModule)
        imports = [n for n in m.body if isinstance(n, IRImport)]
        assert any("stdint.h" in i.module for i in imports)


# =============================================================================
# Real-World C++ Patterns
# =============================================================================


class TestCppRealWorldPatterns:
    """C++ patterns encountered in real codebases: virtuals, operators, constexpr, etc.

    [20260224_TEST] Extended coverage for edge-case C++ constructs.
    """

    def test_operator_overload_in_class(self):
        """operator+ and operator+= inside a class body."""
        src = """
class Vec3 {
public:
    float x, y, z;
    Vec3 operator+(const Vec3& o) const { return Vec3{x+o.x, y+o.y, z+o.z}; }
    Vec3& operator+=(const Vec3& o) { x+=o.x; y+=o.y; z+=o.z; return *this; }
};
"""
        m = _cpp(src)
        cls = _find(m, IRClassDef, "Vec3")
        assert cls is not None
        methods = [n for n in cls.body if isinstance(n, IRFunctionDef)]
        assert any("operator" in fn.name for fn in methods)

    def test_pure_virtual_method(self):
        """Abstract base class with pure virtual methods."""
        src = """
class Shape {
public:
    virtual float area() const = 0;
    virtual float perimeter() const = 0;
    virtual ~Shape() = default;
};
"""
        m = _cpp(src)
        cls = _find(m, IRClassDef, "Shape")
        assert cls is not None
        methods = [n for n in cls.body if isinstance(n, IRFunctionDef)]
        assert any(fn.name == "area" for fn in methods)

    def test_override_method(self):
        """Derived class with override specifier."""
        src = """
class Circle : public Shape {
public:
    float radius;
    float area() const override { return 3.14159f * radius * radius; }
};
"""
        m = _cpp(src)
        cls = _find(m, IRClassDef, "Circle")
        assert cls is not None
        methods = [n for n in cls.body if isinstance(n, IRFunctionDef)]
        assert any(fn.name == "area" for fn in methods)

    def test_multiple_inheritance(self):
        """Class with two public base classes."""
        m = _cpp("class C : public A, public B {};")
        cls = _find(m, IRClassDef, "C")
        assert cls is not None
        base_names = [b.id for b in cls.bases if isinstance(b, IRName)]
        assert "A" in base_names
        assert "B" in base_names

    def test_enum_class(self):
        """Scoped enum (enum class) — must surface as IRClassDef."""
        m = _cpp("enum class Color { Red, Green, Blue };")
        cls = _find(m, IRClassDef, "Color")
        assert cls is not None

    def test_constexpr_function(self):
        """constexpr function must surface as IRFunctionDef."""
        m = _cpp("constexpr float pi() { return 3.14159265f; }")
        fn = _find(m, IRFunctionDef, "pi")
        assert fn is not None

    def test_deleted_and_defaulted_members(self):
        """= delete / = default special members — class must be found."""
        src = """
class Texture {
public:
    Texture() = default;
    Texture(const Texture&) = delete;
    Texture& operator=(const Texture&) = delete;
};
"""
        m = _cpp(src)
        cls = _find(m, IRClassDef, "Texture")
        assert cls is not None

    def test_move_constructor(self):
        """Move constructor and move-assignment — class must be found."""
        src = """
class Buffer {
public:
    Buffer(Buffer&& other) noexcept;
    Buffer& operator=(Buffer&& other) noexcept;
};
"""
        m = _cpp(src)
        cls = _find(m, IRClassDef, "Buffer")
        assert cls is not None

    def test_variadic_template(self):
        """Variadic template function — must surface as IRFunctionDef."""
        src = """
template<typename... Args>
void log(const char* fmt, Args&&... args) {}
"""
        m = _cpp(src)
        fn = _find(m, IRFunctionDef, "log")
        assert fn is not None

    def test_nested_class(self):
        """Inner class nested inside outer class — both must be reachable."""
        src = """
class SceneGraph {
public:
    class Node {
    public:
        int id;
        Node* parent;
    };
    Node* root;
};
"""
        m = _cpp(src)
        outer = _find(m, IRClassDef, "SceneGraph")
        assert outer is not None
        # Node appears either nested inside SceneGraph.body or folded into module body
        inner_in_outer = any(
            isinstance(n, IRClassDef) and n.name == "Node" for n in outer.body
        )
        inner_in_module = _find(m, IRClassDef, "Node") is not None
        assert inner_in_outer or inner_in_module

    def test_anonymous_namespace(self):
        """Anonymous namespace contents fold into module body."""
        src = """
namespace {
    float helper(float x) { return x * 2.0f; }
}
"""
        m = _cpp(src)
        fn = _find(m, IRFunctionDef, "helper")
        assert fn is not None

    def test_auto_trailing_return_type(self):
        """auto + trailing return type arrow syntax — function must be found."""
        src = """
auto dot(float ax, float ay, float bx, float by) -> float {
    return ax*bx + ay*by;
}
"""
        m = _cpp(src)
        fn = _find(m, IRFunctionDef, "dot")
        assert fn is not None

    def test_full_game_math_class_smoke(self):
        """Smoke test: complete game-engine Vec3 with operators and statics."""
        src = """
#include <cmath>

class Vec3 {
public:
    float x, y, z;
    constexpr Vec3() : x(0), y(0), z(0) {}
    constexpr Vec3(float x, float y, float z) : x(x), y(y), z(z) {}
    Vec3 operator+(const Vec3& o) const { return {x+o.x, y+o.y, z+o.z}; }
    Vec3 operator-(const Vec3& o) const { return {x-o.x, y-o.y, z-o.z}; }
    Vec3 operator*(float s)        const { return {x*s,   y*s,   z*s};   }
    bool operator==(const Vec3& o) const { return x==o.x && y==o.y && z==o.z; }
    float dot(const Vec3& o)   const { return x*o.x + y*o.y + z*o.z; }
    float length()             const { return std::sqrt(x*x + y*y + z*z); }
    Vec3  normalized()         const { float l=length(); return {x/l,y/l,z/l}; }
    Vec3  cross(const Vec3& o) const {
        return {y*o.z-z*o.y, z*o.x-x*o.z, x*o.y-y*o.x};
    }
    static Vec3 zero() { return {0,0,0}; }
    static Vec3 up()   { return {0,1,0}; }
};
"""
        m = _cpp(src)
        cls = _find(m, IRClassDef, "Vec3")
        assert cls is not None
        method_names = {fn.name for fn in cls.body if isinstance(fn, IRFunctionDef)}
        assert "dot" in method_names
        assert "length" in method_names
        assert "cross" in method_names
