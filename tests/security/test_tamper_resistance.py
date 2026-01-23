"""
Security tests for tamper resistance.

Re-exports from tests/autonomy/test_tamper_resistance.py for compatibility
with standard test directory layout.

# [20250112_REORG] v3.3.0 - Re-export for tests/security/ organization
"""

# Re-export all test classes and fixtures from the canonical location
from tests.autonomy.test_tamper_resistance import *  # noqa: F401, F403
