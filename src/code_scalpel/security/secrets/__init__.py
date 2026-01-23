"""
Secrets - Secret detection tools.

[20251225_FEATURE] Created as part of Project Reorganization Issue #8.

This module contains secret detection tools:
- secret_scanner.py: Hardcoded secret detection
"""

from .secret_scanner import SecretScanner

__all__ = [
    "SecretScanner",
]
