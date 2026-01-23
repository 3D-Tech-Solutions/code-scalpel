"""
gRPC Contract Analysis - gRPC service contract analysis.

[20251225_FEATURE] Created as part of Project Reorganization Phase 3.

This module provides gRPC contract parsing and analysis:
- contract_analyzer.py: gRPC service definition parsing and issue detection
"""

from .contract_analyzer import (
    ContractIssue,
    GrpcContract,
    GrpcContractAnalyzer,
    GrpcService,
    IssueSeverity,
    RpcMethod,
    StreamingType,
)

__all__ = [
    "GrpcContractAnalyzer",
    "GrpcContract",
    "GrpcService",
    "RpcMethod",
    "ContractIssue",
    "StreamingType",
    "IssueSeverity",
]
