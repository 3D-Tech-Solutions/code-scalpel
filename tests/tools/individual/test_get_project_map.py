# [20251213_TEST] v1.5.0 - Tests for get_project_map MCP tool
"""
Comprehensive tests for get_project_map MCP tool.
Tests the MCP interface, Pydantic models, and async wrapper.
"""

import pytest

from code_scalpel.mcp.server import (
    ModuleInfo,
    PackageInfo,
    ProjectMapResult,
    _get_project_map_sync,
    get_project_map,
)

# ============================================================================
# Test Pydantic Models
# ============================================================================


class TestModuleInfo:
    """Tests for ModuleInfo model."""

    def test_module_creation(self):
        """Test basic module info creation."""
        mod = ModuleInfo(path="test.py")
        assert mod.path == "test.py"
        assert mod.functions == []
        assert mod.classes == []
        assert mod.line_count == 0

    def test_module_with_content(self):
        """Test module with all fields populated."""
        mod = ModuleInfo(
            path="app/main.py",
            functions=["main", "helper"],
            classes=["App", "Config"],
            imports=["os", "sys"],
            entry_points=["app/main.py:main"],
            line_count=150,
            complexity_score=12,
        )
        assert len(mod.functions) == 2
        assert len(mod.classes) == 2
        assert mod.complexity_score == 12

    def test_module_serialization(self):
        """Test module serializes correctly."""
        mod = ModuleInfo(path="mod.py", functions=["func"])
        data = mod.model_dump()
        assert data["path"] == "mod.py"
        assert "func" in data["functions"]


class TestPackageInfo:
    """Tests for PackageInfo model."""

    def test_package_creation(self):
        """Test basic package info creation."""
        pkg = PackageInfo(name="mypackage", path="src/mypackage")
        assert pkg.name == "mypackage"
        assert pkg.path == "src/mypackage"
        assert pkg.modules == []

    def test_package_with_modules(self):
        """Test package with modules and subpackages."""
        pkg = PackageInfo(
            name="app",
            path="src/app",
            modules=["src/app/__init__.py", "src/app/main.py"],
            subpackages=["utils", "models"],
        )
        assert len(pkg.modules) == 2
        assert "utils" in pkg.subpackages

    def test_package_serialization(self):
        """Test package serializes correctly."""
        pkg = PackageInfo(name="pkg", path="pkg")
        data = pkg.model_dump()
        assert data["name"] == "pkg"


class TestProjectMapResult:
    """Tests for ProjectMapResult model."""

    def test_result_creation(self):
        """Test basic result creation."""
        result = ProjectMapResult(project_root="/test")
        assert result.project_root == "/test"
        assert result.total_files == 0
        assert result.packages == []
        assert result.languages == {}
        assert result.error is None

    def test_result_with_content(self):
        """Test result with full content."""
        result = ProjectMapResult(
            project_root="/project",
            total_files=10,
            total_lines=1500,
            languages={"python": 8, "json": 2},
            packages=[PackageInfo(name="app", path="app")],
            modules=[ModuleInfo(path="main.py")],
            entry_points=["main.py:main"],
            circular_imports=[["a.py", "b.py", "a.py"]],
            complexity_hotspots=["complex.py (complexity: 25)"],
            mermaid="graph TD\n    N0[main]",
        )
        assert result.total_files == 10
        assert len(result.packages) == 1
        assert len(result.circular_imports) == 1
        assert result.languages["python"] == 8

    def test_result_with_error(self):
        """Test result with error."""
        result = ProjectMapResult(
            project_root="/nonexistent",
            error="Not found",
        )
        assert result.error is not None


# ============================================================================
# Test Synchronous Implementation
# ============================================================================


