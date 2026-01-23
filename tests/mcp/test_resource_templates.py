"""
Tests for Resource Template feature.

[20251216_FEATURE] v2.0.2 - Tests for code:/// URI resource templates.
"""

import tempfile
from pathlib import Path

import pytest


class TestModuleResolution:
    """Tests for module path resolution."""

    def test_resolve_python_module(self):
        """Test resolving Python module names to file paths."""
        from code_scalpel.mcp.module_resolver import resolve_module_path

        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # Create test files
            (project_root / "utils.py").write_text("# utils module")
            (project_root / "services").mkdir()
            (project_root / "services" / "auth.py").write_text("# auth service")

            # Test direct module
            result = resolve_module_path("python", "utils", project_root)
            assert result is not None
            assert result.name == "utils.py"

            # Test nested module
            result = resolve_module_path("python", "services.auth", project_root)
            assert result is not None
            assert result.name == "auth.py"

    def test_resolve_typescript_module(self):
        """Test resolving TypeScript module names to file paths."""
        from code_scalpel.mcp.module_resolver import resolve_module_path

        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # Create test files
            (project_root / "components").mkdir()
            (project_root / "components" / "UserCard.tsx").write_text("export function UserCard() {}")

            result = resolve_module_path("typescript", "components/UserCard", project_root)
            assert result is not None
            assert result.name == "UserCard.tsx"

    def test_resolve_javascript_module(self):
        """Test resolving JavaScript module names to file paths."""
        from code_scalpel.mcp.module_resolver import resolve_module_path

        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # Create test files
            (project_root / "lib").mkdir()
            (project_root / "lib" / "helpers.js").write_text("export const add = () => {}")

            result = resolve_module_path("javascript", "lib/helpers", project_root)
            assert result is not None
            assert result.name == "helpers.js"

    def test_resolve_java_module(self):
        """Test resolving Java module names to file paths."""
        from code_scalpel.mcp.module_resolver import resolve_module_path

        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # Create test files
            (project_root / "services").mkdir()
            (project_root / "services" / "AuthService.java").write_text("public class AuthService {}")

            result = resolve_module_path("java", "services.AuthService", project_root)
            assert result is not None
            assert result.name == "AuthService.java"

    def test_resolve_module_not_found(self):
        """Test module resolution when file doesn't exist."""
        from code_scalpel.mcp.module_resolver import resolve_module_path

        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            result = resolve_module_path("python", "nonexistent", project_root)
            assert result is None


class TestMimeTypes:
    """Tests for MIME type resolution."""

    def test_get_mime_type_python(self):
        """Test getting MIME type for Python."""
        from code_scalpel.mcp.module_resolver import get_mime_type

        assert get_mime_type("python") == "text/x-python"

    def test_get_mime_type_typescript(self):
        """Test getting MIME type for TypeScript."""
        from code_scalpel.mcp.module_resolver import get_mime_type

        assert get_mime_type("typescript") == "text/x-typescript"
        assert get_mime_type("tsx") == "text/x-tsx"

    def test_get_mime_type_javascript(self):
        """Test getting MIME type for JavaScript."""
        from code_scalpel.mcp.module_resolver import get_mime_type

        assert get_mime_type("javascript") == "text/javascript"
        assert get_mime_type("jsx") == "text/x-jsx"

    def test_get_mime_type_java(self):
        """Test getting MIME type for Java."""
        from code_scalpel.mcp.module_resolver import get_mime_type

        assert get_mime_type("java") == "text/x-java"


