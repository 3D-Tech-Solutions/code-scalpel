"""Reusable tier activation helpers for tests.

[20260120_TEST] Provide license-driven tier setup to replace ad-hoc monkeypatching.

Usage pattern (set tier BEFORE importing Code Scalpel modules):

    from tests.utils.tier_setup import activate_tier, clear_tier_caches
    activate_tier("pro", skip_if_missing=True)
    # Now import tools under the requested tier
    from code_scalpel.mcp.server import crawl_project

Alternatively, use the context manager:

    from tests.utils.tier_setup import tier_context
    with tier_context("enterprise", skip_if_missing=True):
        from code_scalpel.mcp.server import get_project_map
        # run test code here

This works locally (test licenses under tests/licenses/) and in CI (licenses
are provisioned via GitHub Secrets).
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

# [20260120_TEST] Candidate license locations (ordered)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
LICENSE_DIR = PROJECT_ROOT / "tests" / "licenses"
ARCHIVE_DIR = PROJECT_ROOT / ".code-scalpel" / "archive"

PRO_CANDIDATES = [
    LICENSE_DIR / "code_scalpel_license_pro_20260101_190345.jwt",
    LICENSE_DIR / "code_scalpel_license_pro_20260101_170435.jwt",
    ARCHIVE_DIR / "code_scalpel_license_pro_final_test_pro_1766982522.jwt",
]
ENTERPRISE_CANDIDATES = [
    LICENSE_DIR / "code_scalpel_license_enterprise_20260101_190754.jwt",
    LICENSE_DIR / "code_scalpel_license_enterprise_20260101_170506.jwt",
]

Tier = Literal["community", "pro", "enterprise"]


def _find_license_for_tier(tier: Tier) -> Path | None:
    """Find a valid license file for the requested tier.

    Returns first existing path from candidates; does not validate cryptographically here
    to allow early env var setup before server import. Validation will occur in the product
    code at runtime.
    """
    candidates = PRO_CANDIDATES if tier == "pro" else (ENTERPRISE_CANDIDATES if tier == "enterprise" else [])
    for path in candidates:
        if path.exists() and path.is_file():
            # Defer token validation to app code
            return path
    return None


def clear_tier_caches() -> None:
    """Clear tier detection caches to ensure fresh evaluation per test.

    Safe to call before and after tests. Avoids cross-test leakage.
    """
    try:
        from code_scalpel.licensing import config_loader, jwt_validator  # type: ignore

        jwt_validator._LICENSE_VALIDATION_CACHE = None  # type: ignore[attr-defined]
        config_loader.clear_cache()  # type: ignore[attr-defined]
    except Exception:
        # Not imported yet or absent; ignore.
        pass
    try:
        # Reset server-level cached tier if present
        from code_scalpel.mcp import server  # type: ignore

        if hasattr(server, "_cached_tier"):
            server._cached_tier = None
    except Exception:
        pass


def activate_tier(tier: Tier, *, skip_if_missing: bool = False) -> Path | None:
    """Activate a tier by setting environment variables before imports.

    - community: disables license discovery and removes LICENSE_PATH
    - pro/enterprise: sets CODE_SCALPEL_LICENSE_PATH to a valid license file path

    If skip_if_missing is True and the license file is not found for pro/enterprise,
    this will raise pytest.Skip to cleanly skip the test.

    Returns the license Path used (or None for community).
    """
    # Ensure caches are clear before modifying environment
    clear_tier_caches()

    tier = (tier or "community").lower()  # type: ignore[assignment]
    if tier == "community":
        os.environ["CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY"] = "1"
        os.environ.pop("CODE_SCALPEL_LICENSE_PATH", None)
        # Explicit requested tier useful for transparency in some helpers
        os.environ["CODE_SCALPEL_TIER"] = "community"
        return None

    # pro/enterprise require license
    license_path = _find_license_for_tier(tier)
    if not license_path:
        if skip_if_missing:
            # Prefer skip over fallback mocking to preserve test integrity
            try:
                import pytest

                pytest.skip(f"No valid {tier} license file found for tests")
            except Exception:
                # If pytest unavailable, raise RuntimeError
                raise RuntimeError(f"No valid {tier} license file found for tests")
        else:
            # Fall back to community explicitly
            os.environ["CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY"] = "1"
            os.environ.pop("CODE_SCALPEL_LICENSE_PATH", None)
            os.environ["CODE_SCALPEL_TIER"] = "community"
            return None

    # Set license env before any Code Scalpel imports
    os.environ.pop("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", None)
    os.environ["CODE_SCALPEL_LICENSE_PATH"] = str(license_path)
    # Allow tests to explicitly request the same tier (downgrade only semantics still enforced)
    os.environ["CODE_SCALPEL_TIER"] = tier
    return license_path


@contextmanager
def tier_context(tier: Tier, *, skip_if_missing: bool = False):
    """Context manager to activate a tier for the duration of a block.

    Sets environment variables and clears caches on entry; restores on exit.
    Must be entered BEFORE importing Code Scalpel modules inside the block.
    """
    # Snapshot env
    prev_disable = os.environ.get("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY")
    prev_license = os.environ.get("CODE_SCALPEL_LICENSE_PATH")
    prev_tier = os.environ.get("CODE_SCALPEL_TIER")

    license_path = activate_tier(tier, skip_if_missing=skip_if_missing)
    try:
        yield license_path
    finally:
        # Restore environment
        if prev_disable is None:
            os.environ.pop("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", None)
        else:
            os.environ["CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY"] = prev_disable
        if prev_license is None:
            os.environ.pop("CODE_SCALPEL_LICENSE_PATH", None)
        else:
            os.environ["CODE_SCALPEL_LICENSE_PATH"] = prev_license
        if prev_tier is None:
            os.environ.pop("CODE_SCALPEL_TIER", None)
        else:
            os.environ["CODE_SCALPEL_TIER"] = prev_tier
        clear_tier_caches()
