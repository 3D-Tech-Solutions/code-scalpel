"""Pytest fixtures for get_project_map tests.

Provides:
- Tier-aware server mocks (community/pro/enterprise)
- Test project templates (small/large/huge projects)
- Helper validation functions

[20260103_TEST] v3.3.1 - Project map tier testing fixtures
"""

from unittest.mock import patch

import pytest

# ====================
# MCP Server Fixtures
# ====================


@pytest.fixture
def community_server():
    """MCP server with Community tier license (mocked)."""
    from code_scalpel.mcp.server import get_project_map

    class MockCommunityServer:
        def __init__(self):
            self._tier = "community"

        async def get_project_map(self, **kwargs):
            """Community tier: max_files=100, max_modules=50."""
            # Mock tier detection to return 'community'
            with patch("code_scalpel.mcp.server._get_current_tier", return_value="community"):
                return await get_project_map(**kwargs)

    return MockCommunityServer()


@pytest.fixture
def pro_server():
    """MCP server with Pro tier license (mocked)."""
    from code_scalpel.mcp.server import get_project_map

    class MockProServer:
        def __init__(self):
            self._tier = "pro"

        async def get_project_map(self, **kwargs):
            """Pro tier: max_files=1000, max_modules=200."""
            with patch("code_scalpel.mcp.server._get_current_tier", return_value="pro"):
                return await get_project_map(**kwargs)

    return MockProServer()


@pytest.fixture
def enterprise_server():
    """MCP server with Enterprise tier license (mocked)."""
    from code_scalpel.mcp.server import get_project_map

    class MockEnterpriseServer:
        def __init__(self):
            self._tier = "enterprise"

        async def get_project_map(self, **kwargs):
            """Enterprise tier: Unlimited files, max_modules=1000."""
            with patch("code_scalpel.mcp.server._get_current_tier", return_value="enterprise"):
                return await get_project_map(**kwargs)

    return MockEnterpriseServer()


# ====================
# Test Project Fixtures
# ====================


@pytest.fixture
def simple_project(tmp_path):
    """Simple project with 5 files."""
    # Create structure:
    # simple_project/
    #   main.py
    #   utils.py
    #   pkg/
    #     __init__.py
    #     module_a.py
    #     module_b.py

    root = tmp_path / "simple_project"
    root.mkdir()

    (root / "main.py").write_text("def main(): pass")
    (root / "utils.py").write_text("def helper(): pass")

    pkg = root / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "module_a.py").write_text("def func_a(): pass")
    (pkg / "module_b.py").write_text("def func_b(): pass")

    return root


@pytest.fixture
def project_120_files(tmp_path):
    """Project with 120 Python files (exceeds Community limit of 100)."""
    root = tmp_path / "large_project"
    root.mkdir()

    # Create 120 Python files
    for i in range(120):
        (root / f"module_{i:03d}.py").write_text(f"def func_{i}(): pass")

    return root


@pytest.fixture
def project_60_modules(tmp_path):
    """Project with 60 modules (exceeds Community limit of 50)."""
    root = tmp_path / "many_modules"
    root.mkdir()

    # Create 60 modules across 6 packages (10 each)
    for pkg_idx in range(6):
        pkg = root / f"package_{pkg_idx}"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")

        for mod_idx in range(10):
            (pkg / f"module_{mod_idx}.py").write_text("def func(): pass")

    return root


@pytest.fixture
def project_1200_files(tmp_path):
    """Project with 1200 Python files (exceeds Pro limit of 1000)."""
    root = tmp_path / "huge_project"
    root.mkdir()

    # Create 1200 files in batches
    for batch in range(12):
        batch_dir = root / f"batch_{batch}"
        batch_dir.mkdir()
        for i in range(100):
            (batch_dir / f"module_{i:03d}.py").write_text(f"def func_{i}(): pass")

    return root


@pytest.fixture
def project_250_modules(tmp_path):
    """Project with 250 modules (exceeds Pro limit of 200)."""
    root = tmp_path / "many_modules_pro"
    root.mkdir()

    # Create 250 modules across 25 packages (10 each)
    for pkg_idx in range(25):
        pkg = root / f"package_{pkg_idx}"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")

        for mod_idx in range(10):
            (pkg / f"module_{mod_idx}.py").write_text("def func(): pass")

    return root


@pytest.fixture
def huge_project_5000(tmp_path):
    """Huge project with 5000 Python files (Enterprise scale)."""
    root = tmp_path / "enterprise_scale"
    root.mkdir()

    # Create 5000 files in 50 batches
    for batch in range(50):
        batch_dir = root / f"batch_{batch}"
        batch_dir.mkdir()
        for i in range(100):
            (batch_dir / f"module_{i:03d}.py").write_text(f"def func_{i}(): pass")

    return root


