# src/symbolic_execution_tools/__init__.py
"""
Symbolic Execution Tools for Code Scalpel.

v0.3.0 "The Mathematician" - Security Analysis Edition

This module provides symbolic execution capabilities for Python code analysis.
Building on v0.2.0 "Redemption", this release adds STRING SUPPORT and
SECURITY ANALYSIS for detecting vulnerabilities.

Working Features (v0.3.0):
    - SymbolicAnalyzer: Main entry point for symbolic analysis
    - SecurityAnalyzer: Taint-based vulnerability detection
    - ConstraintSolver: Z3-powered satisfiability checking
    - SymbolicInterpreter: Path exploration with smart forking
    - TypeInferenceEngine: Int/Bool/String type tracking
    - TaintTracker: Data flow tracking for security analysis

Security Detectors:
    - SQL Injection (CWE-89)
    - Cross-Site Scripting (CWE-79)
    - Path Traversal (CWE-22)
    - Command Injection (CWE-78)

Sanitizer Support (v0.3.1):
    - Built-in sanitizer registry (html.escape, shlex.quote, etc.)
    - Custom sanitizer registration via register_sanitizer()
    - Configuration via pyproject.toml [tool.code-scalpel.sanitizers]
    - Type coercion (int, float, bool) fully clears taint

Float Support (v2.0.0):
    - [20251215_FEATURE] Full float/Real support in symbolic execution
    - Float constants evaluated using Z3 RealVal
    - Float type inference via TypeInferenceEngine
    - Float arithmetic operations (add, sub, mul, div)
    - Mixed int/float operations return float

Current Limitations:
    - Loops bounded to 10 iterations
    - Function calls are stubbed (not symbolically executed)

For production use cases with full type support:
    - code_scalpel.ast_tools (AST analysis)
    - code_scalpel.pdg_tools (Program Dependence Graphs)

Example (Symbolic Analysis):
    >>> from code_scalpel.symbolic_execution_tools import SymbolicAnalyzer
    >>> analyzer = SymbolicAnalyzer()
    >>> result = analyzer.analyze("x = 5; y = x * 2 if x > 0 else -x")
    >>> print(f"Paths: {result.total_paths}, Feasible: {result.feasible_count}")

Example (Security Analysis):
    >>> from code_scalpel.symbolic_execution_tools import analyze_security
    >>> result = analyze_security('''
    ...     user_id = request.args.get("id")
    ...     cursor.execute("SELECT * FROM users WHERE id=" + user_id)
    ... ''')
    >>> if result.has_vulnerabilities:
    ...     print(result.summary())

Example (Custom Sanitizer):
    >>> from code_scalpel.symbolic_execution_tools import (
    ...     register_sanitizer, SecuritySink
    ... )
    >>> register_sanitizer(
    ...     "my_sanitize_sql",
    ...     clears_sinks={SecuritySink.SQL_QUERY},
    ...     full_clear=False
    ... )
"""

import warnings

# [20251220_FEATURE] v3.0.4: Frontend Input Tracker (TypeScript/JS DOM Detection)
# [20251225_REFACTOR] Import from new location
from code_scalpel.integrations.protocol_analyzers.frontend.input_tracker import (
    DangerousSink,
    DangerousSinkType,
    DataFlow,
    FrontendAnalysisResult,
    FrontendFramework,
    FrontendInputTracker,
    InputSource,
    InputSourceType,
    analyze_frontend_codebase,
    analyze_frontend_file,
    get_xss_risks,
)

# [20251219_FEATURE] v3.0.4: GraphQL Schema Tracking
# [20251225_REFACTOR] Import from new location
from code_scalpel.integrations.protocol_analyzers.graphql.schema_tracker import (
    GraphQLArgument,
    GraphQLChangeSeverity,
    GraphQLChangeType,
    GraphQLField,
    GraphQLSchema,
    GraphQLSchemaChange,
    GraphQLSchemaDrift,
    GraphQLSchemaTracker,
    GraphQLType,
    GraphQLTypeKind,
    compare_graphql_files,
    compare_graphql_schemas,
    track_graphql_schema,
)

