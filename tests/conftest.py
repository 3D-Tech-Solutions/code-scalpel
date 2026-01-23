"""
Test session helpers.

Ensure tests run even when the process working directory has been removed
by earlier test steps or external factors. This mirrors defensive handling
so that `pytest.MonkeyPatch.chdir()` can safely call `os.getcwd()`.

[20260122_TEST] Create session guard to reset CWD if missing.
"""

import os
from pathlib import Path


def pytest_sessionstart(session) -> None:
    """Ensure process CWD is valid at the start of the test session.

    If `os.getcwd()` raises (directory removed), change CWD to the
    repository root (two levels up from the tests/ directory).
    """
    try:
        os.getcwd()
    except (FileNotFoundError, OSError):
        project_root = Path(__file__).resolve().parent.parent
        try:
            os.chdir(project_root)
        except Exception:
            # Best-effort only; if this fails, let tests surface the error.
            pass


def pytest_runtest_setup(item) -> None:
    """Before each test, ensure current working directory exists.

    This helps when earlier tests change into temporary directories that
    have since been removed; `monkeypatch.chdir()` calls `os.getcwd()` and
    would otherwise raise `FileNotFoundError`.
    """
    try:
        os.getcwd()
    except (FileNotFoundError, OSError):
        project_root = Path(__file__).resolve().parent.parent
        try:
            os.chdir(project_root)
        except Exception:
            pass


"""
Pytest configuration and fixtures for Code Scalpel tests.

[20251213_FEATURE] v1.5.2 - OSV client test isolation fixtures with proper mock cleanup.
[20251214_FEATURE] v1.5.3 - OSV client import in ast_tools __init__ for full-suite fix.
[20260108_BUGFIX] Removed pytest_plugins auto-registration; fixtures auto-discover via conftest hierarchy.
"""

import json
import sys
import time
import urllib.error
import warnings
from unittest.mock import MagicMock, patch

import pytest


# [20260104_TEST] Lightweight fallback for pytest-mock's `mocker` fixture used in tier tests.
@pytest.fixture
def mocker():
    """Provide a minimal mocker fixture compatible with pytest-mock's API surface.

    The project does not depend on pytest-mock at runtime; a simple wrapper suffices
    for tests that only need `.patch(...)` and automatic cleanup.
    """

    class _SimpleMocker:
        def __init__(self) -> None:
            self._patches: list[patch] = []

        def patch(self, target: str, *args, **kwargs):
            p = patch(target, *args, **kwargs)
            started = p.start()
            self._patches.append(p)
            return started

        def stopall(self) -> None:
            for p in reversed(self._patches):
                try:
                    p.stop()
                except Exception:
                    pass
            self._patches.clear()

    m = _SimpleMocker()
    try:
        yield m
    finally:
        m.stopall()


# [20251216_TEST] Silence upstream astor ast.Num deprecation noise on Python 3.13
warnings.filterwarnings(
    "ignore",
    message="ast.Num is deprecated and will be removed in Python 3.14",
    category=DeprecationWarning,
)
warnings.filterwarnings(
    "ignore",
    message="ast.Str is deprecated and will be removed in Python 3.14",
    category=DeprecationWarning,
)

# Add the src directory to the path so tests can import code_scalpel
# This allows tests to run both before and after pip install
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if src_path not in sys.path:
    sys.path.insert(0, src_path)


# [20260120_TEST] Ensure tiered tests load a real license when available
@pytest.fixture(scope="session", autouse=True)
def set_default_license_path():
    """Prime CODE_SCALPEL_LICENSE_PATH with a bundled test license if unset.

    We prefer Enterprise (superset of Pro) but fall back to Pro; we never
    override an explicitly provided path (e.g., pipeline secrets).
    """

    if os.environ.get("CODE_SCALPEL_LICENSE_PATH"):
        return

    license_dir = Path(__file__).parent / "licenses"
    candidates = [
        license_dir / "code_scalpel_license_enterprise_20260101_190754.jwt",
        license_dir / "code_scalpel_license_enterprise_20260101_170506.jwt",
        license_dir / "code_scalpel_license_pro_20260101_190345.jwt",
        license_dir / "code_scalpel_license_pro_20260101_170435.jwt",
    ]

    for candidate in candidates:
        if candidate.exists():
            # Allow explicit env overrides while keeping discovery enabled
            os.environ.setdefault("CODE_SCALPEL_LICENSE_PATH", str(candidate))
            os.environ.pop("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", None)
            break


# [20251214_FEATURE] v1.5.3 - Ensure osv_client is imported early
# Now that ast_tools.__init__ imports osv_client, this will automatically
# make osv_client available in the ast_tools namespace
try:
    import code_scalpel.ast_tools  # noqa
except ImportError:
    pass


# =====================================================================
# OSV Client Fixtures (v1.5.2 - Test Isolation)
# =====================================================================
# [20251213_FEATURE] Function-scoped mocks ensure proper test isolation
# Prevents mock state leakage when running full test suite