@pytest.fixture
def project_2000_modules(tmp_path):
    """Project with 2000 modules (exceeds Enterprise limit of 1000)."""
    root = tmp_path / "ultra_modules"
    root.mkdir()

    # Create 2000 modules across 200 packages (10 each)
    for pkg_idx in range(200):
        pkg = root / f"package_{pkg_idx}"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")

        for mod_idx in range(10):
            (pkg / f"module_{mod_idx}.py").write_text("def func(): pass")

    return root


@pytest.fixture
def project_with_complexity(tmp_path):
    """Project with files of varying complexity."""
    root = tmp_path / "complexity_project"
    root.mkdir()

    # Low complexity
    (root / "simple.py").write_text("""
def simple_function():
    return 42
""")

    # High complexity (cyclomatic complexity ~15)
    (root / "complex.py").write_text("""
def complex_function(x, y, z):
    if x > 10:
        if y > 20:
            if z > 30:
                return x + y + z
            elif z > 25:
                return x + y
            else:
                return x
        elif y > 15:
            return y + z
        else:
            return y
    elif x > 5:
        if y > 10:
            return x * y
        else:
            return x
    else:
        return 0
""")

    return root


@pytest.fixture
def flask_project(tmp_path):
    """Flask-like project structure for architectural layer detection."""
    root = tmp_path / "flask_app"
    root.mkdir()

    # Presentation layer
    (root / "app.py").write_text("""
from flask import Flask, request
app = Flask(__name__)

@app.route('/')
def index():
    return "Hello"
""")

    # Business layer
    services = root / "services"
    services.mkdir()
    (services / "__init__.py").write_text("")
    (services / "order_service.py").write_text("""
def process_order(order_data):
    pass
""")

    # Data layer
    models = root / "models"
    models.mkdir()
    (models / "__init__.py").write_text("")
    (models / "order.py").write_text("""
class Order:
    pass
""")

    return root


# ====================
# License Mock Fixtures
# ====================


@pytest.fixture
def server_expired_license():
    """Server with expired license (should fallback to Community)."""
    from code_scalpel.mcp.server import get_project_map

    class MockExpiredServer:
        def __init__(self):
            self._tier = "community"  # Fallback tier

        async def get_project_map(self, **kwargs):
            # Mock expired license scenario
            with patch("code_scalpel.mcp.server._get_current_tier", return_value="community"):
                result = await get_project_map(**kwargs)
                # Add warning about expired license
                if not hasattr(result, "warnings"):
                    result.warnings = []
                result.warnings.append("License expired. Defaulting to Community tier.")
                return result

    return MockExpiredServer()


@pytest.fixture
def server_invalid_license():
    """Server with invalid license (should fallback to Community)."""
    from code_scalpel.mcp.server import get_project_map

    class MockInvalidServer:
        def __init__(self):
            self._tier = "community"

        async def get_project_map(self, **kwargs):
            with patch("code_scalpel.mcp.server._get_current_tier", return_value="community"):
                result = await get_project_map(**kwargs)
                if not hasattr(result, "warnings"):
                    result.warnings = []
                result.warnings.append("Invalid license. Defaulting to Community tier.")
                return result

    return MockInvalidServer()


@pytest.fixture
def server_no_license():
    """Server with no license file (should default to Community)."""
    from code_scalpel.mcp.server import get_project_map

    class MockNoLicenseServer:
        def __init__(self):
            self._tier = "community"

        async def get_project_map(self, **kwargs):
            with patch("code_scalpel.mcp.server._get_current_tier", return_value="community"):
                return await get_project_map(**kwargs)

    return MockNoLicenseServer()


# ====================
# Helper Functions
# ====================


def count_modules(result):
    """Count total modules in result."""
    return len(result.modules)


def count_packages(result):
    """Count total packages in result."""
    return len(result.packages)


def has_pro_features(result):
    """Check if result has Pro-tier features."""
    # Pro features: coupling_metrics, git_ownership, architectural_layers
    data = result.model_dump() if hasattr(result, "model_dump") else vars(result)
    return any(
        key in data and data[key] not in [None, [], {}, ""]
        for key in ["coupling_metrics", "git_ownership", "architectural_layers"]
    )


def has_enterprise_features(result):
    """Check if result has Enterprise-tier features."""
    # Enterprise features: city_map_data, compliance_overlay, multi_repo_summary
    data = result.model_dump() if hasattr(result, "model_dump") else vars(result)
    return any(
        key in data and data[key] not in [None, [], {}, ""]
        for key in [
            "city_map_data",
            "compliance_overlay",
            "multi_repo_summary",
            "force_graph",
            "churn_heatmap",
            "bug_hotspots",
        ]
    )
