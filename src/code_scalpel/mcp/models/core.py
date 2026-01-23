"""Core MCP result models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from code_scalpel import __version__


class FunctionInfo(BaseModel):
    """Information about a function."""

    name: str = Field(description="Function name")
    lineno: int = Field(description="Line number where function starts")
    end_lineno: int | None = Field(default=None, description="Line number where function ends")
    is_async: bool = Field(default=False, description="Whether function is async")


class ClassInfo(BaseModel):
    """Information about a class."""

    name: str = Field(description="Class name")
    lineno: int = Field(description="Line number where class starts")
    end_lineno: int | None = Field(default=None, description="Line number where class ends")
    methods: list[str] = Field(default_factory=list, description="Method names in class")


class AnalysisResult(BaseModel):
    """Result of code analysis.

    [20251229_FEATURE] v3.3.0 - Added cognitive_complexity and code_smells for tier-based features.
    [20251226_FEATURE] Token efficiency - Removed redundant fields, success only included when False.
    """

    # [20251228_BUGFIX] Restore explicit success flag for stable test/tool contract.
    success: bool = Field(
        default=True,
        description="Whether analysis succeeded.",
    )
    functions: list[str] = Field(description="List of function names found")
    classes: list[str] = Field(description="List of class names found")
    imports: list[str] = Field(description="List of import statements")
    complexity: int = Field(description="Cyclomatic complexity estimate")
    lines_of_code: int = Field(description="Total lines of code")
    issues: list[str] = Field(default_factory=list, description="Issues found")
    error: str | None = Field(default=None, description="Error message if failed")
    # v1.3.0: Detailed info with line numbers
    function_details: list[FunctionInfo] = Field(
        default_factory=list, description="Detailed function info with line numbers"
    )
    class_details: list[ClassInfo] = Field(default_factory=list, description="Detailed class info with line numbers")
    # [20251229_FEATURE] v3.3.0: Tier-gated advanced metrics
    cognitive_complexity: int = Field(
        default=0,
        description="Cognitive complexity score (PRO/ENTERPRISE tier, 0 if COMMUNITY)",
    )
    code_smells: list[str] = Field(
        default_factory=list,
        description="Detected code smells (PRO/ENTERPRISE tier, empty if COMMUNITY)",
    )
    # NOTE: The advanced fields below are intentionally declared once.
    # [20251225_FEATURE] Tier-gated advanced analysis outputs
    halstead_metrics: dict[str, float] | None = Field(
        default=None,
        description="Halstead metrics (PRO/ENTERPRISE; None if not computed)",
    )
    duplicate_code_blocks: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Detected duplicate code blocks (PRO/ENTERPRISE)",
    )
    dependency_graph: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Function call adjacency map (PRO/ENTERPRISE)",
    )
    naming_issues: list[str] = Field(
        default_factory=list,
        description="Naming convention issues (ENTERPRISE)",
    )
    compliance_issues: list[str] = Field(
        default_factory=list,
        description="Compliance findings (ENTERPRISE)",
    )
    custom_rule_violations: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Custom rule matches (ENTERPRISE)",
    )
    organization_patterns: list[str] = Field(
        default_factory=list,
        description="Detected architectural patterns (ENTERPRISE)",
    )

    # [20251231_FEATURE] v3.3.x: Additional tier-gated enrichments (best-effort)
    frameworks: list[str] = Field(
        default_factory=list,
        description="Detected application/framework context (PRO/ENTERPRISE; empty if not computed)",
    )
    dead_code_hints: list[str] = Field(
        default_factory=list,
        description="Dead code candidates/unreachable code hints (PRO/ENTERPRISE; empty if not computed)",
    )
    decorator_summary: dict[str, Any] | None = Field(
        default=None,
        description="Decorator/annotation summary (PRO/ENTERPRISE; None if not computed)",
    )
    type_summary: dict[str, Any] | None = Field(
        default=None,
        description="Type annotation / generic usage summary (PRO/ENTERPRISE; None if not computed)",
    )
    architecture_patterns: list[str] = Field(
        default_factory=list,
        description="Architecture/service-pattern hints (ENTERPRISE; empty if not computed)",
    )
    technical_debt: dict[str, Any] | None = Field(
        default=None,
        description="Technical debt scoring summary (ENTERPRISE; None if not computed)",
    )
    api_surface: dict[str, Any] | None = Field(
        default=None,
        description="API surface summary (ENTERPRISE; None if not computed)",
    )
    prioritized: bool = Field(
        default=False,
        description="Whether outputs were priority-ordered (ENTERPRISE)",
    )
    complexity_trends: dict[str, Any] | None = Field(
        default=None,
        description="Historical complexity trend summary keyed by file_path (ENTERPRISE; None if unavailable)",
    )

    # [20260110_FEATURE] v1.0 - Output metadata for transparency
    language_detected: str | None = Field(
        default=None,
        description="Language that was actually analyzed (python/javascript/typescript/java)",
    )
    tier_applied: str | None = Field(
        default=None,
        description="Tier applied for feature gating (community/pro/enterprise)",
    )

    # [20260119_FEATURE] Parsing error context fields (governed by response_config.json include_on_error)
    error_location: str | None = Field(
        default=None,
        description="Line/column of syntax error (e.g., 'line 5' or 'myfile.py:5')",
    )
    suggested_fix: str | None = Field(
        default=None,
        description="Suggested fix for syntax error when applicable",
    )
    sanitization_report: dict[str, Any] | None = Field(
        default=None,
        description="Parsing sanitization details when code was auto-modified",
    )
    parser_warnings: list[str] = Field(
        default_factory=list,
        description="Parser warnings (e.g., sanitization notices)",
    )

    # [20251228_BUGFIX] Backward-compatible convenience counts used by tests.
    @property
    def function_count(self) -> int:
        return len(self.functions)

    @property
    def class_count(self) -> int:
        return len(self.classes)

    @property
    def import_count(self) -> int:
        return len(self.imports)


class VulnerabilityInfo(BaseModel):
    """Information about a detected vulnerability."""

    type: str = Field(description="Vulnerability type (e.g., SQL Injection)")
    cwe: str = Field(description="CWE identifier")
    severity: str = Field(description="Severity level")
    line: int | None = Field(default=None, description="Line number if known")
    description: str = Field(description="Description of the vulnerability")


class SecurityResult(BaseModel):
    """Result of security analysis."""

    success: bool = Field(description="Whether analysis succeeded")
    server_version: str = Field(default=__version__, description="Code Scalpel version")
    has_vulnerabilities: bool = Field(description="Whether vulnerabilities were found")
    vulnerability_count: int = Field(description="Number of vulnerabilities")
    risk_level: str = Field(description="Overall risk level")
    vulnerabilities: list[VulnerabilityInfo] = Field(default_factory=list, description="List of vulnerabilities")
    taint_sources: list[str] = Field(default_factory=list, description="Identified taint sources")
    # [20251226_FEATURE] Tier-aware optional security outputs for Pro/Enterprise
    sanitizer_paths: list[str] | None = Field(default=None, description="Detected sanitizer usages (Pro/Enterprise)")
    confidence_scores: dict[str, float] | None = Field(
        default=None, description="Heuristic confidence scores per finding"
    )
    false_positive_analysis: dict[str, Any] | None = Field(
        default=None, description="False-positive reduction metadata"
    )
    # [20260118_FEATURE] v1.0 - Pro tier remediation suggestions
    remediation_suggestions: list[str] | None = Field(
        default=None,
        description="Remediation suggestions per vulnerability (Pro/Enterprise)",
    )
    policy_violations: list[dict[str, Any]] | None = Field(
        default=None, description="Custom policy violations (Enterprise)"
    )
    compliance_mappings: dict[str, list[str]] | None = Field(
        default=None, description="Compliance framework mappings (Enterprise)"
    )
    custom_rule_results: list[dict[str, Any]] | None = Field(
        default=None, description="Custom rule matches (Enterprise)"
    )
    # [20251230_FEATURE] v1.0 roadmap Enterprise tier fields
    priority_ordered_findings: list[dict[str, Any]] | None = Field(
        default=None, description="Findings sorted by priority (Enterprise)"
    )
    reachability_analysis: dict[str, Any] | None = Field(
        default=None, description="Vulnerability reachability analysis (Enterprise)"
    )
    false_positive_tuning: dict[str, Any] | None = Field(
        default=None, description="False positive tuning results (Enterprise)"
    )
    error: str | None = Field(default=None, description="Error message if failed")


# [20251216_FEATURE] Unified sink detection result model
class UnifiedDetectedSink(BaseModel):
    """Detected sink with confidence and OWASP mapping."""

    # [20260110_FEATURE] v1.0 - Stable identifier for correlation across runs
    sink_id: str = Field(description="Stable sink identifier (for correlation across runs)")

    pattern: str = Field(description="Sink pattern matched")
    sink_type: str = Field(description="Sink type classification")
    confidence: float = Field(description="Confidence score (0.0-1.0)")
    line: int = Field(default=0, description="Line number of sink occurrence")
    column: int = Field(default=0, description="Column offset of sink occurrence")
    code_snippet: str = Field(default="", description="Snippet around the sink")
    # [20260110_FEATURE] v1.0 - Snippet truncation observability
    code_snippet_truncated: bool = Field(default=False, description="Whether code_snippet was truncated")
    code_snippet_original_len: int | None = Field(default=None, description="Original snippet length before truncation")
    vulnerability_type: str | None = Field(default=None, description="Vulnerability category key")
    owasp_category: str | None = Field(default=None, description="Mapped OWASP Top 10 category")
    # [20251231_FEATURE] v1.0 - Added CWE mapping
    cwe_id: str | None = Field(default=None, description="CWE identifier (e.g., CWE-89)")


class UnifiedSinkResult(BaseModel):
    """Result of unified polyglot sink detection."""

    success: bool = Field(description="Whether detection succeeded")
    # [20260110_FEATURE] v1.0 - Machine-readable failures
    error_code: str | None = Field(default=None, description="Machine-readable error code")
    server_version: str = Field(default=__version__, description="Code Scalpel version")
    language: str = Field(description="Language analyzed")
    sink_count: int = Field(description="Number of sinks detected")
    sinks: list[UnifiedDetectedSink] = Field(default_factory=list, description="Detected sinks meeting threshold")
    coverage_summary: dict[str, Any] = Field(default_factory=dict, description="Summary of sink pattern coverage")
    # [20251225_FEATURE] Tier-specific outputs for Pro/Enterprise
    logic_sinks: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Logic sinks (S3/email/payment) detected at Pro tier",
    )
    extended_language_sinks: dict[str, list[dict[str, Any]]] = Field(
        default_factory=dict,
        description="Additional language sink details for extended support",
    )
    confidence_scores: dict[str, float] = Field(
        default_factory=dict, description="Per-sink confidence scores (Pro/Enterprise)"
    )
    sink_categories: dict[str, list[dict[str, Any]]] = Field(
        default_factory=dict, description="Enterprise sink categorization by risk level"
    )
    risk_assessments: list[dict[str, Any]] = Field(
        default_factory=list, description="Enterprise risk assessments with clearance"
    )
    custom_sink_matches: list[dict[str, Any]] = Field(
        default_factory=list, description="Enterprise custom sink pattern matches"
    )
    # [20251231_FEATURE] v1.0 - New fields for roadmap compliance
    context_analysis: dict[str, Any] | None = Field(default=None, description="[Pro] Context-aware detection results")
    framework_sinks: list[dict[str, Any]] = Field(
        default_factory=list, description="[Pro] Framework-specific sink detections"
    )
    compliance_mapping: dict[str, Any] | None = Field(
        default=None,
        description="[Enterprise] Compliance standard mappings (SOC2, HIPAA)",
    )
    historical_comparison: dict[str, Any] | None = Field(
        default=None, description="[Enterprise] Historical sink tracking comparison"
    )
    remediation_suggestions: list[dict[str, Any]] = Field(
        default_factory=list,
        description="[Enterprise] Automated remediation suggestions",
    )

    # [20260110_FEATURE] v1.0 - Limit observability (populated when applicable)
    truncated: bool | None = Field(default=None, description="Whether results were truncated")
    sinks_detected: int | None = Field(default=None, description="Total sinks detected before truncation")
    max_sinks_applied: int | None = Field(default=None, description="max_sinks limit applied to this response")
    error: str | None = Field(default=None, description="Error message if failed")


class PathCondition(BaseModel):
    """A condition along an execution path."""

    condition: str = Field(description="The condition expression")
    is_satisfiable: bool = Field(description="Whether condition is satisfiable")


class ExecutionPath(BaseModel):
    """An execution path discovered by symbolic execution."""

    path_id: int = Field(description="Unique path identifier")
    conditions: list[str] = Field(description="Conditions along the path")
    final_state: dict[str, Any] = Field(description="Variable values at path end")
    reproduction_input: dict[str, Any] | None = Field(default=None, description="Input values that trigger this path")
    is_reachable: bool = Field(description="Whether path is reachable")


class SymbolicResult(BaseModel):
    """Result of symbolic execution."""

    success: bool = Field(description="Whether analysis succeeded")
    server_version: str = Field(default=__version__, description="Code Scalpel version")
    paths_explored: int = Field(description="Number of execution paths explored")
    paths: list[ExecutionPath] = Field(
        default_factory=list,
        description="Discovered execution paths (may be limited by configuration)",
    )
    symbolic_variables: list[str] = Field(default_factory=list, description="Variables treated symbolically")
    constraints: list[str] = Field(default_factory=list, description="Discovered constraints")
    total_paths: int | None = Field(
        default=None,
        description="Total paths discovered before limiting (if known)",
    )
    truncated: bool = Field(
        default=False,
        description="Whether paths were limited by configuration",
    )
    truncation_warning: str | None = Field(
        default=None,
        description="Neutral warning when results are limited by configuration",
    )
    # [20251230_FEATURE] v1.0 roadmap Pro/Enterprise tier fields
    path_prioritization: dict[str, Any] | None = Field(
        default=None, description="Path prioritization metadata (Pro/Enterprise)"
    )
    concolic_results: dict[str, Any] | None = Field(
        default=None, description="Concolic execution results (Pro/Enterprise)"
    )
    state_space_analysis: dict[str, Any] | None = Field(
        default=None, description="State space reduction analysis (Enterprise)"
    )
    memory_model: dict[str, Any] | None = Field(default=None, description="Memory modeling results (Enterprise)")
    error: str | None = Field(default=None, description="Error message if failed")


class GeneratedTestCase(BaseModel):
    """A generated test case."""

    path_id: int = Field(description="Path ID this test covers")
    function_name: str = Field(description="Function being tested")
    inputs: dict[str, Any] = Field(description="Input values for this test")
    description: str = Field(description="Human-readable description")
    path_conditions: list[str] = Field(default_factory=list, description="Conditions that define this path")


class GenerationResult(BaseModel):
    """Result of test generation."""

    success: bool = Field(description="Whether generation succeeded")
    server_version: str = Field(default=__version__, description="Code Scalpel version")
    function_name: str = Field(description="Function tests were generated for")
    test_count: int = Field(description="Number of test cases generated")
    test_cases: list[GeneratedTestCase] = Field(default_factory=list, description="Generated test cases")
    # [20251225_FEATURE] Tier-aware truncation metadata (neutral messaging).
    total_test_cases: int = Field(default=0, description="Total test cases before truncation")
    truncated: bool = Field(default=False, description="Whether results were truncated")
    truncation_warning: str | None = Field(default=None, description="Neutral warning when truncation occurs")
    pytest_code: str = Field(default="", description="Generated pytest code")
    unittest_code: str = Field(default="", description="Generated unittest code")
    error: str | None = Field(default=None, description="Error message if failed")

    # [20260111_FEATURE] Output metadata for transparency
    tier_applied: str = Field(
        default="community",
        description="Tier used for this generation (community/pro/enterprise)",
    )
    framework_used: str = Field(
        default="pytest",
        description="Test framework used for generation",
    )
    max_test_cases_limit: int | None = Field(
        default=None,
        description="Max test cases limit applied (None=unlimited)",
    )
    data_driven_enabled: bool = Field(
        default=False,
        description="Whether data-driven/parametrized tests were generated",
    )
    bug_reproduction_enabled: bool = Field(
        default=False,
        description="Whether bug reproduction mode was used",
    )


class RefactorSecurityIssue(BaseModel):
    """A security issue found in refactored code."""

    type: str = Field(description="Vulnerability type")
    severity: str = Field(description="Severity level")
    line: int | None = Field(default=None, description="Line number")
    description: str = Field(description="Issue description")
    cwe: str | None = Field(default=None, description="CWE identifier")


class RefactorSimulationResult(BaseModel):
    """Result of refactor simulation."""

    success: bool = Field(description="Whether simulation succeeded")
    server_version: str = Field(default=__version__, description="Code Scalpel version")
    is_safe: bool = Field(description="Whether the refactor is safe to apply")
    status: str = Field(description="Status: safe, unsafe, warning, or error")
    reason: str | None = Field(default=None, description="Reason if not safe")
    security_issues: list[RefactorSecurityIssue] = Field(default_factory=list, description="Security issues found")
    structural_changes: dict[str, Any] = Field(default_factory=dict, description="Functions/classes added/removed")
    warnings: list[str] = Field(default_factory=list, description="Warnings")
    error: str | None = Field(default=None, description="Error message if failed")


class CrawlFunctionInfo(BaseModel):
    """Information about a function from project crawl."""

    name: str = Field(description="Function name (qualified if method)")
    lineno: int = Field(description="Line number")
    complexity: int = Field(description="Cyclomatic complexity")


class CrawlClassInfo(BaseModel):
    """Information about a class from project crawl."""

    name: str = Field(description="Class name")
    lineno: int = Field(description="Line number")
    methods: list[CrawlFunctionInfo] = Field(default_factory=list, description="Methods in the class")
    bases: list[str] = Field(default_factory=list, description="Base classes")


class CrawlFileResult(BaseModel):
    """Result of analyzing a single file during crawl."""

    path: str = Field(description="Relative path to the file")
    status: str = Field(description="success or error")
    lines_of_code: int = Field(default=0, description="Lines of code")
    functions: list[CrawlFunctionInfo] = Field(default_factory=list, description="Top-level functions")
    classes: list[CrawlClassInfo] = Field(default_factory=list, description="Classes found")
    imports: list[str] = Field(default_factory=list, description="Import statements")
    complexity_warnings: list[CrawlFunctionInfo] = Field(default_factory=list, description="High-complexity functions")
    error: str | None = Field(default=None, description="Error if failed")


class CrawlSummary(BaseModel):
    """Summary statistics from project crawl."""

    total_files: int = Field(description="Total files scanned")
    successful_files: int = Field(description="Files analyzed successfully")
    failed_files: int = Field(description="Files that failed analysis")
    total_lines_of_code: int = Field(description="Total lines of code")
    total_functions: int = Field(description="Total functions found")
    total_classes: int = Field(description="Total classes found")
    complexity_warnings: int = Field(description="Number of high-complexity functions")


class ProjectCrawlResult(BaseModel):
    """Result of crawling an entire project."""

    # Allow tier-gated feature fields without breaking older clients.
    try:
        from pydantic import ConfigDict as _ConfigDict  # type: ignore

        model_config = _ConfigDict(extra="allow")
    except Exception:

        class Config:  # type: ignore
            extra = "allow"

    success: bool = Field(description="Whether crawl succeeded")
    server_version: str = Field(default=__version__, description="Code Scalpel version")
    root_path: str = Field(description="Project root path")
    timestamp: str = Field(description="When the crawl was performed")
    summary: CrawlSummary = Field(description="Summary statistics")
    files: list[CrawlFileResult] = Field(default_factory=list, description="Analyzed files")
    errors: list[CrawlFileResult] = Field(default_factory=list, description="Files with errors")
    markdown_report: str = Field(default="", description="Markdown report")
    error: str | None = Field(default=None, description="Error if failed")
    # [20260106_FEATURE] v1.0 pre-release - Output transparency metadata
    tier_applied: str | None = Field(
        default=None,
        description="Which tier's rules were applied (community/pro/enterprise)",
    )
    crawl_mode: str | None = Field(
        default=None,
        description="Crawl mode used: 'discovery' (Community) or 'deep' (Pro/Enterprise)",
    )
    files_limit_applied: int | None = Field(
        default=None, description="Max files limit that was applied (None = unlimited)"
    )
    # Tier-gated fields (best-effort, optional)
    language_breakdown: dict[str, int] | None = Field(default=None, description="Counts of files per detected language")
    cache_hits: int | None = Field(
        default=None,
        description="Number of files reused from cache (Pro/Enterprise incremental)",
    )
    compliance_summary: dict[str, Any] | None = Field(
        default=None, description="Enterprise compliance scanning summary"
    )
    framework_hints: list[str] | None = Field(
        default=None, description="Detected frameworks/entrypoints in discovery mode"
    )
    entrypoints: list[str] | None = Field(default=None, description="Detected entrypoint file paths")


class SurgicalExtractionResult(BaseModel):
    """Result of surgical code extraction."""

    success: bool = Field(description="Whether extraction succeeded")
    server_version: str = Field(default=__version__, description="Code Scalpel version")
    name: str = Field(description="Name of extracted element")
    code: str = Field(description="Extracted source code")
    node_type: str = Field(description="Type: function, class, or method")
    line_start: int = Field(default=0, description="Starting line number")
    line_end: int = Field(default=0, description="Ending line number")
    dependencies: list[str] = Field(default_factory=list, description="Names of dependencies")
    imports_needed: list[str] = Field(default_factory=list, description="Required import statements")
    token_estimate: int = Field(default=0, description="Estimated token count")
    error: str | None = Field(default=None, description="Error if failed")


class ContextualExtractionResult(BaseModel):
    """Result of extraction with dependencies included."""

    # Allow tier-gated feature fields without breaking older clients.
    try:
        from pydantic import ConfigDict as _ConfigDict  # type: ignore

        model_config = _ConfigDict(extra="allow")
    except Exception:

        class Config:  # type: ignore
            extra = "allow"

    success: bool = Field(description="Whether extraction succeeded")
    server_version: str = Field(default=__version__, description="Code Scalpel version")
    target_name: str = Field(description="Name of target element")
    target_code: str = Field(description="Target element source code")
    context_code: str = Field(description="Combined dependency source code")
    full_code: str = Field(description="Complete code block for LLM consumption")
    context_items: list[str] = Field(default_factory=list, description="Names of included dependencies")
    total_lines: int = Field(default=0, description="Total lines in extraction")
    # v1.3.0: Line number information
    line_start: int = Field(default=0, description="Starting line number of target")
    line_end: int = Field(default=0, description="Ending line number of target")
    token_estimate: int = Field(default=0, description="Estimated token count")
    error: str | None = Field(default=None, description="Error if failed")

    # [20260111_FEATURE] Output metadata for transparency
    tier_applied: str = Field(
        default="community",
        description="Tier used for this extraction (community/pro/enterprise)",
    )
    language_detected: str | None = Field(
        default=None,
        description="Language detected/used for extraction (python/javascript/typescript/java)",
    )
    cross_file_deps_enabled: bool = Field(
        default=False,
        description="Whether cross-file dependency resolution was enabled",
    )
    max_depth_applied: int | None = Field(
        default=None,
        description="Max depth limit applied for context/dependencies (None=unlimited)",
    )

    # [20251216_FEATURE] v2.0.2 - JSX/TSX extraction metadata
    jsx_normalized: bool = Field(default=False, description="Whether JSX syntax was normalized")
    is_server_component: bool = Field(default=False, description="Next.js Server Component (async)")
    is_server_action: bool = Field(default=False, description="Next.js Server Action ('use server')")
    component_type: str | None = Field(default=None, description="React component type: 'functional', 'class', or None")
    # [20260103_FEATURE] v3.3.1 - Warnings field for tier-aware behavior messaging
    warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal warnings (e.g., tier-aware context depth clamping)",
    )
    advanced: dict[str, Any] = Field(default_factory=dict, description="Tier-specific or experimental metadata")


class PatchResultModel(BaseModel):
    """Result of a surgical code modification."""

    success: bool = Field(description="Whether the patch was applied successfully")
    server_version: str = Field(default=__version__, description="Code Scalpel version")
    file_path: str = Field(description="Path to the modified file")
    target_name: str = Field(description="Name of the modified symbol")
    target_type: str = Field(description="Type: function, class, or method")
    lines_before: int = Field(default=0, description="Lines in original code")
    lines_after: int = Field(default=0, description="Lines in replacement code")
    lines_delta: int = Field(default=0, description="Change in line count")
    backup_path: str | None = Field(default=None, description="Path to backup file")
    # [20260110_FEATURE] Machine-readable failure signaling for minimal output profiles.
    error_code: str | None = Field(default=None, description="Machine-readable error code if failed")
    hint: str | None = Field(default=None, description="Actionable hint to remediate failure")
    # [20260121_REFACTOR] Switched to per-call throughput model; removed session state fields
    # Batch operations report aggregate results and truncation warnings instead of session counts
    max_updates_per_call: int | None = Field(default=None, description="Per-call throughput cap applied for this tier")
    updates_in_batch: int | None = Field(default=None, description="Number of updates in this batch (for batch calls)")
    batch_truncated: bool = Field(default=False, description="True if batch was truncated due to per-call limit")
    # [20251225_FEATURE] Optional warnings for tier-aware behavior (neutral messaging).
    warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal warnings (neutral; no upgrade messaging)",
    )
    error: str | None = Field(default=None, description="Error message if failed")


# Ensure forward references are resolved for tool schemas.
PatchResultModel.model_rebuild()


# [20251212_FEATURE] v1.4.0 - New MCP tool models for enhanced AI context


class FileContextResult(BaseModel):
    """Result of get_file_context - file overview without full content."""

    success: bool = Field(description="Whether analysis succeeded")
    server_version: str = Field(default=__version__, description="Code Scalpel version")

    # [20260111_FEATURE] v1.0 - Output metadata fields for transparency
    tier_applied: str = Field(
        default="community",
        description="The tier used for analysis (community, pro, enterprise)",
    )
    max_context_lines_applied: int | None = Field(
        default=None,
        description="The max context lines limit applied (None = unlimited for Enterprise)",
    )
    pro_features_enabled: bool = Field(
        default=False,
        description="Whether Pro tier features were enabled (code smells, doc coverage, maintainability)",
    )
    enterprise_features_enabled: bool = Field(
        default=False,
        description="Whether Enterprise tier features were enabled (metadata, compliance, owners)",
    )

    file_path: str = Field(description="Path to the analyzed file")
    language: str = Field(default="python", description="Detected language")
    line_count: int = Field(description="Total lines in file")
    functions: list[FunctionInfo | str] = Field(default_factory=list, description="Function names or detailed info")
    classes: list[ClassInfo | str] = Field(default_factory=list, description="Class names or detailed info")
    imports: list[str] = Field(default_factory=list, description="Import statements (max 20)")
    exports: list[str] = Field(default_factory=list, description="Exported symbols (__all__)")
    complexity_score: int = Field(default=0, description="Overall cyclomatic complexity")
    has_security_issues: bool = Field(default=False, description="Whether file has security issues")
    summary: str = Field(default="", description="Brief description of file purpose")
    # [20251220_FEATURE] v3.0.5 - Truncation communication
    imports_truncated: bool = Field(default=False, description="Whether imports list was truncated")
    total_imports: int = Field(default=0, description="Total imports before truncation")
    # [20251225_FEATURE] v3.3.0 - Tiered enrichments and safeguards
    semantic_summary: str | None = Field(default=None, description="AI-lite semantic summary when enabled")
    intent_tags: list[str] = Field(
        default_factory=list,
        description="Extracted intents/topics from docstrings/names",
    )
    related_imports: list[str] = Field(
        default_factory=list,
        description="Resolved related imports for context expansion",
    )
    expanded_context: str | None = Field(
        default=None, description="Smartly expanded context when allowed by tier limits"
    )
    pii_redacted: bool = Field(default=False, description="Whether PII content was redacted")
    secrets_masked: bool = Field(default=False, description="Whether secrets/API keys were masked")
    redaction_summary: list[str] = Field(default_factory=list, description="What redactions/masking actions were taken")
    access_controlled: bool = Field(default=False, description="Whether RBAC/file access controls were applied")
    # [20251231_FEATURE] v3.3.1 - Pro tier: code quality metrics
    code_smells: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Detected code smells (Pro+): [{type, line, message, severity}]",
    )
    doc_coverage: float | None = Field(
        default=None,
        description="Documentation coverage percentage (Pro+): 0.0-100.0",
    )
    maintainability_index: float | None = Field(
        default=None,
        description="Maintainability index (Pro+): 0-100 scale (higher is better)",
    )
    # [20251231_FEATURE] v3.3.1 - Enterprise tier: organizational metadata
    custom_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Custom metadata from .code-scalpel/metadata.yaml (Enterprise)",
    )
    compliance_flags: list[str] = Field(
        default_factory=list,
        description="Compliance flags detected (Enterprise): HIPAA, PCI, SOC2, etc.",
    )
    technical_debt_score: float | None = Field(
        default=None,
        description="Technical debt score (Enterprise): estimated hours to fix issues",
    )
    owners: list[str] = Field(
        default_factory=list,
        description="Code owners from CODEOWNERS file (Enterprise)",
    )
    historical_metrics: dict[str, Any] | None = Field(
        default=None,
        description="Historical metrics from git (Enterprise): churn, age, contributors",
    )
    error: str | None = Field(default=None, description="Error message if failed")


class SymbolReference(BaseModel):
    """A single reference to a symbol."""

    file: str = Field(description="File path containing the reference")
    line: int = Field(description="Line number of the reference")
    column: int = Field(default=0, description="Column number")
    context: str = Field(description="Code snippet showing usage context")
    is_definition: bool = Field(default=False, description="Whether this is the definition")
    # [20251225_FEATURE] Tiered symbol references: optional metadata
    reference_type: str | None = Field(
        default=None,
        description="Reference category (definition|import|call|read|write|reference)",
    )
    is_test_file: bool = Field(
        default=False,
        description="Whether the reference is in a test file",
    )
    owners: list[str] | None = Field(
        default=None,
        description="CODEOWNERS owners for the file (Enterprise)",
    )


class SymbolReferencesResult(BaseModel):
    """Result of get_symbol_references - all usages of a symbol."""

    success: bool = Field(description="Whether search succeeded")
    server_version: str = Field(default=__version__, description="Code Scalpel version")

    # [20250112_FEATURE] Output metadata fields for tier transparency
    tier_applied: str = Field(
        default="community",
        description="The tier that was applied to this request (community, pro, enterprise)",
    )
    max_files_applied: int | None = Field(
        default=None,
        description="The max_files_searched limit applied",
    )
    max_references_applied: int | None = Field(
        default=None,
        description="The max_references limit applied",
    )
    pro_features_enabled: list[str] | None = Field(
        default=None,
        description="List of Pro tier features enabled (None if community tier)",
    )
    enterprise_features_enabled: list[str] | None = Field(
        default=None,
        description="List of Enterprise tier features enabled (None if not enterprise)",
    )

    symbol_name: str = Field(description="Name of the searched symbol")
    definition_file: str | None = Field(default=None, description="File where symbol is defined")
    definition_line: int | None = Field(default=None, description="Line where symbol is defined")
    references: list[SymbolReference] = Field(default_factory=list, description="References found (max 100)")
    total_references: int = Field(default=0, description="Total reference count before truncation")
    # [20251225_FEATURE] Tiered symbol references: scan metadata
    files_scanned: int = Field(default=0, description="Number of files scanned")
    total_files: int = Field(default=0, description="Total candidate files before filtering")
    files_truncated: bool = Field(default=False, description="Whether file scanning was truncated")
    file_truncation_warning: str | None = Field(default=None, description="Warning if file scan was truncated")
    category_counts: dict[str, int] | None = Field(default=None, description="Counts by reference category (Pro+)")
    owner_counts: dict[str, int] | None = Field(default=None, description="Counts by CODEOWNERS owner (Enterprise)")
    change_risk: str | None = Field(default=None, description="Heuristic change risk (Enterprise)")
    # [20251220_FEATURE] v3.0.5 - Truncation communication
    references_truncated: bool = Field(default=False, description="Whether references list was truncated")
    truncation_warning: str | None = Field(default=None, description="Warning if results truncated")
    # [20251226_FEATURE] Enterprise tier: Impact analysis fields
    risk_score: int | None = Field(default=None, description="Weighted risk score 0-100 (Enterprise)")
    risk_factors: list[str] | None = Field(
        default=None, description="List of factors contributing to risk (Enterprise)"
    )
    blast_radius: int | None = Field(default=None, description="Number of unique files affected (Enterprise)")
    test_coverage_ratio: float | None = Field(
        default=None, description="Ratio of references in test files (Enterprise)"
    )
    complexity_hotspots: list[str] | None = Field(
        default=None,
        description="High-complexity files containing references (Enterprise)",
    )
    impact_mermaid: str | None = Field(
        default=None,
        description="Mermaid diagram of reference distribution (Enterprise)",
    )
    codeowners_coverage: float | None = Field(
        default=None,
        description="Ratio of references with CODEOWNERS attribution (Enterprise)",
    )
    error: str | None = Field(default=None, description="Error message if failed")