class TestGetProjectMapSync:
    """Tests for _get_project_map_sync function."""

    @pytest.fixture
    def simple_project(self, tmp_path):
        """Create a simple project structure."""
        (tmp_path / "main.py").write_text("""
def main():
    helper()

def helper():
    pass

if __name__ == "__main__":
    main()
""")
        (tmp_path / "utils.py").write_text("""
def utility():
    return 42
""")
        return tmp_path

    @pytest.fixture
    def package_project(self, tmp_path):
        """Create a project with packages."""
        # Root module
        (tmp_path / "app.py").write_text("from pkg import module")

        # Package with init
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "module.py").write_text("""
def process():
    pass
""")

        # Subpackage
        subpkg = pkg / "sub"
        subpkg.mkdir()
        (subpkg / "__init__.py").write_text("")
        (subpkg / "helper.py").write_text("def help(): pass")

        return tmp_path

    def test_sync_returns_result(self, simple_project):
        """Test sync function returns ProjectMapResult."""
        result = _get_project_map_sync(str(simple_project), True, 10, False)
        assert isinstance(result, ProjectMapResult)
        assert result.error is None

    def test_sync_counts_files(self, simple_project):
        """Test sync function counts files correctly."""
        result = _get_project_map_sync(str(simple_project), True, 10, False)
        assert result.total_files == 2  # main.py and utils.py

    def test_sync_counts_lines(self, simple_project):
        """Test sync function counts lines."""
        result = _get_project_map_sync(str(simple_project), True, 10, False)
        assert result.total_lines > 0

    def test_sync_finds_functions(self, simple_project):
        """Test sync function finds functions."""
        result = _get_project_map_sync(str(simple_project), True, 10, False)
        all_functions = []
        for mod in result.modules:
            all_functions.extend(mod.functions)
        assert "main" in all_functions
        assert "helper" in all_functions
        assert "utility" in all_functions

    def test_sync_detects_entry_points(self, simple_project):
        """Test sync function detects entry points."""
        result = _get_project_map_sync(str(simple_project), True, 10, False)
        assert len(result.entry_points) >= 1
        assert any("main" in ep for ep in result.entry_points)

    def test_sync_detects_packages(self, package_project):
        """Test sync function detects packages."""
        result = _get_project_map_sync(str(package_project), True, 10, False)
        pkg_names = {p.name for p in result.packages}
        assert "pkg" in pkg_names

    def test_sync_calculates_complexity(self, tmp_path):
        """Test sync function calculates complexity."""
        (tmp_path / "complex.py").write_text("""
def complex_func(x):
    if x > 0:
        if x > 10:
            for i in range(x):
                if i % 2:
                    print(i)
        else:
            while x:
                x -= 1
    return x
""")
        result = _get_project_map_sync(str(tmp_path), True, 5, False)

        # Should have complexity score
        complex_mod = next((m for m in result.modules if "complex.py" in m.path), None)
        assert complex_mod is not None
        assert complex_mod.complexity_score > 0

    def test_sync_flags_complexity_hotspots(self, tmp_path):
        """Test sync function flags complexity hotspots."""
        # Create a very complex file
        (tmp_path / "hotspot.py").write_text("""
def mega_complex(a, b, c, d, e):
    if a:
        if b:
            if c:
                if d:
                    if e:
                        for i in range(10):
                            for j in range(10):
                                if i > j:
                                    while i:
                                        i -= 1
                                        if i % 2:
                                            pass
    return a and b and c and d and e
""")
        result = _get_project_map_sync(str(tmp_path), True, 5, False)
        assert len(result.complexity_hotspots) >= 1

    def test_sync_generates_mermaid(self, simple_project):
        """Test sync function generates Mermaid diagram."""
        result = _get_project_map_sync(str(simple_project), True, 10, False)
        assert "graph TD" in result.mermaid

    def test_sync_nonexistent_path(self):
        """Test sync function handles nonexistent path."""
        result = _get_project_map_sync("/nonexistent/path", True, 10, False)
        assert result.error is not None
        assert "not found" in result.error.lower()

    def test_sync_empty_directory(self, tmp_path):
        """Test sync function handles empty directory."""
        result = _get_project_map_sync(str(tmp_path), True, 10, False)
        assert result.error is None
        assert result.total_files == 0


# ============================================================================
# Test Async Wrapper
# ============================================================================


