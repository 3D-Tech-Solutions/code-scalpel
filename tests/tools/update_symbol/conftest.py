# [20260103_TEST] Fixtures and factories for update_symbol tier tests
# [20260105_REFACTOR] Import real tier fixtures from tests/tools/tiers/conftest.py
"""
Shared test fixtures for update_symbol testing across all tiers.
Provides:
- File creation and cleanup
- License/JWT generation (now using REAL JWT files)
- Mock update operations
- Tier configuration (using real tier fixtures)

[20260105_REFACTOR] Now imports pro_tier, enterprise_tier, community_tier
fixtures from tests/tools/tiers/conftest.py which use real JWT licenses.

[20260108_BUGFIX] Removed pytest_plugins declaration - moved to top-level conftest.py
"""

from datetime import datetime, timedelta
from pathlib import Path

import pytest

# =============================================================================
# Real Tier Fixtures (copied from tests/tools/tiers/conftest.py)
# =============================================================================


@pytest.fixture(autouse=True)
def clear_tier_cache():
    """
    Clear tier detection cache and session state before and after each test.
    """
    # Clear the JWT validation cache BEFORE test
    from code_scalpel.licensing import jwt_validator

    jwt_validator._LICENSE_VALIDATION_CACHE = None

    # Clear the config loader cache BEFORE test
    from code_scalpel.licensing import config_loader

    config_loader.clear_cache()

    # Also reset any module-level state in server
    from code_scalpel.mcp import server

    # Clear any cached tier detection
    if hasattr(server, "_cached_tier"):
        server._cached_tier = None

    # Clear session update limits (the actual variable name is _SESSION_UPDATE_COUNTS)
    if hasattr(server, "_SESSION_UPDATE_COUNTS"):
        server._SESSION_UPDATE_COUNTS = {}

    yield

    # Cleanup AFTER test
    jwt_validator._LICENSE_VALIDATION_CACHE = None
    config_loader.clear_cache()
    if hasattr(server, "_cached_tier"):
        server._cached_tier = None
    if hasattr(server, "_SESSION_UPDATE_COUNTS"):
        server._SESSION_UPDATE_COUNTS = {}


# Paths to test license files (relative to project root)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
PRO_LICENSE_PATH = PROJECT_ROOT / "tests/licenses/pro.license.jwt"
ENTERPRISE_LICENSE_PATH = PROJECT_ROOT / "tests/licenses/enterprise.license.jwt"

# Fallback to archive if tests/licenses doesn't have valid ones
ARCHIVE_PRO_LICENSE = PROJECT_ROOT / ".code-scalpel/archive/code_scalpel_license_pro_final_test_pro_1766982522.jwt"


def _find_valid_license(tier: str) -> Path | None:
    """Find a valid license file for the given tier."""
    from code_scalpel.licensing.jwt_validator import JWTLicenseValidator

    validator = JWTLicenseValidator()

    # Check standard test locations
    if tier == "pro":
        candidates = [
            PRO_LICENSE_PATH,
            PROJECT_ROOT / "tests/licenses/code_scalpel_license_pro_20260101_170435.jwt",
            ARCHIVE_PRO_LICENSE,
        ]
    elif tier == "enterprise":
        candidates = [
            ENTERPRISE_LICENSE_PATH,
            PROJECT_ROOT / "tests/licenses/code_scalpel_license_enterprise_20260101_170506.jwt",
        ]
    else:
        return None

    for path in candidates:
        if path.exists():
            try:
                token = path.read_text().strip()
                result = validator.validate_token(token)
                if result.is_valid and result.tier == tier:
                    return path
            except Exception:
                continue

    return None