# [20251219_FEATURE] v3.0.4: gRPC Contract Analysis
# [20251225_REFACTOR] Import from new location
from code_scalpel.integrations.protocol_analyzers.grpc.contract_analyzer import (
    ContractIssue,
    GrpcContract,
    GrpcContractAnalyzer,
    GrpcService,
    IssueSeverity,
    RpcMethod,
    StreamingType,
    analyze_grpc_contract,
    analyze_grpc_file,
    validate_grpc_contract,
)

# [20251220_FEATURE] v3.0.4: Kafka Taint Tracking
# [20251225_REFACTOR] Import from new location
from code_scalpel.integrations.protocol_analyzers.kafka.taint_tracker import (
    KafkaAnalysisResult,
    KafkaConsumer,
    KafkaLibrary,
    KafkaPatternType,
    KafkaProducer,
    KafkaRiskLevel,
    KafkaTaintBridge,
    KafkaTaintTracker,
    KafkaTopicInfo,
    analyze_kafka_codebase,
    analyze_kafka_file,
    get_kafka_taint_bridges,
)

# [20251219_FEATURE] v3.0.4: Schema Drift Detection
# [20251225_REFACTOR] Import from new location
from code_scalpel.integrations.protocol_analyzers.schema.drift_detector import (
    ChangeSeverity,
    ChangeType,
    ProtobufParser,
    SchemaChange,
    SchemaDriftDetector,
    SchemaDriftResult,
    compare_json_schema_files,
    compare_protobuf_files,
)

# [20251225_REFACTOR] Import from new location
from code_scalpel.security.analyzers.security_analyzer import (
    SecurityAnalysisResult,
    SecurityAnalyzer,
    analyze_security,
    find_command_injections,
    find_path_traversals,
    find_sql_injections,
    find_xss,
)

# v0.3.0: Security Analysis
# [20251225_REFACTOR] Import from new location
from code_scalpel.security.analyzers.taint_tracker import (  # v0.3.1: Sanitizer Support; [20251216_FEATURE] v2.2.0: SSR Security
    SANITIZER_REGISTRY,
    SSR_SINK_PATTERNS,
    SanitizerInfo,
    SecuritySink,
    TaintedValue,
    TaintInfo,
    TaintLevel,
    TaintSource,
    TaintTracker,
    Vulnerability,
    detect_ssr_framework,
    detect_ssr_vulnerabilities,
    load_sanitizers_from_config,
    register_sanitizer,
)

# [20251216_FEATURE] v2.3.0: Unified Polyglot Sink Detection
# [20251225_REFACTOR] Import from new location
from code_scalpel.security.analyzers.unified_sink_detector import (
    OWASP_COVERAGE,
    UNIFIED_SINKS,
    DetectedSink,
    Language,
    SinkDefinition,
    UnifiedSinkDetector,
)

from .constraint_solver import ConstraintSolver
from .engine import SymbolicAnalyzer, SymbolicExecutionEngine

# [20251215_REFACTOR] Move warning configuration after imports to satisfy import-order lint rules.
warnings.filterwarnings(
    "ignore",
    message="ast.(Num|Str) is deprecated and will be removed in Python 3.14",
    category=DeprecationWarning,
)

# [20251213_FEATURE] v1.5.1: Cross-File Taint Analysis
# [20251225_REFACTOR] Import from new location
# [20260102_REFACTOR] Deferred imports for optional Pro/Enterprise modules.
# ruff: noqa: E402
try:
    from code_scalpel.security.analyzers.cross_file_taint import (
        CrossFileSink,
        CrossFileTaintFlow,
        CrossFileTaintResult,
        CrossFileTaintTracker,
        CrossFileVulnerability,
        TaintedParameter,
    )
except ImportError:
    CrossFileTaintTracker = None
    CrossFileTaintResult = None
    CrossFileTaintFlow = None
    CrossFileVulnerability = None
    TaintedParameter = None
    CrossFileSink = None

# [20251226_FEATURE] v3.2.9: Path Prioritization (Pro Tier - Crash Optimization)
from .path_prioritization import (
    CrashPrioritizer,
    ErrorPattern,
    PathPrioritizer,
    PathScore,
    PrioritizationStrategy,
    prioritize_for_crashes,
)

# [20251218_BUGFIX] Disabled import warning - info is in docs
# warnings.warn(
#     "symbolic_execution_tools v1.2.0 (Stable). "
#     "Supports Int/Bool/String. See docs for type limitations.",
#     category=UserWarning,
#     stacklevel=2,
# )

