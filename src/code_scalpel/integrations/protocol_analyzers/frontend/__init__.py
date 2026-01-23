"""
Frontend Input Tracking - Frontend framework input source analysis.

[20251225_FEATURE] Created as part of Project Reorganization Phase 3.

This module provides frontend input tracking for React, Vue, and Angular:
- input_tracker.py: Frontend input source and dangerous sink detection
"""

from .input_tracker import (
    DangerousSink,
    DangerousSinkType,
    DataFlow,
    FrontendAnalysisResult,
    FrontendFramework,
    FrontendInputTracker,
    InputSource,
    InputSourceType,
)

__all__ = [
    "FrontendInputTracker",
    "FrontendAnalysisResult",
    "InputSource",
    "DangerousSink",
    "DataFlow",
    "FrontendFramework",
    "InputSourceType",
    "DangerousSinkType",
]