@pytest.fixture
def pro_tier(monkeypatch):
    """
    Fixture that sets up Pro tier for testing.

    Uses a real license file if available, otherwise mocks _get_current_tier().
    """
    from code_scalpel.mcp import server

    license_path = _find_valid_license("pro")

    if license_path:
        # Use real license via env var
        monkeypatch.setenv("CODE_SCALPEL_LICENSE_PATH", str(license_path))
    else:
        # Fallback to mock - this is acceptable for tier feature testing
        monkeypatch.setattr(server, "_get_current_tier", lambda: "pro")

    yield {
        "tier": "pro",
        "license_path": license_path,
        "is_mocked": license_path is None,
    }


@pytest.fixture
def enterprise_tier(monkeypatch):
    """
    Fixture that sets up Enterprise tier for testing.

    Uses a real license file if available, otherwise mocks _get_current_tier().
    """
    from code_scalpel.mcp import server

    license_path = _find_valid_license("enterprise")

    if license_path:
        # Use real license via env var
        monkeypatch.setenv("CODE_SCALPEL_LICENSE_PATH", str(license_path))
    else:
        # Fallback to mock - this is acceptable for tier feature testing
        monkeypatch.setattr(server, "_get_current_tier", lambda: "enterprise")

    yield {
        "tier": "enterprise",
        "license_path": license_path,
        "is_mocked": license_path is None,
    }


@pytest.fixture
def community_tier(monkeypatch):
    """
    Fixture that sets up Community tier for testing.

    Ensures no license is loaded by disabling license discovery.
    """
    # Disable license discovery to ensure community tier
    monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")

    yield {"tier": "community", "license_path": None, "is_mocked": False}


# =============================================================================
# File Fixtures
# =============================================================================


@pytest.fixture
def temp_python_file(tmp_path):
    """Create a temporary Python file with sample code."""
    py_file = tmp_path / "sample.py"
    py_file.write_text("""
def add_numbers(a, b):
    '''Add two numbers.'''
    return a + b

def calculate_tax(amount, rate=0.1):
    '''Calculate tax.'''
    return amount * rate

class Calculator:
    '''Simple calculator.'''

    def multiply(self, x, y):
        '''Multiply two numbers.'''
        return x * y
""")
    return py_file


@pytest.fixture
def temp_js_file(tmp_path):
    """Create a temporary JavaScript file with sample code."""
    js_file = tmp_path / "sample.js"
    js_file.write_text("""
function addNumbers(a, b) {
    // Add two numbers
    return a + b;
}

function calculateTax(amount, rate = 0.1) {
    // Calculate tax
    return amount * rate;
}

class Calculator {
    // Simple calculator

    multiply(x, y) {
        // Multiply two numbers
        return x * y;
    }
}
""")
    return js_file


@pytest.fixture
def temp_multifile_project(tmp_path):
    """Create a temporary project with multiple files."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    # File 1: utils.py
    utils_file = src_dir / "utils.py"
    utils_file.write_text("""
def calculate_discount(price, rate=0.1):
    '''Calculate discount.'''
    return price * (1 - rate)

def validate_price(price):
    '''Validate price.'''
    return price > 0
""")

    # File 2: services.py
    services_file = src_dir / "services.py"
    services_file.write_text("""
from utils import calculate_discount

def apply_discount(price):
    '''Apply discount to price.'''
    return calculate_discount(price)

def process_order(items):
    '''Process order.'''
    total = sum(items)
    return apply_discount(total)
