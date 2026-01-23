"""MCP protocol wiring and shared MCP instance.

[20260116_REFACTOR] Consolidated shared MCP instance with ToolResponseEnvelope wrapper.
All tools, resources, and prompts should import `mcp` from this module.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from code_scalpel import __version__

# [20260116_FEATURE] Import license validator for tier determination
from code_scalpel.licensing.jwt_validator import JWTLicenseValidator

# Current tier for response envelope metadata.
# Initialized to "community" (free tier) by default.
# Can be overridden via CODE_SCALPEL_TIER environment variable.
CURRENT_TIER = "community"

# [20260116_FEATURE] Runtime license grace for long-lived server processes.
# If a license expires mid-session, keep the last known valid tier for 24h.
_LAST_VALID_LICENSE_TIER: str | None = None
_LAST_VALID_LICENSE_AT: float | None = None
_MID_SESSION_EXPIRY_GRACE_SECONDS = 24 * 60 * 60


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
    import os

    requested = os.environ.get("CODE_SCALPEL_TIER") or os.environ.get("SCALPEL_TIER")
    if requested is None:
        return None
    requested = _normalize_tier(requested)
    if requested not in {"community", "pro", "enterprise"}:
        return None
    return requested


def _get_current_tier() -> str:
    """Get the current tier from license validation with env var override.

    [20260116_FEATURE] Updated to do full license validation, not just env var check.

    The tier system works as follows:
    1. License file determines the MAXIMUM tier you're entitled to
    2. Environment variable can REQUEST a tier (for testing/downgrade)
    3. The effective tier is the MINIMUM of licensed and requested

    Returns:
        str: One of 'community', 'pro', or 'enterprise'
    """
    import os
    import time as time_module

    global _LAST_VALID_LICENSE_AT, _LAST_VALID_LICENSE_TIER

    requested = _requested_tier_from_env()
    disable_license_discovery = os.environ.get("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY") == "1"
    force_tier_override = os.environ.get("CODE_SCALPEL_TEST_FORCE_TIER") == "1"

    # [TESTING/OFFLINE] If license discovery is disabled and explicit test override
    # is set, honor the requested tier (used for tier-gated contract tests only).
    if disable_license_discovery and force_tier_override and requested:
        return requested

    # When discovery is disabled and no explicit license path is provided, clamp to
    # Community to avoid silently elevating tier just via env vars.
    if disable_license_discovery and not force_tier_override:
        if not os.environ.get("CODE_SCALPEL_LICENSE_PATH"):
            return "community"

    validator = JWTLicenseValidator()
    license_data = validator.validate()
    licensed = "community"

    if license_data.is_valid:
        licensed = _normalize_tier(license_data.tier)
        _LAST_VALID_LICENSE_TIER = licensed
        _LAST_VALID_LICENSE_AT = time_module.time()
    else:
        # Revocation is immediate: no grace.
        err = (license_data.error_message or "").lower()
        if "revoked" in err:
            licensed = "community"
        # Expiration mid-session: allow 24h grace based on last known valid tier.
        elif getattr(license_data, "is_expired", False) and _LAST_VALID_LICENSE_AT:
            now = time_module.time()
            if now - _LAST_VALID_LICENSE_AT <= _MID_SESSION_EXPIRY_GRACE_SECONDS:
                if _LAST_VALID_LICENSE_TIER in {"pro", "enterprise"}:
                    licensed = _LAST_VALID_LICENSE_TIER

    # If no tier requested via env var, use the licensed tier
    if requested is None:
        return licensed

    # Allow downgrade only: effective tier = min(requested, licensed)
    rank = {"community": 0, "pro": 1, "enterprise": 2}
    return requested if rank[requested] <= rank[licensed] else licensed


def set_current_tier(tier: str) -> None:
    """Set the current tier (called by run_server)."""
    global CURRENT_TIER
    CURRENT_TIER = tier


# [20260116_BUGFIX] Restore standard JSON-RPC errors and structured output.
mcp = FastMCP(
    name="Code Scalpel",
    instructions=f"""Code Scalpel v{__version__} - AI-powered code analysis tools:

**TOKEN-EFFICIENT EXTRACTION (READ):**
- extract_code: Surgically extract functions/classes/methods by FILE PATH.
  The SERVER reads the file - YOU pay ~50 tokens instead of ~10,000.
  Supports Python, JavaScript, TypeScript, Java, JSX, TSX (React components).
  Example: extract_code(file_path="/src/utils.py", target_type="function", target_name="calculate_tax")
  React: extract_code(file_path="/components/Button.tsx", target_type="function", target_name="Button", language="tsx")

**JSX/TSX EXTRACTION (v2.0.2):**
- Extract React components with full metadata
- Detects Server Components (Next.js async components)
- Detects Server Actions ('use server' directive)
- Normalizes JSX for consistent analysis
- Returns component_type: "functional" or "class"

**RESOURCE TEMPLATES (v2.0.2):**
Access code via URIs without knowing file paths:
- code:///python/utils/calculate_tax
- code:///typescript/components/UserCard
- code:///java/services.AuthService/authenticate

**SURGICAL MODIFICATION (WRITE):**
- update_symbol: Replace a function/class/method in a file with new code.
  YOU provide only the new symbol - the SERVER handles safe replacement.
  Example: update_symbol(file_path="/src/utils.py", target_type="function",
           target_name="calculate_tax", new_code="def calculate_tax(amount): ...")
  Creates backup, validates syntax, preserves surrounding code.

**ANALYSIS TOOLS:**
- analyze_code: Parse Python/Java code, extract structure (functions, classes, imports)
- security_scan: Detect vulnerabilities using taint analysis (SQL injection, XSS, etc.)
- symbolic_execute: Explore execution paths using symbolic execution
- generate_unit_tests: Generate pytest/unittest tests from symbolic execution paths
- simulate_refactor: Verify a code change is safe before applying it
- crawl_project: Crawl entire project directory, analyze all Python files

**WORKFLOW OPTIMIZATION:**
1. Use extract_code(file_path=...) to get ONLY the symbol you need
2. Modify the extracted code
3. Use update_symbol(file_path=..., new_code=...) to apply the change safely

Code is PARSED only, never executed.""",
)

__all__ = ["mcp", "set_current_tier", "_get_current_tier"]

# Lazy loading of prompts to avoid circular imports.
# Prompts are loaded on first MCP server start via get_current_tier()
_prompts_loaded = False


def _load_prompts_if_needed() -> None:
    """Lazy load prompts on first access to avoid circular import."""
    global _prompts_loaded
    if not _prompts_loaded:
        import code_scalpel.mcp.prompts  # noqa: F401

        _prompts_loaded = True


# Load prompts when module is imported (but after mcp is defined)
_load_prompts_if_needed()
