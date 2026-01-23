# Code Scalpel MCP Server - Real MCP Protocol Implementation.
#
# This server implements the Model Context Protocol (MCP) specification using
# the official Python SDK. It exposes Code Scalpel's analysis tools to any
# MCP-compliant client (Claude Desktop, Cursor, etc.).
#
# Transports:
# - stdio: Default. Client spawns server as subprocess. Best for local use.
# - streamable-http: Network deployment. Requires explicit --transport flag.
#
# Usage:
#     # stdio (default)
#     python -m code_scalpel.mcp.server
#
#     # HTTP transport for network access
#     python -m code_scalpel.mcp.server --transport streamable-http --port 8080
#
# Security:
#     - Code is PARSED, never executed (ast.parse only)
#     - Maximum code size enforced
#     - HTTP transport binds to 127.0.0.1 by default


from __future__ import annotations

import ast
import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from code_scalpel import SurgicalExtractor
    from code_scalpel.graph_engine.graph import UniversalGraph

from mcp.server.fastmcp import Context
from pydantic import BaseModel, Field

# [20251218_BUGFIX] Import version from package instead of hardcoding
from code_scalpel import __version__

# [20260117_SECURITY] Authoritative startup tier selection via authorization helper
from code_scalpel.licensing.authorization import compute_effective_tier_for_startup

# [20260116_FEATURE] License-gated tier system restored from archive
from code_scalpel.licensing.jwt_validator import JWTLicenseValidator
from code_scalpel.licensing.tier_detector import (  # noqa: F401
    get_current_tier as get_current_tier_from_license,  # Re-exported for test mocking
)
from code_scalpel.mcp.helpers.analyze_helpers import (
    _analyze_code_sync as helper_analyze_code_sync,
)
from code_scalpel.mcp.helpers.analyze_helpers import (
    _analyze_java_code as helper_analyze_java_code,
)
from code_scalpel.mcp.helpers.analyze_helpers import (
    _analyze_javascript_code as helper_analyze_js_code,
)
from code_scalpel.mcp.models.core import AnalysisResult, ClassInfo, FunctionInfo
from code_scalpel.mcp.models.policy import (
    PolicyVerificationResult,  # [20260121_BUGFIX] Reuse canonical model to avoid duplication
)
from code_scalpel.mcp.paths import (
    env_truthy as _env_truthy,
)
from code_scalpel.mcp.paths import (
    maybe_auto_init_config_dir as _maybe_auto_init_config_dir,  # [20260119_BUGFIX]
)
from code_scalpel.mcp.paths import (
    scalpel_home_dir as _scalpel_home_dir,
)

# [20260116_REFACTOR] Import shared mcp instance from protocol
from code_scalpel.mcp.protocol import mcp, set_current_tier

# [20251216_FEATURE] v2.5.0 - Unified sink detection MCP tool
from code_scalpel.security.analyzers.unified_sink_detector import (
    UnifiedSinkDetector,
)

# [20260119_REFACTOR] get_current_tier_from_license is re-exported for tests that mock it.
# server.py has its own _get_current_tier() that does full license validation with env var support.

# Current tier for response envelope metadata.
# Initialized to "community" (free tier) by default.
# The actual tier is determined by license validation at runtime.
CURRENT_TIER = "community"

# [20260119_BUGFIX] Restore backward-compatible project root globals for tests and path validation.
# [20260120_BUGFIX] Use a mutable container to allow dynamic updates from main().
# [20260122_BUGFIX] Guard against missing CWD during collection (e.g., when parent dir removed).
# Direct assignment to PROJECT_ROOT creates a new object, but _PROJECT_ROOT_HOLDER[0]
# can be updated in place and accessed via get_project_root().
try:
    _DEFAULT_PROJECT_ROOT = Path.cwd()
except FileNotFoundError:
    _DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_PROJECT_ROOT_HOLDER: list[Path] = [_DEFAULT_PROJECT_ROOT]
PROJECT_ROOT: Path = _PROJECT_ROOT_HOLDER[0]  # Backward compat - may be stale after main() runs
ALLOWED_ROOTS: list[Path] = []


def get_project_root() -> Path:
    """Get the current project root.

    [20260120_FEATURE] Getter function to access PROJECT_ROOT.
    This allows helper modules to get the dynamically-set value after main() runs.
    """
    return _PROJECT_ROOT_HOLDER[0]


def set_project_root(path: Path) -> None:
    """Set the project root (called by main()).

    [20260120_FEATURE] Setter to update both the holder and backward-compat global.
    """
    global PROJECT_ROOT
    _PROJECT_ROOT_HOLDER[0] = path
    PROJECT_ROOT = path


# [20251228_FEATURE] Runtime license grace for long-lived server processes.
# If a license expires mid-session, keep the last known valid tier for 24h.
# This does NOT change startup behavior: expired licenses remain invalid at startup.
_LAST_VALID_LICENSE_TIER: str | None = None
_LAST_VALID_LICENSE_AT: float | None = None
_MID_SESSION_EXPIRY_GRACE_SECONDS = 24 * 60 * 60


# [20251215_BUGFIX] Configure logging to stderr only to prevent stdio transport corruption
# When using stdio transport, stdout must contain ONLY valid JSON-RPC messages.
# Any logging to stdout will corrupt the protocol stream.
def _configure_logging(transport: str = "stdio"):
    """Configure logging based on transport type."""
    root_logger = logging.getLogger()

    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Always log to stderr to avoid corrupting stdio transport
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

    # [20260116_BUGFIX] Use SCALPEL_MCP_OUTPUT with string levels (DEBUG, INFO, ALERT, WARN)
    # Restores original behavior from archive/server.py
    env_level = os.environ.get("SCALPEL_MCP_OUTPUT", "WARN").upper()
    if env_level == "DEBUG":
        level = logging.DEBUG
    elif env_level == "INFO":
        level = logging.INFO
    elif env_level == "ALERT":
        level = logging.CRITICAL
    else:
        level = logging.WARNING

    handler.setLevel(level)
    root_logger.setLevel(level)
    root_logger.addHandler(handler)


# Setup logging (default to stderr)
logger = logging.getLogger(__name__)


# =============================================================================
# [20260116_FEATURE] License-Gated Tier System
# Restored from archive/server.py - Proper license validation with downgrade capability
# =============================================================================


def _normalize_tier(value: str | None) -> str:
    """Normalize tier string to canonical form."""
    if not value:
        return "community"
    v = value.strip().lower()
    if v == "free":
        return "community"
    if v == "all":
        return "enterprise"
    return v


def _requested_tier_from_env() -> str | None:
    """Get requested tier from environment variables (for testing/downgrade)."""
    requested = os.environ.get("CODE_SCALPEL_TIER") or os.environ.get("SCALPEL_TIER")
    if requested is None:
        return None
    requested = _normalize_tier(requested)
    if requested not in {"community", "pro", "enterprise"}:
        return None
    return requested


def _get_current_tier() -> str:
    """Get the current tier from license validation with env var override.

    The tier system works as follows:
    1. License file determines the MAXIMUM tier you're entitled to
    2. Environment variable can REQUEST a tier (downgrade only - no upgrade via env var)
    3. The effective tier is the MINIMUM of licensed and requested

    This allows Enterprise license holders to test Pro/Community behavior
    by setting CODE_SCALPEL_TIER=pro or CODE_SCALPEL_TIER=community.

    SECURITY NOTE: Environment variables can ONLY downgrade, not upgrade.
    To access a higher tier, you must provide a valid license file.

    Environment Variables:
        CODE_SCALPEL_TIER: Request a specific tier (downgrade only)
        SCALPEL_TIER: Legacy alias for CODE_SCALPEL_TIER
        CODE_SCALPEL_LICENSE_PATH: Path to JWT license file
        CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY: Set to "1" to disable auto-discovery

    Returns:
        str: One of 'community', 'pro', or 'enterprise'
    """
    global _LAST_VALID_LICENSE_AT, _LAST_VALID_LICENSE_TIER

    requested = _requested_tier_from_env()
    disable_license_discovery = os.environ.get("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY") == "1"

    # When discovery is disabled and no explicit license path is provided, clamp to
    # Community to avoid silently elevating tier just via env vars.
    if disable_license_discovery:
        if not os.environ.get("CODE_SCALPEL_LICENSE_PATH"):
            return "community"

    validator = JWTLicenseValidator()
    license_data = validator.validate()
    licensed = "community"

    if license_data.is_valid:
        licensed = _normalize_tier(license_data.tier)
        _LAST_VALID_LICENSE_TIER = licensed
        _LAST_VALID_LICENSE_AT = __import__("time").time()
    else:
        # Revocation is immediate: no grace.
        err = (license_data.error_message or "").lower()
        if "revoked" in err:
            licensed = "community"
        # Expiration mid-session: allow 24h grace based on last known valid tier.
        elif getattr(license_data, "is_expired", False) and _LAST_VALID_LICENSE_AT:
            now = __import__("time").time()
            if now - _LAST_VALID_LICENSE_AT <= _MID_SESSION_EXPIRY_GRACE_SECONDS:
                if _LAST_VALID_LICENSE_TIER in {"pro", "enterprise"}:
                    licensed = _LAST_VALID_LICENSE_TIER

    # If no tier requested via env var, use the licensed tier
    if requested is None:
        return licensed

    # [20260119_SECURITY] Allow downgrade ONLY: effective tier = min(requested, licensed)
    # Environment variables CANNOT be used to upgrade to a higher tier.
    # Users must provide a valid license file to access higher tiers.
    rank = {"community": 0, "pro": 1, "enterprise": 2}
    effective = requested if rank[requested] <= rank[licensed] else licensed

    # Log if user tried to upgrade via env var (security audit)
    if rank[requested] > rank[licensed]:
        import sys

        print(
            f"Warning: Tier downgrade ignored - requested {requested} but licensed {licensed}. "
            f"Use a valid license file to upgrade tier.",
            file=sys.stderr,
        )

    return effective


# [20251230_FEATURE] Support "invisible" onboarding: MCP startup can generate
# the `.code-scalpel/` directory so users do not need to run `code-scalpel init`.
#
# This is intentionally opt-in because it writes files.
#
# Environment:
# - SCALPEL_AUTO_INIT=1 enables auto-init
# - SCALPEL_AUTO_INIT_MODE=full|templates_only selects init behavior
# - SCALPEL_AUTO_INIT_TARGET=project|user selects where to create `.code-scalpel/`


def auto_init_if_enabled(
    project_root: Path,
    tier: str,
    enabled: bool | None = None,
    mode: str | None = None,
    target: str | None = None,
) -> dict[str, Any] | None:
    """Auto-initialize .code-scalpel/ if enabled via env."""
    if enabled is None:
        enabled = _env_truthy(os.environ.get("SCALPEL_AUTO_INIT"))
    if not enabled:
        return None

    selected_target = (target or os.environ.get("SCALPEL_AUTO_INIT_TARGET") or "project").strip().lower()
    if selected_target not in {"project", "user"}:
        selected_target = "project"

    init_root = project_root if selected_target == "project" else _scalpel_home_dir()

    config_dir = init_root / ".code-scalpel"
    if config_dir.exists():
        return {
            "created": False,
            "skipped": True,
            "path": str(config_dir),
            "target": selected_target,
        }

    selected_mode = (mode or os.environ.get("SCALPEL_AUTO_INIT_MODE") or "").strip().lower()
    if not selected_mode:
        # Default: don't create secrets unless Pro/Enterprise.
        selected_mode = "full" if tier in {"pro", "enterprise"} else "templates_only"
    if selected_mode not in {"full", "templates_only"}:
        selected_mode = "templates_only"

    from code_scalpel.config.init_config import init_config_dir

    result = init_config_dir(str(init_root), mode=selected_mode)
    return {
        "created": bool(result.get("success")),
        "skipped": False,
        "mode": selected_mode,
        "path": str(config_dir),
        "target": selected_target,
        "message": result.get("message"),
    }


# Caching enabled by default
CACHE_ENABLED = os.environ.get("SCALPEL_CACHE_ENABLED", "1") != "0"

# [20251220_PERF] v3.0.5 - AST Cache for parsed Python files
# Stores parsed ASTs keyed by (file_path, mtime) to avoid re-parsing unchanged files
# Format: {(file_path_str, mtime): ast.Module}
_AST_CACHE: dict[tuple[str, float], ast.Module] = {}
_AST_CACHE_MAX_SIZE = 500  # Limit memory usage - keep last 500 files


def _get_cached_ast(file_path: Path) -> ast.Module | None:
    """Get cached AST for a file if it hasn't changed."""
    try:
        mtime = file_path.stat().st_mtime
        key = (str(file_path.resolve()), mtime)
        return _AST_CACHE.get(key)
    except OSError:
        return None


def _cache_ast(file_path: Path, tree: ast.Module) -> None:
    """Cache a parsed AST for a file."""
    try:
        mtime = file_path.stat().st_mtime
        key = (str(file_path.resolve()), mtime)

        # Evict old entries if cache is too large
        if len(_AST_CACHE) >= _AST_CACHE_MAX_SIZE:
            # Remove oldest 20% of entries
            entries_to_remove = _AST_CACHE_MAX_SIZE // 5
            keys_to_remove = list(_AST_CACHE.keys())[:entries_to_remove]
            for k in keys_to_remove:
                del _AST_CACHE[k]

        _AST_CACHE[key] = tree
    except OSError:
        pass


def _parse_file_cached(file_path: Path) -> ast.Module | None:
    """Parse a Python file with caching."""
    # Check cache first
    cached = _get_cached_ast(file_path)
    if cached is not None:
        return cached

    try:
        code = file_path.read_text(encoding="utf-8")
        tree = ast.parse(code)
        _cache_ast(file_path, tree)
        return tree
    except (OSError, SyntaxError):
        return None


# [20251220_PERF] v3.0.5 - Singleton UnifiedSinkDetector to avoid rebuilding patterns
_SINK_DETECTOR: UnifiedSinkDetector | None = None


def _get_sink_detector() -> UnifiedSinkDetector:  # type: ignore[return-value]
    """Get or create singleton UnifiedSinkDetector."""
    global _SINK_DETECTOR
    if _SINK_DETECTOR is None:
        from code_scalpel.security.analyzers.unified_sink_detector import (
            UnifiedSinkDetector,
        )

        _SINK_DETECTOR = UnifiedSinkDetector()
    return _SINK_DETECTOR  # type: ignore[return-value]


# [20251219_FEATURE] v3.0.4 - Call graph cache for get_graph_neighborhood
# Stores UniversalGraph objects keyed by project root path
# Format: {project_root_str: (UniversalGraph, timestamp)}
# [20251220_PERF] v3.0.5 - Increased cache TTL from 60s to 300s for large codebases
_GRAPH_CACHE: dict[str, tuple[UniversalGraph, float]] = {}  # type: ignore[name-defined]
_GRAPH_CACHE_TTL = 300.0  # seconds (5 minutes for stable codebases)


def _get_cached_graph(project_root: Path) -> UniversalGraph | None:  # type: ignore[name-defined]
    """Get cached UniversalGraph for project if still valid."""
    import time

    key = str(project_root.resolve())
    if key in _GRAPH_CACHE:
        graph, timestamp = _GRAPH_CACHE[key]
        if time.time() - timestamp < _GRAPH_CACHE_TTL:
            logger.debug(f"Using cached graph for {key}")
            return graph
        else:
            # Cache expired
            del _GRAPH_CACHE[key]
            logger.debug(f"Graph cache expired for {key}")
    return None


def _cache_graph(project_root: Path, graph: UniversalGraph) -> None:  # type: ignore[name-defined]
    """Cache a UniversalGraph for a project."""
    import time

    key = str(project_root.resolve())
    _GRAPH_CACHE[key] = (graph, time.time())
    logger.debug(f"Cached graph for {key}")


def _invalidate_graph_cache(project_root: Path | None = None) -> None:
    """Invalidate graph cache for a project or all projects."""
    if project_root:
        key = str(project_root.resolve())
        if key in _GRAPH_CACHE:
            del _GRAPH_CACHE[key]
            logger.debug(f"Invalidated graph cache for {key}")
    else:
        _GRAPH_CACHE.clear()
        logger.debug("Invalidated all graph caches")


def _is_path_allowed(path: Path) -> bool:
    """
    Check if a path is within allowed roots.

    [20251215_FEATURE] v2.0.0 - Security boundary enforcement

    Args:
        path: Path to validate

    Returns:
        True if path is within allowed roots, False otherwise
    """
    resolved = path.resolve()

    # If no roots specified, use PROJECT_ROOT
    roots_to_check = ALLOWED_ROOTS if ALLOWED_ROOTS else [PROJECT_ROOT]

    for root in roots_to_check:
        try:
            resolved.relative_to(root.resolve())
            return True
        except ValueError:
            continue

    return False


def _validate_path_security(path: Path) -> Path:
    """
    Validate path is within allowed roots and return resolved path.

    [20251215_FEATURE] v2.0.0 - Security validation with helpful errors

    Args:
        path: Path to validate

    Returns:
        Resolved path if valid

    Raises:
        PermissionError: If path is outside allowed roots
    """
    resolved = path.resolve()

    if not _is_path_allowed(resolved):
        roots_str = ", ".join(str(r) for r in (ALLOWED_ROOTS or [PROJECT_ROOT]))
        raise PermissionError(
            f"Access denied: {path} is outside allowed roots.\n"
            f"Allowed roots: {roots_str}\n"
            f"Set roots via the roots/list capability or SCALPEL_ROOT environment variable."
        )

    return resolved


async def _fetch_and_cache_roots(ctx: Context | None) -> list[Path]:
    """
    Fetch roots from client via MCP context and cache in ALLOWED_ROOTS.

    [20251215_FEATURE] v2.0.0 - Dynamic roots capability support

    This function requests the list of allowed filesystem roots from the
    MCP client. Roots define the boundaries where the server can operate.

    Args:
        ctx: MCP Context object (from tool execution)

    Returns:
        List of allowed root paths

    Note:
        If ctx is None or client doesn't support roots, returns PROJECT_ROOT.
        Roots are cached in ALLOWED_ROOTS global for subsequent calls.
    """
    global ALLOWED_ROOTS

    if ctx is None:
        return [PROJECT_ROOT]

    try:
        # Request roots from client via MCP protocol
        # Note: list_roots may not be available on all Context implementations
        list_roots_fn = getattr(ctx, "list_roots", None)
        if list_roots_fn is None:
            return [PROJECT_ROOT]
        roots = await list_roots_fn()

        if roots:
            # Convert file:// URIs to Path objects
            ALLOWED_ROOTS = []
            for root in roots:
                uri = str(root.uri)
                if uri.startswith("file://"):
                    # Handle file:// URIs (e.g., file:///home/user/project)
                    # Remove 'file://' prefix and handle Windows paths
                    path_str = uri[7:]  # Remove 'file://'
                    # Windows paths may have extra slash: file:///C:/path
                    if len(path_str) >= 3 and path_str[0] == "/" and path_str[2] == ":":
                        path_str = path_str[1:]  # Remove leading /
                    ALLOWED_ROOTS.append(Path(path_str))
                else:
                    # Non-file URIs - log warning but try as path
                    logger.warning(f"Non-file root URI: {uri}")
                    ALLOWED_ROOTS.append(Path(uri))

            logger.debug(f"Updated ALLOWED_ROOTS from client: {ALLOWED_ROOTS}")
            return ALLOWED_ROOTS
        else:
            return [PROJECT_ROOT]

    except Exception as e:
        # Client may not support roots capability
        logger.debug(f"Could not fetch roots from client: {e}")
        return [PROJECT_ROOT]


# ============================================================================
# CACHING
# ============================================================================


def _get_cache():
    """Get the analysis cache (lazy initialization)."""
    if not CACHE_ENABLED:
        return None
    try:
        # [20251223_CONSOLIDATION] Import from unified cache
        from code_scalpel.cache import get_cache

        return get_cache()
    except ImportError:
        logger.warning("Cache module not available")
        return None


# ============================================================================
# STRUCTURED OUTPUT MODELS
# ============================================================================


class VulnerabilityInfo(BaseModel):
    """Information about a detected vulnerability."""

    type: str = Field(description="Vulnerability type (e.g., SQL Injection)")
    cwe: str = Field(description="CWE identifier")
    severity: str = Field(description="Severity level")
    line: int | None = Field(default=None, description="Line number if known")
    description: str = Field(description="Description of the vulnerability")


class SecurityResult(BaseModel):
    """Result of security analysis."""

    success: bool = Field(description="Whether analysis succeeded")
    server_version: str = Field(default=__version__, description="Code Scalpel version")
    has_vulnerabilities: bool = Field(description="Whether vulnerabilities were found")
    vulnerability_count: int = Field(description="Number of vulnerabilities")
    risk_level: str = Field(description="Overall risk level")
    vulnerabilities: list[VulnerabilityInfo] = Field(default_factory=list, description="List of vulnerabilities")
    taint_sources: list[str] = Field(default_factory=list, description="Identified taint sources")
    error: str | None = Field(default=None, description="Error message if failed")

    # [20251229_FEATURE] v3.3.0 - Pro/Enterprise fields
    semantic_summary: str | None = Field(default=None, description="AI-generated semantic summary (Pro)")
    related_imports: list[str] = Field(default_factory=list, description="Related imports from other files (Pro)")
    pii_redacted: bool = Field(default=False, description="Whether PII was redacted (Enterprise)")
    access_controlled: bool = Field(default=False, description="Whether access control was applied (Enterprise)")