""")

    return {"root": tmp_path, "utils": utils_file, "services": services_file}


# =============================================================================
# License/JWT Fixtures
# =============================================================================


@pytest.fixture
def mock_community_license():
    """Generate mock Community tier license token."""
    # Community tier: no license required (or basic token)
    return {
        "tier": "community",
        "max_updates_per_session": 10,
        "features": ["basic_verification"],
        "expires_at": (datetime.now() + timedelta(days=365)).isoformat(),
    }


@pytest.fixture
def mock_pro_license():
    """Generate mock Pro tier license token."""
    return {
        "tier": "pro",
        "max_updates_per_session": -1,  # Unlimited
        "features": [
            "basic_verification",
            "atomic_multifile_updates",
            "rollback_available",
            "import_auto_adjustment",
            "formatting_preserved",
        ],
        "expires_at": (datetime.now() + timedelta(days=365)).isoformat(),
    }


@pytest.fixture
def mock_enterprise_license():
    """Generate mock Enterprise tier license token."""
    return {
        "tier": "enterprise",
        "max_updates_per_session": -1,  # Unlimited
        "features": [
            "basic_verification",
            "atomic_multifile_updates",
            "rollback_available",
            "import_auto_adjustment",
            "formatting_preserved",
            "approval_workflow",
            "compliance_check",
            "audit_trail",
            "policy_enforcement",
        ],
        "expires_at": (datetime.now() + timedelta(days=365)).isoformat(),
    }


@pytest.fixture
def mock_expired_license():
    """Generate mock expired license token."""
    return {
        "tier": "pro",
        "max_updates_per_session": -1,
        "features": ["basic_verification"],
        "expires_at": (datetime.now() - timedelta(days=1)).isoformat(),
    }


@pytest.fixture
def mock_invalid_license():
    """Generate invalid/malformed license token."""
    return "not-a-valid-jwt-token-at-all"


# =============================================================================
# Mock Operation Fixtures
# =============================================================================


@pytest.fixture
def update_result_community():
    """Mock successful Community tier update result."""
    return {
        "success": True,
        "file_path": "/src/utils.py",
        "symbol_name": "calculate_tax",
        "symbol_type": "function",
        "backup_path": "/src/utils.py.bak",
        "lines_changed": 3,
        "syntax_valid": True,
        # Community tier: Pro/Enterprise fields are None/excluded
        "files_affected": None,
        "imports_adjusted": None,
        "rollback_available": None,
        "formatting_preserved": None,
        "approval_status": None,
        "compliance_check": None,
        "audit_id": None,
        "mutation_policy": None,
        "error": None,
    }


@pytest.fixture
def update_result_pro():
    """Mock successful Pro tier update result."""
    return {
        "success": True,
        "file_path": "/src/utils.py",
        "symbol_name": "calculate_tax",
        "symbol_type": "function",
        "backup_path": "/src/.code-scalpel/backups/update_20260103_100000/utils.py",
        "lines_changed": 3,
        "syntax_valid": True,
        # Pro tier: additional fields
        "files_affected": ["/src/utils.py"],
        "imports_adjusted": [
            {
                "file": "/src/utils.py",
                "action": "added",
                "import": "from decimal import Decimal",
            }
        ],
        "rollback_available": True,
        "formatting_preserved": True,
        # Enterprise-only fields
        "approval_status": None,
        "compliance_check": None,
        "audit_id": None,
        "mutation_policy": None,
        "error": None,
    }


@pytest.fixture
def update_result_enterprise():
    """Mock successful Enterprise tier update result."""
    return {
        "success": True,
        "file_path": "/src/utils.py",
        "symbol_name": "calculate_tax",
        "symbol_type": "function",
        "backup_path": "/src/.code-scalpel/backups/update_20260103_100000/utils.py",
        "lines_changed": 3,
        "syntax_valid": True,
        # All tier fields
        "files_affected": ["/src/utils.py"],
        "imports_adjusted": [],
        "rollback_available": True,
        "formatting_preserved": True,
        # Enterprise tier
        "approval_status": "approved",
        "compliance_check": {
            "passed": True,
            "rules_checked": ["code-style", "security-scan", "type-safety"],
            "warnings": [],
            "violations": [],
        },
        "audit_id": "audit-update-20260103-100000-abc123",
        "mutation_policy": "standard-update-policy",
        "error": None,
    }


# =============================================================================
# Update Operation Mocks
# =============================================================================


@pytest.fixture
def mock_update_symbol_success(mocker, update_result_community):
    """Mock successful update_symbol operation."""

    async def _mock_update(*args, **kwargs):
        return update_result_community

    return mocker.AsyncMock(return_value=update_result_community)


@pytest.fixture
def mock_update_symbol_syntax_error(mocker):
    """Mock update_symbol with syntax error."""
    error_result = {
        "success": False,
        "file_path": "/src/utils.py",
        "symbol_name": "calculate_tax",
        "symbol_type": "function",
        "backup_path": None,
        "lines_changed": 0,
        "syntax_valid": False,
        "files_affected": None,
        "imports_adjusted": None,
        "rollback_available": None,
        "formatting_preserved": None,
        "approval_status": None,
        "compliance_check": None,
        "audit_id": None,
        "mutation_policy": None,
        "error": "Syntax error in new code: unexpected indent at line 3, column 4",
    }
    return mocker.AsyncMock(return_value=error_result)


@pytest.fixture
def mock_update_symbol_not_found(mocker):
    """Mock update_symbol with symbol not found."""
    error_result = {
        "success": False,
        "file_path": "/src/utils.py",
        "symbol_name": "nonexistent_function",
        "symbol_type": "function",
        "backup_path": None,
        "lines_changed": 0,
        "syntax_valid": True,
        "files_affected": None,
        "imports_adjusted": None,
        "rollback_available": None,
        "formatting_preserved": None,
        "approval_status": None,
        "compliance_check": None,
        "audit_id": None,
        "mutation_policy": None,
        "error": "Symbol 'nonexistent_function' not found in /src/utils.py",
    }
    return mocker.AsyncMock(return_value=error_result)


# =============================================================================
# Tier Configuration Fixtures
# =============================================================================


@pytest.fixture
def tier_config_community():
    """Community tier configuration."""
    return {
        "tier": "community",
        "backup_required": True,
        "validation_level": "syntax",
        "max_updates_per_session": 10,
        "multifile_updates": False,
        "import_adjustment": False,
        "rollback_support": False,
        "approval_required": False,
        "compliance_check": False,
        "audit_logging": False,
        "response_fields": [
            "success",
            "file_path",
            "symbol_name",
            "symbol_type",
            "backup_path",
            "lines_changed",
            "syntax_valid",
            "error",
        ],
    }


@pytest.fixture
def tier_config_pro():
    """Pro tier configuration."""
    return {
        "tier": "pro",
        "backup_required": True,
        "validation_level": "semantic",
        "max_updates_per_session": -1,  # Unlimited
        "multifile_updates": True,
        "import_adjustment": True,
        "rollback_support": True,
        "approval_required": False,
        "compliance_check": False,
        "audit_logging": False,
        "response_fields": [
            "success",
            "file_path",
            "symbol_name",
            "symbol_type",
            "backup_path",
            "lines_changed",
            "syntax_valid",
            "files_affected",
            "imports_adjusted",
            "rollback_available",
            "formatting_preserved",
            "error",
        ],
    }


@pytest.fixture
def tier_config_enterprise():
    """Enterprise tier configuration."""
    return {
        "tier": "enterprise",
        "backup_required": True,
        "validation_level": "full",
        "max_updates_per_session": -1,  # Unlimited
        "multifile_updates": True,
        "import_adjustment": True,
        "rollback_support": True,
        "approval_required": True,
        "compliance_check": True,
        "audit_logging": True,
        "response_fields": [
            "success",
            "file_path",
            "symbol_name",
            "symbol_type",
            "backup_path",
            "lines_changed",
            "syntax_valid",
            "files_affected",
            "imports_adjusted",
            "rollback_available",
            "formatting_preserved",
            "approval_status",
            "compliance_check",
            "audit_id",
            "mutation_policy",
            "error",
        ],
    }


# =============================================================================
# Assertion Helpers
# =============================================================================


@pytest.fixture
def assert_result_has_community_fields():
    """Assert result has only Community tier fields."""

    def _assert(result):
        # Should have these
        assert "success" in result
        assert "file_path" in result
        assert "symbol_name" in result
        assert "backup_path" in result
        assert "lines_changed" in result
        assert "syntax_valid" in result

        # Should NOT expose these (gated to Pro+)
        # These should either be None or not in response
        pro_fields = [
            "files_affected",
            "imports_adjusted",
            "rollback_available",
            "formatting_preserved",
        ]
        for field_name in pro_fields:
            if field_name in result:
                assert result[field_name] is None, f"Community tier should not expose {field_name}"

        return True

    return _assert


@pytest.fixture
def assert_result_has_pro_fields():
    """Assert result has Community + Pro tier fields."""

    def _assert(result):
        # Community fields
        assert "success" in result
        assert "file_path" in result
        assert "symbol_name" in result
        assert "backup_path" in result
        assert "lines_changed" in result
        assert "syntax_valid" in result

        # Pro fields
        assert "files_affected" in result
        assert "imports_adjusted" in result
        assert "rollback_available" in result
        assert "formatting_preserved" in result

        # Enterprise fields should not be exposed
        enterprise_fields = [
            "approval_status",
            "compliance_check",
            "audit_id",
            "mutation_policy",
        ]
        for field_name in enterprise_fields:
            if field_name in result:
                assert result[field_name] is None, f"Pro tier should not expose {field_name}"

        return True

    return _assert


@pytest.fixture
def assert_result_has_enterprise_fields():
    """Assert result has all tier fields (Community + Pro + Enterprise)."""

    def _assert(result):
        # All fields should be present
        all_fields = [
            "success",
            "file_path",
            "symbol_name",
            "symbol_type",
            "backup_path",
            "lines_changed",
            "syntax_valid",
            "files_affected",
            "imports_adjusted",
            "rollback_available",
            "formatting_preserved",
            "approval_status",
            "compliance_check",
            "audit_id",
            "mutation_policy",
            "error",
        ]
        for field_name in all_fields:
            assert field_name in result, f"Enterprise result missing field: {field_name}"

        return True

    return _assert


# =============================================================================
# [20260103_TEST] Performance Testing Infrastructure
# =============================================================================

import time  # noqa: E402

# import psutil  # [20260103_TEST] Not needed for Phase 1 simplified tests
from contextlib import contextmanager  # noqa: E402
from dataclasses import dataclass, field  # noqa: E402

# Simple memory tracking fallback when psutil is not available
try:
    import psutil

    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False


@dataclass
class PerformanceMetrics:
    """Performance measurement results for update_symbol operations."""

    duration_ms: float
    memory_delta_mb: float
    success: bool
    iterations: int
    durations: list[float] = field(default_factory=list)
    median_ms: float | None = None
    p95_ms: float | None = None
    p99_ms: float | None = None

    def __post_init__(self):
        """Calculate percentiles if multiple iterations."""
        if len(self.durations) > 1:
            sorted_durations = sorted(self.durations)
            n = len(sorted_durations)
            self.median_ms = sorted_durations[n // 2]
            self.p95_ms = sorted_durations[min(int(n * 0.95), n - 1)]
            self.p99_ms = sorted_durations[min(int(n * 0.99), n - 1)]


@contextmanager
def measure_performance(iterations: int = 1):
    """
    Context manager for measuring performance of update_symbol operations.

    Usage:
        with measure_performance(iterations=100) as durations:
            for _ in range(100):
                start = time.perf_counter()
                # ... perform operation ...
                durations.append((time.perf_counter() - start) * 1000)

        # Context manager yields PerformanceMetrics on exit
    """
    if _HAS_PSUTIL:
        process = psutil.Process()
        mem_before = process.memory_info().rss / 1024 / 1024  # MB
    else:
        mem_before = 0.0
    durations: list[float] = []

    overall_start = time.perf_counter()
    try:
        yield durations
    finally:
        overall_end = time.perf_counter()
        if _HAS_PSUTIL:
            mem_after = process.memory_info().rss / 1024 / 1024  # MB
        else:
            mem_after = 0.0

        overall_duration_ms = (overall_end - overall_start) * 1000
        memory_delta = mem_after - mem_before

        metrics = PerformanceMetrics(
            duration_ms=overall_duration_ms,
            memory_delta_mb=memory_delta,
            success=True,
            iterations=iterations,
            durations=durations,
        )

        # Store in context for retrieval
        durations.clear()
        durations.append(metrics)


@pytest.fixture
def performance_threshold():
    """
    Fixture providing performance thresholds for update_symbol operations.

    Thresholds based on roadmap targets:
    - Update time: <100ms per symbol (median)
    - Success rate: >99%
    """
    return {
        # Single symbol update thresholds (milliseconds)
        "small_symbol": 50,  # <50ms for small symbols (<50 LOC)
        "medium_symbol": 100,  # <100ms for medium symbols (50-200 LOC)
        "large_symbol": 200,  # <200ms for large symbols (200-500 LOC)
        "very_large_symbol": 500,  # <500ms for very large symbols (500+ LOC)
        # File size impact thresholds
        "small_file": 100,  # <100ms in small file (<500 LOC)
        "medium_file": 150,  # <150ms in medium file (500-2000 LOC)
        "large_file": 300,  # <300ms in large file (2000-5000 LOC)
        "very_large_file": 500,  # <500ms in very large file (5000+ LOC)
        # Batch operations (Pro tier)
        "batch_10_same_file": 1000,  # <1s for 10 updates in same file
        "batch_10_diff_files": 1500,  # <1.5s for 10 updates in different files
        "batch_50_updates": 5000,  # <5s for 50 updates
        "batch_100_updates": 10000,  # <10s for 100 updates
        # Multi-file atomic (Pro tier)
        "multifile_3": 500,  # <500ms for 3-file atomic
        "multifile_10": 2000,  # <2s for 10-file atomic
        "multifile_25": 5000,  # <5s for 25-file atomic
        # Feature overhead thresholds
        "import_overhead": 50,  # <50ms import adjustment overhead
        "compliance_overhead": 50,  # <50ms compliance check overhead
        "audit_overhead": 30,  # <30ms audit logging overhead
        # Error handling (fast-fail)
        "syntax_error": 50,  # <50ms syntax error detection
        "file_not_found": 10,  # <10ms file not found
        "session_limit": 5,  # <5ms session limit check
        "license_validation": 20,  # <20ms license validation
        # Memory thresholds (MB)
        "single_update_memory": 50,  # <50MB increase per update
        "batch_100_memory": 500,  # <500MB for 100 updates
        # Success rate thresholds (percentage)
        "normal_success_rate": 99.0,  # >99% for normal operations
        "edge_case_success_rate": 95.0,  # >95% for edge cases
    }


@pytest.fixture
def large_file_fixture(tmp_path):
    """
    Generate large Python file for performance testing.

    Creates a 5000-line file with 100 functions (50 lines each).
    """
    file_path = tmp_path / "large_module.py"

    lines = []
    lines.append('"""Large module for performance testing."""')
    lines.append("")

    for i in range(100):
        lines.append(f"def function_{i}(x, y):")
        lines.append(f'    """Function {i} for testing."""')
        for j in range(46):  # 46 lines + def + docstring + return = 49 lines
            lines.append(f"    # Processing line {j}")
        lines.append(f"    return x + y + {i}")
        lines.append("")

    file_path.write_text("\n".join(lines))
    return file_path


@pytest.fixture
def very_large_file_fixture(tmp_path):
    """
    Generate very large Python file (8000+ lines) for stress testing.

    Creates an 8000-line file with 160 functions (50 lines each).
    """
    file_path = tmp_path / "very_large_module.py"

    lines = []
    lines.append('"""Very large module for stress testing."""')
    lines.append("")

    for i in range(160):
        lines.append(f"def function_{i}(x, y):")
        lines.append(f'    """Function {i} for testing."""')
        for j in range(46):
            lines.append(f"    # Processing line {j}")
        lines.append(f"    return x + y + {i}")
        lines.append("")

    file_path.write_text("\n".join(lines))
    return file_path
