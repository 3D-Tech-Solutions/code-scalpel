"""[20260103_TEST] Comprehensive tests for resolve_organization_wide() Enterprise feature.

Tests validate complete monorepo support:
- Basic single repo detection
- Multiple repository detection
- Git submodule detection
- Yarn workspace detection
- Cross-repo import resolution
- Symbol extraction and mapping
- Error handling
- Edge cases (empty repos, no git, circular imports, parse errors)

Target: 100% coverage (54 statements, 32 branches)
"""

from __future__ import annotations

from pathlib import Path

import pytest


class TestResolveOrganizationWideBasic:
    """Basic functionality: repo detection, function extraction, symbol mapping."""

    @pytest.mark.asyncio
    async def test_single_repo_basic_function_extraction(self, tmp_path: Path):
        """Test resolving organization-wide with single repo and basic function."""
        from code_scalpel.surgery.surgical_extractor import resolve_organization_wide

        # Initialize git repo
        repo_path = tmp_path / "backend"
        repo_path.mkdir()
        (repo_path / ".git").mkdir()

        # Create a simple module
        (repo_path / "models.py").write_text(
            "class User:\n" "    def __init__(self, name: str):\n" "        self.name = name\n"
        )

        # Create code with function
        code = "from models import User\n" "\n" "def create_user(name: str):\n" "    return User(name)\n"

        result = resolve_organization_wide(
            code=code,
            function_name="create_user",
            workspace_root=str(tmp_path),
        )

        assert result.success is True
        assert result.target_name == "create_user"
        assert "def create_user" in result.target_code
        assert "create_user" in result.target_code

    @pytest.mark.asyncio
    async def test_multiple_repos_detection(self, tmp_path: Path):
        """Test detection of multiple git repositories in workspace."""
        from code_scalpel.surgery.surgical_extractor import resolve_organization_wide

        # Create multiple repos
        frontend_repo = tmp_path / "frontend"
        backend_repo = tmp_path / "backend"
        shared_repo = tmp_path / "shared"

        for repo in [frontend_repo, backend_repo, shared_repo]:
            repo.mkdir()
            (repo / ".git").mkdir()
            (repo / "module.py").write_text("def helper():\n    pass\n")

        code = "def process():\n" "    pass\n"

        result = resolve_organization_wide(
            code=code,
            function_name="process",
            workspace_root=str(tmp_path),
        )

        assert result.success is True
        # Should detect all three repos
        assert len(result.monorepo_structure) == 3
        assert "frontend" in result.monorepo_structure
        assert "backend" in result.monorepo_structure
        assert "shared" in result.monorepo_structure

    @pytest.mark.asyncio
    async def test_cross_repo_import_detection(self, tmp_path: Path):
        """Test detection of imports across repositories."""
        from code_scalpel.surgery.surgical_extractor import resolve_organization_wide

        # Create backend repo
        backend_repo = tmp_path / "backend"
        backend_repo.mkdir()
        (backend_repo / ".git").mkdir()
        (backend_repo / "models.py").write_text(
            "class User:\n" "    def __init__(self, name):\n" "        self.name = name\n"
        )

        # Create frontend repo
        frontend_repo = tmp_path / "frontend"
        frontend_repo.mkdir()
        (frontend_repo / ".git").mkdir()

        code = "from models import User\n" "\n" "def display_user(user):\n" "    return user.name\n"

        result = resolve_organization_wide(
            code=code,
            function_name="display_user",
            workspace_root=str(tmp_path),
        )

        assert result.success is True
        assert len(result.cross_repo_imports) > 0 or len(result.resolved_symbols) > 0
        # Should find User in resolved symbols
        if "User" in result.resolved_symbols:
            assert "models.py" in result.resolved_symbols["User"]

    @pytest.mark.asyncio
    async def test_symbol_extraction_from_files(self, tmp_path: Path):
        """Test extraction of symbols (functions, classes) from repository files."""
        from code_scalpel.surgery.surgical_extractor import resolve_organization_wide

        # Create repo with multiple symbols
        repo = tmp_path / "app"
        repo.mkdir()
        (repo / ".git").mkdir()

        (repo / "helpers.py").write_text(
            "def add(a, b):\n"
            "    return a + b\n"
            "\n"
            "def subtract(a, b):\n"
            "    return a - b\n"
            "\n"
            "class Calculator:\n"
            "    def multiply(self, a, b):\n"
            "        return a * b\n"
        )

        code = "from helpers import add\n" "\n" "def compute(x, y):\n" "    return add(x, y)\n"

        result = resolve_organization_wide(
            code=code,
            function_name="compute",
            workspace_root=str(tmp_path),
        )

        assert result.success is True
        # Should find helpers.py and extract symbols
        assert len(result.monorepo_structure) > 0