# [20251216_FEATURE] Unified sink detection result model
class UnifiedDetectedSink(BaseModel):
    """Detected sink with confidence and OWASP mapping."""

    pattern: str = Field(description="Sink pattern matched")
    sink_type: str = Field(description="Sink type classification")
    confidence: float = Field(description="Confidence score (0.0-1.0)")
    line: int = Field(default=0, description="Line number of sink occurrence")
    column: int = Field(default=0, description="Column offset of sink occurrence")
    code_snippet: str = Field(default="", description="Snippet around the sink")
    vulnerability_type: str | None = Field(default=None, description="Vulnerability category key")
    owasp_category: str | None = Field(default=None, description="Mapped OWASP Top 10 category")


class UnifiedSinkResult(BaseModel):
    """Result of unified polyglot sink detection."""

    success: bool = Field(description="Whether detection succeeded")
    server_version: str = Field(default=__version__, description="Code Scalpel version")
    language: str = Field(description="Language analyzed")
    sink_count: int = Field(description="Number of sinks detected")
    sinks: list[UnifiedDetectedSink] = Field(default_factory=list, description="Detected sinks meeting threshold")
    coverage_summary: dict[str, Any] = Field(default_factory=dict, description="Summary of sink pattern coverage")
    error: str | None = Field(default=None, description="Error message if failed")

    # [20251229_FEATURE] v3.3.0 - Pro/Enterprise fields
    semantic_summary: str | None = Field(default=None, description="AI-generated semantic summary (Pro)")
    related_imports: list[str] = Field(default_factory=list, description="Related imports from other files (Pro)")
    pii_redacted: bool = Field(default=False, description="Whether PII was redacted (Enterprise)")
    access_controlled: bool = Field(default=False, description="Whether access control was applied (Enterprise)")


class PathCondition(BaseModel):
    """A condition along an execution path."""

    condition: str = Field(description="The condition expression")
    is_satisfiable: bool = Field(description="Whether condition is satisfiable")


class ExecutionPath(BaseModel):
    """An execution path discovered by symbolic execution."""

    path_id: int = Field(description="Unique path identifier")
    conditions: list[str] = Field(description="Conditions along the path")
    final_state: dict[str, Any] = Field(description="Variable values at path end")
    reproduction_input: dict[str, Any] | None = Field(default=None, description="Input values that trigger this path")
    is_reachable: bool = Field(description="Whether path is reachable")


class SymbolicResult(BaseModel):
    """Result of symbolic execution."""

    success: bool = Field(description="Whether analysis succeeded")
    server_version: str = Field(default=__version__, description="Code Scalpel version")
    paths_explored: int = Field(description="Number of execution paths explored")
    paths: list[ExecutionPath] = Field(default_factory=list, description="Discovered execution paths")
    symbolic_variables: list[str] = Field(default_factory=list, description="Variables treated symbolically")
    constraints: list[str] = Field(default_factory=list, description="Discovered constraints")
    error: str | None = Field(default=None, description="Error message if failed")

    # [20251229_FEATURE] v3.3.0 - Pro/Enterprise fields
    semantic_summary: str | None = Field(default=None, description="AI-generated semantic summary (Pro)")
    related_imports: list[str] = Field(default_factory=list, description="Related imports from other files (Pro)")
    pii_redacted: bool = Field(default=False, description="Whether PII was redacted (Enterprise)")
    access_controlled: bool = Field(default=False, description="Whether access control was applied (Enterprise)")


class GeneratedTestCase(BaseModel):
    """A generated test case."""

    path_id: int = Field(description="Path ID this test covers")
    function_name: str = Field(description="Function being tested")
    inputs: dict[str, Any] = Field(description="Input values for this test")
    description: str = Field(description="Human-readable description")
    path_conditions: list[str] = Field(default_factory=list, description="Conditions that define this path")


class GenerationResult(BaseModel):
    """Result of test generation."""

    success: bool = Field(description="Whether generation succeeded")
    server_version: str = Field(default=__version__, description="Code Scalpel version")
    function_name: str = Field(description="Function tests were generated for")
    test_count: int = Field(description="Number of test cases generated")
    test_cases: list[GeneratedTestCase] = Field(default_factory=list, description="Generated test cases")
    # [20260120_BUGFIX] Align metadata fields with core model for tier transparency and truncation
    total_test_cases: int = Field(default=0, description="Total test cases before truncation")
    truncated: bool = Field(default=False, description="Whether results were truncated")
    truncation_warning: str | None = Field(default=None, description="Neutral warning when truncation occurs")
    pytest_code: str = Field(default="", description="Generated pytest code")
    unittest_code: str = Field(default="", description="Generated unittest code")
    error: str | None = Field(default=None, description="Error message if failed")

    # [20251229_FEATURE] v3.3.0 - Pro/Enterprise fields
    semantic_summary: str | None = Field(default=None, description="AI-generated semantic summary (Pro)")
    related_imports: list[str] = Field(default_factory=list, description="Related imports from other files (Pro)")
    pii_redacted: bool = Field(default=False, description="Whether PII was redacted (Enterprise)")
    access_controlled: bool = Field(default=False, description="Whether access control was applied (Enterprise)")
    # [20260120_BUGFIX] Output metadata (mirrors mcp.models.core.GenerationResult)
    tier_applied: str = Field(
        default="community",
        description="Tier used for this generation (community/pro/enterprise)",
    )
    framework_used: str = Field(
        default="pytest",
        description="Test framework used for generation",
    )
    max_test_cases_limit: int | None = Field(
        default=None,
        description="Max test cases limit applied (None=unlimited)",
    )
    data_driven_enabled: bool = Field(
        default=False,
        description="Whether data-driven/parametrized tests were generated",
    )
    bug_reproduction_enabled: bool = Field(
        default=False,
        description="Whether bug reproduction mode was used",
    )


class RefactorSecurityIssue(BaseModel):
    """A security issue found in refactored code."""

    type: str = Field(description="Vulnerability type")
    severity: str = Field(description="Severity level")
    line: int | None = Field(default=None, description="Line number")
    description: str = Field(description="Issue description")
    cwe: str | None = Field(default=None, description="CWE identifier")


class RefactorSimulationResult(BaseModel):
    """Result of refactor simulation."""

    success: bool = Field(description="Whether simulation succeeded")
    server_version: str = Field(default=__version__, description="Code Scalpel version")
    is_safe: bool = Field(description="Whether the refactor is safe to apply")
    status: str = Field(description="Status: safe, unsafe, warning, or error")
    reason: str | None = Field(default=None, description="Reason if not safe")
    security_issues: list[RefactorSecurityIssue] = Field(default_factory=list, description="Security issues found")
    structural_changes: dict[str, Any] = Field(default_factory=dict, description="Functions/classes added/removed")
    warnings: list[str] = Field(default_factory=list, description="Warnings")
    error: str | None = Field(default=None, description="Error message if failed")

    # [20251229_FEATURE] v3.3.0 - Pro/Enterprise fields
    semantic_summary: str | None = Field(default=None, description="AI-generated semantic summary (Pro)")
    related_imports: list[str] = Field(default_factory=list, description="Related imports from other files (Pro)")
    pii_redacted: bool = Field(default=False, description="Whether PII was redacted (Enterprise)")
    access_controlled: bool = Field(default=False, description="Whether access control was applied (Enterprise)")


class CrawlFunctionInfo(BaseModel):
    """Information about a function from project crawl."""

    name: str = Field(description="Function name (qualified if method)")
    lineno: int = Field(description="Line number")
    complexity: int = Field(description="Cyclomatic complexity")


class CrawlClassInfo(BaseModel):
    """Information about a class from project crawl."""

    name: str = Field(description="Class name")
    lineno: int = Field(description="Line number")
    methods: list[CrawlFunctionInfo] = Field(default_factory=list, description="Methods in the class")
    bases: list[str] = Field(default_factory=list, description="Base classes")


class CrawlFileResult(BaseModel):
    """Result of analyzing a single file during crawl."""

    path: str = Field(description="Relative path to the file")
    status: str = Field(description="success or error")
    lines_of_code: int = Field(default=0, description="Lines of code")
    functions: list[CrawlFunctionInfo] = Field(default_factory=list, description="Top-level functions")
    classes: list[CrawlClassInfo] = Field(default_factory=list, description="Classes found")
    imports: list[str] = Field(default_factory=list, description="Import statements")
    complexity_warnings: list[CrawlFunctionInfo] = Field(default_factory=list, description="High-complexity functions")
    error: str | None = Field(default=None, description="Error if failed")


class CrawlSummary(BaseModel):
    """Summary statistics from project crawl."""

    total_files: int = Field(description="Total files scanned")
    successful_files: int = Field(description="Files analyzed successfully")
    failed_files: int = Field(description="Files that failed analysis")
    total_lines_of_code: int = Field(description="Total lines of code")
    total_functions: int = Field(description="Total functions found")
    total_classes: int = Field(description="Total classes found")
    complexity_warnings: int = Field(description="Number of high-complexity functions")


class ProjectCrawlResult(BaseModel):
    """Result of crawling an entire project."""

    # Allow tier-gated feature fields without breaking older clients.
    try:
        from pydantic import ConfigDict as _ConfigDict  # type: ignore

        model_config = _ConfigDict(extra="allow")
    except Exception:

        class Config:  # type: ignore
            extra = "allow"

    success: bool = Field(description="Whether crawl succeeded")
    server_version: str = Field(default=__version__, description="Code Scalpel version")
    root_path: str = Field(description="Project root path")
    timestamp: str = Field(description="When the crawl was performed")
    summary: CrawlSummary = Field(description="Summary statistics")
    files: list[CrawlFileResult] = Field(default_factory=list, description="Analyzed files")
    errors: list[CrawlFileResult] = Field(default_factory=list, description="Files with errors")
    markdown_report: str = Field(default="", description="Markdown report")
    error: str | None = Field(default=None, description="Error if failed")
    # [20260106_FEATURE] v1.0 pre-release - Output transparency metadata
    tier_applied: str | None = Field(
        default=None,
        description="Which tier's rules were applied (community/pro/enterprise)",
    )
    crawl_mode: str | None = Field(
        default=None,
        description="Crawl mode used: 'discovery' (Community) or 'deep' (Pro/Enterprise)",
    )
    files_limit_applied: int | None = Field(
        default=None, description="Max files limit that was applied (None = unlimited)"
    )
    # Tier-gated fields (best-effort, optional)
    language_breakdown: dict[str, int] | None = Field(default=None, description="Counts of files per detected language")
    cache_hits: int | None = Field(
        default=None,
        description="Number of files reused from cache (Pro/Enterprise incremental)",
    )
    compliance_summary: dict[str, Any] | None = Field(
        default=None, description="Enterprise compliance scanning summary"
    )
    framework_hints: list[str] | None = Field(
        default=None, description="Detected frameworks/entrypoints in discovery mode"
    )
    entrypoints: list[str] | None = Field(default=None, description="Detected entrypoint file paths")


class SurgicalExtractionResult(BaseModel):
    """Result of surgical code extraction."""

    success: bool = Field(description="Whether extraction succeeded")
    server_version: str = Field(default=__version__, description="Code Scalpel version")
    name: str = Field(description="Name of extracted element")
    code: str = Field(description="Extracted source code")
    node_type: str = Field(description="Type: function, class, or method")
    line_start: int = Field(default=0, description="Starting line number")
    line_end: int = Field(default=0, description="Ending line number")
    dependencies: list[str] = Field(default_factory=list, description="Names of dependencies")
    imports_needed: list[str] = Field(default_factory=list, description="Required import statements")
    token_estimate: int = Field(default=0, description="Estimated token count")
    error: str | None = Field(default=None, description="Error if failed")


class ContextualExtractionResult(BaseModel):
    """Result of extraction with dependencies included."""

    success: bool = Field(description="Whether extraction succeeded")
    server_version: str = Field(default=__version__, description="Code Scalpel version")
    target_name: str = Field(description="Name of target element")
    target_code: str = Field(description="Target element source code")
    context_code: str = Field(description="Combined dependency source code")
    full_code: str = Field(description="Complete code block for LLM consumption")
    context_items: list[str] = Field(default_factory=list, description="Names of included dependencies")
    total_lines: int = Field(default=0, description="Total lines in extraction")
    # v1.3.0: Line number information
    line_start: int = Field(default=0, description="Starting line number of target")
    line_end: int = Field(default=0, description="Ending line number of target")
    token_estimate: int = Field(default=0, description="Estimated token count")
    error: str | None = Field(default=None, description="Error if failed")

    # [20251216_FEATURE] v2.0.2 - JSX/TSX extraction metadata
    jsx_normalized: bool = Field(default=False, description="Whether JSX syntax was normalized")
    is_server_component: bool = Field(default=False, description="Next.js Server Component (async)")
    is_server_action: bool = Field(default=False, description="Next.js Server Action ('use server')")
    component_type: str | None = Field(default=None, description="React component type: 'functional', 'class', or None")


class PatchResultModel(BaseModel):
    """Result of a surgical code modification."""

    success: bool = Field(description="Whether the patch was applied successfully")
    server_version: str = Field(default=__version__, description="Code Scalpel version")
    file_path: str = Field(description="Path to the modified file")
    target_name: str = Field(description="Name of the modified symbol")
    target_type: str = Field(description="Type: function, class, or method")
    lines_before: int = Field(default=0, description="Lines in original code")
    lines_after: int = Field(default=0, description="Lines in replacement code")
    lines_delta: int = Field(default=0, description="Change in line count")
    backup_path: str | None = Field(default=None, description="Path to backup file")
    error: str | None = Field(default=None, description="Error message if failed")

    # [20251229_FEATURE] v3.3.0 - Pro/Enterprise fields
    semantic_summary: str | None = Field(default=None, description="AI-generated semantic summary (Pro)")
    related_imports: list[str] = Field(default_factory=list, description="Related imports from other files (Pro)")
    pii_redacted: bool = Field(default=False, description="Whether PII was redacted (Enterprise)")
    access_controlled: bool = Field(default=False, description="Whether access control was applied (Enterprise)")


# [20251212_FEATURE] v1.4.0 - New MCP tool models for enhanced AI context


class FileContextResult(BaseModel):
    """Result of get_file_context - file overview without full content."""

    # [20260119_REFACTOR] Align schema with models.core to support rich info objects

    success: bool = Field(description="Whether analysis succeeded")
    server_version: str = Field(default=__version__, description="Code Scalpel version")
    file_path: str = Field(description="Path to the analyzed file")
    language: str = Field(default="python", description="Detected language")
    line_count: int = Field(description="Total lines in file")
    functions: list[FunctionInfo | str] = Field(default_factory=list, description="Function names or detailed info")
    classes: list[ClassInfo | str] = Field(default_factory=list, description="Class names or detailed info")
    imports: list[str] = Field(default_factory=list, description="Import statements (max 20)")
    exports: list[str] = Field(default_factory=list, description="Exported symbols (__all__)")
    complexity_score: int = Field(default=0, description="Overall cyclomatic complexity")
    has_security_issues: bool = Field(default=False, description="Whether file has security issues")
    summary: str = Field(default="", description="Brief description of file purpose")
    # [20251220_FEATURE] v3.0.5 - Truncation communication
    imports_truncated: bool = Field(default=False, description="Whether imports list was truncated")
    total_imports: int = Field(default=0, description="Total imports before truncation")
    error: str | None = Field(default=None, description="Error message if failed")

    # [20251229_FEATURE] v3.3.0 - Pro/Enterprise fields
    semantic_summary: str | None = Field(default=None, description="AI-generated semantic summary (Pro)")
    related_imports: list[str] = Field(default_factory=list, description="Related imports from other files (Pro)")
    pii_redacted: bool = Field(default=False, description="Whether PII was redacted (Enterprise)")
    access_controlled: bool = Field(default=False, description="Whether access control was applied (Enterprise)")


class SymbolReference(BaseModel):
    """A single reference to a symbol."""

    file: str = Field(description="File path containing the reference")
    line: int = Field(description="Line number of the reference")
    column: int = Field(default=0, description="Column number")
    context: str = Field(description="Code snippet showing usage context")
    is_definition: bool = Field(default=False, description="Whether this is the definition")


class SymbolReferencesResult(BaseModel):
    """Result of get_symbol_references - all usages of a symbol."""

    success: bool = Field(description="Whether search succeeded")
    server_version: str = Field(default=__version__, description="Code Scalpel version")
    symbol_name: str = Field(description="Name of the searched symbol")
    definition_file: str | None = Field(default=None, description="File where symbol is defined")
    definition_line: int | None = Field(default=None, description="Line where symbol is defined")
    references: list[SymbolReference] = Field(default_factory=list, description="References found (max 100)")
    total_references: int = Field(default=0, description="Total reference count before truncation")
    # [20251220_FEATURE] v3.0.5 - Truncation communication
    references_truncated: bool = Field(default=False, description="Whether references list was truncated")
    truncation_warning: str | None = Field(default=None, description="Warning if results truncated")
    error: str | None = Field(default=None, description="Error message if failed")

    # [20251229_FEATURE] v3.3.0 - Pro/Enterprise fields
    semantic_summary: str | None = Field(default=None, description="AI-generated semantic summary (Pro)")
    related_imports: list[str] = Field(default_factory=list, description="Related imports from other files (Pro)")
    pii_redacted: bool = Field(default=False, description="Whether PII was redacted (Enterprise)")
    access_controlled: bool = Field(default=False, description="Whether access control was applied (Enterprise)")


# ============================================================================
# HELPER FUNCTIONS
# [20260116_REFACTOR] mcp instance and envelope wrapper moved to protocol.py
# ============================================================================

# Maximum code size for analysis (100KB)
MAX_CODE_SIZE = 100_000


def _validate_code(code: str) -> tuple[bool, str | None]:
    """Validate code before analysis."""
    if not code:
        return False, "Code cannot be empty"
    if not isinstance(code, str):
        return False, "Code must be a string"
    if len(code) > MAX_CODE_SIZE:
        return False, f"Code exceeds maximum size of {MAX_CODE_SIZE} characters"
    return True, None


def _count_complexity(tree: ast.AST) -> int:
    """Estimate cyclomatic complexity."""
    complexity = 1
    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
            complexity += 1
        elif isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
            complexity += len(node.values) - 1
    return complexity


def _analyze_java_code(code: str) -> AnalysisResult:
    """Delegate Java analysis to helper implementation (single source of truth)."""

    return helper_analyze_java_code(code)


def _analyze_javascript_code(code: str, is_typescript: bool = False) -> AnalysisResult:
    """Delegate JavaScript/TypeScript analysis to helper implementation."""

    return helper_analyze_js_code(code, is_typescript=is_typescript)


def _walk_ts_tree(node):
    """Generator to walk all nodes in a tree-sitter tree."""
    yield node
    for child in node.children:
        yield from _walk_ts_tree(child)


def _analyze_code_sync(code: str, language: str = "auto") -> AnalysisResult:
    """Synchronous implementation of analyze_code.

    [20251219_BUGFIX] v3.0.4 - Auto-detect language from content if not specified.
    [20251219_BUGFIX] v3.0.4 - Strip UTF-8 BOM if present.
    [20251220_FEATURE] v3.0.4 - Multi-language support for JavaScript/TypeScript.
    [20251221_FEATURE] v3.1.0 - Use unified_extractor for language detection.
    """
    # [20251219_BUGFIX] Strip UTF-8 BOM if present
    if code.startswith("\ufeff"):
        code = code[1:]

    # [20251221_FEATURE] v3.1.0 - Use unified_extractor for language detection
    if language == "auto" or language is None:
        from code_scalpel.unified_extractor import Language, detect_language

        detected = detect_language(None, code)
        lang_map = {
            Language.PYTHON: "python",
            Language.JAVASCRIPT: "javascript",
            Language.TYPESCRIPT: "typescript",
            Language.JAVA: "java",
        }
        language = lang_map.get(detected, "python")

    # [20260110_FEATURE] v1.0 - Explicit language validation (BEFORE code validation)
    # Must happen before _validate_code() to prevent parsing unsupported languages as Python
    SUPPORTED_LANGUAGES = {"python", "javascript", "typescript", "java"}
    if language.lower() not in SUPPORTED_LANGUAGES:
        return AnalysisResult(
            success=False,
            functions=[],
            classes=[],
            imports=[],
            complexity=0,
            lines_of_code=0,
            error=f"Unsupported language '{language}'. Supported: {', '.join(sorted(SUPPORTED_LANGUAGES))}. Roadmap: Go/Rust in Q1 2026.",
        )

    valid, error = _validate_code(code)
    if not valid:
        return AnalysisResult(
            success=False,
            functions=[],
            classes=[],
            imports=[],
            complexity=0,
            lines_of_code=0,
            issues=[],
            function_details=[],
            class_details=[],
            error=error,
        )

    # Check cache first
    cache = _get_cache()
    cache_config = {"language": language}
    if cache:
        cached = cache.get(code, "analysis", cache_config)
        if cached is not None:
            logger.debug("Cache hit for analyze_code")
            # Convert dict back to AnalysisResult if needed
            if isinstance(cached, dict):
                cached = AnalysisResult(**cached)

            # [20260119_BUGFIX] Ensure cached entries carry metadata for output contract
            if cached.language_detected is None:
                cached.language_detected = language
            if cached.tier_applied is None:
                cached.tier_applied = get_current_tier_from_license()

            return cached

    if language.lower() == "java":
        result = _analyze_java_code(code)
        if result.success:
            # [20260119_BUGFIX] Populate metadata fields for v1.0 output contract
            result.language_detected = "java"
            result.tier_applied = get_current_tier_from_license()
        if cache and result.success:
            cache.set(code, "analysis", result.model_dump(), cache_config)
        return result

    # [20251220_FEATURE] v3.0.4 - Route JavaScript/TypeScript to tree-sitter analyzer
    if language.lower() == "javascript":
        result = _analyze_javascript_code(code, is_typescript=False)
        if result.success:
            # [20260119_BUGFIX] Populate metadata fields for v1.0 output contract
            result.language_detected = "javascript"
            result.tier_applied = get_current_tier_from_license()
        if cache and result.success:
            cache.set(code, "analysis", result.model_dump(), cache_config)
        return result

    if language.lower() == "typescript":
        result = _analyze_javascript_code(code, is_typescript=True)
        if result.success:
            # [20260119_BUGFIX] Populate metadata fields for v1.0 output contract
            result.language_detected = "typescript"
            result.tier_applied = get_current_tier_from_license()
        if cache and result.success:
            cache.set(code, "analysis", result.model_dump(), cache_config)
        return result

    # Python analysis - delegate to helper for tier-gated fields
    result = helper_analyze_code_sync(code=code, language="python", file_path=None)

    if cache and result.success:
        cache.set(code, "analysis", result.model_dump(), cache_config)

    return result


