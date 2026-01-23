"""
ML Security - Machine learning-based vulnerability prediction.

[20251225_FEATURE] Created as part of Project Reorganization Issue #8.

This module contains ML-based security analysis:
- ml_vulnerability_predictor.py: ML-based vulnerability prediction
"""

from .ml_vulnerability_predictor import VulnerabilityPrediction, VulnerabilityPredictor

__all__ = [
    "VulnerabilityPredictor",
    "VulnerabilityPrediction",
]