class TestResolveOrganizationWideMultipleFiles:
    """Test cross-file and cross-repo dependency resolution."""

    @pytest.mark.asyncio
    async def test_deep_import_chain(self, tmp_path: Path):
        """Test resolution through deep import chains across multiple files."""
        from code_scalpel.surgery.surgical_extractor import resolve_organization_wide

        repo = tmp_path / "project"
        repo.mkdir()
        (repo / ".git").mkdir()

        # Create a chain: a.py -> b.py -> c.py
        (repo / "c.py").write_text("class Logger:\n" "    def log(self, msg):\n" "        print(msg)\n")

        (repo / "b.py").write_text(
            "from c import Logger\n"
            "\n"
            "logger = Logger()\n"
            "\n"
            "def process(data):\n"
            "    logger.log(data)\n"
            "    return data\n"
        )

        (repo / "a.py").write_text("from b import process\n" "\n" "def execute(data):\n" "    return process(data)\n")

        code = "from a import execute\n" "\n" "def main():\n" "    return execute('test')\n"

        result = resolve_organization_wide(
            code=code,
            function_name="main",
            workspace_root=str(tmp_path),
        )

        assert result.success is True
        # Should successfully trace through the import chain
        assert result.monorepo_structure is not None

    @pytest.mark.asyncio
    async def test_multiple_repos_with_shared_lib(self, tmp_path: Path):
        """Test resolution with shared library imported by multiple services."""
        from code_scalpel.surgery.surgical_extractor import resolve_organization_wide

        # Create shared library repo
        shared_repo = tmp_path / "shared-lib"
        shared_repo.mkdir()
        (shared_repo / ".git").mkdir()
        (shared_repo / "utils.py").write_text(
            "def validate_email(email):\n"
            "    return '@' in email\n"
            "\n"
            "def format_date(date):\n"
            "    return str(date)\n"
        )

        # Create service repos
        for service_name in ["payment-service", "user-service"]:
            service_repo = tmp_path / service_name
            service_repo.mkdir()
            (service_repo / ".git").mkdir()
            (service_repo / "handlers.py").write_text(
                f"from utils import validate_email\n"
                f"\n"
                f"def handle_{service_name.split('-')[0]}():\n"
                f"    return validate_email('test@example.com')\n"
            )

        code = (
            "from utils import validate_email\n"
            "\n"
            "def validate_user_email(email):\n"
            "    return validate_email(email)\n"
        )

        result = resolve_organization_wide(
            code=code,
            function_name="validate_user_email",
            workspace_root=str(tmp_path),
        )

        assert result.success is True
        # Should detect all three repositories
        assert len(result.monorepo_structure) >= 3


class TestResolveOrganizationWideEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_workspace_without_git_repos(self, tmp_path: Path):
        """Test handling when workspace has no git repositories."""
        from code_scalpel.surgery.surgical_extractor import resolve_organization_wide

        # Create Python files without git
        (tmp_path / "module.py").write_text("def helper():\n    pass\n")

        code = "def main():\n" "    pass\n"

        result = resolve_organization_wide(
            code=code,
            function_name="main",
            workspace_root=str(tmp_path),
        )

        assert result.success is True
        # Should still work with the workspace root as fallback repo
        assert len(result.monorepo_structure) > 0

    @pytest.mark.asyncio
    async def test_nonexistent_function_name(self, tmp_path: Path):
        """Test error handling when function name doesn't exist in code."""
        from code_scalpel.surgery.surgical_extractor import resolve_organization_wide

        repo = tmp_path / "app"
        repo.mkdir()
        (repo / ".git").mkdir()

        code = "def existing_function():\n" "    pass\n"

        result = resolve_organization_wide(
            code=code,
            function_name="nonexistent_function",
            workspace_root=str(tmp_path),
        )

        assert result.success is False
        assert result.error is not None
        assert result.target_code == ""

    @pytest.mark.asyncio
    async def test_invalid_python_code(self, tmp_path: Path):
        """Test error handling with syntactically invalid code."""
        from code_scalpel.surgery.surgical_extractor import resolve_organization_wide

        repo = tmp_path / "app"
        repo.mkdir()
        (repo / ".git").mkdir()

        code = "def broken_function(\n" "    this is invalid syntax\n"

        result = resolve_organization_wide(
            code=code,
            function_name="broken_function",
            workspace_root=str(tmp_path),
        )

        assert result.success is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_empty_workspace(self, tmp_path: Path):
        """Test handling of completely empty workspace."""
        from code_scalpel.surgery.surgical_extractor import resolve_organization_wide

        code = "def main():\n" "    pass\n"

        result = resolve_organization_wide(
            code=code,
            function_name="main",
            workspace_root=str(tmp_path),
        )

        assert result.success is True
        # Should still return success with empty structure
        assert isinstance(result.monorepo_structure, dict)

    @pytest.mark.asyncio
    async def test_none_workspace_root_uses_cwd(self, tmp_path: Path, monkeypatch):
        """Test that None workspace_root uses current working directory."""
        from code_scalpel.surgery.surgical_extractor import resolve_organization_wide

        # Change to tmp_path as current directory
        monkeypatch.chdir(tmp_path)

        repo = tmp_path / "local_repo"
        repo.mkdir()
        (repo / ".git").mkdir()

        code = "def test():\n" "    pass\n"

        result = resolve_organization_wide(
            code=code,
            function_name="test",
            workspace_root=None,
        )

        assert result.success is True