# [20260116_REFACTOR] @mcp.tool() analyze_code moved to tools/analyze.py


def _security_scan_sync(code: str | None = None, file_path: str | None = None) -> SecurityResult:
    """
    Synchronous implementation of security_scan.

    [20251214_FEATURE] v2.0.0 - Added file_path parameter support.
    [20251220_FEATURE] v3.0.4 - Multi-language support via UnifiedSinkDetector
    """
    detected_language = "python"  # Default to Python

    # Handle file_path parameter
    if file_path is not None:
        try:
            path = Path(file_path)
            if not path.exists():
                return SecurityResult(
                    success=False,
                    has_vulnerabilities=False,
                    vulnerability_count=0,
                    risk_level="unknown",
                    error=f"File not found: {file_path}.",
                )
            if not path.is_file():
                return SecurityResult(
                    success=False,
                    has_vulnerabilities=False,
                    vulnerability_count=0,
                    risk_level="unknown",
                    error=f"Path is not a file: {file_path}.",
                )
            code = path.read_text(encoding="utf-8")

            # [20251220_FEATURE] v3.0.4 - Detect language from file extension
            ext = path.suffix.lower()
            extension_map = {
                ".py": "python",
                ".pyi": "python",
                ".pyw": "python",
                ".js": "javascript",
                ".mjs": "javascript",
                ".cjs": "javascript",
                ".jsx": "javascript",
                ".ts": "typescript",
                ".tsx": "typescript",
                ".mts": "typescript",
                ".cts": "typescript",
                ".java": "java",
            }
            detected_language = extension_map.get(ext, "python")
        except Exception as e:
            return SecurityResult(
                success=False,
                has_vulnerabilities=False,
                vulnerability_count=0,
                risk_level="unknown",
                error=f"Failed to read file: {str(e)}.",
            )

    if code is None:
        return SecurityResult(
            success=False,
            has_vulnerabilities=False,
            vulnerability_count=0,
            risk_level="unknown",
            error="Either 'code' or 'file_path' must be provided.",
        )

    valid, error = _validate_code(code)
    if not valid:
        return SecurityResult(
            success=False,
            has_vulnerabilities=False,
            vulnerability_count=0,
            risk_level="unknown",
            error=error,
        )

    # Check cache first
    cache = _get_cache()
    if cache:
        cached = cache.get(code, "security")
        if cached is not None:
            logger.debug("Cache hit for security_scan")
            if isinstance(cached, dict):
                # Reconstruct VulnerabilityInfo objects
                if "vulnerabilities" in cached:
                    cached["vulnerabilities"] = [VulnerabilityInfo(**v) for v in cached["vulnerabilities"]]
                return SecurityResult(**cached)
            return cached

    try:
        vulnerabilities = []
        taint_sources = []

        # [20251220_FEATURE] v3.0.4 - Use UnifiedSinkDetector for non-Python languages
        if detected_language != "python":
            # [20251220_PERF] v3.0.5 - Use singleton detector to avoid rebuilding patterns
            detector = _get_sink_detector()
            detected_sinks = detector.detect_sinks(code, detected_language, min_confidence=0.7)

            for sink in detected_sinks:
                vulnerabilities.append(
                    VulnerabilityInfo(
                        type=getattr(sink, "vulnerability_type", "") or sink.pattern,
                        cwe=f"CWE-{_get_cwe_from_sink_type(sink.sink_type)}",
                        severity="high" if sink.confidence >= 0.9 else "medium",
                        line=sink.line,
                        description=f"Detected {sink.pattern} with {sink.confidence:.0%} confidence",
                    )
                )

            # [20251229_FEATURE] v3.0.4 - Type System Evaporation detection for TypeScript
            if detected_language == "typescript":
                try:
                    from code_scalpel.security.type_safety.type_evaporation_detector import (
                        TypeEvaporationDetector,
                    )

                    te_detector = TypeEvaporationDetector()
                    te_result = te_detector.analyze(code, file_path or "<string>")

                    for vuln in te_result.vulnerabilities:
                        vulnerabilities.append(
                            VulnerabilityInfo(
                                type=f"Type Evaporation: {vuln.risk_type.name}",
                                cwe=vuln.cwe_id,
                                severity=vuln.severity.lower(),
                                line=vuln.location[0],
                                description=vuln.description,
                            )
                        )
                except ImportError:
                    pass  # Type evaporation detector not available
        else:
            # Use full SecurityAnalyzer for Python (supports taint tracking)
            from code_scalpel.security.analyzers.security_analyzer import (
                SecurityAnalyzer,
            )

            analyzer = SecurityAnalyzer()
            result = analyzer.analyze(code).to_dict()

            for vuln in result.get("vulnerabilities", []):
                # Extract line number from sink_location tuple (line, col)
                sink_loc = vuln.get("sink_location")
                line_number = sink_loc[0] if sink_loc and isinstance(sink_loc, (list, tuple)) else None

                vulnerabilities.append(
                    VulnerabilityInfo(
                        type=vuln.get("type", "Unknown"),
                        cwe=vuln.get("cwe", "Unknown"),
                        severity=vuln.get("severity", "medium"),
                        line=line_number,
                        description=vuln.get("description", ""),
                    )
                )

            for source in result.get("taint_sources", []):
                taint_sources.append(str(source))

        vuln_count = len(vulnerabilities)
        if vuln_count == 0:
            risk_level = "low"
        elif vuln_count <= 2:
            risk_level = "medium"
        elif vuln_count <= 5:
            risk_level = "high"
        else:
            risk_level = "critical"

        security_result = SecurityResult(
            success=True,
            has_vulnerabilities=vuln_count > 0,
            vulnerability_count=vuln_count,
            risk_level=risk_level,
            vulnerabilities=vulnerabilities,
            taint_sources=taint_sources,
        )

        # Cache successful result
        if cache:
            cache.set(code, "security", security_result.model_dump())

        return security_result

    except ImportError:
        # Fallback to basic pattern matching if SecurityAnalyzer not available
        return _basic_security_scan(code)
    except Exception as e:
        return SecurityResult(
            success=False,
            has_vulnerabilities=False,
            vulnerability_count=0,
            risk_level="unknown",
            error=f"Security scan failed: {str(e)}.",
        )


def _get_cwe_from_sink_type(sink_type) -> str:
    """[20251220_FEATURE] v3.0.4 - Map sink types to CWE IDs.
    [20251220_FIX] v3.0.5 - Added more sink types, fallback to CWE-20 instead of Unknown.
    """
    cwe_map = {
        "SQL_QUERY": "89",
        "HTML_OUTPUT": "79",
        "DOM_XSS": "79",
        "FILE_PATH": "22",
        "SHELL_COMMAND": "78",
        "EVAL": "94",
        "DESERIALIZATION": "502",
        "XXE": "611",
        "SSRF": "918",
        "SSTI": "1336",
        "WEAK_CRYPTO": "327",
        "PROTOTYPE_POLLUTION": "1321",
        "HARDCODED_SECRET": "798",
        "LDAP_QUERY": "90",
        "NOSQL_QUERY": "943",
        "XPATH_QUERY": "643",
        "LOG_INJECTION": "117",
        "HTTP_REDIRECT": "601",
        "REGEX_DOS": "1333",
    }
    sink_name = getattr(sink_type, "name", str(sink_type))
    # Fallback to CWE-20 (Improper Input Validation) instead of Unknown
    return cwe_map.get(sink_name, "20")


# ==========================================================================
# [20251216_FEATURE] v2.5.0 - Unified sink detection MCP tool
# ==========================================================================


def _sink_coverage_summary(detector: UnifiedSinkDetector) -> dict[str, Any]:
    """Compute coverage summary across languages."""

    by_language: dict[str, int] = {}
    total_patterns = 0

    for vuln_sinks in detector.sinks.values():
        for lang, sink_list in vuln_sinks.items():
            by_language[lang] = by_language.get(lang, 0) + len(sink_list)
            total_patterns += len(sink_list)

    return {
        "total_patterns": total_patterns,
        "by_language": by_language,
    }


def _unified_sink_detect_sync(code: str, language: str, min_confidence: float) -> UnifiedSinkResult:
    """Synchronous unified sink detection wrapper."""

    lang = (language or "").lower()

    if code is None or code.strip() == "":
        return UnifiedSinkResult(
            success=False,
            language=lang,
            sink_count=0,
            error="Parameter 'code' is required.",
            coverage_summary={},
        )

    if not 0.0 <= min_confidence <= 1.0:
        return UnifiedSinkResult(
            success=False,
            language=lang,
            sink_count=0,
            error="Parameter 'min_confidence' must be between 0.0 and 1.0.",
            coverage_summary={},
        )

    # [20251220_PERF] v3.0.5 - Use singleton detector to avoid rebuilding patterns
    detector = _get_sink_detector()
    try:
        detected = detector.detect_sinks(code, lang, min_confidence)
    except ValueError as e:
        return UnifiedSinkResult(
            success=False,
            language=lang,
            sink_count=0,
            error=str(e),
            coverage_summary=_sink_coverage_summary(detector),
        )

    sinks: list[UnifiedDetectedSink] = []
    for sink in detected:
        owasp = detector.get_owasp_category(sink.vulnerability_type)
        sinks.append(
            UnifiedDetectedSink(
                pattern=sink.pattern,
                sink_type=getattr(sink.sink_type, "name", str(sink.sink_type)),
                confidence=sink.confidence,
                line=sink.line,
                column=getattr(sink, "column", 0),
                code_snippet=getattr(sink, "code_snippet", ""),
                vulnerability_type=getattr(sink, "vulnerability_type", None),
                owasp_category=owasp,
            )
        )

    return UnifiedSinkResult(
        success=True,
        language=lang,
        sink_count=len(sinks),
        sinks=sinks,
        coverage_summary=_sink_coverage_summary(detector),
    )


# [20260116_REFACTOR] @mcp.tool() unified_sink_detect moved to tools/security.py


# =============================================================================
# [20251229_FEATURE] v3.0.4 - Cross-File Type Evaporation Detection
# =============================================================================


class TypeEvaporationResultModel(BaseModel):
    """Result of type evaporation analysis."""

    success: bool = Field(description="Whether analysis succeeded")
    server_version: str = Field(default=__version__, description="Code Scalpel version")
    frontend_vulnerabilities: int = Field(default=0, description="Number of frontend vulnerabilities")
    backend_vulnerabilities: int = Field(default=0, description="Number of backend vulnerabilities")
    cross_file_issues: int = Field(default=0, description="Number of cross-file issues")
    matched_endpoints: list[str] = Field(default_factory=list, description="Correlated API endpoints")
    vulnerabilities: list[VulnerabilityInfo] = Field(default_factory=list, description="All vulnerabilities")
    summary: str = Field(default="", description="Analysis summary")
    error: str | None = Field(default=None, description="Error message if failed")

    # [20251229_FEATURE] v3.3.0 - Pro/Enterprise fields
    semantic_summary: str | None = Field(default=None, description="AI-generated semantic summary (Pro)")
    related_imports: list[str] = Field(default_factory=list, description="Related imports from other files (Pro)")
    pii_redacted: bool = Field(default=False, description="Whether PII was redacted (Enterprise)")
    access_controlled: bool = Field(default=False, description="Whether access control was applied (Enterprise)")


def _type_evaporation_scan_sync(
    frontend_code: str,
    backend_code: str,
    frontend_file: str = "frontend.ts",
    backend_file: str = "backend.py",
) -> TypeEvaporationResultModel:
    """
    Synchronous implementation of cross-file type evaporation analysis.

    [20251229_FEATURE] v3.0.4 - Ninja Warrior Stage 3.1 Type System Evaporation
    """
    try:
        from code_scalpel.security.type_safety.type_evaporation_detector import (
            analyze_type_evaporation_cross_file,
        )

        result = analyze_type_evaporation_cross_file(frontend_code, backend_code, frontend_file, backend_file)

        all_vulns: list[VulnerabilityInfo] = []

        # Add frontend vulnerabilities
        for v in result.frontend_result.vulnerabilities:
            all_vulns.append(
                VulnerabilityInfo(
                    type=f"[Frontend] {v.risk_type.name}",
                    cwe=v.cwe_id,
                    severity=v.severity.lower(),
                    line=v.location[0],
                    description=v.description,
                )
            )

        # Add backend vulnerabilities
        for v in result.backend_vulnerabilities:
            all_vulns.append(
                VulnerabilityInfo(
                    type=f"[Backend] {v.vulnerability_type}",
                    cwe=v.cwe_id,
                    severity=getattr(v, "severity", "high"),
                    line=v.sink_location[0] if v.sink_location else None,
                    description=getattr(v, "description", ""),
                )
            )

        # Add cross-file issues
        for v in result.cross_file_issues:
            all_vulns.append(
                VulnerabilityInfo(
                    type=f"[Cross-File] {v.risk_type.name}",
                    cwe=v.cwe_id,
                    severity=v.severity.lower(),
                    line=v.location[0],
                    description=v.description,
                )
            )

        matched = [
            f"{endpoint}: TS line {ts_line} → Python line {py_line}"
            for endpoint, ts_line, py_line in result.matched_endpoints
        ]

        return TypeEvaporationResultModel(
            success=True,
            frontend_vulnerabilities=len(result.frontend_result.vulnerabilities),
            backend_vulnerabilities=len(result.backend_vulnerabilities),
            cross_file_issues=len(result.cross_file_issues),
            matched_endpoints=matched,
            vulnerabilities=all_vulns,
            summary=result.summary(),
        )

    except ImportError as e:
        return TypeEvaporationResultModel(
            success=False,
            error=f"Type evaporation detector not available: {str(e)}.",
        )
    except Exception as e:
        return TypeEvaporationResultModel(
            success=False,
            error=f"Analysis failed: {str(e)}.",
        )


# [20260116_REFACTOR] @mcp.tool() type_evaporation_scan moved to tools/*.py


# =============================================================================
# [20251219_FEATURE] v3.0.4 - A06 Vulnerable Components Detection (OSV API)
# [20251220_FEATURE] v3.0.5 - Added DependencyInfo/DependencyVulnerability models for test compatibility
# =============================================================================


class DependencyVulnerability(BaseModel):
    """A vulnerability associated with a specific dependency.

    [20251220_FEATURE] v3.0.5 - Model for per-dependency vulnerability tracking.
    """

    id: str = Field(description="Vulnerability ID (OSV, CVE, or GHSA)")
    summary: str = Field(default="", description="Brief description of the vulnerability")
    severity: str = Field(default="UNKNOWN", description="Severity: CRITICAL, HIGH, MEDIUM, LOW, UNKNOWN")
    package: str = Field(description="Name of the vulnerable package")
    vulnerable_version: str = Field(description="Version that is vulnerable")
    fixed_version: str | None = Field(default=None, description="First version that fixes this vulnerability")


class DependencyInfo(BaseModel):
    """Information about a scanned dependency.

    [20251220_FEATURE] v3.0.5 - Model for tracking individual dependencies and their vulnerabilities.
    """

    name: str = Field(description="Package name")
    version: str = Field(description="Package version (may be '*' for unspecified)")
    ecosystem: str = Field(description="Package ecosystem: PyPI, npm, Maven, etc.")
    vulnerabilities: list[DependencyVulnerability] = Field(
        default_factory=list, description="Vulnerabilities affecting this dependency"
    )


class DependencyScanResult(BaseModel):
    """Result of a dependency vulnerability scan with per-dependency details.

    [20251220_FEATURE] v3.0.5 - Comprehensive scan result with dependency-level tracking.
    """

    success: bool = Field(description="Whether the scan completed successfully")
    server_version: str = Field(default=__version__, description="Code Scalpel version")
    error: str | None = Field(default=None, description="Error message if failed")

    # [20251229_FEATURE] v3.3.0 - Pro/Enterprise fields
    semantic_summary: str | None = Field(default=None, description="AI-generated semantic summary (Pro)")
    related_imports: list[str] = Field(default_factory=list, description="Related imports from other files (Pro)")
    pii_redacted: bool = Field(default=False, description="Whether PII was redacted (Enterprise)")
    access_controlled: bool = Field(default=False, description="Whether access control was applied (Enterprise)")
    total_dependencies: int = Field(default=0, description="Number of dependencies found")
    vulnerable_count: int = Field(default=0, description="Number of dependencies with vulnerabilities")
    total_vulnerabilities: int = Field(default=0, description="Total number of vulnerabilities found")
    severity_summary: dict[str, int] = Field(default_factory=dict, description="Count of vulnerabilities by severity")
    dependencies: list[DependencyInfo] = Field(
        default_factory=list,
        description="All scanned dependencies with their vulnerabilities",
    )


class VulnerabilityFindingModel(BaseModel):
    """A vulnerability found in a dependency."""

    id: str = Field(description="OSV vulnerability ID (e.g., GHSA-xxxx-xxxx-xxxx)")
    cve_id: str | None = Field(default=None, description="CVE ID if available")
    severity: str = Field(default="UNKNOWN", description="Severity: CRITICAL, HIGH, MEDIUM, LOW, UNKNOWN")
    package_name: str = Field(description="Name of the vulnerable package")
    package_version: str = Field(description="Version of the vulnerable package")
    ecosystem: str = Field(description="Package ecosystem (npm, Maven, PyPI)")
    summary: str = Field(default="", description="Brief description of the vulnerability")
    fixed_versions: list[str] = Field(default_factory=list, description="Versions that fix this vulnerability")
    source_file: str = Field(default="", description="Dependency file where package was found")


class DependencyScanResultModel(BaseModel):
    """Result of a dependency vulnerability scan."""

    success: bool = Field(description="Whether the scan completed successfully")
    server_version: str = Field(default=__version__, description="Code Scalpel version")
    error: str | None = Field(default=None, description="Error message if failed")

    # [20251229_FEATURE] v3.3.0 - Pro/Enterprise fields
    semantic_summary: str | None = Field(default=None, description="AI-generated semantic summary (Pro)")
    related_imports: list[str] = Field(default_factory=list, description="Related imports from other files (Pro)")
    pii_redacted: bool = Field(default=False, description="Whether PII was redacted (Enterprise)")
    access_controlled: bool = Field(default=False, description="Whether access control was applied (Enterprise)")
    dependencies_scanned: int = Field(default=0, description="Number of dependencies checked")
    vulnerabilities_found: int = Field(default=0, description="Number of vulnerabilities found")
    critical_count: int = Field(default=0, description="Number of CRITICAL severity")
    high_count: int = Field(default=0, description="Number of HIGH severity")
    medium_count: int = Field(default=0, description="Number of MEDIUM severity")
    low_count: int = Field(default=0, description="Number of LOW severity")
    findings: list[VulnerabilityFindingModel] = Field(default_factory=list, description="Detailed findings")
    errors: list[str] = Field(default_factory=list, description="Errors encountered during scan")
    summary: str = Field(default="", description="Human-readable summary")