class TestGetProjectMapAsync:
    """Tests for async get_project_map function."""

    @pytest.fixture
    def sample_project(self, tmp_path):
        """Create a sample project."""
        (tmp_path / "main.py").write_text("""
def main():
    run()

def run():
    pass
""")
        (tmp_path / "config.py").write_text("""
class Config:
    DEBUG = True
""")
        return tmp_path

    @pytest.mark.asyncio
    async def test_async_returns_result(self, sample_project):
        """Test async function returns result."""
        result = await get_project_map(project_root=str(sample_project))
        assert isinstance(result, ProjectMapResult)

    @pytest.mark.asyncio
    async def test_async_finds_modules(self, sample_project):
        """Test async function finds modules."""
        result = await get_project_map(project_root=str(sample_project))
        paths = {m.path for m in result.modules}
        assert "main.py" in paths
        assert "config.py" in paths

    @pytest.mark.asyncio
    async def test_async_default_parameters(self, sample_project):
        """Test async function uses default parameters."""
        result = await get_project_map(project_root=str(sample_project))
        # Defaults should work
        assert result.error is None

    @pytest.mark.asyncio
    async def test_async_with_complexity_disabled(self, sample_project):
        """Test async function with complexity disabled."""
        result = await get_project_map(
            project_root=str(sample_project),
            include_complexity=False,
        )
        # All modules should have 0 complexity
        for mod in result.modules:
            assert mod.complexity_score == 0

    @pytest.mark.asyncio
    async def test_async_with_circular_check(self, tmp_path):
        """Test async function checks circular imports."""
        (tmp_path / "a.py").write_text("import b")
        (tmp_path / "b.py").write_text("import a")

        result = await get_project_map(
            project_root=str(tmp_path),
            include_circular_check=True,
        )
        assert len(result.circular_imports) >= 1


# ============================================================================
# Test Entry Point Detection
# ============================================================================


class TestEntryPointDetection:
    """Tests for entry point detection."""

    @pytest.mark.asyncio
    async def test_main_function_detected(self, tmp_path):
        """Test main() function is detected as entry point."""
        (tmp_path / "app.py").write_text("def main(): pass")

        result = await get_project_map(project_root=str(tmp_path))
        assert any("main" in ep for ep in result.entry_points)

    @pytest.mark.asyncio
    async def test_click_command_detected(self, tmp_path):
        """Test @click.command decorated function is detected."""
        (tmp_path / "cli.py").write_text("""
import click

@click.command()
def cli():
    pass
""")
        result = await get_project_map(project_root=str(tmp_path))
        entry_funcs = [ep.split(":")[-1] for ep in result.entry_points]
        assert "cli" in entry_funcs

    @pytest.mark.asyncio
    async def test_flask_route_detected(self, tmp_path):
        """Test @app.route decorated function is detected."""
        (tmp_path / "web.py").write_text("""
from flask import Flask
app = Flask(__name__)

@app.route("/")
def index():
    return "Hello"

@app.get("/api")
def api():
    return {}
""")
        result = await get_project_map(project_root=str(tmp_path))
        entry_funcs = [ep.split(":")[-1] for ep in result.entry_points]
        assert "index" in entry_funcs
        assert "api" in entry_funcs