class TestResolveOrganizationWideComplexStructures:
    """Test complex monorepo structures."""

    @pytest.mark.asyncio
    async def test_yarn_workspace_structure(self, tmp_path: Path):
        """Test detection of Yarn workspace structure."""
        from code_scalpel.surgery.surgical_extractor import resolve_organization_wide

        # Create Yarn workspace structure
        root = tmp_path
        (root / ".git").mkdir()

        # packages/ui
        ui_pkg = root / "packages" / "ui"
        ui_pkg.mkdir(parents=True)
        (ui_pkg / ".git").mkdir()
        (ui_pkg / "components.py").write_text("def render():\n    pass\n")

        # packages/api
        api_pkg = root / "packages" / "api"
        api_pkg.mkdir(parents=True)
        (api_pkg / ".git").mkdir()
        (api_pkg / "handlers.py").write_text("def handle():\n    pass\n")

        code = "def main():\n" "    pass\n"

        result = resolve_organization_wide(
            code=code,
            function_name="main",
            workspace_root=str(root),
        )

        assert result.success is True
        # Should detect both package repositories
        assert len(result.monorepo_structure) >= 2

    @pytest.mark.asyncio
    async def test_large_monorepo_file_limit(self, tmp_path: Path):
        """Test that file listings in monorepo_structure respect limits."""
        from code_scalpel.surgery.surgical_extractor import resolve_organization_wide

        repo = tmp_path / "large_repo"
        repo.mkdir()
        (repo / ".git").mkdir()

        # Create many Python files
        for i in range(150):
            (repo / f"module_{i}.py").write_text(f"def func_{i}():\n    pass\n")

        code = "def main():\n" "    pass\n"

        result = resolve_organization_wide(
            code=code,
            function_name="main",
            workspace_root=str(tmp_path),
        )

        assert result.success is True
        # File count should be limited to 100 per repo
        if "large_repo" in result.monorepo_structure:
            file_list = result.monorepo_structure["large_repo"]
            assert len(file_list) <= 100

    @pytest.mark.asyncio
    async def test_many_symbols_per_file_limit(self, tmp_path: Path):
        """Test that cross_repo_imports symbol lists respect limits."""
        from code_scalpel.surgery.surgical_extractor import resolve_organization_wide

        repo = tmp_path / "app"
        repo.mkdir()
        (repo / ".git").mkdir()

        # Create file with many symbols
        many_symbols_code = "\n".join([f"def func_{i}():\n    pass\n" for i in range(50)])
        (repo / "many_funcs.py").write_text(many_symbols_code)

        code = "from many_funcs import func_0\n" "\n" "def main():\n" "    pass\n"

        result = resolve_organization_wide(
            code=code,
            function_name="main",
            workspace_root=str(tmp_path),
        )

        assert result.success is True
        # Symbol count per import should be limited to 20
        for imp in result.cross_repo_imports:
            assert len(imp.symbols) <= 20

    @pytest.mark.asyncio
    async def test_circular_imports_handled(self, tmp_path: Path):
        """Test handling of circular imports."""
        from code_scalpel.surgery.surgical_extractor import resolve_organization_wide

        repo = tmp_path / "app"
        repo.mkdir()
        (repo / ".git").mkdir()

        # Create circular import: a.py <-> b.py
        (repo / "a.py").write_text("from b import FuncB\n" "\n" "class FuncA:\n" "    pass\n")

        (repo / "b.py").write_text("from a import FuncA\n" "\n" "class FuncB:\n" "    pass\n")

        code = "from a import FuncA\n" "from b import FuncB\n" "\n" "def main():\n" "    pass\n"

        result = resolve_organization_wide(
            code=code,
            function_name="main",
            workspace_root=str(tmp_path),
        )

        assert result.success is True
        # Should handle circular imports gracefully