__all__ = [
    # Core symbolic execution
    "ConstraintSolver",
    "SymbolicExecutionEngine",
    "SymbolicAnalyzer",
    # v0.3.0: Security Analysis
    "TaintTracker",
    "TaintSource",
    "TaintLevel",
    "SecuritySink",
    "TaintInfo",
    "TaintedValue",
    "Vulnerability",
    "SecurityAnalyzer",
    "SecurityAnalysisResult",
    "analyze_security",
    "find_sql_injections",
    "find_xss",
    "find_command_injections",
    "find_path_traversals",
    # v0.3.1: Sanitizer Support
    "SanitizerInfo",
    "SANITIZER_REGISTRY",
    "register_sanitizer",
    "load_sanitizers_from_config",
    # [20251216_FEATURE] v2.2.0: SSR Security
    "SSR_SINK_PATTERNS",
    "detect_ssr_vulnerabilities",
    "detect_ssr_framework",
    # [20251216_FEATURE] v2.3.0: Unified Polyglot Sink Detection
    "UnifiedSinkDetector",
    "SinkDefinition",
    "DetectedSink",
    "Language",
    "UNIFIED_SINKS",
    "OWASP_COVERAGE",
    # [20251219_FEATURE] v3.0.4: Schema Drift Detection
    "SchemaDriftDetector",
    "SchemaDriftResult",
    "SchemaChange",
    "ChangeType",
    "ChangeSeverity",
    "ProtobufParser",
    "compare_protobuf_files",
    "compare_json_schema_files",
    # [20251219_FEATURE] v3.0.4: gRPC Contract Analysis
    "GrpcContractAnalyzer",
    "GrpcContract",
    "GrpcService",
    "RpcMethod",
    "StreamingType",
    "ContractIssue",
    "IssueSeverity",
    "analyze_grpc_contract",
    "validate_grpc_contract",
    "analyze_grpc_file",
    # [20251219_FEATURE] v3.0.4: GraphQL Schema Tracking
    "GraphQLSchemaTracker",
    "GraphQLSchema",
    "GraphQLType",
    "GraphQLTypeKind",
    "GraphQLField",
    "GraphQLArgument",
    "GraphQLSchemaDrift",
    "GraphQLSchemaChange",
    "GraphQLChangeType",
    "GraphQLChangeSeverity",
    "track_graphql_schema",
    "compare_graphql_schemas",
    "compare_graphql_files",
    # [20251220_FEATURE] v3.0.4: Kafka Taint Tracking
    "KafkaTaintTracker",
    "KafkaProducer",
    "KafkaConsumer",
    "KafkaTaintBridge",
    "KafkaTopicInfo",
    "KafkaAnalysisResult",
    "KafkaLibrary",
    "KafkaPatternType",
    "KafkaRiskLevel",
    "analyze_kafka_file",
    "analyze_kafka_codebase",
    "get_kafka_taint_bridges",
    # [20251220_FEATURE] v3.0.4: Frontend Input Tracker
    "FrontendInputTracker",
    "FrontendAnalysisResult",
    "FrontendFramework",
    "InputSource",
    "InputSourceType",
    "DangerousSink",
    "DangerousSinkType",
    "DataFlow",
    "analyze_frontend_file",
    "analyze_frontend_codebase",
    "get_xss_risks",
    # v1.5.1: Cross-File Taint Analysis
    "CrossFileTaintTracker",
    "CrossFileTaintResult",
    "CrossFileTaintFlow",
    "CrossFileVulnerability",
    "TaintedParameter",
    "CrossFileSink",
    # [20251226_FEATURE] v3.2.9: Path Prioritization (Pro Tier)
    "PathPrioritizer",
    "PathScore",
    "PrioritizationStrategy",
    "ErrorPattern",
    "prioritize_for_crashes",
    "CrashPrioritizer",
]

# ===================================
#
# COMMUNITY (Current & Planned):
# Documentation & Guides:
#
# Examples & Tutorials:
#
# Testing & Validation:
#
# PRO (Enhanced Features):
# Core Engine Enhancements:
#
# Analysis Capabilities:
#
# Performance & Scalability:
#
# Vulnerability Detection:
#
# ENTERPRISE (Advanced Capabilities):
# Distributed & Scalability:
#
# Advanced Analysis:
#
# Integration & Compliance:
#
# Intelligence & Automation:
