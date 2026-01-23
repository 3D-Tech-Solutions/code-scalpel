"""
Schema Drift Detection - Protocol buffer schema drift analysis.

[20251225_FEATURE] Created as part of Project Reorganization Phase 3.

This module provides protobuf schema parsing and drift detection:
- drift_detector.py: Protocol buffer schema comparison and change detection
"""

from .drift_detector import (
    ChangeSeverity,
    ChangeType,
    ProtobufEnum,
    ProtobufField,
    ProtobufMessage,
    ProtobufParser,
    ProtobufSchema,
    SchemaChange,
    SchemaDriftDetector,
    SchemaDriftResult,
)

__all__ = [
    "SchemaDriftDetector",
    "SchemaDriftResult",
    "SchemaChange",
    "ProtobufSchema",
    "ProtobufMessage",
    "ProtobufField",
    "ProtobufEnum",
    "ProtobufParser",
    "ChangeType",
    "ChangeSeverity",
]