def _scan_dependencies_sync(
    project_root: str | None = None,
    path: str | None = None,
    scan_vulnerabilities: bool = True,
    include_dev: bool = True,
    timeout: float = 30.0,
) -> DependencyScanResult:
    """
    Synchronous implementation of dependency vulnerability scanning.

    [20251219_FEATURE] v3.0.4 - A06 Vulnerable Components
    [20251220_FIX] v3.0.5 - Added timeout parameter for OSV API calls
    [20251220_FEATURE] v3.0.5 - Returns DependencyScanResult with per-dependency tracking

    Args:
        project_root: Path to the project root directory (for backward compatibility)
        path: Alternative parameter name for project_root
        scan_vulnerabilities: Whether to check OSV for vulnerabilities (default True)
        include_dev: Whether to include dev dependencies (default True)
        timeout: Timeout for OSV API calls in seconds

    Returns:
        DependencyScanResult with dependency-level vulnerability tracking
    """
    # Handle parameter aliasing (support both 'path' and 'project_root')
    resolved_path_str = project_root or path or str(PROJECT_ROOT)

    try:
        from code_scalpel.security.dependencies.vulnerability_scanner import (
            DependencyParser,
            VulnerabilityScanner,
        )

        resolved_path = Path(resolved_path_str)
        if not resolved_path.is_absolute():
            resolved_path = PROJECT_ROOT / resolved_path_str

        if not resolved_path.exists():
            return DependencyScanResult(
                success=False,
                error=f"Path not found: {resolved_path_str}",
            )

        # Parse dependencies from files
        all_deps: list[Any] = []
        errors: list[str] = []

        if resolved_path.is_file():
            # Single file scan
            try:
                if resolved_path.name == "requirements.txt":
                    all_deps = DependencyParser.parse_requirements_txt(resolved_path)
                elif resolved_path.name == "pyproject.toml":
                    all_deps = DependencyParser.parse_pyproject_toml(resolved_path)
                elif resolved_path.name == "package.json":
                    all_deps = DependencyParser.parse_package_json(resolved_path)
                elif resolved_path.name == "pom.xml":
                    all_deps = DependencyParser.parse_pom_xml(resolved_path)
                elif resolved_path.name == "build.gradle":
                    all_deps = DependencyParser.parse_build_gradle(resolved_path)
            except Exception as e:
                errors.append(f"Failed to parse {resolved_path}: {str(e)}")
        else:
            # Directory scan - find all dependency files
            dep_files = [
                ("requirements.txt", DependencyParser.parse_requirements_txt),
                ("pyproject.toml", DependencyParser.parse_pyproject_toml),
                ("package.json", DependencyParser.parse_package_json),
                ("pom.xml", DependencyParser.parse_pom_xml),
                ("build.gradle", DependencyParser.parse_build_gradle),
            ]

            for filename, parser in dep_files:
                file_path = resolved_path / filename
                if file_path.exists():
                    try:
                        all_deps.extend(parser(file_path))
                    except Exception as e:
                        errors.append(f"Failed to parse {filename}: {str(e)}")

        # Filter dev dependencies if requested
        if not include_dev:
            all_deps = [d for d in all_deps if not getattr(d, "is_dev", False)]

        # Build DependencyInfo list
        dependency_infos: list[DependencyInfo] = []
        severity_summary: dict[str, int] = {}
        total_vulns = 0
        vulnerable_count = 0

        # Query vulnerabilities if requested
        vuln_map: dict[str, list[dict[str, Any]]] = {}
        if scan_vulnerabilities and all_deps:
            try:
                with VulnerabilityScanner(timeout=timeout) as scanner:
                    vuln_map = scanner.osv_client.query_batch(all_deps)
            except Exception as e:
                errors.append(f"OSV query failed: {str(e)}")

        for dep in all_deps:
            dep_vulns: list[DependencyVulnerability] = []
            dep_key = f"{dep.name}@{dep.version}"

            if dep_key in vuln_map:
                for vuln in vuln_map[dep_key]:
                    severity = _extract_severity(vuln)
                    fixed = _extract_fixed_version(vuln, dep.name)

                    dep_vulns.append(
                        DependencyVulnerability(
                            id=vuln.get("id", "UNKNOWN"),
                            summary=vuln.get("summary", ""),
                            severity=severity,
                            package=dep.name,
                            vulnerable_version=dep.version,
                            fixed_version=fixed,
                        )
                    )

                    severity_summary[severity] = severity_summary.get(severity, 0) + 1
                    total_vulns += 1

            if dep_vulns:
                vulnerable_count += 1

            dependency_infos.append(
                DependencyInfo(
                    name=dep.name,
                    version=dep.version,
                    ecosystem=(dep.ecosystem.value if hasattr(dep.ecosystem, "value") else str(dep.ecosystem)),
                    vulnerabilities=dep_vulns,
                )
            )

        return DependencyScanResult(
            success=True,
            total_dependencies=len(dependency_infos),
            vulnerable_count=vulnerable_count,
            total_vulnerabilities=total_vulns,
            severity_summary=severity_summary,
            dependencies=dependency_infos,
        )

    except ImportError as e:
        return DependencyScanResult(
            success=False,
            error=f"Vulnerability scanner not available: {str(e)}",
        )
    except Exception as e:
        return DependencyScanResult(
            success=False,
            error=f"Scan failed: {str(e)}",
        )


def _extract_severity(vuln: dict[str, Any]) -> str:
    """Extract severity from OSV vulnerability data.

    [20251220_FIX] v3.0.5 - Improved severity extraction from OSV responses.
    """
    # Try database_specific.severity first (most common for GitHub advisories)
    if "database_specific" in vuln:
        db_severity = vuln["database_specific"].get("severity", "")
        if db_severity:
            # Map GitHub severity names to standard names
            severity_map = {
                "CRITICAL": "CRITICAL",
                "HIGH": "HIGH",
                "MODERATE": "MEDIUM",
                "MEDIUM": "MEDIUM",
                "LOW": "LOW",
            }
            return severity_map.get(db_severity.upper(), "UNKNOWN")

    # Try CVSS severity array
    if "severity" in vuln:
        for sev in vuln.get("severity", []):
            if sev.get("type") == "CVSS_V3":
                score_str = sev.get("score", "")
                # Parse CVSS score to severity
                try:
                    # CVSS format: "CVSS:3.1/AV:N/AC:L/..."
                    # or just the score like "7.5"
                    if "/" in score_str:
                        # Extract base score if full vector
                        pass
                    else:
                        score = float(score_str)
                        if score >= 9.0:
                            return "CRITICAL"
                        elif score >= 7.0:
                            return "HIGH"
                        elif score >= 4.0:
                            return "MEDIUM"
                        else:
                            return "LOW"
                except (ValueError, TypeError):
                    pass

    # Try ecosystem_specific
    if "ecosystem_specific" in vuln:
        eco_severity = vuln["ecosystem_specific"].get("severity", "")
        if eco_severity.upper() in ("CRITICAL", "HIGH", "MEDIUM", "MODERATE", "LOW"):
            return "MEDIUM" if eco_severity.upper() == "MODERATE" else eco_severity.upper()

    return "UNKNOWN"


def _extract_fixed_version(vuln: dict[str, Any], package_name: str) -> str | None:
    """Extract fixed version from OSV vulnerability data."""
    for affected in vuln.get("affected", []):
        if affected.get("package", {}).get("name") == package_name:
            for rng in affected.get("ranges", []):
                for event in rng.get("events", []):
                    if "fixed" in event:
                        return event["fixed"]
    return None


def _scan_dependencies_sync_legacy(path: str, timeout: float = 30.0) -> DependencyScanResultModel:
    """
    Synchronous implementation of dependency vulnerability scanning.

    [20251219_FEATURE] v3.0.4 - A06 Vulnerable Components
    [20251220_FIX] v3.0.5 - Added timeout parameter for OSV API calls
    """
    try:
        from code_scalpel.security.dependencies.vulnerability_scanner import (
            VulnerabilityScanner,
        )

        resolved_path = Path(path)
        if not resolved_path.is_absolute():
            resolved_path = PROJECT_ROOT / path

        if not resolved_path.exists():
            return DependencyScanResultModel(
                success=False,
                errors=[f"Path not found: {path}"],
            )

        with VulnerabilityScanner(timeout=timeout) as scanner:
            if resolved_path.is_file():
                result = scanner.scan_file(resolved_path)
            else:
                result = scanner.scan_directory(resolved_path)

        # Convert to Pydantic models and count severities
        findings = []
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}

        for f in result.findings:
            findings.append(
                VulnerabilityFindingModel(
                    id=f.id,
                    cve_id=f.cve_id,
                    severity=f.severity,
                    package_name=f.package_name,
                    package_version=f.package_version,
                    ecosystem=f.ecosystem,
                    summary=f.summary,
                    fixed_versions=f.fixed_versions,
                    source_file=f.source_file,
                )
            )
            if f.severity in severity_counts:
                severity_counts[f.severity] += 1

        # Generate summary
        if result.vulnerabilities_found == 0:
            summary = f"✅ No vulnerabilities found in {result.dependencies_scanned} dependencies."
        else:
            summary = (
                f"⚠️ Found {result.vulnerabilities_found} vulnerabilities in "
                f"{result.dependencies_scanned} dependencies: "
                f"{severity_counts['CRITICAL']} critical, {severity_counts['HIGH']} high, "
                f"{severity_counts['MEDIUM']} medium, {severity_counts['LOW']} low."
            )

        return DependencyScanResultModel(
            success=True,
            dependencies_scanned=result.dependencies_scanned,
            vulnerabilities_found=result.vulnerabilities_found,
            critical_count=severity_counts["CRITICAL"],
            high_count=severity_counts["HIGH"],
            medium_count=severity_counts["MEDIUM"],
            low_count=severity_counts["LOW"],
            findings=findings,
            errors=result.errors,
            summary=summary,
        )

    except ImportError as e:
        return DependencyScanResultModel(
            success=False,
            errors=[f"Vulnerability scanner not available: {e}"],
        )
    except Exception as e:
        return DependencyScanResultModel(
            success=False,
            errors=[f"Scan failed: {e}"],
        )


# [20260116_REFACTOR] @mcp.tool() scan_dependencies moved to tools/*.py


# [20260116_REFACTOR] @mcp.tool() security_scan moved to tools/*.py


def _basic_security_scan(code: str) -> SecurityResult:
    """Fallback security scan using pattern matching."""
    vulnerabilities = []
    taint_sources = []

    # Detect common dangerous patterns
    patterns = [
        (
            "execute(",
            "SQL Injection",
            "CWE-89",
            "Possible SQL injection via execute()",
        ),
        ("cursor.execute", "SQL Injection", "CWE-89", "SQL query execution detected"),
        ("os.system(", "Command Injection", "CWE-78", "os.system() call detected"),
        (
            "subprocess.call(",
            "Command Injection",
            "CWE-78",
            "subprocess.call() detected",
        ),
        ("eval(", "Code Injection", "CWE-94", "eval() call detected"),
        ("exec(", "Code Injection", "CWE-94", "exec() call detected"),
        (
            "render_template_string(",
            "XSS",
            "CWE-79",
            "Template injection risk",
        ),
    ]

    for line_num, line in enumerate(code.splitlines(), 1):
        for pattern, vuln_type, cwe, desc in patterns:
            if pattern in line:
                vulnerabilities.append(
                    VulnerabilityInfo(
                        type=vuln_type,
                        cwe=cwe,
                        severity="high" if "Injection" in vuln_type else "medium",
                        line=line_num,
                        description=desc,
                    )
                )

    # Detect taint sources
    source_patterns = ["request.args", "request.form", "input(", "sys.argv"]
    for pattern in source_patterns:
        if pattern in code:
            taint_sources.append(pattern)

    vuln_count = len(vulnerabilities)
    if vuln_count == 0:
        risk_level = "low"
    elif vuln_count <= 2:
        risk_level = "medium"
    else:
        risk_level = "high"

    return SecurityResult(
        success=True,
        has_vulnerabilities=vuln_count > 0,
        vulnerability_count=vuln_count,
        risk_level=risk_level,
        vulnerabilities=vulnerabilities,
        taint_sources=taint_sources,
    )


def _symbolic_execute_sync(code: str, max_paths: int = 10) -> SymbolicResult:
    """Synchronous implementation of symbolic_execute."""
    valid, error = _validate_code(code)
    if not valid:
        return SymbolicResult(
            success=False,
            paths_explored=0,
            error=error,
        )

    # Check cache first (symbolic execution is expensive!)
    cache = _get_cache()
    # [20251214_FEATURE] Include schema to bust caches when model format changes
    cache_config = {"max_paths": max_paths, "model_schema": "friendly_names_v20251214"}
    if cache:
        cached = cache.get(code, "symbolic", cache_config)
        if cached is not None:
            logger.debug("Cache hit for symbolic_execute")
            if isinstance(cached, dict):
                # Reconstruct ExecutionPath objects
                if "paths" in cached:
                    cached["paths"] = [ExecutionPath(**p) for p in cached["paths"]]
                return SymbolicResult(**cached)
            return cached

    try:
        # Import here to avoid circular imports
        from code_scalpel.symbolic_execution_tools import SymbolicAnalyzer
        from code_scalpel.symbolic_execution_tools.engine import PathStatus

        analyzer = SymbolicAnalyzer(max_loop_iterations=max_paths)
        result = analyzer.analyze(code)

        paths = []
        all_constraints = []
        for _i, path in enumerate(result.paths):
            # PathResult has: path_id, status, constraints, variables, model
            # Convert Z3 constraints to string conditions
            conditions = [str(c) for c in path.constraints] if path.constraints else []
            all_constraints.extend(conditions)

            paths.append(
                ExecutionPath(
                    path_id=path.path_id,
                    conditions=conditions,
                    final_state=path.variables or {},
                    reproduction_input=path.model or {},
                    is_reachable=path.status == PathStatus.FEASIBLE,
                )
            )

        # If symbolic execution didn't find variables or constraints,
        # supplement with AST-based analysis
        symbolic_vars = list(result.all_variables.keys()) if result.all_variables else []
        constraints_list = list(set(all_constraints))

        if not symbolic_vars or not constraints_list:
            basic = _basic_symbolic_analysis(code)
            if not symbolic_vars and basic.symbolic_variables:
                symbolic_vars = basic.symbolic_variables
            if not constraints_list and basic.constraints:
                constraints_list = basic.constraints
            # Also use basic paths if symbolic found nothing
            if not paths and basic.paths:
                paths = basic.paths

        symbolic_result = SymbolicResult(
            success=True,
            paths_explored=len(paths) if paths else result.total_paths,
            paths=paths,
            symbolic_variables=symbolic_vars,
            constraints=constraints_list,
        )

        # Cache successful result
        if cache:
            cache.set(code, "symbolic", symbolic_result.model_dump(), cache_config)

        return symbolic_result

    except ImportError as e:
        # Fallback to basic path analysis - SymbolicAnalyzer not available
        logger.warning(f"Symbolic execution not available (ImportError: {e}), using basic analysis")
        basic_result = _basic_symbolic_analysis(code)
        # Indicate fallback in error field without marking as failure
        basic_result.error = f"[FALLBACK] Symbolic engine not available, using AST analysis: {e}"
        return basic_result
    except Exception as e:
        # If symbolic execution fails (e.g., unsupported AST nodes like f-strings),
        # fall back to basic AST-based analysis instead of returning an error
        # [20251220_FIX] v3.0.5 - Improved error reporting: include original error in result
        logger.warning(f"Symbolic execution failed, using basic analysis: {e}")
        basic_result = _basic_symbolic_analysis(code)
        # Indicate fallback occurred without marking as failure
        basic_result.error = f"[FALLBACK] Symbolic execution failed ({type(e).__name__}: {e}), using AST analysis"
        return basic_result


# [20260116_REFACTOR] @mcp.tool() symbolic_execute moved to tools/*.py


def _basic_symbolic_analysis(code: str) -> SymbolicResult:
    """Fallback symbolic analysis using AST inspection."""
    try:
        tree = ast.parse(code)

        # Count branches
        branch_count = 0
        symbolic_vars = []
        conditions = []

        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                branch_count += 1
                conditions.append(ast.unparse(node.test))
            elif isinstance(node, ast.While):
                branch_count += 1
                conditions.append(f"while: {ast.unparse(node.test)}")
            elif isinstance(node, ast.For):
                branch_count += 1
                if isinstance(node.target, ast.Name):
                    symbolic_vars.append(node.target.id)
            elif isinstance(node, ast.FunctionDef):
                for arg in node.args.args:
                    symbolic_vars.append(arg.arg)

        # Estimate paths (2^branches, capped)
        estimated_paths = min(2**branch_count, 10)

        paths = [
            ExecutionPath(
                path_id=i,
                conditions=conditions[: i + 1] if i < len(conditions) else conditions,
                final_state={},
                reproduction_input=None,
                is_reachable=True,
            )
            for i in range(estimated_paths)
        ]

        return SymbolicResult(
            success=True,
            paths_explored=estimated_paths,
            paths=paths,
            symbolic_variables=list(set(symbolic_vars)),
            constraints=conditions,
        )

    except Exception as e:
        return SymbolicResult(
            success=False,
            paths_explored=0,
            error=f"Basic analysis failed: {str(e)}",
        )


# ============================================================================
# TEST GENERATION
# ============================================================================


def _generate_tests_sync(
    code: str | None = None,
    file_path: str | None = None,
    function_name: str | None = None,
    framework: str = "pytest",
) -> GenerationResult:
    """Synchronous implementation of generate_unit_tests.

    [20251220_FIX] v3.0.5 - Added file_path parameter for consistency with other tools.
    """
    # Read from file if file_path provided
    if file_path and not code:
        try:
            resolved = Path(file_path)
            if not resolved.is_absolute():
                resolved = PROJECT_ROOT / file_path
            if not resolved.exists():
                return GenerationResult(
                    success=False,
                    function_name=function_name or "unknown",
                    test_count=0,
                    error=f"File not found: {file_path}.",
                )
            code = resolved.read_text(encoding="utf-8")
        except Exception as e:
            return GenerationResult(
                success=False,
                function_name=function_name or "unknown",
                test_count=0,
                error=f"Failed to read file: {str(e)}.",
            )

    if not code:
        return GenerationResult(
            success=False,
            function_name=function_name or "unknown",
            test_count=0,
            error="Either 'code' or 'file_path' must be provided.",
        )

    valid, error = _validate_code(code)
    if not valid:
        return GenerationResult(
            success=False,
            function_name=function_name or "unknown",
            test_count=0,
            error=error,
        )

    try:
        from code_scalpel.generators import TestGenerator

        generator = TestGenerator(framework=framework)
        result = generator.generate(code, function_name=function_name)

        test_cases = [
            GeneratedTestCase(
                path_id=tc.path_id,
                function_name=tc.function_name,
                inputs=tc.inputs,
                description=tc.description,
                path_conditions=tc.path_conditions,
            )
            for tc in result.test_cases
        ]

        return GenerationResult(
            success=True,
            function_name=result.function_name,
            test_count=len(test_cases),
            test_cases=test_cases,
            pytest_code=result.pytest_code,
            unittest_code=result.unittest_code,
        )

    except Exception as e:
        return GenerationResult(
            success=False,
            function_name=function_name or "unknown",
            test_count=0,
            error=f"Test generation failed: {str(e)}",
        )


# [20260116_REFACTOR] @mcp.tool() generate_unit_tests moved to tools/*.py


# ============================================================================
# REFACTOR SIMULATION
# ============================================================================


def _simulate_refactor_sync(
    original_code: str,
    new_code: str | None = None,
    patch: str | None = None,
    strict_mode: bool = False,
) -> RefactorSimulationResult:
    """Synchronous implementation of simulate_refactor."""
    valid, error = _validate_code(original_code)
    if not valid:
        return RefactorSimulationResult(
            success=False,
            is_safe=False,
            status="error",
            error=f"Invalid original code: {error}.",
        )

    if new_code is None and patch is None:
        return RefactorSimulationResult(
            success=False,
            is_safe=False,
            status="error",
            error="Must provide either 'new_code' or 'patch'.",
        )

    try:
        from code_scalpel.generators import RefactorSimulator

        simulator = RefactorSimulator(strict_mode=strict_mode)
        result = simulator.simulate(
            original_code=original_code,
            new_code=new_code,
            patch=patch,
        )

        security_issues = [
            RefactorSecurityIssue(
                type=issue.type,
                severity=issue.severity,
                line=issue.line,
                description=issue.description,
                cwe=issue.cwe,
            )
            for issue in result.security_issues
        ]

        return RefactorSimulationResult(
            success=True,
            is_safe=result.is_safe,
            status=result.status.value,
            reason=result.reason,
            security_issues=security_issues,
            structural_changes=result.structural_changes,
            warnings=result.warnings,
        )

    except Exception as e:
        return RefactorSimulationResult(
            success=False,
            is_safe=False,
            status="error",
            error=f"Simulation failed: {str(e)}",
        )


# [20260116_REFACTOR] @mcp.tool() simulate_refactor moved to tools/*.py


def _crawl_project_discovery(
    root_path: str,
    exclude_dirs: list[str] | None = None,
) -> ProjectCrawlResult:
    """
    Discovery-only crawl for Community tier.

    Provides file inventory and structure without deep analysis:
    - Lists Python files and their paths
    - Identifies entrypoint patterns (main blocks, CLI commands)
    - Basic statistics (file count, directory structure)
    - NO complexity analysis
    - NO function/class details
    - NO file contents

    [20251223_FEATURE] v3.2.8 - Community tier discovery crawl.
    """
    import os
    from datetime import datetime
    from pathlib import Path

    try:
        root = Path(root_path)
        if not root.exists():
            raise FileNotFoundError(f"Project root not found: {root_path}")

        # Default excludes
        default_excludes = {
            "__pycache__",
            ".git",
            ".venv",
            "venv",
            "node_modules",
            ".pytest_cache",
            ".mypy_cache",
            "dist",
            "build",
            ".tox",
            "htmlcov",
            ".eggs",
            "*.egg-info",
        }
        if exclude_dirs:
            default_excludes.update(exclude_dirs)

        python_files = []
        entrypoints = []
        total_files = 0

        # Walk the directory tree
        for dirpath, dirnames, filenames in os.walk(root):
            # Filter out excluded directories
            dirnames[:] = [d for d in dirnames if d not in default_excludes]

            for filename in filenames:
                if filename.endswith(".py"):
                    total_files += 1
                    file_path = Path(dirpath) / filename
                    rel_path = str(file_path.relative_to(root))

                    # Check for entrypoint patterns without parsing
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="ignore")
                        is_entrypoint = (
                            'if __name__ == "__main__"' in content
                            or "if __name__ == '__main__'" in content
                            or "@click.command" in content
                            or "@app.route" in content
                            or "def main(" in content
                        )

                        if is_entrypoint:
                            entrypoints.append(rel_path)

                        # Create minimal file result (discovery mode)
                        python_files.append(
                            CrawlFileResult(
                                path=rel_path,
                                status="discovered",
                                lines_of_code=len(content.splitlines()),
                                functions=[],
                                classes=[],
                                imports=[],
                                complexity_warnings=[],
                                error=None,
                            )
                        )
                    except Exception as e:
                        python_files.append(
                            CrawlFileResult(
                                path=rel_path,
                                status="error",
                                lines_of_code=0,
                                error=f"Could not read file: {str(e)}",
                            )
                        )

        # Build discovery report
        report = f"""# Project Discovery Report (Community)

## Summary
- Total Python files: {total_files}
- Entrypoints detected: {len(entrypoints)}

## Structure
This is a discovery-only crawl providing file inventory and structure.
For detailed analysis including complexity, dependencies, and code metrics,
upgrade to Pro or Enterprise tier.

## Entrypoints
{chr(10).join(f"- {ep}" for ep in entrypoints) if entrypoints else "(none detected)"}

## Files
{chr(10).join(f"- {f.path}" for f in python_files[:50])}
{"..." if len(python_files) > 50 else ""}

**Note:** Upgrade to Pro/Enterprise for:
- Complexity analysis
- Function and class inventories
- Cross-file dependency resolution
- Detailed code metrics
"""

        summary = CrawlSummary(
            total_files=total_files,
            successful_files=len([f for f in python_files if f.status == "discovered"]),
            failed_files=len([f for f in python_files if f.status == "error"]),
            total_lines_of_code=sum(f.lines_of_code for f in python_files),
            total_functions=0,  # Not analyzed in discovery mode
            total_classes=0,  # Not analyzed in discovery mode
            complexity_warnings=0,  # Not analyzed in discovery mode
        )

        return ProjectCrawlResult(
            success=True,
            root_path=str(root),
            timestamp=datetime.now().isoformat(),
            summary=summary,
            files=python_files,
            errors=[],
            markdown_report=report,
        )

    except Exception as e:
        return ProjectCrawlResult(
            success=False,
            root_path=root_path,
            timestamp=datetime.now().isoformat(),
            summary=CrawlSummary(
                total_files=0,
                successful_files=0,
                failed_files=0,
                total_lines_of_code=0,
                total_functions=0,
                total_classes=0,
                complexity_warnings=0,
            ),
            error=f"Discovery crawl failed: {str(e)}",
        )