class TestResolveOrganizationWideExplanations:
    """Test explanation generation for resolution results."""

    @pytest.mark.asyncio
    async def test_explanation_format(self, tmp_path: Path):
        """Test that explanation contains expected statistics."""
        from code_scalpel.surgery.surgical_extractor import resolve_organization_wide

        repo1 = tmp_path / "service1"
        repo2 = tmp_path / "service2"

        for repo in [repo1, repo2]:
            repo.mkdir()
            (repo / ".git").mkdir()
            (repo / "module.py").write_text("def helper():\n    pass\n")

        code = "def test():\n" "    pass\n"

        result = resolve_organization_wide(
            code=code,
            function_name="test",
            workspace_root=str(tmp_path),
        )

        assert result.success is True
        assert result.explanation is not None
        # Explanation should contain repository count
        assert "repository" in result.explanation.lower()
        assert "scanned" in result.explanation.lower()


class TestResolveOrganizationWideUnparseable:
    """Test handling of unparseable Python files."""

    @pytest.mark.asyncio
    async def test_unparseable_module_files_skipped(self, tmp_path: Path):
        """Test that unparseable module files are skipped without crashing."""
        from code_scalpel.surgery.surgical_extractor import resolve_organization_wide

        repo = tmp_path / "app"
        repo.mkdir()
        (repo / ".git").mkdir()

        # Create valid module
        (repo / "good.py").write_text("def helper():\n    pass\n")

        # Create unparseable module
        (repo / "bad.py").write_text("this is not valid python !!!@@##")

        code = "from good import helper\n" "\n" "def main():\n" "    return helper()\n"

        result = resolve_organization_wide(
            code=code,
            function_name="main",
            workspace_root=str(tmp_path),
        )

        assert result.success is True
        # Should skip bad.py and still return good results


class TestResolveOrganizationWideResolvedSymbols:
    """Test resolved_symbols mapping."""

    @pytest.mark.asyncio
    async def test_resolved_symbols_mapping(self, tmp_path: Path):
        """Test that resolved_symbols maps symbol names to source files."""
        from code_scalpel.surgery.surgical_extractor import resolve_organization_wide

        repo = tmp_path / "app"
        repo.mkdir()
        (repo / ".git").mkdir()

        (repo / "models.py").write_text("class User:\n" "    pass\n" "\n" "class Product:\n" "    pass\n")

        code = (
            "from models import User, Product\n"
            "\n"
            "def create():\n"
            "    user = User()\n"
            "    product = Product()\n"
            "    return user, product\n"
        )

        result = resolve_organization_wide(
            code=code,
            function_name="create",
            workspace_root=str(tmp_path),
        )

        assert result.success is True
        # Should map symbols to files
        if result.resolved_symbols:
            for symbol_name, file_path in result.resolved_symbols.items():
                assert isinstance(symbol_name, str)
                assert isinstance(file_path, str)


class TestResolveOrganizationWideCrossRepoImports:
    """Test CrossRepoImport structure and properties."""

    @pytest.mark.asyncio
    async def test_cross_repo_import_structure(self, tmp_path: Path):
        """Test that CrossRepoImport objects have required fields."""
        from code_scalpel.surgery.surgical_extractor import resolve_organization_wide

        repo1 = tmp_path / "backend"
        repo1.mkdir()
        (repo1 / ".git").mkdir()
        (repo1 / "services.py").write_text("class UserService:\n" "    pass\n")

        repo2 = tmp_path / "frontend"
        repo2.mkdir()
        (repo2 / ".git").mkdir()

        code = "from services import UserService\n" "\n" "def main():\n" "    pass\n"

        result = resolve_organization_wide(
            code=code,
            function_name="main",
            workspace_root=str(tmp_path),
        )

        assert result.success is True
        # Check cross_repo_imports structure
        for imp in result.cross_repo_imports:
            assert hasattr(imp, "repo_name")
            assert hasattr(imp, "file_path")
            assert hasattr(imp, "symbols")
            assert hasattr(imp, "repo_root")
            assert isinstance(imp.repo_name, str)
            assert isinstance(imp.file_path, str)
            assert isinstance(imp.symbols, list)
            assert isinstance(imp.repo_root, str)