@pytest.fixture(scope="function")
def osv_mock_urlopen():
    """
    Function-scoped mock for urllib.request.urlopen.

    Ensures complete isolation between tests - each test gets a fresh mock instance.
    This prevents mock state leakage which was the root cause of test failures when
    running the full test suite.

    Now that osv_client is imported in ast_tools.__init__, the patch target
    'code_scalpel.ast_tools.osv_client.urllib.request.urlopen' is always valid.

    Yields:
        MagicMock: A mock object configured to behave like urlopen.
    """
    patcher = patch("code_scalpel.ast_tools.osv_client.urllib.request.urlopen")
    mock = patcher.start()
    yield mock
    patcher.stop()


@pytest.fixture(scope="function")
def osv_client_no_cache(osv_mock_urlopen):
    """
    OSVClient instance with caching disabled and mocked network calls.

    Use this fixture when you want to test the OSV client without making real API calls.
    The mock is automatically cleaned up after each test.

    Args:
        osv_mock_urlopen: Injected osv_mock_urlopen fixture

    Returns:
        OSVClient: Configured client instance
    """
    # Import here to avoid module resolution issues
    from code_scalpel.security.dependencies import OSVClient

    return OSVClient(cache_enabled=False)


@pytest.fixture(scope="function")
def osv_client_with_cache(osv_mock_urlopen):
    """
    OSVClient instance with caching enabled and mocked network calls.

    Use this fixture when testing caching behavior.

    Args:
        osv_mock_urlopen: Injected osv_mock_urlopen fixture

    Returns:
        OSVClient: Configured client instance with caching
    """
    # Import here to avoid module resolution issues
    from code_scalpel.security.dependencies import OSVClient

    return OSVClient(cache_enabled=True)


@pytest.fixture(scope="function")
def mock_osv_response():
    """
    Factory fixture for creating mock OSV API responses.

    Returns:
        Callable: Function that creates a properly configured mock response

    Example:
        >>> mock_response = mock_osv_response()
        >>> mock_response.configure(vulns=[{"id": "CVE-123"}])
        >>> mock_urlopen.return_value = mock_response
    """

    def _create_response(data=None):
        """Create a mock response with proper context manager behavior."""
        mock_response = MagicMock()

        if data is None:
            data = {"vulns": []}

        mock_response.read.return_value = json.dumps(data).encode()
        # Context manager support for 'with' statement
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        return mock_response

    return _create_response


@pytest.fixture(scope="function")
def mock_osv_error():
    """
    Factory fixture for creating mock OSV API errors.

    Returns:
        Callable: Function that creates various error types

    Example:
        >>> mock_urlopen.side_effect = mock_osv_error("URLError")
    """

    def _create_error(error_type="URLError"):
        """Create appropriate error for the given type."""
        if error_type == "URLError":
            return urllib.error.URLError("Connection failed")
        elif error_type == "HTTPError":
            return urllib.error.HTTPError("https://api.osv.dev/v1/query", 503, "Service Unavailable", {}, None)
        elif error_type == "Timeout":
            return TimeoutError("Request timeout")
        else:
            return Exception(f"Unknown error: {error_type}")

    return _create_error


# Auto-use fixture for cleanup
@pytest.fixture(autouse=True)
def reset_osv_cache():
    """
    Auto-used fixture to reset OSV client cache before each test.

    This ensures no state leakage from caching between tests.

    [20251213_FEATURE] v1.5.2 - Automatic cleanup for test isolation
    """
    yield
    # Cleanup after test
    try:
        from code_scalpel.security.dependencies import OSVClient

        client = OSVClient()
        client.clear_cache()
    except Exception:
        pass  # Ignore errors on cleanup


# [20251217_BUGFIX] Prevent health server bind conflicts during tests
@pytest.fixture(autouse=True)
def disable_health_server(monkeypatch):
    """
    Auto-used fixture to prevent health server startup during tests.

    The health server can cause "Address already in use" warnings when
    running the full test suite, as multiple test modules try to start
    servers on the same port. This fixture patches the thread start
    to be a no-op during tests.

    [20251217_BUGFIX] Silence health server bind warnings in test runs
    """
    # Patch threading.Thread.start to skip health server startup
    import threading

    original_start = threading.Thread.start

    def patched_start(self):
        # Skip starting threads named with "run_health_server" target
        if hasattr(self, "_target") and self._target:
            target_name = getattr(self._target, "__name__", "")
            if "health_server" in target_name.lower():
                return  # Skip health server threads
        original_start(self)

    monkeypatch.setattr(threading.Thread, "start", patched_start)


