# src/pdg_tools/__init__.py
"""
Program Dependence Graph (PDG) Tools - Advanced program analysis toolkit.

PDG is a fundamental program representation that captures both data and control
dependencies between program statements, enabling sophisticated code analysis
for security, optimization, and refactoring.
"""

from .analyzer import (
    DataFlowAnomaly,
    DependencyType,
    PDGAnalyzer,
    SecurityVulnerability,
)
from .builder import NodeType, PDGBuilder, Scope, build_pdg
from .slicer import ProgramSlicer, SliceInfo, SliceType, SlicingCriteria

__all__ = [
    # Builder
    "PDGBuilder",
    "build_pdg",
    "NodeType",
    "Scope",
    # Analyzer
    "PDGAnalyzer",
    "DependencyType",
    "DataFlowAnomaly",
    "SecurityVulnerability",
    # Slicer
    "ProgramSlicer",
    "SlicingCriteria",
    "SliceType",
    "SliceInfo",
]