def _crawl_project_sync(
    root_path: str,
    exclude_dirs: list[str] | None = None,
    complexity_threshold: int = 10,
    include_report: bool = True,
) -> ProjectCrawlResult:
    """Synchronous implementation of crawl_project."""
    try:
        from code_scalpel.project_crawler import ProjectCrawler

        crawler = ProjectCrawler(
            root_path,
            exclude_dirs=frozenset(exclude_dirs) if exclude_dirs else None,
            complexity_threshold=complexity_threshold,
        )
        result = crawler.crawl()

        # Convert to Pydantic models
        def to_func_info(f) -> CrawlFunctionInfo:
            return CrawlFunctionInfo(
                name=f.qualified_name,
                lineno=f.lineno,
                complexity=f.complexity,
            )

        def to_class_info(c) -> CrawlClassInfo:
            return CrawlClassInfo(
                name=c.name,
                lineno=c.lineno,
                methods=[to_func_info(m) for m in c.methods],
                bases=c.bases,
            )

        def to_file_result(fr, root: str) -> CrawlFileResult:
            import os

            return CrawlFileResult(
                path=os.path.relpath(fr.path, root),
                status=fr.status,
                lines_of_code=fr.lines_of_code,
                functions=[to_func_info(f) for f in fr.functions],
                classes=[to_class_info(c) for c in fr.classes],
                imports=fr.imports,
                complexity_warnings=[to_func_info(f) for f in fr.complexity_warnings],
                error=fr.error,
            )

        summary = CrawlSummary(
            total_files=result.total_files,
            successful_files=len(result.files_analyzed),
            failed_files=len(result.files_with_errors),
            total_lines_of_code=result.total_lines_of_code,
            total_functions=result.total_functions,
            total_classes=result.total_classes,
            complexity_warnings=len(result.all_complexity_warnings),
        )

        files = [to_file_result(f, result.root_path) for f in result.files_analyzed]
        errors = [to_file_result(f, result.root_path) for f in result.files_with_errors]

        report = ""
        if include_report:
            report = crawler.generate_report(result)

        return ProjectCrawlResult(
            success=True,
            root_path=result.root_path,
            timestamp=result.timestamp,
            summary=summary,
            files=files,
            errors=errors,
            markdown_report=report,
        )

    except Exception as e:
        return ProjectCrawlResult(
            success=False,
            root_path=root_path,
            timestamp="",
            summary=CrawlSummary(
                total_files=0,
                successful_files=0,
                failed_files=0,
                total_lines_of_code=0,
                total_functions=0,
                total_classes=0,
                complexity_warnings=0,
            ),
            error=f"Crawl failed: {str(e)}",
        )


# --- Helper functions for extract_code (refactored for maintainability) ---


def _extraction_error(target_name: str, error: str) -> ContextualExtractionResult:
    """Create a standardized error result for extraction failures."""
    return ContextualExtractionResult(
        success=False,
        target_name=target_name,
        target_code="",
        context_code="",
        full_code="",
        error=error,
    )


async def _extract_polyglot(
    target_type: str,
    target_name: str,
    file_path: str | None,
    code: str | None,
    language: Any,
    include_token_estimate: bool,
) -> ContextualExtractionResult:
    """
    [20251214_FEATURE] v2.0.0 - Multi-language extraction using PolyglotExtractor.

    Handles extraction for JavaScript, TypeScript, and Java using tree-sitter
    and the Unified IR system.

    Args:
        target_type: "function", "class", or "method"
        target_name: Name of element to extract
        file_path: Path to source file
        code: Source code string (if file_path not provided)
        language: Language enum value
        include_token_estimate: Include token count estimate

    Returns:
        ContextualExtractionResult with extracted code
    """
    # [20251221_FEATURE] v3.1.0 - Use UnifiedExtractor instead of PolyglotExtractor
    from code_scalpel.mcp.path_resolver import resolve_path
    from code_scalpel.unified_extractor import UnifiedExtractor

    if file_path is None and code is None:
        return _extraction_error(target_name, "Must provide either 'file_path' or 'code' argument")

    try:
        # Create extractor from file or code
        if file_path is not None:
            resolved_path = resolve_path(file_path, str(PROJECT_ROOT))
            extractor = UnifiedExtractor.from_file(resolved_path, language)
        else:
            # code is guaranteed to be str here (checked earlier in function)
            assert code is not None
            extractor = UnifiedExtractor(code, language=language)

        # Perform extraction
        result = extractor.extract(target_type, target_name)

        if not result.success:
            return _extraction_error(target_name, result.error or "Extraction failed")

        token_estimate = result.token_estimate if include_token_estimate else 0

        # [20251216_FEATURE] v2.0.2 - Include JSX/TSX metadata in result
        return ContextualExtractionResult(
            success=True,
            target_name=target_name,
            target_code=result.code,
            context_code="",  # Cross-file deps not yet supported for non-Python
            full_code=result.code,
            context_items=[],
            total_lines=result.end_line - result.start_line + 1,
            line_start=result.start_line,
            line_end=result.end_line,
            token_estimate=token_estimate,
            jsx_normalized=result.jsx_normalized,
            is_server_component=result.is_server_component,
            is_server_action=result.is_server_action,
            component_type=result.component_type,
        )
    except FileNotFoundError as e:
        return _extraction_error(target_name, str(e))
    except Exception as e:
        return _extraction_error(target_name, f"Extraction failed: {str(e)}")


def _create_extractor(
    file_path: str | None, code: str | None, target_name: str
) -> tuple[SurgicalExtractor | None, ContextualExtractionResult | None]:
    """
    Create a SurgicalExtractor from file_path or code.

    [20251214_FEATURE] v1.5.3 - Integrated PathResolver for intelligent path resolution

    Returns (extractor, None) on success, (None, error_result) on failure.
    """
    from code_scalpel import SurgicalExtractor
    from code_scalpel.mcp.path_resolver import resolve_path

    if file_path is None and code is None:
        return None, _extraction_error(target_name, "Must provide either 'file_path' or 'code' argument")

    if file_path is not None:
        try:
            # [20251214_FEATURE] Use PathResolver for intelligent path resolution
            resolved_path = resolve_path(file_path, str(PROJECT_ROOT))
            return SurgicalExtractor.from_file(resolved_path), None
        except FileNotFoundError as e:
            # PathResolver provides helpful error messages
            return None, _extraction_error(target_name, str(e))
        except ValueError as e:
            return None, _extraction_error(target_name, str(e))
    else:
        try:
            # code is guaranteed to be str here (we checked file_path is None and code is not None above)
            assert code is not None
            return SurgicalExtractor(code), None
        except (SyntaxError, ValueError) as e:
            return None, _extraction_error(target_name, f"Syntax error in code: {str(e)}")


def _extract_method(extractor: SurgicalExtractor, target_name: str):
    """Extract a method, handling the ClassName.method_name parsing."""
    if "." not in target_name:
        return None, _extraction_error(target_name, "Method name must be 'ClassName.method_name' format")
    class_name, method_name = target_name.rsplit(".", 1)
    return extractor.get_method(class_name, method_name), None


def _perform_extraction(
    extractor: SurgicalExtractor,
    target_type: str,
    target_name: str,
    include_context: bool,
    include_cross_file_deps: bool,
    context_depth: int,
    file_path: str | None,
):
    """
    Perform the actual extraction based on target type and options.

    Returns (result, cross_file_result, error_result).
    """
    from code_scalpel.surgical_extractor import CrossFileResolution

    cross_file_result: CrossFileResolution | None = None

    # CROSS-FILE RESOLUTION PATH
    if include_cross_file_deps and file_path is not None:
        if target_type in ("function", "class"):
            cross_file_result = extractor.resolve_cross_file_dependencies(
                target_name=target_name,
                target_type=target_type,
                max_depth=context_depth,
            )
            return cross_file_result.target, cross_file_result, None
        else:
            # Method - fall back to regular extraction
            result, error = _extract_method(extractor, target_name)
            return result, None, error

    # INTRA-FILE CONTEXT PATH
    if target_type == "function":
        if include_context:
            return (
                extractor.get_function_with_context(target_name, max_depth=context_depth),
                None,
                None,
            )
        return extractor.get_function(target_name), None, None

    if target_type == "class":
        if include_context:
            return (
                extractor.get_class_with_context(target_name, max_depth=context_depth),
                None,
                None,
            )
        return extractor.get_class(target_name), None, None

    if target_type == "method":
        result, error = _extract_method(extractor, target_name)
        return result, None, error

    return (
        None,
        None,
        _extraction_error(
            target_name,
            f"Unknown target_type: {target_type}. Use 'function', 'class', or 'method'.",
        ),
    )


def _process_cross_file_context(cross_file_result) -> tuple[str, list[str]]:
    """Process cross-file resolution results into context_code and context_items."""
    if cross_file_result is None or not cross_file_result.external_symbols:
        return "", []

    external_parts = []
    external_names = []
    for sym in cross_file_result.external_symbols:
        external_parts.append(f"# From {sym.source_file}")
        external_parts.append(sym.code)
        external_names.append(f"{sym.name} ({sym.source_file})")

    context_code = "\n\n".join(external_parts)

    # Add unresolved imports as a comment
    if cross_file_result.unresolved_imports:
        unresolved_comment = "# Unresolved imports: " + ", ".join(cross_file_result.unresolved_imports)
        context_code = unresolved_comment + "\n\n" + context_code

    return context_code, external_names


def _build_full_code(imports_needed: list[str], context_code: str, target_code: str) -> str:
    """Build the combined full_code for LLM consumption."""
    parts = []
    if imports_needed:
        parts.append("\n".join(imports_needed))
    if context_code:
        parts.append(context_code)
    parts.append(target_code)
    return "\n\n".join(parts)


def _extract_code_sync(
    target_type: str,
    target_name: str,
    file_path: str | None,
    code: str | None = None,
    include_context: bool = True,
    include_token_estimate: bool = True,
) -> ContextualExtractionResult:
    from code_scalpel.surgical_extractor import SurgicalExtractor

    if not file_path and not code:
        return _extraction_error(target_name, "Must provide either 'file_path' or 'code' argument")

    extractor = SurgicalExtractor.from_file(file_path) if file_path is not None else SurgicalExtractor(code or "")

    context = None
    if target_type == "class":
        target = extractor.get_class(target_name)
        if include_context:
            context = extractor.get_class_with_context(target_name)
    elif target_type == "method":
        if "." not in target_name:
            return _extraction_error(target_name, "Method targets must use Class.method format")
        class_name, method_name = target_name.split(".", 1)
        target = extractor.get_method(class_name, method_name)
        if include_context:
            # [20251220_FEATURE] Use get_method_with_context for token-efficient extraction
            # Falls back to class context if method-level context unavailable
            if hasattr(extractor, "get_method_with_context"):
                context = extractor.get_method_with_context(class_name, method_name)
            else:
                context = extractor.get_class_with_context(class_name)
    else:
        target = extractor.get_function(target_name)
        if include_context:
            context = extractor.get_function_with_context(target_name)

    if not target.success:
        return _extraction_error(target_name, target.error or "Extraction failed")

    context_code = context.context_code if context else ""
    context_items = context.context_items if context else (target.dependencies or [])
    full_code = context.full_code if context else target.code
    total_lines = (
        context.total_lines
        if context
        else (
            target.line_end - target.line_start + 1
            if target.line_end and target.line_start
            else max(1, full_code.count("\n") + 1)
        )
    )
    token_estimate = context.token_estimate if context and include_token_estimate else 0

    return ContextualExtractionResult(
        success=True,
        server_version=__version__,
        target_name=target_name,
        target_code=target.code,
        context_code=context_code,
        full_code=full_code,
        context_items=context_items,
        total_lines=total_lines,
        line_start=target.line_start,
        line_end=target.line_end,
        token_estimate=token_estimate,
        error=None,
    )


def _get_file_context_sync(file_path: str) -> FileContextResult:
    """
    Synchronous implementation of get_file_context.

    [20251214_FEATURE] v1.5.3 - Integrated PathResolver for intelligent path resolution
    [20251220_FEATURE] v3.0.5 - Multi-language support via file extension detection
    """
    from code_scalpel.mcp.path_resolver import resolve_path

    # Language detection by file extension
    LANG_EXTENSIONS = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".java": "java",
    }

    try:
        # [20251214_FEATURE] Use PathResolver for intelligent path resolution
        try:
            # [20260119_BUGFIX] Safe fallback when PROJECT_ROOT not initialized
            try:
                base_root = str(PROJECT_ROOT)  # type: ignore[name-defined]
            except NameError:
                base_root = str(Path.cwd())
            resolved_path = resolve_path(file_path, base_root)
            path = Path(resolved_path)
        except FileNotFoundError as e:
            # PathResolver provides helpful error messages
            return FileContextResult(
                success=False,
                file_path=file_path,
                line_count=0,
                error=str(e),
            )

        code = path.read_text(encoding="utf-8")
        lines = code.splitlines()

        # [20251220_FEATURE] Detect language from file extension
        detected_lang = LANG_EXTENSIONS.get(path.suffix.lower(), "unknown")

        # For non-Python files, use analyze_code which handles multi-language
        if detected_lang != "python":
            analysis = _analyze_code_sync(code, detected_lang)
            total_imports = len(analysis.imports)
            return FileContextResult(
                success=analysis.success,
                file_path=str(path),
                language=detected_lang,
                line_count=len(lines),
                functions=analysis.functions,  # type: ignore[assignment]
                classes=analysis.classes,  # type: ignore[assignment]
                imports=analysis.imports[:20],
                exports=[],
                complexity_score=analysis.complexity,
                has_security_issues=False,  # Security check is Python-specific for now
                summary=f"{detected_lang.title()} module with {analysis.function_count} function(s), {analysis.class_count} class(es)",
                imports_truncated=total_imports > 20,
                total_imports=total_imports,
                error=analysis.error,
            )

        # [20260119_REFACTOR] Use unified parser for Python files
        # Python-specific parsing via unified parser with filename context
        try:
            from code_scalpel.parsing import parse_python_code

            tree, _san_report = parse_python_code(code, filename=str(path))
        except Exception as e:  # Handle ParsingError or unexpected exceptions
            # Prefer explicit ParsingError details when available
            err_msg = str(e)
            return FileContextResult(
                success=False,
                file_path=str(path),
                line_count=len(lines),
                error=err_msg,
            )

        from code_scalpel.mcp.models.core import ClassInfo, FunctionInfo

        functions: list[FunctionInfo] = []
        classes: list[ClassInfo] = []
        imports = []
        exports = []
        complexity = 0

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Only top-level functions
                if hasattr(node, "col_offset") and node.col_offset == 0:
                    functions.append(
                        FunctionInfo(
                            name=node.name,
                            lineno=getattr(node, "lineno", 0),
                            end_lineno=getattr(node, "end_lineno", None),
                            is_async=isinstance(node, ast.AsyncFunctionDef),
                        )
                    )
                    complexity += _count_complexity_node(node)
            elif isinstance(node, ast.ClassDef):
                if hasattr(node, "col_offset") and node.col_offset == 0:
                    # Collect method names for the class
                    method_names: list[str] = []
                    for child in getattr(node, "body", []):
                        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            method_names.append(child.name)
                    classes.append(
                        ClassInfo(
                            name=node.name,
                            lineno=getattr(node, "lineno", 0),
                            end_lineno=getattr(node, "end_lineno", None),
                            methods=method_names,
                        )
                    )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")
            elif isinstance(node, ast.Assign):
                # Check for __all__ exports
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        if isinstance(node.value, ast.List | ast.Tuple):
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                    exports.append(elt.value)

        # Quick security check
        has_security_issues = False
        security_patterns = [
            "eval(",
            "exec(",
            "cursor.execute",
            "os.system(",
            "subprocess.call(",
        ]
        for pattern in security_patterns:
            if pattern in code:
                has_security_issues = True
                break

        # Generate summary based on content
        summary_parts = []
        if classes:
            summary_parts.append(f"{len(classes)} class(es)")
        if functions:
            summary_parts.append(f"{len(functions)} function(s)")
        if "flask" in code.lower() or "app.route" in code:
            summary_parts.append("Flask web application")
        elif "django" in code.lower():
            summary_parts.append("Django module")
        elif "test_" in path.name or "pytest" in code:
            summary_parts.append("Test module")

        summary = ", ".join(summary_parts) if summary_parts else "Python module"

        # [20251220_FEATURE] v3.0.5 - Communicate truncation
        total_imports = len(imports)
        imports_truncated = total_imports > 20

        return FileContextResult(
            success=True,
            file_path=str(path),
            language="python",
            line_count=len(lines),
            functions=functions,  # type: ignore[assignment]
            classes=classes,  # type: ignore[assignment]
            imports=imports[:20],
            exports=exports,
            complexity_score=complexity,
            has_security_issues=has_security_issues,
            summary=summary,
            imports_truncated=imports_truncated,
            total_imports=total_imports,
        )

    except Exception as e:
        return FileContextResult(
            success=False,
            file_path=file_path,
            line_count=0,
            error=f"Analysis failed: {str(e)}",
        )


def _count_complexity_node(node: ast.AST) -> int:
    """Count cyclomatic complexity for a single node."""
    complexity = 1  # Base complexity
    for child in ast.walk(node):
        if isinstance(child, ast.If | ast.While | ast.For | ast.ExceptHandler):
            complexity += 1
        elif isinstance(child, ast.BoolOp):
            complexity += len(child.values) - 1
    return complexity


# [20260116_REFACTOR] @mcp.tool() get_file_context moved to tools/*.py


def _get_symbol_references_sync(symbol_name: str, project_root: str | None = None) -> SymbolReferencesResult:
    """
    Synchronous implementation of get_symbol_references.

    [20251220_FEATURE] v3.0.5 - Optimized single-pass AST walking with deduplication
    [20251220_PERF] v3.0.5 - Uses AST cache to avoid re-parsing unchanged files
    """
    try:
        root = Path(project_root) if project_root else PROJECT_ROOT

        if not root.exists():
            return SymbolReferencesResult(
                success=False,
                symbol_name=symbol_name,
                error=f"Project root not found: {root}.",
            )

        references: list[SymbolReference] = []
        definition_file = None
        definition_line = None
        # Track seen (file, line) pairs to avoid duplicates in single pass
        seen: set[tuple[str, int]] = set()

        # Walk through all Python files
        for py_file in root.rglob("*.py"):
            # Skip common non-source directories
            if any(
                part.startswith(".") or part in ("__pycache__", "node_modules", "venv", ".venv", "dist", "build")
                for part in py_file.parts
            ):
                continue

            try:
                # [20251220_PERF] v3.0.5 - Use cached AST parsing
                tree = _parse_file_cached(py_file)
                if tree is None:
                    continue

                code = py_file.read_text(encoding="utf-8")
                lines = code.splitlines()
                rel_path = str(py_file.relative_to(root))

                # Single-pass AST walk with optimized checks
                for node in ast.walk(tree):
                    node_line = getattr(node, "lineno", 0)
                    node_col = getattr(node, "col_offset", 0)

                    # Skip if already seen this location in this file
                    loc_key = (rel_path, node_line)
                    if loc_key in seen:
                        continue

                    is_def = False
                    matched = False

                    # Check definitions (FunctionDef, AsyncFunctionDef, ClassDef)
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        if node.name == symbol_name:
                            matched = True
                            is_def = True
                            if definition_file is None:
                                definition_file = rel_path
                                definition_line = node_line

                    # Check function calls
                    elif isinstance(node, ast.Call):
                        func = node.func
                        if isinstance(func, ast.Name) and func.id == symbol_name:
                            matched = True
                        elif isinstance(func, ast.Attribute) and func.attr == symbol_name:
                            matched = True

                    # Check name references (but avoid duplicating Call nodes)
                    elif isinstance(node, ast.Name) and node.id == symbol_name:
                        matched = True

                    if matched:
                        seen.add(loc_key)
                        context = lines[node_line - 1] if 0 < node_line <= len(lines) else ""
                        references.append(
                            SymbolReference(
                                file=rel_path,
                                line=node_line,
                                column=node_col,
                                context=context.strip(),
                                is_definition=is_def,
                            )
                        )

            except (SyntaxError, UnicodeDecodeError):
                # Skip files that can't be parsed
                continue

        # Sort: definitions first, then by file and line
        references.sort(key=lambda r: (not r.is_definition, r.file, r.line))

        # [20251220_FEATURE] v3.0.5 - Communicate truncation
        total_refs = len(references)
        refs_truncated = total_refs > 100
        truncation_msg = None
        if refs_truncated:
            truncation_msg = f"Results truncated: showing 100 of {total_refs} references. Use more specific symbol name or filter by file."

        return SymbolReferencesResult(
            success=True,
            symbol_name=symbol_name,
            definition_file=definition_file,
            definition_line=definition_line,
            references=references[:100],
            total_references=total_refs,
            references_truncated=refs_truncated,
            truncation_warning=truncation_msg,
        )

    except Exception as e:
        return SymbolReferencesResult(
            success=False,
            symbol_name=symbol_name,
            error=f"Search failed: {str(e)}",
        )


