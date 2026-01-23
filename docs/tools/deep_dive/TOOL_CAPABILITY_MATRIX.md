# Code Scalpel Tool Capability Matrix

**Last Updated:** 2026-01-12  
**Code Scalpel Version:** v3.3+

This document provides a consolidated index of all MCP tools available in the Code Scalpel suite. It maps each tool to its operational status, tier availability, and primary capabilities.

## Tool Index

| Tool Name | Status | Tier Availability | Key Capabilities | Deep Dive Documentation |
| :--- | :--- | :--- | :--- | :--- |
| **analyze_code** | ✅ Stable | **All** (Comm/Pro/Ent) | • AST Parsing / Tree-sitter<br>• Zero Hallucination Structure<br>• Complexity Metrics | [Read Docs](ANALYZE_CODE_DEEP_DIVE.md) |
| **code_policy_check** | ✅ Stable | **All** (Comm/Pro/Ent) | • Style + Security + Compliance<br>• HIPAA/SOC2 Enforcement (Ent)<br>• Automated Fixes | [Read Docs](CODE_POLICY_CHECK_DEEP_DIVE.md) |
| **crawl_project** | ✅ Stable | **All** (Comm/Pro/Ent) | • Project-wide Inventory<br>• Hotspot Identification<br>• Framework Detection | [Read Docs](CRAWL_PROJECT_DEEP_DIVE.md) |
| **cross_file_security_scan** | ✅ Stable | **All** (Comm/Pro/Ent) | • Taint Tracking across files<br>• Data Flow Visuals (Mermaid)<br>• Risk Assessment | [Read Docs](CROSS_FILE_SECURITY_SCAN_DEEP_DIVE.md) |
| **extract_code** | ✅ Stable | **All** (Comm/Pro/Ent) | • Token-Efficient Extraction<br>• Precision Symbol Targeting<br>• React/JSX Metadata | [Read Docs](EXTRACT_CODE_DEEP_DIVE.md) |
| **generate_unit_tests** | ✅ Validated | **All** (Comm/Pro/Ent) | • Symbolic Execution (Z3)<br>• 100% Path Coverage<br>• Data-driven Tests (Pro) | [Read Docs](GENERATE_UNIT_TESTS_DEEP_DIVE.md) |
| **get_call_graph** | ✅ Stable | **All** (Comm/Pro/Ent) | • Static Call Graphs<br>• Circular Dependency Check<br>• Visual Architecture | [Read Docs](GET_CALL_GRAPH_DEEP_DIVE.md) |
| **get_cross_file_dependencies** | ✅ Stable | **All** (Comm/Pro/Ent) | • Import Chain Resolution<br>• Transitive Extraction<br>• Confidence Scoring | [Read Docs](GET_CROSS_FILE_DEPENDENCIES_DEEP_DIVE.md) |
| **get_file_context** | ✅ Stable | **All** (Comm/Pro/Ent) | • "Peek" without Read<br>• Token Efficiency (95% savings)<br>• Security Summaries | [Read Docs](GET_FILE_CONTEXT_DEEP_DIVE.md) |
| **get_graph_neighborhood** | ✅ Stable | **All** (Comm/Pro/Ent) | • K-Hop Traversal<br>• "Exploding Graph" Prevention<br>• Local Architecture Viz | [Read Docs](GET_GRAPH_NEIGHBORHOOD_DEEP_DIVE.md) |
| **get_project_map** | ✅ Stable | **All** (Comm/Pro/Ent) | • Architectural Reconnaissance<br>• 3D City Maps (Ent)<br>• Layer Detection | [Read Docs](GET_PROJECT_MAP_DEEP_DIVE.md) |
| **get_symbol_references** | ✅ Best-in-Class | **All** (Comm/Pro/Ent) | • AST-Based Reference Finding<br>• Impact Analysis<br>• Safe Refactoring Prep | [Read Docs](GET_SYMBOL_REFERENCES_DEEP_DIVE.md) |
| **rename_symbol** | ✅ Stable | **All** (Comm/Pro/Ent) | • Surgical Rename<br>• Auto-Update References<br>• Comment Preservation | [Read Docs](RENAME_SYMBOL_DEEP_DIVE.md) |
| **scan_dependencies** | ✅ Stable | **All** (Comm/Pro/Ent) | • Supply Chain Security (OSV)<br>• Reachability Analysis (Pro)<br>• License Compliance | [Read Docs](SCAN_DEPENDENCIES_DEEP_DIVE.md) |
| **security_scan** | ✅ Stable | **All** (Comm/Pro/Ent) | • Single-file SAST<br>• Taint Analysis (Python)<br>• Polyglot Sink Detection | [Read Docs](SECURITY_SCAN_DEEP_DIVE.md) |
| **simulate_refactor** | ✅ Stable | **All** (Comm/Pro/Ent) | • Pre-flight Safety Check<br>• AST Diffing<br>• Security Regression Test | [Read Docs](SIMULATE_REFACTOR_DEEP_DIVE.md) |
| **symbolic_execute** | ✅ Stable | **All** (Comm/Pro/Ent) | • Mathematical Verification (Z3)<br>• Edge Case Discovery<br>• Path Constraint Solving | [Read Docs](SYMBOLIC_EXECUTE_DEEP_DIVE.md) |
| **type_evaporation_scan** | ✅ Stable | **All** (Comm/Pro/Ent) | • Full-Stack Type Safety<br>• Frontend/Backend Correlation<br>• Zod Schema Gen (Ent) | [Read Docs](TYPE_EVAPORATION_SCAN_DEEP_DIVE.md) |
| **unified_sink_detect** | ✅ Stable | **All** (Comm/Pro/Ent) | • Polyglot Sink Detection<br>• CWE Mapping<br>• Confidence Scoring | [Read Docs](UNIFIED_SINK_DETECT_DEEP_DIVE.md) |
| **update_symbol** | ✅ Stable | **All** (Comm/Pro/Ent) | • Surgical Replacement<br>• Syntax Validation<br>• Atomic Writes & Backups | [Read Docs](UPDATE_SYMBOL_DEEP_DIVE.md) |
| **validate_paths** | ✅ Stable | **All** (Comm/Pro/Ent) | • Pre-Flight Checks<br>• Docker Awareness<br>• Path Traversal Prevention | [Read Docs](VALIDATE_PATHS_DEEP_DIVE.md) |
| **verify_policy_integrity** | ✅ Stable | **Enterprise** | • Tamper Detection<br>• Checksum Verification<br>• Signature Validation | [Read Docs](VERIFY_POLICY_INTEGRITY_DEEP_DIVE.md) |

## Tier Feature Summary

| Tier | Focus | Key Differentiators |
| :--- | :--- | :--- |
| **Community** | Individual Developers | • Foundational AST parsing<br>• Accurate, hallucination-free basic ops<br>• Capped limits (e.g., 50 sinks, 100 paths) |
| **Pro** | Professional Teams | • Feature Unlocking (Context-Aware, Reachability Analysis)<br>• Increased Limits (Unlimited paths, higher deep-scan depths)<br>• Framework-specific intelligence |
| **Enterprise** | Organizations | • Governance & Policy Enforcement (HIPAA, SOC2)<br>• Risk Scoring & Prioritization<br>• Audit Trails & Team Workflows (CODEOWNERS)<br>• Multi-repo / System-wide Analysis |
