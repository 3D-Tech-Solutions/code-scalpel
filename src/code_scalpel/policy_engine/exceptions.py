"""
Policy Engine Exceptions.

# [20251216_FEATURE] v2.5.0 Guardian - Tamper resistance exceptions
"""


class PolicyEngineError(Exception):
    """Base exception for policy engine errors."""

    pass


class TamperDetectedError(PolicyEngineError):
    """Raised when policy file tampering is detected."""

    pass


class PolicyModificationError(PolicyEngineError):
    """Raised when agent attempts to modify protected policy files."""

    pass


class OverrideTimeoutError(PolicyEngineError):
    """Raised when human override request times out."""

    pass


class InvalidOverrideCodeError(PolicyEngineError):
    """Raised when invalid override code is provided."""

    pass
