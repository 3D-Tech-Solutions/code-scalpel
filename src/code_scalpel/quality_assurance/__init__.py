from .error_fixer import ErrorFixer, FixResult, FixResults

# [20251224_REFACTOR] Import from submodules
from .error_scanner import CodeError, ErrorScanner, ErrorSeverity, ScanResults

__all__ = [
    # Error Scanner
    "ErrorScanner",
    "ScanResults",
    "CodeError",
    "ErrorSeverity",
    # Error Fixer
    "ErrorFixer",
    "FixResult",
    "FixResults",
]

__version__ = "1.0.0"
