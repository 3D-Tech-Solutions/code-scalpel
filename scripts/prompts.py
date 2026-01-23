import os

# --------------------------------------------------------------------------------
# THE MASTER TEMPLATE
# --------------------------------------------------------------------------------
# UPDATED: Phase 1 now explicitly instructs the agent to prepare/verify ALL tiers.
# --------------------------------------------------------------------------------

TEMPLATE = """
# Role & Persona
You are the **Lead Software Architect and Quality Assurance Director** for **3D Tech Solutions**. Your standard is "World Class"—functional code is not enough; it must be secure, scalable, and profitable.

# Context
We are finalizing the release of the **{tool_name}** tool, a core module of the **Code Scalpel** MCP server.
* **Tool Purpose:** {tool_purpose}
* **Goal:** Ensure this tool is production-ready, commercially viable, and strictly tested across **ALL Tiers** (Community, Pro, Enterprise).

# Available Tools
You have access to the **Code Scalpel MCP Server**.
* **Primary Tools:** Use `get_file_context` and `list_directory` to read code, docs, and map the structure.
* **Secondary Tools:** Use specific execution or testing tools **only if necessary** to validate a fix or run a required test suite. Do not force tool usage if static analysis is sufficient.

# Your Objectives
Execute the following workflow step-by-step. Do not skip steps.

## Phase 1: Static Analysis & Commercial Review
Analyze the **{tool_name}** directory and associated `roadmap.md`. Evaluate:
* **Code Quality:** Is the code modular, scalable, and compliant with 3D Tech Solutions' standards?
* **Commercial Logic & Tier Verification:** Verify `licensing`, `rate limits`, and `feature gating` for **ALL Tiers**:
    * **Community Tier:** Are limits (e.g., {tier_limits}) strictly enforced?
    * **Pro Tier:** Does the license check correctly unlock Pro features and expand limits?
    * **Enterprise Tier:** Does the license check unlock Enterprise features (e.g., SSO, Compliance, Custom Rules) and remove limits?
* **Roadmap Alignment:** Identify if the current version meets v1.0 goals and suggest specific items to add to the roadmap for v1.1+.

## Phase 2: Dynamic Testing & Verification
* **Retrieve Context:** Use `get_file_context` to read the `MCP Test Checklist` and `tests assessments` documents.
* **Gap Analysis:** Compare the existing tests against the checklist.
    * **CRITICAL TESTING FOCUS:** {testing_focus}
    * *Tier-Gating Tests:* Do we have tests that prove a Community user *cannot* access Pro features?
* **Execution:** If executable test tools are available and needed to verify a gap, run them. If tests are missing, **create the test code**.
* **Evidence:** You must generate sufficient evidence (logs, code analysis, or test outputs) to back up your claim that the tool is "Ready."

## Phase 3: Remediation & Finalization
* Implement any necessary code fixes, documentation updates, or new tests identified in Phase 2.
* Ensure the tool passes all internal standards found in the test assessment documents.

## Phase 4: Delivery
Once you are satisfied that **{tool_name}** is robust:
1.  Generate a professional **Commit Message** summarizing updates, fixes, and test additions.
2.  Simulate/Perform the push for tool readiness.

# Immediate Action Required
Start by listing the files in the directory for **{tool_name}** to begin your assessment.
"""

# --------------------------------------------------------------------------------
# TOOL DATA DICTIONARY
# --------------------------------------------------------------------------------
# Contains specific metadata extracted from the v1.0 Roadmap files.
# --------------------------------------------------------------------------------