# ============================================================================
# Test Edge Cases
# ============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_syntax_error_in_file(self, tmp_path):
        """Test handling of syntax errors."""
        (tmp_path / "good.py").write_text("def good(): pass")
        (tmp_path / "bad.py").write_text("def broken(")  # Syntax error

        result = await get_project_map(project_root=str(tmp_path))
        # Should still process good files
        assert result.total_files >= 1

    @pytest.mark.asyncio
    async def test_binary_file_handling(self, tmp_path):
        """Test handling of binary files."""
        (tmp_path / "code.py").write_text("def func(): pass")
        (tmp_path / "binary.pyc").write_bytes(b"\x00\x01\x02\x03")

        result = await get_project_map(project_root=str(tmp_path))
        # Should only count .py files
        assert result.total_files == 1

    @pytest.mark.asyncio
    async def test_excluded_directories(self, tmp_path):
        """Test that excluded directories are skipped."""
        # Create a regular file
        (tmp_path / "main.py").write_text("def main(): pass")

        # Create files in excluded dirs
        pycache = tmp_path / "__pycache__"
        pycache.mkdir()
        (pycache / "cached.py").write_text("# cached")

        venv = tmp_path / "venv"
        venv.mkdir()
        (venv / "venv_mod.py").write_text("# venv")

        result = await get_project_map(project_root=str(tmp_path))

        paths = {m.path for m in result.modules}
        assert "main.py" in paths
        assert not any("__pycache__" in p for p in paths)
        assert not any("venv" in p for p in paths)

    @pytest.mark.asyncio
    async def test_deeply_nested_project(self, tmp_path):
        """Test with deeply nested directory structure."""
        # Create nested structure
        path = tmp_path
        for i in range(5):
            path = path / f"level{i}"
            path.mkdir()
            (path / "__init__.py").write_text("")
            (path / "module.py").write_text(f"def func{i}(): pass")

        result = await get_project_map(project_root=str(tmp_path))

        # Should find all modules
        assert result.total_files >= 5

    @pytest.mark.asyncio
    async def test_empty_python_files(self, tmp_path):
        """Test handling of empty Python files."""
        (tmp_path / "empty.py").write_text("")
        (tmp_path / "comment_only.py").write_text("# Just a comment")

        result = await get_project_map(project_root=str(tmp_path))
        assert result.total_files == 2


# ============================================================================
# Test Integration Scenarios
# ============================================================================


class TestIntegrationScenarios:
    """Integration tests with realistic scenarios."""

    @pytest.mark.asyncio
    async def test_flask_application(self, tmp_path):
        """Test with Flask-like application structure."""
        app = tmp_path / "app"
        app.mkdir()

        (app / "__init__.py").write_text("""
from flask import Flask

def create_app():
    app = Flask(__name__)
    return app
""")

        (app / "routes.py").write_text("""
from flask import Blueprint

bp = Blueprint("main", __name__)

@bp.route("/")
def index():
    return "Hello"

@bp.route("/api")
def api():
    return get_data()

def get_data():
    return {"status": "ok"}
""")

        (app / "models.py").write_text("""
class User:
    def __init__(self, name):
        self.name = name

class Post:
    def __init__(self, title):
        self.title = title
""")

        result = await get_project_map(project_root=str(tmp_path))

        # Should find package
        assert any(p.name == "app" for p in result.packages)

        # Should find entry points
        assert len(result.entry_points) >= 2  # index and api

        # Should find classes
        all_classes = []
        for mod in result.modules:
            all_classes.extend(mod.classes)
        assert "User" in all_classes
        assert "Post" in all_classes

    @pytest.mark.asyncio
    async def test_cli_application(self, tmp_path):
        """Test with CLI application structure."""
        (tmp_path / "cli.py").write_text("""
import click

@click.group()
def main():
    pass

@main.command()
def init():
    setup_config()

@main.command()
def run():
    execute()

def setup_config():
    pass

def execute():
    process()

def process():
    pass
""")

        result = await get_project_map(project_root=str(tmp_path))

        # Should detect CLI entry points
        entry_funcs = [ep.split(":")[-1] for ep in result.entry_points]
        assert "main" in entry_funcs
        assert "init" in entry_funcs
        assert "run" in entry_funcs

    @pytest.mark.asyncio
    async def test_data_science_project(self, tmp_path):
        """Test with data science project structure."""
        src = tmp_path / "src"
        src.mkdir()

        (src / "__init__.py").write_text("")

        (src / "data.py").write_text("""
def load_data(path):
    pass

def clean_data(df):
    pass

def transform(df):
    pass
""")

        (src / "model.py").write_text("""
class Model:
    def fit(self, X, y):
        pass

    def predict(self, X):
        pass

def train_model(data):
    model = Model()
    model.fit(data["X"], data["y"])
    return model
""")

        (src / "evaluate.py").write_text("""
def calculate_metrics(y_true, y_pred):
    pass

def plot_results(metrics):
    pass
""")

        result = await get_project_map(project_root=str(tmp_path))

        # Should find src package
        assert any(p.name == "src" for p in result.packages)

        # Should find Model class
        all_classes = []
        for mod in result.modules:
            all_classes.extend(mod.classes)
        assert "Model" in all_classes