# [20260122_REFACTOR] Canonicalize call graph models to avoid duplicate classes
from code_scalpel.mcp.models.graph import (  # noqa: E402
    CallEdgeModel as _CallEdgeModelCanonical,
)
from code_scalpel.mcp.models.graph import (
    CallGraphResultModel as _CallGraphResultModelCanonical,
)
from code_scalpel.mcp.models.graph import (
    CallNodeModel as _CallNodeModelCanonical,
)

# Re-export canonical models so imports from server.py match helper/tool outputs
CallNodeModel = _CallNodeModelCanonical
CallEdgeModel = _CallEdgeModelCanonical
CallGraphResultModel = _CallGraphResultModelCanonical


def _get_call_graph_sync(
    project_root: str | None,
    entry_point: str | None,
    depth: int,
    include_circular_import_check: bool,
    tier: str = "community",
    capabilities: dict[str, Any] | None = None,
) -> CallGraphResultModel:
    """Synchronous implementation of get_call_graph."""
    from code_scalpel.ast_tools.call_graph import CallGraphBuilder

    root_path = Path(project_root) if project_root else PROJECT_ROOT

    if not root_path.exists():
        return CallGraphResultModel(
            success=False,
            error=f"Project root not found: {root_path}.",
            tier_applied=tier,
        )

    # [20260120_FEATURE] Apply tier limits
    limits = capabilities.get("limits", {}) if capabilities else {}
    max_depth_limit = limits.get("max_depth", None)
    max_nodes_limit = limits.get("max_nodes", None)

    # Ensure limits and depth are integers
    try:
        if max_depth_limit is not None:
            max_depth_limit = int(max_depth_limit)
        if max_nodes_limit is not None:
            max_nodes_limit = int(max_nodes_limit)
        if depth is not None:
            depth = int(depth)
    except (ValueError, TypeError) as e:
        return CallGraphResultModel(
            success=False,
            error=f"Invalid depth or limit types: depth={depth} ({type(depth)}), max_depth={max_depth_limit} ({type(max_depth_limit)}), max_nodes={max_nodes_limit} ({type(max_nodes_limit)}): {e}",
            tier_applied=tier,
        )

    # Apply depth limit
    if max_depth_limit is not None and (depth is None or depth > max_depth_limit):
        depth = max_depth_limit

    # [20260120_FEATURE] Check for advanced resolution capability
    advanced_resolution = "advanced_call_graph" in capabilities.get("capabilities", set()) if capabilities else False

    try:
        builder = CallGraphBuilder(root_path)
        result = builder.build_with_details(
            entry_point=entry_point,
            depth=depth,
            max_nodes=max_nodes_limit,
            advanced_resolution=advanced_resolution,
        )

        # Convert dataclasses to Pydantic models
        nodes = [
            CallNodeModel(
                name=n.name,
                file=n.file,
                line=n.line,
                end_line=n.end_line,
                is_entry_point=n.is_entry_point,
            )
            for n in result.nodes
        ]

        edges = [CallEdgeModel(caller=e.caller, callee=e.callee) for e in result.edges]

        # Optionally check for circular imports
        circular_imports = []
        if include_circular_import_check:
            circular_imports = builder.detect_circular_imports()

        # [20260120_FEATURE] Populate metadata fields
        enterprise_metrics = tier == "enterprise"

        return CallGraphResultModel(
            nodes=nodes,
            edges=edges,
            entry_point=result.entry_point,
            depth_limit=result.depth_limit,
            mermaid=result.mermaid,
            circular_imports=circular_imports,
            tier_applied=tier,
            max_depth_applied=max_depth_limit,
            max_nodes_applied=max_nodes_limit,
            advanced_resolution_enabled=advanced_resolution,
            enterprise_metrics_enabled=enterprise_metrics,
        )

    except Exception as e:
        return CallGraphResultModel(
            success=False,
            error=f"Call graph analysis failed: {str(e)}",
            tier_applied=tier,
        )


class NeighborhoodNodeModel(BaseModel):
    """A node in the neighborhood subgraph."""

    id: str = Field(description="Node ID (language::module::type::name)")
    depth: int = Field(description="Distance from center node (0 = center)")
    metadata: dict = Field(default_factory=dict, description="Additional node metadata")


class NeighborhoodEdgeModel(BaseModel):
    """An edge in the neighborhood subgraph."""

    from_id: str = Field(description="Source node ID")
    to_id: str = Field(description="Target node ID")
    edge_type: str = Field(description="Type of relationship")
    confidence: float = Field(description="Confidence score (0.0-1.0)")


class GraphNeighborhoodResult(BaseModel):
    """Result of k-hop neighborhood extraction."""

    success: bool = Field(description="Whether extraction succeeded")
    server_version: str = Field(default=__version__, description="Code Scalpel version")

    # Center node info
    center_node_id: str = Field(default="", description="ID of the center node")
    k: int = Field(default=0, description="Number of hops used")

    # Subgraph
    nodes: list[NeighborhoodNodeModel] = Field(default_factory=list, description="Nodes in the neighborhood")
    edges: list[NeighborhoodEdgeModel] = Field(default_factory=list, description="Edges in the neighborhood")
    total_nodes: int = Field(default=0, description="Number of nodes in subgraph")
    total_edges: int = Field(default=0, description="Number of edges in subgraph")

    # Truncation info
    max_depth_reached: int = Field(default=0, description="Maximum depth actually reached")
    truncated: bool = Field(default=False, description="Whether graph was truncated")
    truncation_warning: str | None = Field(default=None, description="Warning if truncated")

    # Mermaid diagram
    mermaid: str = Field(default="", description="Mermaid diagram of neighborhood")

    error: str | None = Field(default=None, description="Error message if failed")

    # [20251229_FEATURE] v3.3.0 - Pro/Enterprise fields
    semantic_summary: str | None = Field(default=None, description="AI-generated semantic summary (Pro)")
    related_imports: list[str] = Field(default_factory=list, description="Related imports from other files (Pro)")
    pii_redacted: bool = Field(default=False, description="Whether PII was redacted (Enterprise)")
    access_controlled: bool = Field(default=False, description="Whether access control was applied (Enterprise)")


def _generate_neighborhood_mermaid(
    nodes: list[NeighborhoodNodeModel],
    edges: list[NeighborhoodEdgeModel],
    center_node_id: str,
) -> str:
    """Generate Mermaid diagram for neighborhood."""
    lines = ["graph TD"]

    # Add nodes with depth-based styling
    for node in nodes:
        # Sanitize node ID for Mermaid
        safe_id = node.id.replace("::", "_").replace(".", "_").replace("-", "_")
        label = node.id.split("::")[-1] if "::" in node.id else node.id

        if node.depth == 0:
            # Center node - special styling
            lines.append(f'    {safe_id}["{label}"]:::center')
        elif node.depth == 1:
            lines.append(f'    {safe_id}["{label}"]:::depth1')
        else:
            lines.append(f'    {safe_id}["{label}"]:::depth2plus')

    # Add edges
    for edge in edges:
        from_safe = edge.from_id.replace("::", "_").replace(".", "_").replace("-", "_")
        to_safe = edge.to_id.replace("::", "_").replace(".", "_").replace("-", "_")
        lines.append(f"    {from_safe} --> {to_safe}")

    # Add style definitions
    lines.append("    classDef center fill:#f9f,stroke:#333,stroke-width:3px")
    lines.append("    classDef depth1 fill:#bbf,stroke:#333,stroke-width:2px")
    lines.append("    classDef depth2plus fill:#ddd,stroke:#333,stroke-width:1px")

    return "\n".join(lines)


def _normalize_graph_center_node_id(center_node_id: str) -> str:
    """Normalize common legacy node-id formats into canonical IDs.

    Canonical format: python::<module>::function::<name>

    Accepted legacy inputs:
    - routes.py:search_route
    - path/to/routes.py:search_route
    - routes:search_route
    """
    raw = (center_node_id or "").strip()
    if not raw:
        return raw

    if raw.startswith("python::") and "::function::" in raw:
        return raw

    # Common legacy format: <file>:<symbol>
    if ":" in raw and "::" not in raw:
        left, right = raw.rsplit(":", 1)
        file_part = left.strip()
        name = right.strip()
        if not name:
            return raw

        # If this looks like a path, convert to module.
        if file_part.endswith(".py"):
            module = file_part.replace("/", ".").replace("\\", ".")
            if module.endswith(".py"):
                module = module[: -len(".py")]
            # Drop leading dots that can happen with absolute-ish inputs.
            module = module.strip(".")
            if module:
                return f"python::{module}::function::{name}"

        # If this looks like a bare module name.
        module = file_part.replace("/", ".").replace("\\", ".").strip(".")
        if module:
            return f"python::{module}::function::{name}"

    return raw


def _fast_validate_python_function_node_exists(root_path: Path, center_node_id: str) -> tuple[bool, str | None]:
    """Best-effort fast validation for python::<module>::function::<name>.

    This avoids building the full call graph when the node ID points to a module
    file that doesn't exist or a function name that doesn't exist in that file.

    Returns:
        (ok, error_message)
    """
    import re

    m = re.match(
        r"^(?P<lang>[^:]+)::(?P<module>[^:]+)::(?P<kind>[^:]+)::(?P<name>.+)$",
        center_node_id.strip(),
    )
    if not m:
        return (
            False,
            "Invalid center_node_id format; expected language::module::type::name",
        )

    lang = m.group("lang")
    module = m.group("module")
    kind = m.group("kind")
    name = m.group("name")

    if lang != "python" or kind != "function":
        return True, None

    if module in ("external", "unknown"):
        return False, f"Center node module '{module}' is not a local module"

    # Map module -> file path
    candidate = root_path / (module.replace(".", "/") + ".py")
    if not candidate.exists():
        return False, f"Center node file not found for module '{module}': {candidate}"

    # Quick AST scan for a matching function name in that single file.
    try:
        import ast

        code = candidate.read_text(encoding="utf-8")
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
                return True, None
        return False, f"Center node function '{name}' not found in {candidate}"
    except Exception:
        # If parsing fails, fall back to the slow path (graph build)
        return True, None


class ModuleInfo(BaseModel):
    """Information about a Python module/file."""

    path: str = Field(description="Relative file path")
    functions: list[str] = Field(default_factory=list, description="Function names in the module")
    classes: list[str] = Field(default_factory=list, description="Class names in the module")
    imports: list[str] = Field(default_factory=list, description="Import statements")
    entry_points: list[str] = Field(default_factory=list, description="Detected entry points")
    line_count: int = Field(default=0, description="Number of lines in file")
    complexity_score: int = Field(default=0, description="Cyclomatic complexity score")


class PackageInfo(BaseModel):
    """Information about a Python package (directory with __init__.py)."""

    name: str = Field(description="Package name")
    path: str = Field(description="Relative path to package")
    modules: list[str] = Field(default_factory=list, description="Module names in package")
    subpackages: list[str] = Field(default_factory=list, description="Subpackage names")


class ProjectMapResult(BaseModel):
    """Result of project map analysis."""

    success: bool = Field(default=True, description="Whether analysis succeeded")
    server_version: str = Field(default=__version__, description="Code Scalpel version")
    project_root: str = Field(description="Absolute path to project root")
    total_files: int = Field(default=0, description="Total Python files")
    total_lines: int = Field(default=0, description="Total lines of code")
    languages: dict[str, int] = Field(default_factory=dict, description="Language breakdown by file count")
    packages: list[PackageInfo] = Field(default_factory=list, description="Detected packages")
    modules: list[ModuleInfo] = Field(default_factory=list, description="Modules analyzed (max 50 in Mermaid diagram)")
    entry_points: list[str] = Field(default_factory=list, description="All detected entry points")
    circular_imports: list[list[str]] = Field(default_factory=list, description="Circular import cycles")
    complexity_hotspots: list[str] = Field(default_factory=list, description="Files with high complexity")
    mermaid: str = Field(default="", description="Mermaid diagram of package structure")
    # [20251220_FEATURE] v3.0.5 - Truncation communication
    modules_in_diagram: int = Field(default=0, description="Number of modules shown in Mermaid diagram")
    diagram_truncated: bool = Field(default=False, description="Whether Mermaid diagram was truncated")
    error: str | None = Field(default=None, description="Error message if failed")

    # [20260120_FEATURE] v1.0 pre-release - Output transparency metadata
    tier_applied: str | None = Field(
        default=None,
        description="Which tier's rules were applied (community/pro/enterprise)",
    )
    max_files_applied: int | None = Field(
        default=None, description="Max files limit that was applied (None = unlimited)"
    )
    max_modules_applied: int | None = Field(
        default=None,
        description="Max modules limit that was applied (None = unlimited)",
    )
    pro_features_enabled: bool = Field(default=False, description="Whether Pro features are enabled")
    enterprise_features_enabled: bool = Field(default=False, description="Whether enterprise features are enabled")

    # [20251229_FEATURE] v3.3.0 - Pro/Enterprise fields
    semantic_summary: str | None = Field(default=None, description="AI-generated semantic summary (Pro)")
    related_imports: list[str] = Field(default_factory=list, description="Related imports from other files (Pro)")
    pii_redacted: bool = Field(default=False, description="Whether PII was redacted (Enterprise)")
    access_controlled: bool = Field(default=False, description="Whether access control was applied (Enterprise)")


