from pathlib import Path

from code_scalpel.mcp.module_resolver import get_mime_type, resolve_module_path

# [20251216_TEST] Cover module resolver branches across languages and fallbacks


def test_python_resolution_variants(tmp_path: Path) -> None:
    (tmp_path / "utils.py").write_text("# util module")
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("# pkg init")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "core").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "core" / "service.py").write_text("# service")

    assert resolve_module_path("python", "utils", tmp_path) == tmp_path / "utils.py"
    assert resolve_module_path("python", "pkg", tmp_path) == tmp_path / "pkg" / "__init__.py"
    assert resolve_module_path("python", "core.service", tmp_path) == tmp_path / "src" / "core" / "service.py"


def test_javascript_and_typescript_resolution(tmp_path: Path) -> None:
    components = tmp_path / "components" / "Button"
    components.mkdir(parents=True)
    (components / "index.jsx").write_text("// jsx index")

    shared = tmp_path / "src" / "shared"
    shared.mkdir(parents=True)
    (shared / "index.js").write_text("// js shared")

    lib_src = tmp_path / "src" / "lib" / "api"
    lib_src.mkdir(parents=True)
    (lib_src / "index.ts").write_text("// ts index")

    assert resolve_module_path("javascript", "components/Button", tmp_path) == components / "index.jsx"
    assert resolve_module_path("javascript", "shared", tmp_path) == shared / "index.js"
    assert resolve_module_path("typescript", "lib/api", tmp_path) == lib_src / "index.ts"
    assert resolve_module_path("ts", "lib/api", tmp_path) == lib_src / "index.ts"


def test_java_resolution_and_unknown_language(tmp_path: Path) -> None:
    java_main = tmp_path / "src" / "main" / "java" / "com" / "example"
    java_main.mkdir(parents=True)
    (java_main / "Service.java").write_text("// service")

    assert resolve_module_path("java", "com.example.Service", tmp_path) == java_main / "Service.java"
    assert resolve_module_path("ruby", "foo", tmp_path) is None
    assert get_mime_type("unknown") == "text/plain"
    assert get_mime_type("tsx") == "text/x-tsx"


def test_direct_resolution_variants(tmp_path: Path) -> None:
    """[20251216_TEST] Cover direct file resolutions for TS, JSX, and Java."""
    (tmp_path / "utils.ts").write_text("// ts util")
    (tmp_path / "Widget.jsx").write_text("// jsx widget")
    (tmp_path / "Service.java").write_text("// java service")
    pkg_index = tmp_path / "pkg"
    pkg_index.mkdir()
    (pkg_index / "index.ts").write_text("// pkg index")

    assert resolve_module_path("typescript", "utils", tmp_path) == tmp_path / "utils.ts"
    assert resolve_module_path("javascript", "Widget", tmp_path) == tmp_path / "Widget.jsx"
    assert resolve_module_path("java", "Service", tmp_path) == tmp_path / "Service.java"
    assert resolve_module_path("typescript", "pkg", tmp_path) == pkg_index / "index.ts"


def test_javascript_resolution_src_fallback(tmp_path: Path) -> None:
    """[20251216_TEST] Ensure JS resolver falls back to src/index.js when direct paths miss."""
    src_app = tmp_path / "src" / "app"
    src_app.mkdir(parents=True)
    (src_app / "index.js").write_text("// src app")

    # No direct or top-level index, should hit src/app/index.js branch
    resolved = resolve_module_path("javascript", "app", tmp_path)
    assert resolved == src_app / "index.js"


def test_typescript_resolution_src_index_tsx(tmp_path: Path) -> None:
    """[20251216_TEST] Cover TS resolver src index.tsx fallback branch."""
    src_comp = tmp_path / "src" / "components" / "Card"
    src_comp.mkdir(parents=True)
    (src_comp / "index.tsx").write_text("// tsx index")

    resolved = resolve_module_path("typescript", "components/Card", tmp_path)
    assert resolved == src_comp / "index.tsx"


def test_js_and_ts_resolution_nested_src_variants(tmp_path: Path) -> None:
    """[20251216_TEST] Exercise src-based JSX/TSX fallbacks for nested modules."""
    src_ui = tmp_path / "src" / "ui"
    src_ui.mkdir(parents=True)
    (src_ui / "View.jsx").write_text("// jsx view")

    src_tsx = tmp_path / "src" / "widgets"
    src_tsx.mkdir(parents=True)
    (src_tsx / "Widget.tsx").write_text("// tsx widget")

    jsx_index = tmp_path / "pages" / "Home"
    jsx_index.mkdir(parents=True)
    (jsx_index / "index.jsx").write_text("// jsx home")

    assert resolve_module_path("javascript", "ui/View", tmp_path) == src_ui / "View.jsx"
    assert resolve_module_path("typescript", "widgets/Widget", tmp_path) == src_tsx / "Widget.tsx"
    assert resolve_module_path("javascript", "pages/Home", tmp_path) == jsx_index / "index.jsx"


def test_mime_type_aliases_and_defaults() -> None:
    """[20251216_TEST] Validate MIME type aliases and default fallback."""
    assert get_mime_type("JS") == "text/javascript"
    assert get_mime_type("TS") == "text/x-typescript"
    assert get_mime_type("") == "text/plain"


def test_python_src_package_init_fallback(tmp_path: Path) -> None:
    """[20251217_TEST] Cover Python src/__init__.py fallback branch."""
    src_pkg = tmp_path / "src" / "mypackage"
    src_pkg.mkdir(parents=True)
    (src_pkg / "__init__.py").write_text("# init")

    resolved = resolve_module_path("python", "mypackage", tmp_path)
    assert resolved == src_pkg / "__init__.py"


def test_java_src_main_java_fallback_missing(tmp_path: Path) -> None:
    """[20251217_TEST] Java resolution returns None when all paths miss."""
    resolved = resolve_module_path("java", "com.missing.Service", tmp_path)
    assert resolved is None


def test_typescript_all_extensions_miss_returns_none(tmp_path: Path) -> None:
    """[20251217_TEST] TS resolver returns None when all paths fail."""
    resolved = resolve_module_path("typescript", "nonexistent/Module", tmp_path)
    assert resolved is None


def test_javascript_all_extensions_miss_returns_none(tmp_path: Path) -> None:
    """[20251217_TEST] JS resolver returns None when all paths fail."""
    resolved = resolve_module_path("javascript", "nonexistent/Component", tmp_path)
    assert resolved is None