# ============================================================================
# Test Language Breakdown Feature
# ============================================================================


class TestLanguageBreakdown:
    """Tests for language breakdown feature in get_project_map."""

    @pytest.mark.asyncio
    async def test_python_only_project(self, tmp_path):
        """Test language breakdown with Python-only project."""
        (tmp_path / "main.py").write_text("def main(): pass")
        (tmp_path / "utils.py").write_text("def helper(): pass")
        (tmp_path / "config.py").write_text("DEBUG = True")

        result = await get_project_map(project_root=str(tmp_path))

        assert "python" in result.languages
        assert result.languages["python"] == 3

    @pytest.mark.asyncio
    async def test_multi_language_project(self, tmp_path):
        """Test language breakdown with multiple file types."""
        # Python files
        (tmp_path / "app.py").write_text("def app(): pass")
        (tmp_path / "utils.py").write_text("def util(): pass")

        # JavaScript/TypeScript
        (tmp_path / "script.js").write_text("function hello() {}")
        (tmp_path / "types.ts").write_text("export interface User {}")

        # Config files
        (tmp_path / "config.json").write_text('{"key": "value"}')
        (tmp_path / "settings.yaml").write_text("setting: value")

        # Web files
        (tmp_path / "index.html").write_text("<html></html>")
        (tmp_path / "style.css").write_text("body {}")

        result = await get_project_map(project_root=str(tmp_path))

        # Should detect all languages
        assert result.languages.get("python", 0) == 2
        assert result.languages.get("javascript", 0) == 1
        assert result.languages.get("typescript", 0) == 1
        assert result.languages.get("json", 0) == 1
        assert result.languages.get("yaml", 0) == 1
        assert result.languages.get("html", 0) == 1
        assert result.languages.get("css", 0) == 1

    @pytest.mark.asyncio
    async def test_java_project(self, tmp_path):
        """Test language breakdown detects Java files."""
        (tmp_path / "Main.java").write_text("public class Main {}")
        (tmp_path / "Utils.java").write_text("public class Utils {}")
        (tmp_path / "pom.xml").write_text("<project></project>")  # Not counted

        result = await get_project_map(project_root=str(tmp_path))

        assert result.languages.get("java", 0) == 2

    @pytest.mark.asyncio
    async def test_markdown_documentation(self, tmp_path):
        """Test language breakdown detects Markdown files."""
        docs = tmp_path / "docs"
        docs.mkdir()

        (docs / "README.md").write_text("# Project")
        (docs / "GUIDE.md").write_text("# Guide")
        (tmp_path / "CHANGELOG.md").write_text("# Changes")

        result = await get_project_map(project_root=str(tmp_path))

        assert result.languages.get("markdown", 0) == 3

    @pytest.mark.asyncio
    async def test_yaml_variants(self, tmp_path):
        """Test language breakdown counts both .yaml and .yml."""
        (tmp_path / "config.yaml").write_text("key: value")
        (tmp_path / "settings.yml").write_text("setting: true")

        result = await get_project_map(project_root=str(tmp_path))

        # Both extensions should count as yaml
        assert result.languages.get("yaml", 0) == 2

    @pytest.mark.asyncio
    async def test_empty_project_no_languages(self, tmp_path):
        """Test empty project returns empty languages dict."""
        result = await get_project_map(project_root=str(tmp_path))

        # Should have empty or no entries
        assert result.languages == {} or all(v == 0 for v in result.languages.values())

    @pytest.mark.asyncio
    async def test_nested_language_files(self, tmp_path):
        """Test language detection in nested directories."""
        # Create nested structure
        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text("pass")

        static = tmp_path / "static"
        static.mkdir()
        (static / "app.js").write_text("function() {}")
        (static / "style.css").write_text("body {}")

        templates = tmp_path / "templates"
        templates.mkdir()
        (templates / "index.html").write_text("<html></html>")

        result = await get_project_map(project_root=str(tmp_path))

        assert result.languages.get("python", 0) == 1
        assert result.languages.get("javascript", 0) == 1
        assert result.languages.get("css", 0) == 1
        assert result.languages.get("html", 0) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