def _get_project_map_sync(
    project_root: str | None,
    include_complexity: bool,
    complexity_threshold: int,
    include_circular_check: bool,
) -> ProjectMapResult:
    """Synchronous implementation of get_project_map."""
    import ast

    from code_scalpel.ast_tools.call_graph import CallGraphBuilder

    root_path = Path(project_root) if project_root else PROJECT_ROOT

    if not root_path.exists():
        return ProjectMapResult(
            success=False,
            project_root=str(root_path),
            error=f"Project root not found: {root_path}.",
        )

    try:
        modules: list[ModuleInfo] = []
        packages: dict[str, PackageInfo] = {}
        all_entry_points: list[str] = []
        complexity_hotspots: list[str] = []
        total_lines = 0

        # Entry point detection patterns
        entry_decorators = {
            "command",
            "main",
            "cli",
            "app",
            "route",
            "get",
            "post",
            "put",
            "delete",
        }

        def is_entry_point(func_node: ast.AST) -> bool:
            """Check if function is an entry point."""
            # Type guard: must be FunctionDef or AsyncFunctionDef
            if not isinstance(func_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return False
            if func_node.name == "main":
                return True
            for dec in getattr(func_node, "decorator_list", []):
                dec_name = ""
                if isinstance(dec, ast.Name):
                    dec_name = dec.id
                elif isinstance(dec, ast.Attribute):
                    dec_name = dec.attr
                elif isinstance(dec, ast.Call):
                    if isinstance(dec.func, ast.Attribute):
                        dec_name = dec.func.attr
                    elif isinstance(dec.func, ast.Name):
                        dec_name = dec.func.id
                if dec_name in entry_decorators:
                    return True
            return False

        def calculate_complexity(tree: ast.AST) -> int:
            """Calculate cyclomatic complexity of a module."""
            complexity = 1  # Base complexity
            for node in ast.walk(tree):
                if isinstance(
                    node,
                    (
                        ast.If,
                        ast.While,
                        ast.For,
                        ast.AsyncFor,
                        ast.ExceptHandler,
                        ast.With,
                        ast.AsyncWith,
                        ast.Assert,
                        ast.comprehension,
                    ),
                ):
                    complexity += 1
                elif isinstance(node, (ast.And, ast.Or)):
                    complexity += 1
                elif isinstance(node, ast.BoolOp):
                    complexity += len(node.values) - 1
            return complexity

        # Collect all Python files
        python_files = list(root_path.rglob("*.py"))

        # Filter out common excluded directories
        exclude_patterns = {
            "__pycache__",
            ".git",
            "venv",
            ".venv",
            "env",
            ".env",
            "node_modules",
            "dist",
            "build",
            ".tox",
            ".pytest_cache",
            "htmlcov",
            ".mypy_cache",
        }

        for file_path in python_files:
            # Skip excluded directories
            if any(part in exclude_patterns for part in file_path.parts):
                continue

            rel_path = str(file_path.relative_to(root_path))

            try:
                with open(file_path, encoding="utf-8", errors="ignore") as f:
                    code = f.read()

                lines = code.count("\n") + 1
                total_lines += lines

                tree = ast.parse(code)

                # Extract module info
                functions = []
                classes = []
                imports = []
                entry_points = []

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        functions.append(node.name)
                        if is_entry_point(node):
                            entry_points.append(f"{rel_path}:{node.name}")
                    elif isinstance(node, ast.ClassDef):
                        classes.append(node.name)
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imports.append(node.module)

                # Calculate complexity if requested
                complexity = 0
                if include_complexity:
                    complexity = calculate_complexity(tree)
                    if complexity >= complexity_threshold:
                        complexity_hotspots.append(f"{rel_path} (complexity: {complexity})")

                all_entry_points.extend(entry_points)

                modules.append(
                    ModuleInfo(
                        path=rel_path,
                        functions=functions,
                        classes=classes,
                        imports=list(set(imports)),  # Dedupe
                        entry_points=entry_points,
                        line_count=lines,
                        complexity_score=complexity,
                    )
                )

                # Track packages
                parent = file_path.parent
                while parent != root_path and parent.exists():
                    init_file = parent / "__init__.py"
                    if init_file.exists():
                        pkg_path = str(parent.relative_to(root_path))
                        pkg_name = parent.name
                        if pkg_path not in packages:
                            packages[pkg_path] = PackageInfo(
                                name=pkg_name,
                                path=pkg_path,
                                modules=[],
                                subpackages=[],
                            )
                        # Add module to package
                        if rel_path not in packages[pkg_path].modules:
                            packages[pkg_path].modules.append(rel_path)
                    parent = parent.parent

            except Exception:
                # Skip files with errors
                continue

        # Organize package hierarchy
        pkg_list = list(packages.values())
        for pkg in pkg_list:
            for other_pkg in pkg_list:
                if other_pkg.path.startswith(pkg.path + "/") and other_pkg.name not in pkg.subpackages:
                    pkg.subpackages.append(other_pkg.name)

        # Check for circular imports
        circular_imports = []
        if include_circular_check:
            builder = CallGraphBuilder(root_path)
            circular_imports = builder.detect_circular_imports()

        # [20251213_FEATURE] Calculate language breakdown
        languages: dict[str, int] = {"python": len(modules)}
        # Also count other common file types
        for ext, lang in [
            (".js", "javascript"),
            (".ts", "typescript"),
            (".java", "java"),
            (".json", "json"),
            (".yaml", "yaml"),
            (".yml", "yaml"),
            (".md", "markdown"),
            (".html", "html"),
            (".css", "css"),
        ]:
            len(list(root_path.rglob(f"*{ext}")))
            # Exclude common ignored dirs
            actual_count = sum(1 for f in root_path.rglob(f"*{ext}") if not any(p in exclude_patterns for p in f.parts))
            if actual_count > 0:
                languages[lang] = languages.get(lang, 0) + actual_count

        # Generate Mermaid package diagram
        mermaid_lines = ["graph TD"]
        mermaid_lines.append("    subgraph Project")
        modules_in_diagram = min(len(modules), 50)
        for i, mod in enumerate(modules[:50]):  # Limit to 50 modules
            mod_id = f"M{i}"
            label = mod.path.replace("/", "_").replace(".", "_")
            if mod.entry_points:
                mermaid_lines.append(f'        {mod_id}[["{label}"]]')  # Stadium for entry
            else:
                mermaid_lines.append(f'        {mod_id}["{label}"]')
        mermaid_lines.append("    end")

        # [20251220_FEATURE] v3.0.5 - Communicate truncation
        diagram_truncated = len(modules) > 50
        if diagram_truncated:
            mermaid_lines.append(f"    Note[... and {len(modules) - 50} more modules]")

        return ProjectMapResult(
            project_root=str(root_path),
            total_files=len(modules),
            total_lines=total_lines,
            languages=languages,
            packages=pkg_list,
            modules=modules,
            entry_points=all_entry_points,
            circular_imports=circular_imports,
            complexity_hotspots=complexity_hotspots,
            mermaid="\n".join(mermaid_lines),
            modules_in_diagram=modules_in_diagram,
            diagram_truncated=diagram_truncated,
        )

    except Exception as e:
        return ProjectMapResult(
            success=False,
            project_root=str(root_path),
            error=f"Project map analysis failed: {str(e)}",
        )


class ImportNodeModel(BaseModel):
    """Information about an import in the import graph."""

    module: str = Field(description="Module name (e.g., 'os', 'mypackage.utils')")
    import_type: str = Field(description="Import type: 'direct', 'from', or 'star'")
    names: list[str] = Field(default_factory=list, description="Imported names (for 'from' imports)")
    alias: str | None = Field(default=None, description="Alias if import uses 'as'")
    line: int = Field(default=0, description="Line number of import")


class SymbolDefinitionModel(BaseModel):
    """Information about a symbol defined in a file."""

    name: str = Field(description="Symbol name")
    file: str = Field(description="File where symbol is defined (relative path)")
    line: int = Field(default=0, description="Line number of definition")
    symbol_type: str = Field(description="Type: 'function', 'class', or 'variable'")
    is_exported: bool = Field(default=False, description="Whether symbol is in __all__")


class ExtractedSymbolModel(BaseModel):
    """An extracted symbol with its code and dependencies."""

    name: str = Field(description="Symbol name")
    code: str = Field(description="Full source code of the symbol")
    file: str = Field(description="Source file (relative path)")
    line_start: int = Field(default=0, description="Starting line number")
    line_end: int = Field(default=0, description="Ending line number")
    dependencies: list[str] = Field(default_factory=list, description="Names of symbols this depends on")
    # [20251216_FEATURE] v2.5.0 - Confidence decay for deep dependency chains
    depth: int = Field(default=0, description="Depth from original target (0 = target)")
    confidence: float = Field(
        default=1.0,
        description="Confidence score with decay applied (0.0-1.0). Formula: C_base × 0.9^depth",
    )
    low_confidence: bool = Field(default=False, description="True if confidence is below threshold (0.5)")


class CrossFileDependenciesResult(BaseModel):
    """Result of cross-file dependency analysis."""

    success: bool = Field(description="Whether analysis succeeded")
    server_version: str = Field(default=__version__, description="Code Scalpel version")

    # Target symbol info
    target_name: str = Field(default="", description="Name of the analyzed symbol")
    target_file: str = Field(default="", description="File containing the target symbol")

    # Dependency info
    extracted_symbols: list[ExtractedSymbolModel] = Field(
        default_factory=list,
        description="All symbols extracted (target + dependencies)",
    )
    total_dependencies: int = Field(default=0, description="Number of dependencies resolved")
    unresolved_imports: list[str] = Field(
        default_factory=list, description="External imports that could not be resolved"
    )

    # Import graph info
    import_graph: dict[str, list[str]] = Field(
        default_factory=dict, description="Import graph: file -> list of imported files"
    )
    circular_imports: list[list[str]] = Field(default_factory=list, description="Detected circular import cycles")

    # Combined code for AI consumption
    combined_code: str = Field(default="", description="All extracted code combined, ready for AI consumption")
    token_estimate: int = Field(default=0, description="Estimated token count for combined code")

    # Mermaid diagram
    mermaid: str = Field(default="", description="Mermaid diagram of import relationships")

    # [20251216_FEATURE] v2.5.0 - Confidence decay tracking
    confidence_decay_factor: float = Field(
        default=0.9,
        description="Decay factor used: C_effective = C_base × decay_factor^depth",
    )
    low_confidence_count: int = Field(default=0, description="Number of symbols below confidence threshold (0.5)")
    low_confidence_warning: str | None = Field(
        default=None, description="Warning message if low-confidence symbols detected"
    )

    error: str | None = Field(default=None, description="Error message if failed")

    # [20251229_FEATURE] v3.3.0 - Pro/Enterprise fields
    semantic_summary: str | None = Field(default=None, description="AI-generated semantic summary (Pro)")
    related_imports: list[str] = Field(default_factory=list, description="Related imports from other files (Pro)")
    pii_redacted: bool = Field(default=False, description="Whether PII was redacted (Enterprise)")
    access_controlled: bool = Field(default=False, description="Whether access control was applied (Enterprise)")


def _get_cross_file_dependencies_sync(
    target_file: str,
    target_symbol: str,
    project_root: str | None,
    max_depth: int,
    include_code: bool,
    include_diagram: bool,
    confidence_decay_factor: float = 0.9,
) -> CrossFileDependenciesResult:
    """
    Synchronous implementation of get_cross_file_dependencies.

    [20251220_BUGFIX] v3.0.5 - Parameter order matches async function for consistency.
    """
    from code_scalpel.ast_tools.cross_file_extractor import CrossFileExtractor

    root_path = Path(project_root) if project_root else PROJECT_ROOT

    if not root_path.exists():
        return CrossFileDependenciesResult(
            success=False,
            error=f"Project root not found: {root_path}.",
        )

    # Resolve target file path
    target_path = Path(target_file)
    if not target_path.is_absolute():
        target_path = root_path / target_file

    if not target_path.exists():
        return CrossFileDependenciesResult(
            success=False,
            error=f"Target file not found: {target_path}.",
        )

    try:
        from concurrent.futures import (
            ThreadPoolExecutor,
        )
        from concurrent.futures import (
            TimeoutError as FuturesTimeoutError,
        )

        def run_with_timeout(func, timeout_seconds, *args, **kwargs):
            """
            Cross-platform timeout wrapper using ThreadPoolExecutor.

            Works on both Unix/Linux and Windows by running the function
            in a thread pool with a timeout.

            Args:
                func: Function to execute
                timeout_seconds: Maximum execution time in seconds
                *args, **kwargs: Arguments to pass to func

            Returns:
                Result from func

            Raises:
                TimeoutError: If execution exceeds timeout_seconds
            """
            # NOTE: Avoid `with ThreadPoolExecutor(...)` here.
            # If `future.result(timeout=...)` times out, the context manager's
            # shutdown(wait=True) can block forever waiting for a hung worker.
            executor = ThreadPoolExecutor(max_workers=1)
            future = executor.submit(func, *args, **kwargs)
            try:
                return future.result(timeout=timeout_seconds)
            except FuturesTimeoutError:
                future.cancel()
                raise TimeoutError(f"Operation timed out after {timeout_seconds} seconds")
            finally:
                # Do not wait for a potentially hung worker thread.
                executor.shutdown(wait=False, cancel_futures=True)

        # Build CrossFileExtractor (includes ImportResolver.build()) with timeout protection.
        def build_extractor():
            extractor = CrossFileExtractor(root_path)
            extractor.build()
            return extractor

        try:
            extractor = run_with_timeout(build_extractor, 60)
        except TimeoutError as e:
            return CrossFileDependenciesResult(
                success=False,
                error=f"CrossFileExtractor.build() timed out after 60s. Project may be too large. Error: {e}",
            )

        # [20251216_FEATURE] v2.5.0 - Pass confidence_decay_factor to extractor
        def extract_dependencies():
            return extractor.extract(
                str(target_path),
                target_symbol,
                depth=max_depth,
                confidence_decay_factor=confidence_decay_factor,
            )

        try:
            extraction_result = run_with_timeout(extract_dependencies, 30)
        except TimeoutError as e:
            return CrossFileDependenciesResult(
                success=False,
                error=f"extractor.extract() timed out after 30s for {target_symbol}. Error: {e}",
            )

        # Check for extraction errors
        if not extraction_result.success:
            return CrossFileDependenciesResult(
                success=False,
                error=f"Extraction failed: {'; '.join(extraction_result.errors)}.",
            )

        # Build the list of all symbols (target + dependencies)
        all_symbols = []
        if extraction_result.target:
            all_symbols.append(extraction_result.target)
        all_symbols.extend(extraction_result.dependencies)

        # Convert extracted symbols to models
        extracted_symbols = []
        combined_parts = []

        # [20251216_FEATURE] v2.5.0 - Low confidence threshold
        LOW_CONFIDENCE_THRESHOLD = 0.5

        for sym in all_symbols:
            rel_file = str(Path(sym.file).relative_to(root_path)) if Path(sym.file).is_absolute() else sym.file
            # [20251216_FEATURE] v2.5.0 - Include depth and confidence in symbol model
            extracted_symbols.append(
                ExtractedSymbolModel(
                    name=sym.name,
                    code=sym.code if include_code else "",
                    file=rel_file,
                    line_start=sym.line,  # ExtractedSymbol uses 'line' not 'line_start'
                    line_end=sym.end_line or 0,  # ExtractedSymbol uses 'end_line'
                    dependencies=list(sym.dependencies),
                    depth=sym.depth,
                    confidence=sym.confidence,
                    low_confidence=sym.confidence < LOW_CONFIDENCE_THRESHOLD,
                )
            )
            if include_code:
                combined_parts.append(f"# From {rel_file}")
                combined_parts.append(sym.code)

        combined_code = "\n\n".join(combined_parts) if include_code else ""

        # Use the extractor's combined code if available (includes proper ordering)
        if include_code and extraction_result.combined_code:
            combined_code = extraction_result.combined_code

        # Get unresolved imports from extraction result
        unresolved_imports = extraction_result.module_imports  # These are imports that couldn't be resolved

        # Build import graph dict (file -> list of imported files)
        # Use the extractor's resolver (avoid double-building) and keep this focused.
        resolver = extractor.resolver
        import_graph: dict[str, list[str]] = {}

        # Limit graph construction to files actually involved in the extraction.
        files_of_interest: set[str] = set()
        for sym in all_symbols:
            try:
                p = Path(sym.file)
                if not p.is_absolute():
                    p = root_path / p
                p = p.resolve()
                files_of_interest.add(str(p))
            except Exception:
                continue
        files_of_interest.add(str(target_path.resolve()))

        for abs_file in files_of_interest:
            module_name = resolver.file_to_module.get(abs_file)
            if not module_name:
                continue

            rel_path = str(Path(abs_file).relative_to(root_path))
            imported_files: list[str] = []
            for imp in resolver.imports.get(module_name, []):
                resolved_file = resolver.module_to_file.get(imp.module)
                if not resolved_file:
                    continue
                try:
                    resolved_abs = str(Path(resolved_file).resolve())
                    if resolved_abs not in files_of_interest:
                        continue
                    resolved_rel = str(Path(resolved_abs).relative_to(root_path))
                except Exception:
                    continue
                if resolved_rel not in imported_files:
                    imported_files.append(resolved_rel)

            if imported_files:
                import_graph[rel_path] = imported_files

        # Detect circular imports using get_circular_imports()
        circular_import_objs = resolver.get_circular_imports()
        circular_import_lists = [ci.cycle for ci in circular_import_objs]  # CircularImport uses 'cycle'

        # Make target file relative (used by diagram + returned fields)
        target_rel = str(target_path.relative_to(root_path)) if target_path.is_absolute() else target_file

        # Generate Mermaid diagram
        mermaid = ""
        if include_diagram:
            from collections import deque

            # Generate a focused diagram to avoid project-wide graph explosion.
            # We bound the subgraph by max_depth and cap nodes/edges.
            max_mermaid_nodes = 60
            max_mermaid_edges = 200

            start_file = target_rel
            # BFS from target file using the computed import_graph (file -> imported files)
            queue = deque([(start_file, 0)])
            seen_nodes: set[str] = set()
            edges_out: list[tuple[str, str]] = []

            while queue and len(seen_nodes) < max_mermaid_nodes and len(edges_out) < max_mermaid_edges:
                cur, depth = queue.popleft()
                if cur in seen_nodes:
                    continue
                seen_nodes.add(cur)
                if depth >= max_depth:
                    continue
                for dep in import_graph.get(cur, [])[:max_mermaid_edges]:
                    if len(edges_out) >= max_mermaid_edges:
                        break
                    edges_out.append((cur, dep))
                    if dep not in seen_nodes:
                        queue.append((dep, depth + 1))

            # Mermaid with stable short node ids
            lines = ["graph TD"]
            node_ids: dict[str, str] = {}
            # Always include the start node (even if it has no outgoing edges)
            seen_nodes.add(start_file)
            for i, n in enumerate(sorted(seen_nodes)):
                node_ids[n] = f"N{i}"
                safe_label = n.replace("/", "_").replace(".", "_")
                lines.append(f"    {node_ids[n]}[{safe_label}]")

            for a, b in edges_out:
                if a in node_ids and b in node_ids:
                    lines.append(f"    {node_ids[a]} --> {node_ids[b]}")

            # Truncation hint
            if len(seen_nodes) >= max_mermaid_nodes or len(edges_out) >= max_mermaid_edges:
                lines.append(f"    %% Diagram truncated (nodes<={max_mermaid_nodes}, edges<={max_mermaid_edges})")

            mermaid = "\n".join(lines)

        # Calculate token estimate (rough: 4 chars per token)
        token_estimate = len(combined_code) // 4 if combined_code else 0

        # [20251216_FEATURE] v2.5.0 - Build low confidence warning if needed
        low_confidence_warning = None
        if extraction_result.low_confidence_count > 0:
            low_conf_names = [s.name for s in extraction_result.get_low_confidence_symbols()[:5]]
            low_confidence_warning = (
                f"⚠️ {extraction_result.low_confidence_count} symbol(s) have low confidence "
                f"(below 0.5): {', '.join(low_conf_names)}"
                + ("..." if extraction_result.low_confidence_count > 5 else "")
            )

        return CrossFileDependenciesResult(
            success=True,
            target_name=target_symbol,
            target_file=target_rel,
            extracted_symbols=extracted_symbols,
            total_dependencies=len(extracted_symbols) - 1,  # Exclude target itself
            unresolved_imports=unresolved_imports,  # Use local variable set from module_imports
            import_graph=import_graph,
            circular_imports=circular_import_lists,
            combined_code=combined_code,
            token_estimate=token_estimate,
            mermaid=mermaid,
            # [20251216_FEATURE] v2.5.0 - Confidence decay fields
            confidence_decay_factor=confidence_decay_factor,
            low_confidence_count=extraction_result.low_confidence_count,
            low_confidence_warning=low_confidence_warning,
        )

    except Exception as e:
        return CrossFileDependenciesResult(
            success=False,
            error=f"Cross-file dependency analysis failed: {str(e)}",
        )


class TaintFlowModel(BaseModel):
    """Model for a taint flow across files."""

    source_function: str = Field(description="Function where taint originates")
    source_file: str = Field(description="File containing taint source")
    source_line: int = Field(default=0, description="Line number of taint source")
    sink_function: str = Field(description="Function where taint reaches sink")
    sink_file: str = Field(description="File containing sink")
    sink_line: int = Field(default=0, description="Line number of sink")
    flow_path: list[str] = Field(default_factory=list, description="Path: file:function -> file:function")
    taint_type: str = Field(description="Type of taint source (e.g., 'request_input')")


class CrossFileVulnerabilityModel(BaseModel):
    """Model for a cross-file vulnerability."""

    type: str = Field(description="Vulnerability type (e.g., 'SQL Injection')")
    cwe: str = Field(description="CWE identifier")
    severity: str = Field(description="Severity: low, medium, high, critical")
    source_file: str = Field(description="File where taint originates")
    sink_file: str = Field(description="File where vulnerability manifests")
    description: str = Field(description="Human-readable description")
    flow: TaintFlowModel = Field(description="The taint flow that causes this vulnerability")


class CrossFileSecurityResult(BaseModel):
    """Result of cross-file security analysis."""

    success: bool = Field(description="Whether analysis succeeded")
    server_version: str = Field(default=__version__, description="Code Scalpel version")

    # Summary
    files_analyzed: int = Field(default=0, description="Number of files analyzed")
    has_vulnerabilities: bool = Field(default=False, description="Whether vulnerabilities were found")
    vulnerability_count: int = Field(default=0, description="Total vulnerabilities found")
    risk_level: str = Field(default="low", description="Overall risk level")

    # Detailed findings
    vulnerabilities: list[CrossFileVulnerabilityModel] = Field(
        default_factory=list, description="Cross-file vulnerabilities found"
    )
    taint_flows: list[TaintFlowModel] = Field(default_factory=list, description="All taint flows detected")

    # Entry points and sinks
    taint_sources: list[str] = Field(default_factory=list, description="Functions containing taint sources")
    dangerous_sinks: list[str] = Field(default_factory=list, description="Functions containing dangerous sinks")

    error: str | None = Field(default=None, description="Error message if failed")

    # [20260120_FEATURE] v1.0 pre-release - Output transparency metadata
    tier_applied: str = Field(
        default="community",
        description="Which tier's rules were applied (community/pro/enterprise)",
    )
    max_depth_applied: int | None = Field(
        default=None, description="Max depth limit that was applied (None = unlimited)"
    )
    max_modules_applied: int | None = Field(
        default=None,
        description="Max modules limit that was applied (None = unlimited)",
    )
    framework_aware_enabled: bool = Field(
        default=False, description="Whether framework-aware analysis is enabled (Pro)"
    )
    enterprise_features_enabled: bool = Field(default=False, description="Whether enterprise features are enabled")

    # [20251229_FEATURE] v3.3.0 - Pro/Enterprise fields
    semantic_summary: str | None = Field(default=None, description="AI-generated semantic summary (Pro)")
    related_imports: list[str] = Field(default_factory=list, description="Related imports from other files (Pro)")
    pii_redacted: bool = Field(default=False, description="Whether PII was redacted (Enterprise)")
    access_controlled: bool = Field(default=False, description="Whether access control was applied (Enterprise)")
    framework_contexts: dict[str, Any] | None = Field(
        default=None, description="Framework-specific analysis context (Enterprise)"
    )
    dependency_chains: list[str] | None = Field(default=None, description="Full dependency chains (Enterprise)")
    confidence_scores: dict[str, float] | None = Field(
        default=None, description="Confidence scores for findings (Enterprise)"
    )
    global_flows: list[TaintFlowModel] | None = Field(
        default=None, description="Global taint flows across all modules (Enterprise)"
    )
    microservice_boundaries: list[str] | None = Field(
        default=None, description="Detected microservice boundaries (Enterprise)"
    )
    distributed_trace: dict[str, Any] | None = Field(
        default=None,
        description="Distributed trace information for cross-service flows (Enterprise)",
    )


def _cross_file_security_scan_sync(
    project_root: str | None,
    entry_points: list[str] | None,
    max_depth: int,
    include_diagram: bool,
    timeout_seconds: float | None = 120.0,  # [20251220_PERF] Default 2 minute timeout
    max_modules: int | None = 500,  # [20251220_PERF] Default module limit for large projects
    tier: str = "community",
    capabilities: dict[str, Any] | None = None,
    confidence_threshold: float = 0.7,
) -> CrossFileSecurityResult:
    """Synchronous implementation of cross_file_security_scan."""
    from code_scalpel.security.analyzers.cross_file_taint import (
        CrossFileTaintTracker,
    )

    root_path = Path(project_root) if project_root else PROJECT_ROOT

    if not root_path.exists():
        return CrossFileSecurityResult(
            success=False,
            error=f"Project root not found: {root_path}.",
        )

    # [20260120_FEATURE] Apply tier limits
    limits = capabilities.get("limits", {}) if capabilities else {}
    max_depth_limit = limits.get("max_depth", max_depth)
    max_modules_limit = limits.get("max_modules", max_modules)

    # Apply limits (None means unlimited)
    if max_depth_limit is not None:
        max_depth = min(max_depth, max_depth_limit)
    if max_modules_limit is not None:
        max_modules = min(max_modules, max_modules_limit) if max_modules else max_modules_limit

    try:
        tracker = CrossFileTaintTracker(root_path)
        # [20251220_PERF] Pass timeout and module limit to prevent hanging
        result = tracker.analyze(
            entry_points=entry_points,
            max_depth=max_depth,
            timeout_seconds=timeout_seconds,
            max_modules=max_modules,
        )

        # Helper to get file path from module name
        def get_file_for_module(module: str) -> str:
            """Get file path for a module, falling back to module name if not found."""
            file_path = tracker.resolver.module_to_file.get(module, module)
            if isinstance(file_path, Path):
                file_path = str(file_path)
            # Make relative if absolute
            try:
                p = Path(file_path)
                if p.is_absolute():
                    return str(p.relative_to(root_path))
            except (ValueError, TypeError):
                pass
            return file_path

        # Convert vulnerabilities to models
        vulnerabilities = []
        for vuln in result.vulnerabilities:
            # [20251215_BUGFIX] v2.0.1 - Use source_module not source_file
            source_file = get_file_for_module(vuln.flow.source_module)
            sink_file = get_file_for_module(vuln.flow.sink_module)

            flow_model = TaintFlowModel(
                source_function=vuln.flow.source_function,
                source_file=source_file,
                source_line=vuln.flow.source_line,
                sink_function=vuln.flow.sink_function,
                sink_file=sink_file,
                sink_line=vuln.flow.sink_line,
                flow_path=[f"{get_file_for_module(m)}:{f}" for m, f, _ in vuln.flow.flow_path],
                taint_type=str(
                    vuln.flow.sink_type.name if hasattr(vuln.flow.sink_type, "name") else vuln.flow.sink_type
                ),
            )
            vulnerabilities.append(
                CrossFileVulnerabilityModel(
                    type=vuln.vulnerability_type,
                    cwe=vuln.cwe_id,
                    severity=vuln.severity,
                    source_file=source_file,
                    sink_file=sink_file,
                    description=vuln.description,
                    flow=flow_model,
                )
            )

        # Convert taint flows to models
        taint_flows = []
        for flow in result.taint_flows:
            # [20251215_BUGFIX] v2.0.1 - Use source_module not source_file
            source_file = get_file_for_module(flow.source_module)
            sink_file = get_file_for_module(flow.sink_module)

            taint_flows.append(
                TaintFlowModel(
                    source_function=flow.source_function,
                    source_file=source_file,
                    source_line=flow.source_line,
                    sink_function=flow.sink_function,
                    sink_file=sink_file,
                    sink_line=flow.sink_line,
                    flow_path=[f"{get_file_for_module(m)}:{f}" for m, f, _ in flow.flow_path],
                    taint_type=str(flow.sink_type.name if hasattr(flow.sink_type, "name") else flow.sink_type),
                )
            )

        # Determine risk level
        vuln_count = len(vulnerabilities)
        if vuln_count == 0:
            risk_level = "low"
        elif vuln_count <= 2:
            risk_level = "medium"
        elif vuln_count <= 5:
            risk_level = "high"
        else:
            risk_level = "critical"

        # Generate Mermaid diagram
        # Generate mermaid diagram if requested
        if include_diagram:
            _ = tracker.get_taint_graph_mermaid()  # Future enhancement
            # Store diagram for potential future use in result

        # Extract taint sources from tracker's internal state
        taint_sources = []
        dangerous_sinks = []

        # Get taint sources if available
        if hasattr(tracker, "module_taint_sources"):
            for module, sources in tracker.module_taint_sources.items():
                for src in sources:
                    taint_sources.append(f"{module}:{src.function}")

        # Get sinks from taint flows
        for flow in result.taint_flows:
            sink_key = f"{flow.sink_function}"
            if sink_key not in dangerous_sinks:
                dangerous_sinks.append(sink_key)

        return CrossFileSecurityResult(
            success=True,
            files_analyzed=result.modules_analyzed,  # Use modules_analyzed
            has_vulnerabilities=vuln_count > 0,
            vulnerability_count=vuln_count,
            risk_level=risk_level,
            vulnerabilities=vulnerabilities,
            taint_flows=taint_flows,
            taint_sources=taint_sources,
            dangerous_sinks=dangerous_sinks,
            # [20260120_FEATURE] v1.0 pre-release - Output transparency metadata
            tier_applied=tier,
            max_depth_applied=max_depth if max_depth else None,
            max_modules_applied=max_modules,
            framework_aware_enabled=(
                bool(capabilities and "framework_aware_taint" in capabilities.get("capabilities", set()))
                if capabilities
                else False
            ),
            enterprise_features_enabled=tier == "enterprise",
        )

    except Exception as e:
        return CrossFileSecurityResult(
            success=False,
            error=f"Cross-file security analysis failed: {str(e)}",
        )


class PathValidationResult(BaseModel):
    """Result of path validation."""

    success: bool = Field(description="Whether all paths were accessible")
    server_version: str = Field(default=__version__, description="Code Scalpel version")
    error: str | None = Field(default=None, description="Error message if failed")

    # [20251229_FEATURE] v3.3.0 - Pro/Enterprise fields
    semantic_summary: str | None = Field(default=None, description="AI-generated semantic summary (Pro)")
    related_imports: list[str] = Field(default_factory=list, description="Related imports from other files (Pro)")
    pii_redacted: bool = Field(default=False, description="Whether PII was redacted (Enterprise)")
    access_controlled: bool = Field(default=False, description="Whether access control was applied (Enterprise)")
    accessible: list[str] = Field(default_factory=list, description="Paths that were successfully resolved")
    inaccessible: list[str] = Field(default_factory=list, description="Paths that could not be resolved")
    suggestions: list[str] = Field(default_factory=list, description="Suggestions for resolving inaccessible paths")
    workspace_roots: list[str] = Field(default_factory=list, description="Detected workspace root directories")
    is_docker: bool = Field(default=False, description="Whether running in Docker container")


def _validate_paths_sync(paths: list[str], project_root: str | None) -> PathValidationResult:
    """Synchronous implementation of validate_paths."""
    from code_scalpel.mcp.path_resolver import PathResolver

    resolver = PathResolver()
    accessible, inaccessible = resolver.validate_paths(paths, project_root)

    suggestions = []
    if inaccessible:
        if resolver.is_docker:
            suggestions.append("Running in Docker: Mount your project with -v /path/to/project:/workspace")
            suggestions.append("Example: docker run -v $(pwd):/workspace code-scalpel:latest")
        else:
            suggestions.append("Ensure files exist and use absolute paths or place in workspace roots:")
            for root in resolver.workspace_roots[:3]:
                suggestions.append(f"  - {root}")
        suggestions.append("Set WORKSPACE_ROOT env variable to specify custom root")

    return PathValidationResult(
        success=len(inaccessible) == 0,
        accessible=accessible,
        inaccessible=inaccessible,
        suggestions=suggestions,
        workspace_roots=resolver.workspace_roots,
        is_docker=resolver.is_docker,
    )


def _verify_policy_integrity_sync(
    policy_dir: str | None = None,
    manifest_source: str = "file",
    tier: str | None = None,
    capabilities: dict | None = None,
) -> PolicyVerificationResult:
    """
    Synchronous implementation of policy integrity verification.

    [20250108_FEATURE] v2.5.0 Guardian - Cryptographic verification
    [20251220_BUGFIX] v3.0.5 - Consolidated imports inside try block
    [20260120_BUGFIX] Added tier and capabilities parameters to match signature
    """
    # Delegate to the helper implementation which has the full tier-aware logic
    from code_scalpel.mcp.helpers.policy_helpers import (
        _verify_policy_integrity_sync as helper_verify,
    )

    return helper_verify(
        policy_dir=policy_dir,
        manifest_source=manifest_source,
        tier=tier,
        capabilities=capabilities,
    )


def run_server(
    transport: str = "stdio",
    host: str = "127.0.0.1",
    port: int = 8080,
    allow_lan: bool = False,
    root_path: str | None = None,
    tier: str | None = None,
    ssl_certfile: str | None = None,
    ssl_keyfile: str | None = None,
):
    """
    Run the Code Scalpel MCP server.

    Args:
        transport: Transport type - "stdio" or "streamable-http"
        host: Host to bind to (HTTP only)
        port: Port to bind to (HTTP only)
        allow_lan: Allow connections from LAN (disables host validation)
        root_path: Project root directory (default: current directory)
        tier: Tool tier (community, pro, enterprise). Defaults to env vars or enterprise.
        ssl_certfile: Path to SSL certificate file for HTTPS (optional)
        ssl_keyfile: Path to SSL private key file for HTTPS (optional)

    Security Note:
        By default, the HTTP transport only allows connections from localhost.
        Use --allow-lan to enable LAN access. This disables DNS rebinding
        protection and allows connections from any host. Only use on trusted
        networks.

    HTTPS Note:
        [20251215_FEATURE] For production deployments (especially with Claude API),
        provide ssl_certfile and ssl_keyfile to enable HTTPS. Both must be specified
        for HTTPS to be enabled.
    """
    # [20251215_BUGFIX] Configure logging to stderr before anything else
    _configure_logging(transport)

    # [20260116_REFACTOR] Register tools, resources, and prompts from dedicated modules
    import code_scalpel.mcp.prompts  # noqa: F401 - registers @mcp.prompt handlers
    import code_scalpel.mcp.resources  # noqa: F401 - registers @mcp.resource handlers
    from code_scalpel.mcp.tools import register_tools

    register_tools()

    # [20260117_SECURITY] Authoritative startup tier selection
    # Uses the centralized authorization helper so remote verifier decisions
    # remain authoritative and paid tiers fail closed without a valid license.
    # CLI/env can request a tier, but it will be clamped by the license.
    validator = JWTLicenseValidator()
    requested_tier = tier or os.environ.get("CODE_SCALPEL_TIER") or os.environ.get("SCALPEL_TIER")
    effective_tier, startup_warning = compute_effective_tier_for_startup(
        requested_tier=requested_tier,
        validator=validator,
    )

    # Record last known valid tier/time when verifier allows it so mid-session
    # expiry grace continues to work.
    global _LAST_VALID_LICENSE_AT, _LAST_VALID_LICENSE_TIER
    if effective_tier in {"pro", "enterprise"}:
        _LAST_VALID_LICENSE_TIER = effective_tier
        _LAST_VALID_LICENSE_AT = __import__("time").time()

    # Emit startup warnings (e.g., revoked -> community) to stderr for stdio safety.
    if startup_warning:
        print(startup_warning, file=sys.stderr)

    tier = effective_tier

    # Expose tier to the response envelope wrapper (both local and protocol).
    global CURRENT_TIER
    CURRENT_TIER = tier
    set_current_tier(tier)  # Update protocol.py's tier for envelope wrapper

    # Tool surface is tier-scoped by removing disallowed tools.
    # NOTE: this is process-global; the server is intended to run once per process.
    _apply_tier_tool_filter(tier)

    # [20260120_BUGFIX] Use set_project_root() to update both holder and global.
    if root_path:
        resolved_root = Path(root_path).resolve()
        if not resolved_root.exists():
            # Use stderr for warnings to avoid corrupting stdio transport
            print(
                f"Warning: Root path {resolved_root} does not exist. Using current directory.",
                file=sys.stderr,
            )
            resolved_root = Path.cwd()
        set_project_root(resolved_root)

    # [20260117_FEATURE] v1.0.0 - Auto-initialize .code-scalpel/ on first run
    # Creates essential config files if the directory doesn't exist.
    # Uses "templates_only" mode (no secrets) by default for safety.
    init_result = _maybe_auto_init_config_dir(
        project_root=get_project_root(),
        tier=tier,
        enabled=True,  # Always enabled for v1.0 - creates config on first run
        mode="templates_only",  # Safe default - no secrets written
        target="project",
    )
    if init_result and init_result.get("created"):
        print(
            f"Created .code-scalpel/ configuration at {init_result['path']}",
            file=sys.stderr,
        )

    # [20251215_BUGFIX] Print to stderr for stdio transport
    output = sys.stderr if transport == "stdio" else sys.stdout
    print(f"Code Scalpel MCP Server v{__version__}", file=output)
    print(f"Project Root: {get_project_root()}", file=output)
    print(f"Tier: {tier}", file=output)

    # [20251215_FEATURE] SSL/HTTPS support for production deployments
    use_https = ssl_certfile and ssl_keyfile
    if use_https:
        print(f"SSL/TLS: ENABLED (cert: {ssl_certfile})", file=output)
    else:
        if transport in ("streamable-http", "sse"):
            print(
                "SSL/TLS: DISABLED (use --ssl-cert and --ssl-key for HTTPS)",
                file=output,
            )

    if transport == "streamable-http" or transport == "sse":
        from mcp.server.transport_security import TransportSecuritySettings

        mcp.settings.host = host
        mcp.settings.port = port

        # [20251215_FEATURE] Configure SSL if certificates provided
        if use_https:
            # Use setattr for optional SSL settings that may not be in all FastMCP versions
            mcp.settings.ssl_certfile = ssl_certfile
            mcp.settings.ssl_keyfile = ssl_keyfile
            protocol = "https"
        else:
            protocol = "http"

        if allow_lan or host == "0.0.0.0":  # nosec B104
            # [20251218_SECURITY] Intentional LAN binding for server functionality (B104)
            # Disable host validation for LAN access
            # WARNING: Only use on trusted networks!
            mcp.settings.transport_security = TransportSecuritySettings(
                enable_dns_rebinding_protection=False,
                allowed_hosts=["*"],
                allowed_origins=["*"],
            )
            print("WARNING: LAN access enabled. Host validation disabled.", file=output)
            print("Only use on trusted networks!", file=output)

        # FastMCP defaults: streamable-http mounts at /mcp and SSE mounts at /sse
        # (see mcp.server.fastmcp.server.FastMCP settings)
        endpoint_path = "/mcp" if transport == "streamable-http" else "/sse"
        print(f"MCP endpoint: {protocol}://{host}:{port}{endpoint_path}", file=output)

        # [20251215_FEATURE] Register HTTP health endpoint for Docker health checks
        _register_http_health_endpoint(mcp, host, port, ssl_certfile, ssl_keyfile)

        mcp.run(transport=transport)
    else:
        mcp.run()


def _apply_tier_tool_filter(tier: str) -> None:
    """Apply tier-based limits to tool responses.

    [20260119_FEATURE] v1.0.0 - All tools available in all tiers.
    Tier enforcement is done through response limits, not tool removal.

    The tier is available to all tools via CURRENT_TIER global variable.
    Each tool applies tier-specific limits (max results, max paths, etc.) at runtime.

    Example tier limits:
    - Community: symbolic_execute limited to 50 paths max
    - Community: crawl_project limited to discovery mode
    - Pro: Most features available with reasonable limits
    - Enterprise: Full access with audit logging
    """
    # Tool availability is now uniform across all tiers.
    # Tier-specific limits are applied within individual tool implementations,
    # not by removing tools from the MCP server.
    pass


def _register_http_health_endpoint(
    mcp_instance,
    host: str,
    port: int,
    ssl_certfile: str | None = None,
    ssl_keyfile: str | None = None,
):
    """
    Register a simple HTTP/HTTPS /health endpoint for Docker health checks.

    [20251215_FEATURE] v2.0.0 - HTTP health endpoint that returns immediately.
    [20251215_FEATURE] HTTPS support for production deployments.

    This endpoint is separate from the MCP protocol and provides a simple
    200 OK response for container orchestration health checks.
    """
    import json
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    use_https = ssl_certfile and ssl_keyfile

    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/health":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                response = json.dumps(
                    {
                        "status": "healthy",
                        "version": __version__,
                        "transport": "https" if use_https else "http",
                    }
                )
                self.wfile.write(response.encode())
            else:
                # Let other paths fall through to MCP handler
                self.send_response(404)
                self.end_headers()

        def log_message(self, format, *args):
            # Suppress HTTP access logs to stderr
            pass

    def run_health_server():
        # Run on a different port (health_port = mcp_port + 1)
        health_port = port + 1
        try:
            server = HTTPServer((host, health_port), HealthHandler)

            # [20251215_FEATURE] Wrap with SSL if certificates provided
            if use_https:
                import ssl

                ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                # ssl_certfile and ssl_keyfile are guaranteed non-None when use_https is True
                assert ssl_certfile is not None and ssl_keyfile is not None
                ssl_context.load_cert_chain(ssl_certfile, ssl_keyfile)
                server.socket = ssl_context.wrap_socket(server.socket, server_side=True)
                protocol = "https"
            else:
                protocol = "http"

            logger.info(f"Health endpoint available at {protocol}://{host}:{health_port}/health")
            server.serve_forever()
        except Exception as e:
            logger.warning(f"Could not start health server: {e}")

    # Start health server in background thread
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()