class TestCodeResourceTemplate:
    """Tests for code:/// resource template."""

    @pytest.mark.asyncio
    async def test_code_resource_python(self):
        """Test accessing Python code via code:/// URI."""
        import json

        from code_scalpel.mcp.server import PROJECT_ROOT, get_code_resource

        with tempfile.TemporaryDirectory() as tmpdir:
            # Temporarily change PROJECT_ROOT and ALLOWED_ROOTS
            original_root = PROJECT_ROOT
            from code_scalpel.mcp import server

            original_allowed_roots = server.ALLOWED_ROOTS

            server.PROJECT_ROOT = Path(tmpdir)
            server.ALLOWED_ROOTS = [Path(tmpdir)]  # Reset to temp dir

            try:
                # Create test file
                test_file = Path(tmpdir) / "utils.py"
                test_file.write_text('''
def calculate_tax(amount):
    """Calculate tax."""
    return amount * 0.1
''')

                # Test resource access
                result_json = await get_code_resource("python", "utils", "calculate_tax")
                result = json.loads(result_json)

                assert "error" not in result
                assert result["uri"] == "code:///python/utils/calculate_tax"
                assert result["mimeType"] == "text/x-python"
                assert "calculate_tax" in result["code"]
                assert result["metadata"]["language"] == "python"
                assert result["metadata"]["module"] == "utils"
                assert result["metadata"]["symbol"] == "calculate_tax"

            finally:
                server.PROJECT_ROOT = original_root
                server.ALLOWED_ROOTS = original_allowed_roots

    @pytest.mark.asyncio
    async def test_code_resource_typescript(self):
        """Test accessing TypeScript code via code:/// URI."""
        import json

        from code_scalpel.mcp.server import get_code_resource

        with tempfile.TemporaryDirectory() as tmpdir:
            from code_scalpel.mcp import server

            original_root = server.PROJECT_ROOT
            original_allowed_roots = server.ALLOWED_ROOTS
            server.PROJECT_ROOT = Path(tmpdir)
            server.ALLOWED_ROOTS = [Path(tmpdir)]  # Reset to temp dir

            try:
                # Create test file
                components_dir = Path(tmpdir) / "components"
                components_dir.mkdir()
                test_file = components_dir / "Button.tsx"
                test_file.write_text("""
export function Button({ label }: { label: string }) {
  return <button>{label}</button>;
}
""")

                # Test resource access
                result_json = await get_code_resource("typescript", "components/Button", "Button")
                result = json.loads(result_json)

                assert "error" not in result
                assert result["uri"] == "code:///typescript/components/Button/Button"
                assert result["mimeType"] == "text/x-typescript"
                assert "Button" in result["code"]
                assert result["metadata"]["jsx_normalized"] is True
                assert result["metadata"]["component_type"] == "functional"

            finally:
                server.PROJECT_ROOT = original_root
                server.ALLOWED_ROOTS = original_allowed_roots

    @pytest.mark.asyncio
    async def test_code_resource_module_not_found(self):
        """Test error handling when module doesn't exist."""
        import json

        from code_scalpel.mcp.server import get_code_resource

        with tempfile.TemporaryDirectory() as tmpdir:
            from code_scalpel.mcp import server

            original_root = server.PROJECT_ROOT
            server.PROJECT_ROOT = Path(tmpdir)

            try:
                result_json = await get_code_resource("python", "nonexistent", "func")
                result = json.loads(result_json)

                assert "error" in result
                assert "not found" in result["error"].lower()

            finally:
                server.PROJECT_ROOT = original_root

    @pytest.mark.asyncio
    async def test_code_resource_symbol_not_found(self):
        """Test error handling when symbol doesn't exist."""
        import json

        from code_scalpel.mcp.server import get_code_resource

        with tempfile.TemporaryDirectory() as tmpdir:
            from code_scalpel.mcp import server

            original_root = server.PROJECT_ROOT
            server.PROJECT_ROOT = Path(tmpdir)

            try:
                # Create test file
                test_file = Path(tmpdir) / "utils.py"
                test_file.write_text("def foo(): pass")

                result_json = await get_code_resource("python", "utils", "nonexistent")
                result = json.loads(result_json)

                assert "error" in result

            finally:
                server.PROJECT_ROOT = original_root