# [20251227_BUGFIX] Do not collect Ninja Warrior torture-tests by default
def pytest_ignore_collect(collection_path, config):
    """Skip opt-in Ninja Warrior torture-tests unless explicitly enabled.

    These torture-tests are designed for manual/contract validation and can
    include intentionally duplicated basenames (e.g., multiple test_edge_cases.py)
    and framework-specific harness imports.

    Enable collection by setting RUN_NINJA_WARRIOR=1.
    """

    path_str = str(collection_path)
    if "tests/Code-Scalpel-Ninja-Warrior" in path_str:
        return os.environ.get("RUN_NINJA_WARRIOR") not in {
            "1",
            "true",
            "TRUE",
            "yes",
            "YES",
        }
    return False


# =====================================================================
# Licensing Fixtures (Test Helpers)
# =====================================================================
# [20251228_TEST] Shared fixtures for generating HS256 licenses/CRLs in tests.


@pytest.fixture(scope="function")
def hs256_test_secret() -> str:
    """Stable secret key for HS256 test tokens."""

    return "test-secret"


@pytest.fixture(scope="function")
def write_hs256_license_jwt(tmp_path, hs256_test_secret):
    """Factory: write a license JWT to disk and return its path."""

    from pathlib import Path

    from code_scalpel.licensing.jwt_generator import generate_license

    def _write(
        *,
        tier: str = "pro",
        customer_id: str = "user@example.com",
        duration_days: int = 7,
        jti: str,
        filename: str = "license.jwt",
        base_dir: Path | None = None,
    ) -> Path:
        token = generate_license(
            tier=tier,
            customer_id=customer_id,
            duration_days=duration_days,
            algorithm="HS256",
            secret_key=hs256_test_secret,
            jti=jti,
        )

        out_dir = base_dir if base_dir is not None else tmp_path
        path = Path(out_dir) / filename
        path.write_text(token + "\n", encoding="utf-8")
        return path

    return _write


@pytest.fixture(scope="function")
def write_hs256_crl_jwt(tmp_path, hs256_test_secret):
    """Factory: write a CRL JWT (revoked jti list) to disk and return its path."""

    from pathlib import Path

    import jwt

    def _write(
        *,
        revoked_jtis: list[str],
        filename: str = "crl.jwt",
        base_dir: Path | None = None,
        issuer: str = "code-scalpel",
        audience: str = "code-scalpel-users",
        expires_in_seconds: int = 3600,
    ) -> Path:
        now = int(time.time())
        claims = {
            "iss": issuer,
            "aud": audience,
            "iat": now - 10,
            "exp": now + expires_in_seconds,
            "revoked": revoked_jtis,
        }
        token = jwt.encode(claims, hs256_test_secret, algorithm="HS256")

        out_dir = base_dir if base_dir is not None else tmp_path
        path = Path(out_dir) / filename
        path.write_text(token + "\n", encoding="utf-8")
        return path

    return _write


@pytest.fixture(scope="function")
def set_hs256_license_env(monkeypatch, hs256_test_secret):
    """Helper to enable HS256 validation in-process via env vars."""

    def _apply(*, license_path: str, crl_path: str | None = None) -> None:
        monkeypatch.setenv("CODE_SCALPEL_ALLOW_HS256", "1")
        monkeypatch.setenv("CODE_SCALPEL_SECRET_KEY", hs256_test_secret)
        monkeypatch.setenv("CODE_SCALPEL_LICENSE_PATH", license_path)
        if crl_path is not None:
            monkeypatch.setenv("CODE_SCALPEL_LICENSE_CRL_PATH", crl_path)
        else:
            monkeypatch.delenv("CODE_SCALPEL_LICENSE_CRL_PATH", raising=False)
        monkeypatch.delenv("CODE_SCALPEL_LICENSE_CRL_JWT", raising=False)

    return _apply


@pytest.fixture(scope="function")
def hs256_license_state_paths(tmp_path, write_hs256_license_jwt, write_hs256_crl_jwt):
    """Prebuilt license-state artifacts.

    Returns a dict with:
    - missing: None
    - valid: license path
    - expired: license path
    - revoked: (license path, crl path)

    [20251228_TEST] Canonical fixtures for valid/expired/revoked license states.
    """

    valid_jti = "lic-valid"
    expired_jti = "lic-expired"
    revoked_jti = "lic-revoked"

    valid = write_hs256_license_jwt(
        jti=valid_jti,
        duration_days=7,
        base_dir=tmp_path,
        filename="license_valid.jwt",
    )
    expired = write_hs256_license_jwt(
        jti=expired_jti,
        duration_days=-1,
        base_dir=tmp_path,
        filename="license_expired.jwt",
    )
    revoked_license = write_hs256_license_jwt(
        jti=revoked_jti,
        duration_days=7,
        base_dir=tmp_path,
        filename="license_revoked.jwt",
    )
    revoked_crl = write_hs256_crl_jwt(
        revoked_jtis=[revoked_jti],
        base_dir=tmp_path,
        filename="crl_revoked.jwt",
    )

    return {
        "missing": None,
        "valid": valid,
        "expired": expired,
        "revoked": (revoked_license, revoked_crl),
    }