if __name__ == "__main__":
    # [20260120_BUGFIX] Register this module as code_scalpel.mcp.server in sys.modules.
    # When running via `python -m`, the module is loaded as __main__ but helpers import
    # from code_scalpel.mcp.server. Without this fix, those imports get a DIFFERENT
    # module object, causing _PROJECT_ROOT_HOLDER to not be shared.
    import sys

    if "code_scalpel.mcp.server" not in sys.modules:
        sys.modules["code_scalpel.mcp.server"] = sys.modules[__name__]

    import argparse

    parser = argparse.ArgumentParser(description="Code Scalpel MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http", "sse"],
        default="stdio",
        help="Transport type (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (HTTP only, default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port to bind to (HTTP only, default: 8080)",
    )
    parser.add_argument(
        "--allow-lan",
        action="store_true",
        help="Allow LAN connections (disables host validation, use on trusted networks only)",
    )
    parser.add_argument(
        "--root",
        help="Project root directory for resources (default: current directory)",
    )
    parser.add_argument(
        "--tier",
        choices=["community", "pro", "enterprise"],
        default=None,
        help="Tool tier (default: enterprise or CODE_SCALPEL_TIER/SCALPEL_TIER)",
    )
    # [20251215_FEATURE] SSL/TLS support for HTTPS
    parser.add_argument(
        "--ssl-cert",
        help="Path to SSL certificate file for HTTPS (required for production/Claude)",
    )
    parser.add_argument(
        "--ssl-key",
        help="Path to SSL private key file for HTTPS (required for production/Claude)",
    )

    args = parser.parse_args()
    run_server(
        transport=args.transport,
        host=args.host,
        port=args.port,
        allow_lan=args.allow_lan,
        root_path=args.root,
        tier=args.tier,
        ssl_certfile=args.ssl_cert,
        ssl_keyfile=args.ssl_key,
    )


# ============================================================================
# BACKWARD-COMPATIBLE RE-EXPORTS
# [20260116_REFACTOR] Re-export tool, resource, and prompt functions for backward compatibility
# Tools, resources, and prompts have been moved to dedicated modules but are
# re-exported here so existing code (e.g., tests) continues to work.
#
# [20260117_DEPRECATE] These re-exports are DEPRECATED. New code should import from:
#     from code_scalpel.mcp import <symbol>
# This section will be removed in a future major release.
# ============================================================================

# [20260119_REFACTOR] Explicit __all__ to silence Pylance "not accessed" warnings
# These are intentional re-exports for backward compatibility
__all__ = [
    # Server functions
    "run_server",
    "CURRENT_TIER",
    "PROJECT_ROOT",
    "ALLOWED_ROOTS",
    # Tools (22 total)
    "analyze_code",
    "security_scan",
    "scan_dependencies",
    "type_evaporation_scan",
    "unified_sink_detect",
    "extract_code",
    "rename_symbol",
    "update_symbol",
    "generate_unit_tests",
    "simulate_refactor",
    "symbolic_execute",
    "crawl_project",
    "get_file_context",
    "get_symbol_references",
    "cross_file_security_scan",
    "get_call_graph",
    "get_cross_file_dependencies",
    "get_graph_neighborhood",
    "get_project_map",
    "code_policy_check",
    "validate_paths",
    "verify_policy_integrity",
    # Resources
    "get_code_resource",
    "get_project_call_graph",
    "get_project_dependencies",
    "get_project_structure",
    # Prompts (Intent-Driven UX)
    "deep_security_audit",
    "explain_and_document",
    "map_architecture",
    "modernize_legacy",
    "safe_refactor",
    "verify_supply_chain",
    # Models (public)
    "AnalysisResult",
    "SecurityResult",
    "SymbolicResult",
    "RefactorSimulationResult",
    "ProjectCrawlResult",
    "ContextualExtractionResult",
    "FileContextResult",
    "SymbolReferencesResult",
    "CallGraphResultModel",
    "GraphNeighborhoodResult",
    "CrossFileSecurityResult",
    # Licensing
    "get_tool_capabilities",
]

# Re-export session variables for backward compatibility
# Re-export enterprise tier functions from extraction_helpers for backward compatibility
from code_scalpel.mcp.helpers.extraction_helpers import (  # noqa: E402, F401
    _check_code_review_approval,
    _check_compliance,
    _run_post_update_hook,
    _run_pre_update_hook,
)
from code_scalpel.mcp.session import (  # noqa: E402, F401
    _SESSION_AUDIT_TRAIL,
    _SESSION_UPDATE_COUNTS,
    _add_audit_entry,
    _get_session_update_count,
    _increment_session_update_count,
)


# Re-export with underscore aliases for backward compatibility
def _get_audit_trail() -> list:
    """Return the session audit trail."""
    return _SESSION_AUDIT_TRAIL.copy()


# Tool re-exports from tools/*.py - all 22 tools
# [20260116_BUGFIX] Removed re-export of _get_current_tier from protocol.py
# server.py has its own _get_current_tier() that does full license validation.
# The protocol.py version only checks env vars - do NOT import it here.
# [20260117_REFACTOR] Removed model re-exports that shadow local definitions
# CallGraphResultModel, GraphNeighborhoodResult, CrossFileSecurityResult are
# already defined in server.py - do NOT re-import from models/graph.py
# Re-export licensing features for backward compatibility
from code_scalpel.licensing.features import (  # noqa: E402, F401
    get_tool_capabilities,
)

# Re-export additional extraction helpers for backward compatibility
from code_scalpel.mcp.helpers.extraction_helpers import (  # noqa: E402, F401
    _update_cross_file_references,
)

# Prompt re-exports from prompts.py (Intent-Driven UX)
from code_scalpel.mcp.prompts import (  # noqa: E402, F401
    deep_security_audit,
    explain_and_document,
    map_architecture,
    modernize_legacy,
    safe_refactor,
    verify_supply_chain,
)

# Resource re-exports from resources.py
from code_scalpel.mcp.resources import (  # noqa: E402, F401
    get_code_resource,
    get_project_call_graph,
    get_project_dependencies,
    get_project_structure,
)
from code_scalpel.mcp.tools.analyze import analyze_code  # noqa: E402, F401
from code_scalpel.mcp.tools.context import (  # noqa: E402, F401
    crawl_project,
    get_file_context,
    get_symbol_references,
)
from code_scalpel.mcp.tools.extraction import (  # noqa: E402, F401
    extract_code,
    rename_symbol,
    update_symbol,
)
from code_scalpel.mcp.tools.graph import (  # noqa: E402, F401
    cross_file_security_scan,
    get_call_graph,
    get_cross_file_dependencies,
    get_graph_neighborhood,
    get_project_map,
)
from code_scalpel.mcp.tools.policy import (  # noqa: E402, F401
    code_policy_check,
    validate_paths,
    verify_policy_integrity,
)
from code_scalpel.mcp.tools.security import (  # noqa: E402, F401
    scan_dependencies,
    security_scan,
    type_evaporation_scan,
    unified_sink_detect,
)
from code_scalpel.mcp.tools.symbolic import (  # noqa: E402, F401
    generate_unit_tests,
    simulate_refactor,
    symbolic_execute,
)

# Note: SymbolReferencesResult, ALLOWED_ROOTS, PROJECT_ROOT, _get_symbol_references_sync are already in server.py