tools = {
    # --- Batch 1 Tools ---
    "scan_dependencies": {
        "purpose": "Scans project dependencies (Python, JS, Java) for known vulnerabilities using the OSV database and calculates supply chain risk.",
        "tier_limits": "Max 50 dependencies for Community Tier",
        "testing_focus": "Verify that 'reachability_analysis' (Pro feature) is accessible to both Pro and Enterprise tiers, but strictly blocked for Community users. Ensure the 'max_dependencies' limit applies only to Community.",
    },
    "verify_policy_integrity": {
        "purpose": "Cryptographically verifies that policy files have not been tampered with using digital signatures and hash validation.",
        "tier_limits": "Max 50 policy files for Community Tier",
        "testing_focus": "Verify 'Tamper Detection' works for all tiers. Check that 'certificate_chain_valid' and 'crl_status' are available to Pro and Enterprise users, but gated for Community.",
    },
    "security_scan": {
        "purpose": "Detects security vulnerabilities using taint-based analysis (Python) and sink detection (JS/TS/Java).",
        "tier_limits": "Max 50 findings / 500KB file size for Community Tier",
        "testing_focus": "Verify Polyglot Gaps: Confirm Python has full taint analysis. Ensure 'sanitizer_recognition' (Pro feature) is active for Pro and Enterprise tiers, but disabled for Community.",
    },
    "rename_symbol": {
        "purpose": "Safely renames functions, classes, or methods in a file while ensuring consistent changes throughout the codebase.",
        "tier_limits": "Single-file rename only for Community Tier (No cross-file)",
        "testing_focus": "CRITICAL: Verify v1.0 is PYTHON-ONLY. Ensure 'Cross-file rename' logic is accessible to Pro/Enterprise users (limited only by file count in Pro), but strictly blocked for Community users.",
    },
    "symbolic_execute": {
        "purpose": "Explores execution paths using Z3 constraint solving to find edge cases, bugs, and unreachable code.",
        "tier_limits": "Max 50 paths / 10 loop depth for Community Tier",
        "testing_focus": "Verify strict enforcement of 'max_depth=10' for Community. Confirm 'smart_path_prioritization' is enabled for Pro and Enterprise users, but disabled for Community.",
    },
    "unified_sink_detect": {
        "purpose": "Detects dangerous sinks (eval, execute, innerHTML) across Python, JS, TS, and Java with confidence scoring.",
        "tier_limits": "Max 50 sinks detected for Community Tier",
        "testing_focus": "Verify 'confidence_scoring' works for all tiers. Ensure 'framework_specific_sinks' (Pro feature) are detected for Pro/Enterprise users, but ignored/blocked for Community.",
    },
    "type_evaporation_scan": {
        "purpose": "Detects 'Type Evaporation' where TypeScript types are lost at runtime boundaries (JSON.stringify, API calls) leading to type confusion.",
        "tier_limits": "Frontend-only analysis / Max 50 files for Community Tier",
        "testing_focus": "Verify 'cross_file_issues' (Pro feature) works for Pro and Enterprise tiers. Ensure Community Tier is strictly limited to frontend-only analysis.",
    },
    "simulate_refactor": {
        "purpose": "Simulates code changes to detect security issues, structural breaks, and semantic changes before applying them.",
        "tier_limits": "Basic syntax/security checks only for Community Tier",
        "testing_focus": "Verify 'security_issues' detection works for all tiers. Check that 'behavior_equivalent' and 'performance_impact' (Pro features) are computed for Pro/Enterprise users only.",
    },
    "validate_paths": {
        "purpose": "Validates file paths and permissions, specifically checking for Docker volume mount issues and container accessibility.",
        "tier_limits": "Max 100 paths for Community Tier",
        "testing_focus": "Verify 'docker_detected' logic works for all tiers. Ensure 'permission_details' (Pro feature) are returned for Pro/Enterprise users, but omitted for Community.",
    },
    "update_symbol": {
        "purpose": "Surgically replaces function/class bodies while preserving surrounding code, formatting, and creating backups.",
        "tier_limits": "Max 10 updates per session for Community Tier",
        "testing_focus": "Verify 'backup_path' is created for all tiers. Test 'atomic multi-file updates' (Pro feature) to ensure they work for Pro/Enterprise but fail/warn for Community.",
    },
    # --- Batch 2 Tools ---
    "crawl_project": {
        "purpose": "Recursively indexes project files while respecting .gitignore rules and detecting binary files.",
        "tier_limits": "Max 100 files indexed for Community Tier",
        "testing_focus": "Verify '.gitignore' compliance for all tiers. Check that Pro/Enterprise users can index beyond the 100-file Community limit.",
    },
    "cross_file_security_scan": {
        "purpose": "Detects complex security vulnerabilities and taint flows that propagate across file boundaries (imports/exports).",
        "tier_limits": "Max 50 files scanned for Community Tier",
        "testing_focus": "Verify taint propagation works. Ensure Pro/Enterprise tiers can scan unlimited files (or higher limits), while Community is capped at 50.",
    },
    "extract_code": {
        "purpose": "Parses and extracts specific code blocks (classes, functions) or line ranges while preserving context and comments.",
        "tier_limits": "Max 50 extractions per session for Community Tier",
        "testing_focus": "Verify AST parsing accuracy. Ensure Pro/Enterprise users are not hit by the 'Max 50' session limit.",
    },
    "generate_unit_tests": {
        "purpose": "Autonomously generates comprehensive unit test suites (pytest/jest) with mocking for specified code.",
        "tier_limits": "Max 10 test suites per session for Community Tier",
        "testing_focus": "Verify 'runnability' of tests. Ensure Pro/Enterprise users can generate unlimited suites, while Community is strictly capped at 10.",
    },
    "get_call_graph": {
        "purpose": "Generates a static call graph to visualize function invocation flows and dependencies.",
        "tier_limits": "Max 50 graph nodes for Community Tier",
        "testing_focus": "Verify graph accuracy. Ensure Pro/Enterprise users receive full graphs, while Community graphs are truncated at 50 nodes.",
    },
    "get_cross_file_dependencies": {
        "purpose": "Maps import/export relationships between files to build a project-wide dependency graph.",
        "tier_limits": "Max 50 files analyzed for Community Tier",
        "testing_focus": "Verify relative import resolution. Ensure Pro/Enterprise users can map the entire project, while Community is limited to 50 files.",
    },
    "get_file_context": {
        "purpose": "Retrieves file content and metadata (token count, AST summary) optimized for LLM context windows.",
        "tier_limits": "Max 100KB file size for Community Tier",
        "testing_focus": "Verify the 100KB limit triggers an error/truncation for Community. Ensure Pro/Enterprise users can retrieve larger files (up to their respective limits).",
    },
    "get_graph_neighborhood": {
        "purpose": "Retrieves the immediate dependency neighborhood (upstream/downstream) for a specific symbol or file.",
        "tier_limits": "Max 1 hop distance for Community Tier",
        "testing_focus": "Verify the '1 hop' limit enforcement for Community. Ensure Pro/Enterprise users can query with deeper hop distances.",
    },
    "get_project_map": {
        "purpose": "Generates a high-level topographical map of the project structure, identifying key components and entry points.",
        "tier_limits": "Max 50 files summarized for Community Tier",
        "testing_focus": "Verify 'key_component_identification'. Ensure Pro/Enterprise maps cover the full project, whereas Community maps are partial (50 files).",
    },
    "get_symbol_references": {
        "purpose": "Locates all semantic references to a specific symbol across the codebase, distinguishing between definitions and usages.",
        "tier_limits": "Max 50 references for Community Tier",
        "testing_focus": "Verify scope awareness. Ensure Pro/Enterprise users get all references, while Community results are truncated at 50.",
    },
    # --- Batch 3 Tools ---
    "analyze_code": {
        "purpose": "Performs static code analysis to calculate complexity metrics (Cyclomatic, Halstead) and maintainability indices.",
        "tier_limits": "Max file size 1MB for Community Tier (10MB Pro, 100MB Enterprise)",
        "testing_focus": "Verify the 1MB limit blocks analysis for Community. Ensure Pro/Enterprise users can analyze larger files.",
    },
    "code_policy_check": {
        "purpose": "Enforces coding standards and policy compliance (formatting, docstrings, forbidden patterns) based on configuration.",
        "tier_limits": "Max 10 rules per scan for Community Tier",
        "testing_focus": "Verify the 'Max 10 rules' limit for Community. Test 'custom_regex_rules' (Pro feature) to ensure they are available to Pro/Enterprise users, but gated for Community.",
    },
}

# --------------------------------------------------------------------------------
# GENERATION LOGIC
# --------------------------------------------------------------------------------

script_dir = os.path.dirname(os.path.abspath(__file__))
output_filename = os.path.join(script_dir, "Code_Scalpel_Prompts.md")

with open(output_filename, "w", encoding="utf-8") as f:
    f.write("# Code Scalpel Agent Prompts\n")
    f.write("> **Auto-Generated from Roadmap v1.0 Data**\n\n")

    for name, data in tools.items():
        f.write(f"--- \n\n### Prompt for: {name}\n")
        f.write(
            TEMPLATE.format(
                tool_name=name,
                tool_purpose=data["purpose"],
                tier_limits=data["tier_limits"],
                testing_focus=data["testing_focus"],
            )
        )
        f.write("\n\n")

print(f"Successfully generated prompts for {len(tools)} tools at:\n{output_filename}")
