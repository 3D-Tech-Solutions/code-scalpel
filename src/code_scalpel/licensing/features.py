"""
Feature Capabilities - Hierarchical feature gating for all MCP tools.

[20251225_FEATURE] Implements parameter-level feature gating instead of tool-level hiding.

This module defines capabilities and limits for each tool at each tier.
ALL tools are available at COMMUNITY tier, but with restricted parameters/features.

Architecture:
    - All 20 MCP tools available at all tiers
    - Features/parameters gated by capabilities
    - Limits enforced at runtime
    - Automatic upgrade hints generation

Usage:
    from code_scalpel.licensing.features import get_tool_capabilities

    caps = get_tool_capabilities("security_scan", "community")
    if "full_vulnerability_list" in caps["capabilities"]:
        # Show all findings
    else:
        # Limit to caps["limits"]["max_findings"]
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# [20251225_FEATURE] Comprehensive tool capability matrix
# Every tool has capabilities and limits defined for each tier
TOOL_CAPABILITIES: dict[str, dict[str, dict[str, Any]]] = {
    "analyze_code": {
        "community": {
            "enabled": True,
            "capabilities": {
                "basic_ast",
                "function_inventory",
                "class_inventory",
                "imports",
                "complexity_metrics",
            },
            "limits": {"max_file_size_mb": 1},
            "description": "Basic AST parsing with complexity metrics",
        },
        "pro": {
            "enabled": True,
            "capabilities": {
                "basic_ast",
                "function_inventory",
                "class_inventory",
                "imports",
                "complexity_metrics",
                "code_smells",
                "halstead_metrics",
                "cognitive_complexity",
                "duplicate_code_detection",
                "dependency_graph",
                # [20251231_FEATURE] v3.3.x - Additional enrichments
                "framework_detection",
                "dead_code_detection",
                "decorator_analysis",
            },
            "limits": {"max_file_size_mb": 10},
            "description": "Full analysis with complexity metrics",
        },
        "enterprise": {
            "enabled": True,
            "capabilities": {
                "basic_ast",
                "function_inventory",
                "class_inventory",
                "imports",
                "complexity_metrics",
                "code_smells",
                "halstead_metrics",
                "cognitive_complexity",
                "duplicate_code_detection",
                "dependency_graph",
                "custom_rules",
                "compliance_checks",
                "organization_patterns",
                "naming_conventions",
                # [20251231_FEATURE] v3.3.x - Enterprise enrichments
                "framework_detection",
                "dead_code_detection",
                "decorator_analysis",
                "architecture_patterns",
                "technical_debt_scoring",
                "api_surface_analysis",
                "priority_ordering",
                "complexity_trends",
            },
            "limits": {"max_file_size_mb": 100},
            "description": "Advanced analysis with custom rules and compliance",
        },
    },
    "security_scan": {
        "community": {
            "enabled": True,
            # [20251226_FEATURE] Align security_scan capability matrix with tier tests
            # [20251228_BUGFIX] Renamed owasp_top_10_checks → owasp_checks for documentation alignment
            # [20251230_FEATURE] v1.0 roadmap alignment - added path_traversal_detection
            "capabilities": {
                "basic_vulnerabilities",
                "owasp_checks",
                "ast_pattern_matching",
                "sql_injection_detection",
                "xss_detection",
                "command_injection_detection",
                "path_traversal_detection",  # CWE-22 per roadmap v1.0
            },
            "limits": {
                "max_findings": 50,
                "max_file_size_kb": 500,
                "vulnerability_types": "owasp_top_10",
            },
            "description": "Basic vulnerability detection with OWASP focus",
        },
        "pro": {
            "enabled": True,
            # [20251230_FEATURE] v1.0 roadmap alignment - added NoSQL, LDAP, secret detection, confidence scoring
            "capabilities": {
                "basic_vulnerabilities",
                "owasp_checks",
                "ast_pattern_matching",
                "sql_injection_detection",
                "xss_detection",
                "command_injection_detection",
                "path_traversal_detection",
                "context_aware_scanning",
                "sanitizer_recognition",
                "data_flow_sensitive_analysis",
                "false_positive_reduction",
                "remediation_suggestions",
                "owasp_categorization",
                "full_vulnerability_list",
                # v1.0 roadmap Pro tier capabilities
                "nosql_injection_detection",  # MongoDB, etc.
                "ldap_injection_detection",
                "secret_detection",  # API keys, passwords
                "confidence_scoring",  # Per-finding confidence
                # [20260107_FEATURE] v1.0 roadmap advanced vulnerability types
                "csrf_detection",  # Cross-Site Request Forgery
                "ssrf_detection",  # Server-Side Request Forgery
                "jwt_vulnerability_detection",  # JWT security issues
            },
            "limits": {
                "max_findings": None,
                "max_file_size_kb": None,
                "vulnerability_types": "all",
            },
            "description": "Advanced taint analysis with sanitizer recognition and FP reduction",
        },
        "enterprise": {
            "enabled": True,
            # [20251230_FEATURE] v1.0 roadmap alignment - added reachability, priority ordering
            "capabilities": {
                "basic_vulnerabilities",
                "owasp_checks",
                "ast_pattern_matching",
                "sql_injection_detection",
                "xss_detection",
                "command_injection_detection",
                "path_traversal_detection",
                "context_aware_scanning",
                "sanitizer_recognition",
                "data_flow_sensitive_analysis",
                "false_positive_reduction",
                "remediation_suggestions",
                "owasp_categorization",
                "full_vulnerability_list",
                "nosql_injection_detection",
                "ldap_injection_detection",
                "secret_detection",
                "confidence_scoring",
                # [20260107_FEATURE] v1.0 roadmap advanced vulnerability types
                "csrf_detection",  # Cross-Site Request Forgery
                "ssrf_detection",  # Server-Side Request Forgery
                "jwt_vulnerability_detection",  # JWT security issues
                "cross_file_taint",
                "custom_policy_engine",
                "org_specific_rules",
                "log_encryption_enforcement",
                "compliance_rule_checking",
                "custom_security_rules",
                "compliance_reporting",
                "priority_cve_alerts",
                # v1.0 roadmap Enterprise tier capabilities
                "priority_finding_ordering",  # Priority-based finding ordering
                "vulnerability_reachability_analysis",  # Reachability analysis
                "false_positive_tuning",  # FP tuning (distinct from FP reduction)
            },
            "limits": {
                "max_findings": None,
                "max_file_size_kb": None,
                "vulnerability_types": "all",
            },
            "description": "Enterprise security with custom policy engine and compliance mapping",
        },
    },
    "extract_code": {
        "community": {
            "enabled": True,
            "capabilities": {"single_file_extraction", "basic_symbols"},
            "limits": {
                "include_cross_file_deps": False,
                "max_depth": 0,
                "max_extraction_size_mb": 1,
            },
            "description": "Single-file symbol extraction only",
        },
        "pro": {
            "enabled": True,
            "capabilities": {
                "single_file_extraction",
                "basic_symbols",
                "cross_file_deps",
                "context_extraction",
                "variable_promotion",
                "closure_detection",
                "dependency_injection_suggestions",
            },
            "limits": {
                "include_cross_file_deps": True,
                "max_depth": 1,  # Direct dependencies only
                "max_extraction_size_mb": 10,
            },
            "description": "Cross-file extraction with variable promotion",
        },
        "enterprise": {
            "enabled": True,
            "capabilities": {
                "single_file_extraction",
                "basic_symbols",
                "cross_file_deps",
                "context_extraction",
                "org_wide_resolution",
                "custom_extraction_patterns",
                "dockerfile_generation",
                "service_boundaries",
            },
            "limits": {
                "include_cross_file_deps": True,
                "max_depth": None,  # Unlimited
                "max_extraction_size_mb": 100,
            },
            "description": "Unlimited depth with Dockerfile generation and org-wide resolution",
        },
    },
    "rename_symbol": {
        "community": {
            "enabled": True,
            "capabilities": {
                "definition_rename",
                "backup",
                "path_security_validation",
            },
            "limits": {
                # Community: definition-only rename (no cross-file updates)
                "max_files_searched": 0,
                "max_files_updated": 0,
            },
            "description": "Rename symbol definition in a single file",
        },
        "pro": {
            "enabled": True,
            "capabilities": {
                "definition_rename",
                "backup",
                "path_security_validation",
                "cross_file_reference_rename",
                "import_rename",
            },
            "limits": {
                "max_files_searched": 500,
                "max_files_updated": 200,
            },
            "description": "Rename definition + conservative cross-file references/imports",
        },
        "enterprise": {
            "enabled": True,
            "capabilities": {
                "definition_rename",
                "backup",
                "path_security_validation",
                "cross_file_reference_rename",
                "import_rename",
                "organization_wide_rename",
            },
            "limits": {
                # Unlimited by omission in limits.toml; defaults kept as None here.
                "max_files_searched": None,
                "max_files_updated": None,
            },
            "description": "Enterprise-scale rename with org-wide scope",
        },
    },
    "symbolic_execute": {
        "community": {
            "enabled": True,
            # [20251230_FEATURE] v1.0 roadmap alignment - added loop_unrolling, updated constraint types
            "capabilities": {
                "basic_symbolic_execution",
                "simple_constraints",
                "path_exploration",
                "loop_unrolling",  # max 10 iterations
            },
            "limits": {
                "max_paths": 50,  # Roadmap v1.0: 50 paths max
                "max_depth": 10,  # max loop iterations
                "constraint_types": [
                    "int",
                    "bool",
                    "string",
                    "float",
                ],  # Basic types per roadmap
            },
            "description": "Basic symbolic execution (50 paths max, basic types)",
        },
        "pro": {
            "enabled": True,
            # [20251230_FEATURE] v1.0 roadmap alignment - added Pro tier features
            "capabilities": {
                "basic_symbolic_execution",
                "simple_constraints",
                "path_exploration",
                "loop_unrolling",
                "complex_constraints",
                "string_constraints",
                # v1.0 roadmap Pro capabilities
                "smart_path_prioritization",
                "constraint_optimization",
                "deep_loop_unrolling",  # max 100 iterations
                "list_dict_types",  # List, Dict support
                "concolic_execution",  # Concrete + symbolic
            },
            "limits": {
                "max_paths": None,  # Unlimited per roadmap v1.0
                "max_depth": 100,  # Deeper loop unrolling
                "constraint_types": ["int", "bool", "string", "float", "list", "dict"],
            },
            "description": "Advanced symbolic execution with smart prioritization and concolic mode",
        },
        "enterprise": {
            "enabled": True,
            # [20251230_FEATURE] v1.0 roadmap alignment - added Enterprise tier features
            "capabilities": {
                "basic_symbolic_execution",
                "simple_constraints",
                "path_exploration",
                "loop_unrolling",
                "complex_constraints",
                "string_constraints",
                "smart_path_prioritization",
                "constraint_optimization",
                "deep_loop_unrolling",
                "list_dict_types",
                "concolic_execution",
                "custom_solvers",
                "advanced_types",
                "formal_verification",
                "equivalence_checking",
                # v1.0 roadmap Enterprise capabilities
                "custom_path_prioritization",
                "distributed_execution",
                "state_space_reduction",
                "complex_object_types",
                "memory_modeling",
            },
            "limits": {
                "max_paths": None,  # Unlimited
                "max_depth": None,  # Unlimited loop unrolling
                "constraint_types": "all",
            },
            "description": "Unlimited symbolic execution with distributed analysis and memory modeling",
        },
    },
    "generate_unit_tests": {
        "community": {
            "enabled": True,
            "capabilities": {"basic_test_generation"},
            "limits": {
                "max_test_cases": 5,
                "test_frameworks": ["pytest"],
            },
            "description": "Basic test generation (5 tests max)",
        },
        "pro": {
            "enabled": True,
            "capabilities": {
                "basic_test_generation",
                "advanced_test_generation",
                # [20251229_FEATURE] v3.3.0 - Parametrized/data-driven tests.
                "data_driven_tests",
                "edge_case_detection",
            },
            "limits": {
                "max_test_cases": 20,
                "test_frameworks": ["pytest", "unittest"],
            },
            "description": "Advanced test generation with edge cases",
        },
        "enterprise": {
            "enabled": True,
            "capabilities": {
                "basic_test_generation",
                "advanced_test_generation",
                "edge_case_detection",
                "custom_test_templates",
                # [20251229_FEATURE] v3.3.0 - Parametrized/data-driven tests (inherited from Pro).
                "data_driven_tests",
                # [20251229_FEATURE] v3.3.0 - Bug reproduction from crash logs.
                "bug_reproduction",
                "coverage_optimization",
            },
            "limits": {
                "max_test_cases": None,
                "test_frameworks": "all",
            },
            "description": "Unlimited tests with custom templates",
        },
    },
    "crawl_project": {
        "community": {
            "enabled": True,
            "capabilities": {
                "full_file_tree_indexing",
                "language_breakdown",
                "gitignore_respect",
                "basic_statistics",
                "entrypoint_detection",
            },
            "limits": {
                "max_files": 100,
                "max_depth": 10,
            },
            "description": "Full file tree indexing with language breakdown, respects .gitignore",
        },
        "pro": {
            "enabled": True,
            "capabilities": {
                "full_file_tree_indexing",
                "language_breakdown",
                "gitignore_respect",
                "basic_statistics",
                "entrypoint_detection",
                "parallel_file_processing",
                "incremental_crawling",
                "smart_crawl",
                "framework_entrypoint_detection",
                "dependency_mapping",
                "hotspot_identification",
                "generated_code_detection",
                "nextjs_pages_detection",
                "django_views_detection",
                "flask_routes_detection",
            },
            "limits": {
                "max_files": None,
                "max_depth": None,
            },
            "description": "Smart Crawl with framework-specific entry point detection",
        },
        "enterprise": {
            "enabled": True,
            "capabilities": {
                "full_file_tree_indexing",
                "language_breakdown",
                "gitignore_respect",
                "basic_statistics",
                "entrypoint_detection",
                "smart_crawl",
                "framework_entrypoint_detection",
                "generated_code_detection",
                "nextjs_pages_detection",
                "django_views_detection",
                "flask_routes_detection",
                "parallel_file_processing",
                "incremental_crawling",
                "dependency_mapping",
                "hotspot_identification",
                "distributed_crawling",
                "historical_trend_analysis",
                "custom_crawl_rules",
                "compliance_scanning",
                "incremental_indexing",
                "monorepo_support",
                "cross_repo_dependency_linking",
                "100k_plus_files_support",
            },
            "limits": {
                "max_files": None,
                "max_depth": None,
                "max_repos": None,
            },
            "description": "Incremental indexing for massive Monorepos and cross-repository linking",
        },
    },
    "get_call_graph": {
        "community": {
            "enabled": True,
            "capabilities": {
                "static_call_graph",
                "caller_analysis",
                "callee_analysis",
                "mermaid_diagram_generation",
                "circular_import_detection",
                "entry_point_detection",
            },
            "limits": {
                "max_depth": 3,
                "max_nodes": 50,
            },
            "description": "Static call graph generation with tier limits",
        },
        "pro": {
            "enabled": True,
            "capabilities": {
                "static_call_graph",
                "caller_analysis",
                "callee_analysis",
                "mermaid_diagram_generation",
                "circular_import_detection",
                "entry_point_detection",
                "advanced_call_graph",
                "interface_resolution",
                "polymorphism_resolution",
                "virtual_call_tracking",
                "dynamic_dispatch_analysis",
            },
            "limits": {
                "max_depth": 50,
                "max_nodes": 500,
            },
            "description": "Deeper call graphs with improved call resolution",
        },
        "enterprise": {
            "enabled": True,
            "capabilities": {
                "static_call_graph",
                "caller_analysis",
                "callee_analysis",
                "mermaid_diagram_generation",
                "circular_import_detection",
                "entry_point_detection",
                "advanced_call_graph",
                "interface_resolution",
                "polymorphism_resolution",
                "virtual_call_tracking",
                "dynamic_dispatch_analysis",
                "hot_path_identification",
                "dead_code_detection",
                "runtime_trace_overlay",
                "custom_graph_analysis",
            },
            "limits": {
                "max_depth": None,
                "max_nodes": None,
            },
            "description": "Unlimited depth with advanced metadata",
        },
    },
    "get_graph_neighborhood": {
        "community": {
            "enabled": True,
            "capabilities": {"basic_neighborhood"},
            "limits": {
                "max_k": 1,  # Immediate neighbors only
                "max_nodes": 20,
            },
            "description": "1-hop neighborhood only",
        },
        "pro": {
            "enabled": True,
            "capabilities": {
                "basic_neighborhood",
                "advanced_neighborhood",
                "semantic_neighbors",
                "logical_relationship_detection",
            },
            "limits": {
                "max_k": 5,
                "max_nodes": 100,
            },
            "description": "Configurable k-hop traversal with semantic neighbors",
        },
        "enterprise": {
            "enabled": True,
            "capabilities": {
                "basic_neighborhood",
                "advanced_neighborhood",
                "semantic_neighbors",
                "logical_relationship_detection",
                "custom_traversal",
                "weighted_paths",
                "graph_query_language",
                "custom_traversal_rules",
                "path_constraint_queries",
            },
            "limits": {
                "max_k": None,
                "max_nodes": None,
            },
            "description": "Unlimited hops with query language and custom traversal",
        },
    },
    "get_symbol_references": {
        "community": {
            "enabled": True,
            # [20251225_FEATURE] Capability-driven gating for references tool
            "capabilities": {
                "ast_based_find_usages",
                "exact_reference_matching",
                "comment_string_exclusion",
                "definition_location",
            },
            "limits": {
                # [20251225_FEATURE] Community limits: bounded scan and output
                "max_files_searched": 100,
                "max_references": 100,
            },
            "description": "Bounded reference search across the project",
        },
        "pro": {
            "enabled": True,
            "capabilities": {
                "ast_based_find_usages",
                "exact_reference_matching",
                "comment_string_exclusion",
                "definition_location",
                "project_wide_search",
                # [20251225_FEATURE] Pro features
                "usage_categorization",
                "read_write_classification",
                "import_classification",
                "scope_filtering",
                "test_file_filtering",
            },
            "limits": {
                "max_files_searched": None,
                "max_references": None,
            },
            "description": "Full project-wide reference search with categorization",
        },
        "enterprise": {
            "enabled": True,
            "capabilities": {
                "ast_based_find_usages",
                "exact_reference_matching",
                "comment_string_exclusion",
                "definition_location",
                "project_wide_search",
                "usage_categorization",
                "read_write_classification",
                "import_classification",
                "scope_filtering",
                "test_file_filtering",
                # [20251225_FEATURE] Enterprise features
                "impact_analysis",
                "codeowners_integration",
                "ownership_attribution",
                "change_risk_assessment",
            },
            "limits": {
                "max_files_searched": None,
                "max_references": None,
            },
            "description": "Ownership attribution and impact analysis",
        },
    },
    "simulate_refactor": {
        "community": {
            "enabled": True,
            "capabilities": {"basic_simulation", "structural_diff"},
            "limits": {
                "max_file_size_mb": 1,
                "analysis_depth": "basic",
            },
            "description": "Basic refactor simulation with structural diff",
        },
        "pro": {
            "enabled": True,
            "capabilities": {
                "basic_simulation",
                "structural_diff",
                "advanced_simulation",
                "behavior_preservation",
                "type_checking",
                "build_check",
            },
            "limits": {
                "max_file_size_mb": 10,
                "analysis_depth": "advanced",
            },
            "description": "Advanced simulation with type checking and behavior validation",
        },
        "enterprise": {
            "enabled": True,
            "capabilities": {
                "basic_simulation",
                "structural_diff",
                "advanced_simulation",
                "behavior_preservation",
                "type_checking",
                "build_check",
                "regression_prediction",
                "impact_analysis",
                "custom_rules",
                "compliance_validation",
            },
            "limits": {
                "max_file_size_mb": 100,
                "analysis_depth": "deep",
            },
            "description": "Deep simulation with custom validation",
        },
    },
    "scan_dependencies": {
        "community": {
            "enabled": True,
            "capabilities": {
                "basic_dependency_scan",
                "osv_vulnerability_detection",
                "severity_scoring",
                "basic_remediation_suggestions",
            },
            "limits": {
                "max_dependencies": 50,
                "osv_lookup": True,
            },
            "description": "Basic dependency vulnerability scan with CVE detection",
        },
        "pro": {
            "enabled": True,
            "capabilities": {
                "basic_dependency_scan",
                "osv_vulnerability_detection",
                "severity_scoring",
                "basic_remediation_suggestions",
                # [20251231_FEATURE] v3.3.1 - Pro tier capabilities per roadmap v1.0
                "reachability_analysis",
                "license_compliance",
                "typosquatting_detection",
                "supply_chain_risk_scoring",
                "false_positive_reduction",
                "update_recommendations",
            },
            "limits": {
                "max_dependencies": None,
                "osv_lookup": True,
            },
            "description": "Full scan with reachability analysis and license compliance",
        },
        "enterprise": {
            "enabled": True,
            "capabilities": {
                "basic_dependency_scan",
                "osv_vulnerability_detection",
                "severity_scoring",
                "basic_remediation_suggestions",
                "reachability_analysis",
                "license_compliance",
                "typosquatting_detection",
                "supply_chain_risk_scoring",
                "false_positive_reduction",
                "update_recommendations",
                # [20251231_FEATURE] v3.3.1 - Enterprise tier capabilities per roadmap v1.0
                "custom_vulnerability_database",
                "private_dependency_scanning",
                "automated_remediation",
                "policy_based_blocking",
                "compliance_reporting",
            },
            "limits": {
                "max_dependencies": None,
                "osv_lookup": True,
            },
            "description": "Enterprise scan with compliance reporting and custom policies",
        },
    },
    "get_cross_file_dependencies": {
        "community": {
            "enabled": True,
            "capabilities": {
                # [20251226_FEATURE] Community focuses on direct imports only
                "direct_import_mapping",
                "circular_import_detection",
                "import_graph_generation",
            },
            "limits": {
                "max_depth": 1,  # Direct deps only
                "max_files": 50,
            },
            "description": "Direct dependencies only",
        },
        "pro": {
            "enabled": True,
            "capabilities": {
                "direct_import_mapping",
                "circular_import_detection",
                "import_graph_generation",
                "transitive_dependency_mapping",
                "dependency_chain_visualization",
                "deep_coupling_analysis",
            },
            "limits": {
                "max_depth": 5,
                "max_files": 500,
            },
            "description": "Transitive dependencies with graph",
        },
        "enterprise": {
            "enabled": True,
            "capabilities": {
                "direct_import_mapping",
                "circular_import_detection",
                "import_graph_generation",
                "transitive_dependency_mapping",
                "dependency_chain_visualization",
                "deep_coupling_analysis",
                # [20251226_FEATURE] Enterprise architectural controls
                "architectural_firewall",
                "boundary_violation_alerts",
                "layer_constraint_enforcement",
                "dependency_rule_engine",
            },
            "limits": {
                "max_depth": None,
                "max_files": None,
            },
            "description": "Unlimited depth with circular detection",
        },
    },
    "cross_file_security_scan": {
        "community": {
            "enabled": True,
            "capabilities": {
                "basic_cross_file_scan",
                "single_module_taint_tracking",
                "source_to_sink_tracing",
                "basic_taint_propagation",
            },
            "limits": {
                "max_modules": 10,
                "max_depth": 3,
            },
            "description": "Basic cross-file scan (10 files max)",
        },
        "pro": {
            "enabled": True,
            "capabilities": {
                "basic_cross_file_scan",
                "single_module_taint_tracking",
                "source_to_sink_tracing",
                "basic_taint_propagation",
                "advanced_taint_tracking",
                "framework_aware_taint",
                "spring_bean_tracking",
                "react_context_tracking",
                "dependency_injection_resolution",
            },
            "limits": {
                "max_modules": 100,
                "max_depth": 10,
            },
            "description": "Advanced cross-file taint tracking",
        },
        "enterprise": {
            "enabled": True,
            "capabilities": {
                "basic_cross_file_scan",
                "single_module_taint_tracking",
                "source_to_sink_tracing",
                "basic_taint_propagation",
                "advanced_taint_tracking",
                "framework_aware_taint",
                "spring_bean_tracking",
                "react_context_tracking",
                "dependency_injection_resolution",
                "project_wide_scan",
                "custom_taint_rules",
                "global_taint_flow",
                "frontend_to_backend_tracing",
                "api_to_database_tracing",
                "microservice_boundary_crossing",
            },
            "limits": {
                "max_modules": None,
                "max_depth": None,
            },
            "description": "Project-wide scan with custom rules",
        },
    },
    "verify_policy_integrity": {
        "community": {
            "enabled": True,
            "capabilities": {"basic_verification"},
            "limits": {
                "signature_validation": False,
                "tamper_detection": False,
            },
            "description": "Basic policy file verification",
        },
        "pro": {
            "enabled": True,
            "capabilities": {"basic_verification", "signature_validation"},
            "limits": {
                "signature_validation": True,
                "tamper_detection": True,
            },
            "description": "Cryptographic signature validation",
        },
        "enterprise": {
            "enabled": True,
            "capabilities": {
                "basic_verification",
                "signature_validation",
                "full_integrity_check",
                "audit_logging",
            },
            "limits": {
                "signature_validation": True,
                "tamper_detection": True,
            },
            "description": "Full integrity with audit logging",
        },
    },
    # [20251226_FEATURE] Code policy check tool for style, patterns, and compliance
    "code_policy_check": {
        "community": {
            "enabled": True,
            "capabilities": {
                "style_guide_checking",
                "pep8_validation",
                "eslint_rules",
                "basic_patterns",
            },
            "limits": {
                "max_files": 100,
                "max_rules": 50,
            },
            "description": "Basic style guide and pattern checking",
        },
        "pro": {
            "enabled": True,
            "capabilities": {
                "style_guide_checking",
                "pep8_validation",
                "eslint_rules",
                "basic_patterns",
                "best_practice_analysis",
                "async_error_patterns",
                "security_patterns",
                "custom_rules",
            },
            "limits": {
                # [20260111_BUGFIX] Fixed Pro tier max_files to match limits.toml (was None/unlimited)
                "max_files": 1000,
                "max_rules": 200,
            },
            "description": "Advanced analysis with best practices and security patterns",
        },
        "enterprise": {
            "enabled": True,
            "capabilities": {
                "style_guide_checking",
                "pep8_validation",
                "eslint_rules",
                "basic_patterns",
                "best_practice_analysis",
                "async_error_patterns",
                "security_patterns",
                "custom_rules",
                "compliance_auditing",
                "hipaa_checks",
                "soc2_checks",
                "gdpr_checks",
                "pci_dss_checks",
                "pdf_certification",
                "audit_trail",
            },
            "limits": {
                "max_files": None,
                "max_rules": None,
            },
            "description": "Enterprise compliance auditing with certifications",
        },
    },
    # [20251226_FEATURE] Updated capabilities to align with tier tests
    "type_evaporation_scan": {
        # [20251231_FIX] v1.1 - Restored Community tier per verification document
        "community": {
            "enabled": True,
            "capabilities": {
                "explicit_any_detection",
                "typescript_any_scanning",
                "basic_type_check",
            },
            "limits": {
                "max_files": 50,
                "frontend_only": True,
            },
            "description": "Basic TypeScript type checking and explicit any detection",
        },
        "pro": {
            "enabled": True,
            # [20251231_FEATURE] v1.1 roadmap alignment - added capability names
            "capabilities": {
                "explicit_any_detection",
                "typescript_any_scanning",
                "basic_type_check",
                "frontend_backend_correlation",
                "implicit_any_tracing",
                "network_boundary_analysis",
                "library_boundary_analysis",
                "json_parse_tracking",
            },
            "limits": {
                "max_files": 500,
                "frontend_only": False,
            },
            "description": "Frontend-backend type correlation with boundary analysis",
        },
        "enterprise": {
            "enabled": True,
            # [20251231_FEATURE] v1.0 - All Enterprise capabilities implemented
            "capabilities": {
                "explicit_any_detection",
                "typescript_any_scanning",
                "basic_type_check",
                "frontend_backend_correlation",
                "implicit_any_tracing",
                "network_boundary_analysis",
                "library_boundary_analysis",
                "json_parse_tracking",
                "zod_schema_generation",
                "pydantic_model_generation",
                "api_contract_validation",
                "schema_coverage_metrics",
                "automated_remediation",
                "custom_type_rules",
                "compliance_validation",
            },
            "limits": {
                "max_files": None,
                "frontend_only": False,
            },
            "description": "Full type evaporation with schema generation and remediation",
        },
    },
    "unified_sink_detect": {
        "community": {
            "enabled": True,
            # [20251231_FEATURE] v1.0 roadmap alignment - added missing capabilities
            "capabilities": {
                "python_sink_detection",
                "javascript_sink_detection",
                "typescript_sink_detection",
                "java_sink_detection",
                "basic_confidence_scoring",
                "cwe_mapping",
                "sql_sink_detection",
                "shell_command_sink_detection",
                "file_operation_sinks",
                "xss_sink_detection",
            },
            "limits": {
                "languages": ["python", "javascript", "typescript", "java"],
                "max_sinks": 50,
            },
            "description": "Basic polyglot sink detection with CWE mapping",
        },
        "pro": {
            "enabled": True,
            # [20251231_FEATURE] v1.0 roadmap alignment - added Pro capabilities
            "capabilities": {
                "python_sink_detection",
                "javascript_sink_detection",
                "typescript_sink_detection",
                "java_sink_detection",
                "basic_confidence_scoring",
                "cwe_mapping",
                "sql_sink_detection",
                "shell_command_sink_detection",
                "file_operation_sinks",
                "xss_sink_detection",
                # Pro-specific
                "advanced_confidence_scoring",
                "context_aware_detection",
                "framework_specific_sinks",
                "custom_sink_definitions",
                "sink_coverage_analysis",
                # Existing Pro capabilities
                "logic_sink_detection",
                "s3_public_write_detection",
                "email_send_detection",
                "payment_api_detection",
                "extended_language_support",
            },
            "limits": {
                "languages": [
                    "python",
                    "javascript",
                    "typescript",
                    "java",
                    "go",
                    "rust",
                ],
                "max_sinks": None,
            },
            "description": "Advanced sink detection with framework and context awareness",
        },
        "enterprise": {
            "enabled": True,
            # [20251231_FEATURE] v1.0 roadmap alignment - added Enterprise capabilities
            "capabilities": {
                "python_sink_detection",
                "javascript_sink_detection",
                "typescript_sink_detection",
                "java_sink_detection",
                "basic_confidence_scoring",
                "cwe_mapping",
                "sql_sink_detection",
                "shell_command_sink_detection",
                "file_operation_sinks",
                "xss_sink_detection",
                "advanced_confidence_scoring",
                "context_aware_detection",
                "framework_specific_sinks",
                "custom_sink_definitions",
                "sink_coverage_analysis",
                "logic_sink_detection",
                "s3_public_write_detection",
                "email_send_detection",
                "payment_api_detection",
                "extended_language_support",
                # Enterprise-specific
                "organization_sink_rules",
                "sink_risk_scoring",
                "compliance_mapping",
                "historical_sink_tracking",
                "automated_sink_remediation",
                "sink_categorization",
                "risk_level_tagging",
                "clearance_requirement_tagging",
                "custom_sink_patterns",
                "sink_inventory_reporting",
            },
            "limits": {
                "languages": None,
                "max_sinks": None,
                "custom_sinks_limit": None,
            },
            "description": "Enterprise sink detection with compliance and remediation",
        },
    },
    # [20250101_FEATURE] v1.0 roadmap alignment - updated update_symbol capabilities
    "update_symbol": {
        "community": {
            "enabled": True,
            "capabilities": {
                "basic_replacement",  # Functions, classes, methods
                "syntax_validation",  # Pre-save syntax check
                "automatic_backup",  # .bak file creation
                "python_support",  # Python patching
                "javascript_support",  # JS patching
                "typescript_support",  # TS patching
                "java_support",  # Java patching
            },
            "limits": {
                "backup_enabled": True,
                "validation_level": "syntax",
                # [20260121_REFACTOR] Switch to stateless per-call throughput cap
                # Roadmap v1.0: "10 updates per call" for Community
                "max_updates_per_call": 10,
            },
            "description": "Replace a function/class/method with new code (10 updates/call)",
        },
        "pro": {
            "enabled": True,
            "capabilities": {
                "basic_replacement",
                "syntax_validation",
                "automatic_backup",
                "python_support",
                "javascript_support",
                "typescript_support",
                "java_support",
                # Pro-specific capabilities (v1.0 roadmap)
                "semantic_validation",  # Check symbol name matches target
                "cross_file_updates",  # Update references in other files
                "atomic_multi_file",  # All-or-nothing multi-file updates
                "rollback_on_failure",  # Automatic rollback if update fails
                "pre_update_hook",  # Hook before update
                "post_update_hook",  # Hook after update
                "formatting_preservation",  # Keep original formatting
                "import_auto_adjustment",  # Add/remove imports as needed
            },
            "limits": {
                "backup_enabled": True,
                "validation_level": "semantic",
                # [20260121_REFACTOR] Per-call model; -1 means unlimited
                "max_updates_per_call": -1,
            },
            "description": "Unlimited updates with atomic multi-file, rollback, and hooks",
        },
        "enterprise": {
            "enabled": True,
            "capabilities": {
                "basic_replacement",
                "syntax_validation",
                "automatic_backup",
                "python_support",
                "javascript_support",
                "typescript_support",
                "java_support",
                "semantic_validation",
                "cross_file_updates",
                "atomic_multi_file",
                "rollback_on_failure",
                "pre_update_hook",
                "post_update_hook",
                "formatting_preservation",
                "import_auto_adjustment",
                # Enterprise-specific capabilities (v1.0 roadmap)
                "impact_analysis",  # Change impact before update
                "git_integration",  # Git branch + commit
                "branch_creation",  # Auto-create feature branch
                "test_execution",  # Run tests after update
                "code_review_approval",  # Require approval before mutation
                "compliance_check",  # Check compliance rules
                "audit_trail",  # Log all modifications
                "custom_validation_rules",  # User-defined validation
                "policy_gated_mutations",  # Policy engine integration
            },
            "limits": {
                "backup_enabled": True,
                "validation_level": "full",
                # [20260121_REFACTOR] Per-call model; -1 means unlimited
                "max_updates_per_call": -1,
            },
            "description": "Atomic refactoring: approval, compliance, audit trail, policies",
        },
    },
    "get_file_context": {
        "community": {
            "enabled": True,
            "capabilities": {
                "raw_source_retrieval",
                "ast_based_outlining",
                "function_folding",
                "class_folding",
                "line_range_extraction",
            },
            "limits": {
                "max_context_lines": 500,
            },
            "description": "Basic file overview with AST outlining",
        },
        "pro": {
            "enabled": True,
            "capabilities": {
                "raw_source_retrieval",
                "ast_based_outlining",
                "function_folding",
                "class_folding",
                "line_range_extraction",
                "semantic_summarization",
                "intent_extraction",
                "related_imports_inclusion",
                "smart_context_expansion",
                # [20251231_FEATURE] v3.3.1 - Pro code quality metrics
                "code_smell_detection",
                "documentation_coverage",
                "maintainability_index",
            },
            "limits": {
                "max_context_lines": 2000,
            },
            "description": "Semantic summarization with code quality metrics",
        },
        "enterprise": {
            "enabled": True,
            "capabilities": {
                "raw_source_retrieval",
                "ast_based_outlining",
                "function_folding",
                "class_folding",
                "line_range_extraction",
                "semantic_summarization",
                "intent_extraction",
                "related_imports_inclusion",
                "smart_context_expansion",
                "code_smell_detection",
                "documentation_coverage",
                "maintainability_index",
                "pii_redaction",
                "secret_masking",
                "api_key_detection",
                "rbac_aware_retrieval",
                "file_access_control",
                # [20251231_FEATURE] v3.3.1 - Enterprise organizational metadata
                "custom_metadata_extraction",
                "compliance_flags",
                "technical_debt_scoring",
                "owner_team_mapping",
                "historical_metrics",
            },
            "limits": {
                "max_context_lines": None,
            },
            "description": "Enterprise context with compliance, ownership, and metrics",
        },
    },
    "get_project_map": {
        "community": {
            "enabled": True,
            "capabilities": {
                "text_tree_generation",
                "basic_mermaid_diagram",
                "folder_structure_visualization",
                "file_count_statistics",
            },
            "limits": {
                "max_files": 100,
                "max_modules": 50,
                "detail_level": "basic",
            },
            "description": "Basic project structure map",
        },
        "pro": {
            "enabled": True,
            "capabilities": {
                "text_tree_generation",
                "basic_mermaid_diagram",
                "folder_structure_visualization",
                "file_count_statistics",
                "module_relationship_visualization",
                "import_dependency_diagram",
                "architectural_layer_detection",
                "coupling_analysis",
                # [20251231_FEATURE] v3.3.1 - Code ownership per roadmap v1.0
                "code_ownership_mapping",
                "git_blame_integration",
            },
            "limits": {
                "max_files": 1000,
                "max_modules": 200,
                "detail_level": "detailed",
            },
            "description": "Detailed map with dependencies and ownership",
        },
        "enterprise": {
            "enabled": True,
            "capabilities": {
                "text_tree_generation",
                "basic_mermaid_diagram",
                "folder_structure_visualization",
                "file_count_statistics",
                "module_relationship_visualization",
                "import_dependency_diagram",
                "architectural_layer_detection",
                "coupling_analysis",
                "interactive_city_map",
                "force_directed_graph",
                "bug_hotspot_heatmap",
                "code_churn_visualization",
                "git_blame_integration",
                # [20251231_FEATURE] v3.3.1 - Missing Enterprise features per roadmap v1.0
                "multi_repository_maps",
                "historical_architecture_trends",
                "custom_map_metrics",
                "compliance_overlay",
            },
            "limits": {
                "max_files": None,
                "max_modules": 1000,
                "detail_level": "comprehensive",
            },
            "description": "Comprehensive map with multi-repo, historical trends, and compliance",
        },
    },
    "validate_paths": {
        "community": {
            "enabled": True,
            # [20251231_BUGFIX] v1.0 roadmap: All tiers get core features
            # Roadmap v1.0 specifies: path_accessibility, docker_detection,
            # workspace_root_detection, actionable_messages, volume_suggestions, batch_validation
            "capabilities": {
                # v1.0 Core (all tiers)
                "path_accessibility_checking",
                "docker_environment_detection",
                "workspace_root_detection",
                "actionable_error_messages",
                "docker_volume_mount_suggestions",
                "batch_path_validation",
                # Legacy compatibility
                "file_existence_validation",
                "import_path_checking",
                "broken_reference_detection",
                "basic_validation",
            },
            "limits": {
                "max_paths": 100,
            },
            "description": "Path validation with Docker detection and volume suggestions",
        },
        "pro": {
            "enabled": True,
            # [20251231_BUGFIX] v1.0 roadmap: Pro adds alias resolution
            "capabilities": {
                # v1.0 Core (all tiers)
                "path_accessibility_checking",
                "docker_environment_detection",
                "workspace_root_detection",
                "actionable_error_messages",
                "docker_volume_mount_suggestions",
                "batch_path_validation",
                # Legacy compatibility
                "file_existence_validation",
                "import_path_checking",
                "broken_reference_detection",
                "basic_validation",
                # Pro advanced features (v1.1+ roadmap preview)
                "path_alias_resolution",
                "tsconfig_paths_support",
                "webpack_alias_support",
                "dynamic_import_resolution",
                "extended_language_support",
            },
            "limits": {
                "max_paths": None,
            },
            "description": "Docker-aware validation with alias resolution and dynamic imports",
        },
        "enterprise": {
            "enabled": True,
            # [20251231_BUGFIX] v1.0 roadmap: Enterprise adds security features
            "capabilities": {
                # v1.0 Core (all tiers)
                "path_accessibility_checking",
                "docker_environment_detection",
                "workspace_root_detection",
                "actionable_error_messages",
                "docker_volume_mount_suggestions",
                "batch_path_validation",
                # Legacy compatibility
                "file_existence_validation",
                "import_path_checking",
                "broken_reference_detection",
                "basic_validation",
                # Pro advanced features
                "path_alias_resolution",
                "tsconfig_paths_support",
                "webpack_alias_support",
                "dynamic_import_resolution",
                "extended_language_support",
                # Enterprise security features (v1.1+ roadmap preview)
                "permission_checks",
                "security_validation",
                "path_traversal_simulation",
                "symbolic_path_breaking",
                "security_boundary_testing",
            },
            "limits": {
                "max_paths": None,
            },
            "description": "Full validation with security simulation and boundary testing",
        },
    },
}


def get_tool_capabilities(tool_id: str, tier: str) -> dict[str, Any]:
    """
    Get capabilities and limits for a tool at a specific tier.

    Args:
        tool_id: MCP tool identifier
        tier: Tier level ("community", "pro", "enterprise")

    Returns:
        Dictionary with enabled, capabilities, limits, description

    Example:
        caps = get_tool_capabilities("security_scan", "community")
        if "full_vulnerability_list" in caps["capabilities"]:
            # Show all findings
        else:
            # Limit to caps["limits"]["max_findings"]
    """
    tool_caps = TOOL_CAPABILITIES.get(tool_id, {})
    normalized_tier = tier.lower()
    tier_caps = tool_caps.get(normalized_tier, {})

    if not tier_caps:
        logger.warning(f"Unknown tool or tier: {tool_id}/{tier}")
        # Return minimal fallback
        return {
            "enabled": True,
            "capabilities": set(),
            "limits": {},
            "description": "Unknown tool/tier",
        }

    # [20251231_CONFIG] Merge TOML-configured LIMITS into hardcoded defaults.
    # Capabilities remain code-defined (license-gated) and are NOT granted via config.
    try:
        from .config_loader import get_cached_limits, get_tool_limits, merge_limits

        overrides = get_tool_limits(tool_id, normalized_tier, config=get_cached_limits())
        if overrides:
            merged_caps = dict(tier_caps)
            merged_caps["limits"] = merge_limits(tier_caps.get("limits", {}), overrides)
            return merged_caps
    except Exception as e:
        logger.debug(f"Failed to apply TOML limits overrides for {tool_id}/{tier}: {e}")

    return tier_caps


def has_capability(tool_id: str, capability: str, tier: str) -> bool:
    """
    Check if a tool has a specific capability at a tier.

    Args:
        tool_id: MCP tool identifier
        capability: Capability name
        tier: Tier level

    Returns:
        True if capability is available
    """
    caps = get_tool_capabilities(tool_id, tier)
    return capability in caps.get("capabilities", set())


def get_upgrade_hint(tool_id: str, missing_capability: str, current_tier: str) -> str | None:
    """
    Generate upgrade hint for a missing capability.

    Args:
        tool_id: MCP tool identifier
        missing_capability: Capability user tried to use
        current_tier: Current tier level

    Returns:
        Upgrade hint message or None if capability not found in higher tiers
    """
    # Check which tier provides this capability
    for tier in ["pro", "enterprise"]:
        if tier == current_tier:
            continue

        if has_capability(tool_id, missing_capability, tier):
            return (
                f"Feature '{missing_capability}' requires {tier.upper()} tier. "
                f"Current tier: {current_tier.upper()}. "
                f"Upgrade at http://codescalpel.dev/pricing"
            )

    return None


def get_all_tools_for_tier(tier: str) -> list[str]:
    """
    Get all tool IDs available at a tier.

    NOTE: This returns ALL tools since all tools are available at all tiers.
    Use get_tool_capabilities() to check feature restrictions.

    Args:
        tier: Tier level

    Returns:
        List of all tool IDs
    """
    return list(TOOL_CAPABILITIES.keys())


def get_missing_capabilities(tool_id: str, current_tier: str, target_tier: str) -> set[str]:
    """
    Get capabilities available in target tier but not in current tier.

    Args:
        tool_id: MCP tool identifier
        current_tier: Current tier level
        target_tier: Target tier level

    Returns:
        Set of capability names
    """
    current_caps = get_tool_capabilities(tool_id, current_tier)
    target_caps = get_tool_capabilities(tool_id, target_tier)

    current_set = current_caps.get("capabilities", set())
    target_set = target_caps.get("capabilities", set())

    return target_set - current_set
