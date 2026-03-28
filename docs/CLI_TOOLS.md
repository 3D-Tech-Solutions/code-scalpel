# CLI Tools Reference

Complete reference for all Code Scalpel CLI tools. All MCP tools are now accessible directly from the command line.

## Table of Contents

- [Quick Start](#quick-start)
- [Analysis Tools](#analysis-tools)
- [Extraction Tools](#extraction-tools)
- [Security Tools](#security-tools)
- [Refactoring Tools](#refactoring-tools)
- [Testing Tools](#testing-tools)
- [Validation Tools](#validation-tools)
- [Policy Tools](#policy-tools)
- [Configuration Management](#configuration-management)
- [Common Options](#common-options)
- [Tier System](#tier-system)

## Quick Start

```bash
# Install Code Scalpel
pip install codescalpel

# View all available commands
codescalpel --help

# Get help for a specific command
codescalpel extract-code --help

# Most commands support JSON output
codescalpel analyze myfile.py --json
```

---

## Analysis Tools

### analyze

Analyze code using AST and static analysis.

**Usage:**
```bash
codescalpel analyze <file_path> [options]
codescalpel analyze --code "<code_string>" [options]
```

**Options:**
- `--json, -j` - Output as JSON
- `--language, -l` - Specify language (python, javascript, typescript, java, c, cpp)

**Examples:**
```bash
# Analyze a Python file
codescalpel analyze src/main.py

# Analyze JavaScript with JSON output
codescalpel analyze app.js --language javascript --json

# Analyze code string
codescalpel analyze --code "def foo(): return 42"
```

**Tier Limits:**
- Community: 1MB files, basic AST analysis
- Pro: 100MB files, advanced metrics and control/data-flow analysis
- Enterprise: 100MB files, Pro-scale limits plus compliance/custom-rule capabilities

---

### get-file-context

Get file overview with structure analysis without reading full content.

**Usage:**
```bash
codescalpel get-file-context <file_path> [options]
```

**Options:**
- `--json, -j` - Output as JSON

**Examples:**
```bash
# Get file context
codescalpel get-file-context src/models.py

# Get context as JSON
codescalpel get-file-context src/api.py --json
```

**Tier Limits:**
- Community: 500 lines of context, basic structure
- Pro: 2000 lines, code quality metrics
- Enterprise: Unlimited context, security redaction

---

### get-call-graph

Generate function call graph showing relationships.

**Usage:**
```bash
codescalpel get-call-graph <file_path> [options]
```

**Options:**
- `--output, -o` - Output file path
- `--format` - Output format (mermaid, json)
- `--json, -j` - Output full response as JSON

**Examples:**
```bash
# Generate call graph
codescalpel get-call-graph src/main.py

# Output as Mermaid diagram to file
codescalpel get-call-graph src/app.js --format mermaid -o graph.md

# Get JSON output
codescalpel get-call-graph src/api.py --json
```

**Tier Limits:**
- Community: Max depth 3, max nodes 50
- Pro: Max depth 10, max nodes 500
- Enterprise: Unlimited depth and nodes

---

### get-symbol-references

Find all references to a symbol across the project.

**Usage:**
```bash
codescalpel get-symbol-references <symbol_name> [options]
```

**Options:**
- `--project-root` - Project root directory
- `--scope-prefix` - Optional scope prefix to filter results
- `--no-tests` - Exclude test files from search
- `--json, -j` - Output as JSON

**Examples:**
```bash
# Find all references to a function
codescalpel get-symbol-references calculate_total

# Search in specific project root
codescalpel get-symbol-references UserModel --project-root /path/to/project

# Exclude test files
codescalpel get-symbol-references helper_func --no-tests
```

**Tier Limits:**
- Community: Single file search only
- Pro: Project-wide search, max 1000 files
- Enterprise: Unlimited files, cross-repository search

---

### get-graph-neighborhood

Get k-hop neighborhood of a node in the call graph.

**Usage:**
```bash
codescalpel get-graph-neighborhood <node_id> [options]
```

**Options:**
- `--project-root` - Project root directory
- `--k` - Number of hops (default: 2)
- `--direction` - Edge direction: incoming, outgoing, both (default: both)
- `--json, -j` - Output as JSON

**Examples:**
```bash
# Get 2-hop neighborhood
codescalpel get-graph-neighborhood process_payment

# Get 3-hop neighborhood with incoming edges only
codescalpel get-graph-neighborhood validate_user --k 3 --direction incoming

# Output as JSON
codescalpel get-graph-neighborhood main --k 2 --json
```

**Tier Limits:**
- Community: Max k=2, max nodes 50
- Pro: Max k=5, max nodes 500
- Enterprise: Unlimited

---

### get-project-map

Generate project structure map and visualization.

**Usage:**
```bash
codescalpel get-project-map [options]
```

**Options:**
- `--project-root` - Project root directory
- `--entry-point` - Entry point file for analysis
- `--depth` - Maximum depth for analysis (default: 10)
- `--format` - Output format: mermaid, json, text (default: text)
- `--json, -j` - Output full response as JSON

**Examples:**
```bash
# Generate project map
codescalpel get-project-map

# Generate with specific entry point
codescalpel get-project-map --entry-point src/main.py

# Generate Mermaid diagram
codescalpel get-project-map --format mermaid

# Limit depth
codescalpel get-project-map --depth 5
```

**Tier Limits:**
- Community: Max depth 3, basic structure
- Pro: Max depth 10, dependency mapping
- Enterprise: Unlimited depth, framework detection

---

### get-cross-file-dependencies

Analyze cross-file dependencies.

**Usage:**
```bash
codescalpel get-cross-file-dependencies <file_path> [options]
```

**Options:**
- `--project-root` - Project root directory
- `--depth` - Maximum dependency depth (default: 3)
- `--include-external` - Include external library dependencies
- `--json, -j` - Output as JSON

**Examples:**
```bash
# Analyze dependencies
codescalpel get-cross-file-dependencies src/api.py

# Include external libraries
codescalpel get-cross-file-dependencies src/main.py --include-external

# Limit depth
codescalpel get-cross-file-dependencies src/app.js --depth 2
```

**Tier Limits:**
- Community: Max depth 2, internal only
- Pro: Max depth 5, external dependencies
- Enterprise: Unlimited depth, cross-repository analysis

---

### crawl-project

Crawl and analyze project directory comprehensively.

**Usage:**
```bash
codescalpel crawl-project [options]
```

**Options:**
- `--root-path` - Root directory to crawl
- `--exclude-dirs` - Directories to exclude (e.g., node_modules __pycache__)
- `--complexity-threshold` - Complexity threshold (default: 10)
- `--pattern` - File pattern to match (regex or glob)
- `--pattern-type` - Pattern type: regex, glob (default: regex)
- `--no-report` - Exclude detailed report
- `--json, -j` - Output as JSON

**Examples:**
```bash
# Crawl current directory
codescalpel crawl-project

# Exclude specific directories
codescalpel crawl-project --exclude-dirs node_modules __pycache__ .git

# Match specific file pattern
codescalpel crawl-project --pattern ".*\\.py$" --pattern-type regex

# Set complexity threshold
codescalpel crawl-project --complexity-threshold 15
```

**Tier Limits:**
- Community: Max 100 files, depth 10
- Pro: Unlimited files, parallel processing
- Enterprise: Unlimited, distributed crawling, monorepo support

---

## Extraction Tools

### extract-code

Surgically extract code with dependencies.

**Usage:**
```bash
codescalpel extract-code <file_path> --function <name> [options]
```

**Options:**
- `--function, -f` - Function name to extract (required)
- `--class, -c` - Class name (if extracting a method)
- `--include-deps` - Include cross-file dependencies (Pro+)
- `--include-context` - Include surrounding code context
- `--output, -o` - Output file
- `--json, -j` - Output as JSON

**Examples:**
```bash
# Extract a function
codescalpel extract-code src/utils.py --function calculate_total

# Extract with dependencies
codescalpel extract-code src/api.py --function process_request --include-deps

# Extract method from class
codescalpel extract-code src/models.py --function save --class User

# Save to file
codescalpel extract-code src/lib.py --function helper -o extracted.py
```

**Tier Limits:**
- Community: Single file, max depth 1, 1MB files, no cross-file deps
- Pro: Cross-file deps enabled, unlimited depth, 100MB files
- Enterprise: Pro-scale limits plus org-wide/service-boundary features

---

## Security Tools

### scan

Scan for security vulnerabilities.

**Usage:**
```bash
codescalpel scan <file_path> [options]
codescalpel scan --code "<code_string>" [options]
```

**Options:**
- `--json, -j` - Output as JSON

**Examples:**
```bash
# Scan a file
codescalpel scan src/api.py

# Scan code string
codescalpel scan --code "import os; os.system(user_input)"

# Get JSON output
codescalpel scan src/auth.py --json
```

**Tier Limits:**
- Community: Basic OWASP Top 10 detection
- Pro: Advanced patterns, data flow analysis
- Enterprise: ML-powered detection, custom rules

---

### cross-file-security-scan

Cross-file taint analysis for security vulnerabilities.

**Usage:**
```bash
codescalpel cross-file-security-scan [options]
```

**Options:**
- `--project-root` - Project root directory
- `--entry-point` - Entry point file for analysis
- `--max-depth` - Maximum analysis depth (default: 5)
- `--json, -j` - Output as JSON

**Examples:**
```bash
# Scan entire project
codescalpel cross-file-security-scan

# Scan from specific entry point
codescalpel cross-file-security-scan --entry-point src/main.py

# Limit analysis depth
codescalpel cross-file-security-scan --max-depth 3
```

**Tier Limits:**
- Community: Max depth 2, single entry point
- Pro: Max depth 5, multiple entry points
- Enterprise: Unlimited depth, whole-program analysis

---

### type-evaporation-scan

Detect type system evaporation vulnerabilities.

**Usage:**
```bash
codescalpel type-evaporation-scan [options]
```

**Options:**
- `--frontend-file` - Frontend TypeScript file path
- `--backend-file` - Backend Python file path
- `--frontend-code` - Frontend code (alternative to file)
- `--backend-code` - Backend code (alternative to file)
- `--json, -j` - Output as JSON

**Examples:**
```bash
# Scan frontend/backend pair
codescalpel type-evaporation-scan \
  --frontend-file src/api.ts \
  --backend-file src/views.py

# Use code strings
codescalpel type-evaporation-scan \
  --frontend-code "const data: any = response.data" \
  --backend-code "def handler(data): return data"
```

**Tier Limits:**
- Community: Basic `any` detection
- Pro: Frontend-backend correlation
- Enterprise: Schema generation, Pydantic/Zod remediation

---

### unified-sink-detect

Detect security sinks across multiple languages.

**Usage:**
```bash
codescalpel unified-sink-detect <code> [options]
```

**Options:**
- `--language` - Programming language (default: auto)
- `--confidence-threshold` - Confidence threshold 0.0-1.0 (default: 0.7)
- `--json, -j` - Output as JSON

**Examples:**
```bash
# Detect sinks in Python code
codescalpel unified-sink-detect "import os; os.system(cmd)" --language python

# Auto-detect language
codescalpel unified-sink-detect "eval(user_input)"

# Lower confidence threshold
codescalpel unified-sink-detect "execute(query)" --confidence-threshold 0.5
```

**Tier Limits:**
- Community: Basic sink patterns
- Pro: 196 sink patterns, context analysis
- Enterprise: ML-powered detection, custom patterns

---

### symbolic-execute

Perform symbolic execution analysis.

**Usage:**
```bash
codescalpel symbolic-execute <code> [options]
```

**Options:**
- `--max-paths` - Maximum paths to explore
- `--max-depth` - Maximum execution depth
- `--json, -j` - Output as JSON

**Examples:**
```bash
# Symbolic execution
codescalpel symbolic-execute "def foo(x): return x * 2 if x > 0 else -x"

# Limit path exploration
codescalpel symbolic-execute "complex_function()" --max-paths 10

# Limit depth
codescalpel symbolic-execute "recursive_func()" --max-depth 5
```

**Tier Limits:**
- Community: Max 10 paths, depth 5
- Pro: Max 100 paths, depth 20
- Enterprise: Unlimited, concolic execution

---

## Refactoring Tools

### rename-symbol

Safely rename a function, class, or method.

**Usage:**
```bash
codescalpel rename-symbol <file_path> <target_name> <new_name> [options]
```

**Options:**
- `--type` - Symbol type: function, class, method (default: function)
- `--no-backup` - Do not create backup before renaming
- `--json, -j` - Output as JSON

**Examples:**
```bash
# Rename a function
codescalpel rename-symbol src/utils.py calculate_sum compute_total

# Rename a class
codescalpel rename-symbol src/models.py User UserModel --type class

# Skip backup
codescalpel rename-symbol src/api.py old_func new_func --no-backup
```

**Tier Limits:**
- Community: Single file renames only
- Pro: Cross-file renames, max 500 files
- Enterprise: Unlimited, audit trail, approval workflows

---

### update-symbol

Update symbol implementation.

**Usage:**
```bash
codescalpel update-symbol <file_path> <target_name> <new_body> [options]
```

**Options:**
- `--type` - Symbol type: function, class, method (default: function)
- `--no-backup` - Do not create backup
- `--json, -j` - Output as JSON

**Examples:**
```bash
# Update function body
codescalpel update-symbol src/utils.py foo "return 42"

# Update method
codescalpel update-symbol src/models.py save "self.db.commit()" --type method

# Skip backup
codescalpel update-symbol src/api.py handler "pass" --no-backup
```

**Tier Limits:**
- Community: Single file updates
- Pro: Cross-file impact analysis
- Enterprise: Automated testing, rollback support

---

### simulate-refactor

Simulate refactoring impact before applying.

**Usage:**
```bash
codescalpel simulate-refactor <file_path> --changes <description> [options]
```

**Options:**
- `--changes` - Description of changes to simulate (required)
- `--json, -j` - Output as JSON

**Examples:**
```bash
# Simulate renaming
codescalpel simulate-refactor src/api.py --changes "rename process_data to handle_request"

# Simulate extraction
codescalpel simulate-refactor src/utils.py --changes "extract validation logic to separate function"
```

**Tier Limits:**
- Community: Single file simulation
- Pro: Cross-file impact analysis
- Enterprise: Automated test generation, risk assessment

---

## Testing Tools

### generate-unit-tests

AI-powered unit test generation.

**Usage:**
```bash
codescalpel generate-unit-tests <file_path> [options]
```

**Options:**
- `--function` - Specific function to test
- `--framework` - Test framework: pytest, unittest, jest, mocha (default: pytest)
- `--coverage-target` - Target coverage % (default: 80)
- `--json, -j` - Output as JSON

**Examples:**
```bash
# Generate tests for entire file
codescalpel generate-unit-tests src/utils.py

# Generate tests for specific function
codescalpel generate-unit-tests src/api.py --function process_request

# Use Jest framework
codescalpel generate-unit-tests src/app.js --framework jest

# Target 90% coverage
codescalpel generate-unit-tests src/lib.py --coverage-target 90
```

**Tier Limits:**
- Community: Max 5 tests, basic patterns
- Pro: Advanced test generation, edge cases
- Enterprise: Unlimited, custom templates, coverage optimization

---

## Validation Tools

### validate-paths

Validate import paths in project.

**Usage:**
```bash
codescalpel validate-paths <file_path> [options]
```

**Options:**
- `--fix` - Auto-fix invalid paths
- `--json, -j` - Output as JSON

**Examples:**
```bash
# Validate paths
codescalpel validate-paths src/main.py

# Auto-fix invalid paths
codescalpel validate-paths src/api.py --fix
```

**Tier Limits:**
- Community: Single file validation
- Pro: Project-wide validation, auto-fix
- Enterprise: Cross-repository validation, migration tools

---

### scan-dependencies

Scan project dependencies for issues.

**Usage:**
```bash
codescalpel scan-dependencies [options]
```

**Options:**
- `--project-root` - Project root directory
- `--include-dev` - Include development dependencies
- `--check-security` - Check for security vulnerabilities
- `--json, -j` - Output as JSON

**Examples:**
```bash
# Scan dependencies
codescalpel scan-dependencies

# Include dev dependencies
codescalpel scan-dependencies --include-dev

# Check security vulnerabilities
codescalpel scan-dependencies --check-security
```

**Tier Limits:**
- Community: Basic dependency listing
- Pro: Security vulnerability checking
- Enterprise: License compliance, update recommendations

---

## Policy Tools

### code-policy-check

Check code against policy rules.

**Usage:**
```bash
codescalpel code-policy-check <file_path> [options]
```

**Options:**
- `--policy-dir` - Policy directory (default: .code-scalpel)
- `--strict` - Fail on any policy violation
- `--json, -j` - Output as JSON

**Examples:**
```bash
# Check against policies
codescalpel code-policy-check src/api.py

# Use custom policy directory
codescalpel code-policy-check src/main.py --policy-dir policies/

# Strict mode
codescalpel code-policy-check src/utils.py --strict
```

**Tier Limits:**
- Community: Basic policy rules
- Pro: Custom rules, violation tracking
- Enterprise: Automated enforcement, approval workflows

---

### verify-policy-integrity

Verify policy file integrity using cryptographic signatures.

**Usage:**
```bash
codescalpel verify-policy-integrity [options]
```

**Options:**
- `--policy-dir` - Policy directory (default: .code-scalpel)
- `--json, -j` - Output as JSON

**Examples:**
```bash
# Verify policy integrity
codescalpel verify-policy-integrity

# Use custom policy directory
codescalpel verify-policy-integrity --policy-dir policies/
```

**Tier Limits:**
- Community: Basic verification
- Pro: Signature validation
- Enterprise: Full integrity check, audit logging

---

## Common Options

All commands support these common patterns:

### JSON Output
```bash
# Add --json or -j to any command
codescalpel <command> <args> --json
```

### Help
```bash
# Get help for any command
codescalpel <command> --help
```

### Output to File
```bash
# Most commands support --output or -o
codescalpel <command> <args> --output result.txt
```

---

## Tier System

Code Scalpel uses a three-tier licensing system:

### Community (Free)
- All 22 tools available
- Basic features and limited thresholds
- Suitable for individual developers and small projects

### Pro
- All 22 tools available
- Enhanced limits and advanced features
- Cross-file analysis, parallel processing
- Suitable for professional developers and teams

### Enterprise
- All 22 tools available
- Unlimited thresholds
- Advanced features: distributed processing, custom rules, audit trails
- Suitable for large organizations and critical applications

### Check Your Tier
```bash
codescalpel capabilities
```

### Upgrade
To upgrade your tier, visit: https://code-scalpel.ai/pricing

---

## Common Workflows

### Workflow 1: Extract and Analyze Function

Extract a function and perform comprehensive analysis.

```bash
# 1. Extract function with dependencies
codescalpel extract-code src/api.py --function process_payment --include-deps > extracted.py

# 2. Analyze the extracted code
codescalpel analyze extracted.py --json > analysis.json

# 3. Check for security issues
codescalpel scan extracted.py

# 4. Generate comprehensive tests
codescalpel generate-unit-tests extracted.py --coverage-target 90

# 5. View call graph
codescalpel get-call-graph extracted.py --format mermaid
```

**Use Case**: When you need to understand, test, and secure a specific function before refactoring or optimization.

---

### Workflow 2: Security Audit Pipeline

Comprehensive security audit of a project.

```bash
# 1. Run basic security scan on entry point
codescalpel scan src/main.py --json > basic-scan.json

# 2. Cross-file taint analysis
codescalpel cross-file-security-scan --entry-point src/main.py --max-depth 10 \
  --json > taint-analysis.json

# 3. Check for type evaporation vulnerabilities
codescalpel type-evaporation-scan \
  --frontend-file src/api.ts \
  --backend-file src/views.py \
  --json > type-issues.json

# 4. Detect security sinks across the codebase
find src -name "*.py" -exec codescalpel unified-sink-detect "$(cat {})" --json \; > sinks.json

# 5. Verify code policies
codescalpel code-policy-check src/ --strict

# 6. Validate import paths
codescalpel validate-paths src/main.py --fix
```

**Use Case**: Pre-release security audit, compliance checking, or security review before deployment.

---

### Workflow 3: Refactoring with Impact Analysis

Safe refactoring with comprehensive impact analysis.

```bash
# 1. Get current call graph to understand dependencies
codescalpel get-call-graph src/auth.py --format mermaid -o before-refactor.md

# 2. Find all references to the symbol you want to change
codescalpel get-symbol-references UserAuthentication --json > references.json

# 3. Simulate the refactor to see potential impacts
codescalpel simulate-refactor src/auth.py \
  --changes "rename UserAuthentication to AuthService and extract token logic"

# 4. Perform the actual rename
codescalpel rename-symbol src/auth.py UserAuthentication AuthService

# 5. Verify no broken imports
codescalpel validate-paths src/auth.py --fix

# 6. Check call graph after refactor
codescalpel get-call-graph src/auth.py --format mermaid -o after-refactor.md

# 7. Run security scan to ensure no issues introduced
codescalpel scan src/auth.py

# 8. Generate tests for refactored code
codescalpel generate-unit-tests src/auth.py
```

**Use Case**: Large-scale refactoring where you need to ensure changes don't break dependencies or introduce security issues.

---

### Workflow 4: Project-Wide Analysis and Documentation

Comprehensive project analysis for onboarding or architecture review.

```bash
# 1. Generate high-level project map
codescalpel get-project-map --entry-point src/main.py --format mermaid -o project-map.md

# 2. Crawl entire project for complexity analysis
codescalpel crawl-project --root-path . \
  --exclude-dirs node_modules __pycache__ .git .venv \
  --complexity-threshold 15 \
  --json > complexity-report.json

# 3. Analyze cross-file dependencies
codescalpel get-cross-file-dependencies src/main.py \
  --include-external \
  --depth 5 \
  --json > dependencies.json

# 4. Scan dependencies for security issues
codescalpel scan-dependencies --include-dev --check-security --json > dep-security.json

# 5. Get call graph for critical modules
codescalpel get-call-graph src/core/engine.py --format mermaid -o core-callgraph.md

# 6. Find all references to critical symbols
codescalpel get-symbol-references DatabaseConnection --json > db-refs.json

# 7. Get 3-hop neighborhood of critical functions
codescalpel get-graph-neighborhood process_transaction --k 3 --json > transaction-neighbors.json

# 8. Run comprehensive security audit
codescalpel cross-file-security-scan --max-depth 10 --json > security-audit.json
```

**Use Case**: New team member onboarding, architecture review, technical debt assessment, or pre-acquisition due diligence.

---

### Workflow 5: Continuous Integration Pipeline

Automated quality and security checks in CI/CD.

```bash
#!/bin/bash
# ci-checks.sh - Run in CI pipeline

set -e  # Exit on error

echo "=== Code Scalpel CI Checks ==="

# 1. Verify policy integrity
codescalpel verify-policy-integrity || exit 1

# 2. Security scan on changed files
codescalpel scan src/ --json > scan-results.json

# 3. Check for high-complexity functions
codescalpel crawl-project --complexity-threshold 10 --json > complexity.json

# 4. Validate all import paths
find src -name "*.py" -exec codescalpel validate-paths {} \; || exit 1

# 5. Policy compliance check
codescalpel code-policy-check src/ --strict || exit 1

# 6. Cross-file security scan on main entry point
codescalpel cross-file-security-scan --entry-point src/main.py --max-depth 5 \
  --json > xfile-security.json

# 7. Check if any critical security issues found
if grep -q '"severity": "critical"' scan-results.json; then
    echo "❌ Critical security issues found!"
    exit 1
fi

echo "✅ All CI checks passed!"
```

**Use Case**: Automated quality gates in CI/CD pipelines, pre-commit hooks, or pull request checks.

---

### Workflow 6: Dependency Migration

Safely migrate from one dependency to another.

```bash
# 1. Scan current dependencies
codescalpel scan-dependencies --include-dev --json > current-deps.json

# 2. Find all references to old library
codescalpel get-symbol-references OldLibrary --project-root . --json > old-lib-refs.json

# 3. Get call graph showing usage
codescalpel get-call-graph src/integrations/old_lib.py --format mermaid -o old-lib-usage.md

# 4. Simulate refactor
codescalpel simulate-refactor src/integrations/old_lib.py \
  --changes "replace OldLibrary with NewLibrary"

# 5. Extract integration code
codescalpel extract-code src/integrations/old_lib.py --function initialize --include-deps > old-integration.py

# 6. Generate tests for current implementation
codescalpel generate-unit-tests src/integrations/old_lib.py --coverage-target 95

# (Manual step: implement new integration)

# 7. Validate new implementation
codescalpel scan src/integrations/new_lib.py
codescalpel validate-paths src/integrations/new_lib.py

# 8. Verify no broken references
codescalpel get-symbol-references OldLibrary --project-root . --no-tests
```

**Use Case**: Migrating from deprecated libraries, upgrading to newer versions, or replacing third-party dependencies.

---

## Configuration Management

Commands for setting up and maintaining the `.code-scalpel/` configuration directory.

### init

Initialize a `.code-scalpel/` configuration directory, or safely add any missing files to an existing one.

**Usage:**
```bash
codescalpel init [options]
```

**Options:**
- `--dir, -d <path>` — Target directory (default: current directory)
- `--force, -f` — Deprecated; directory existence no longer blocks init

**Behaviour:**
- If `.code-scalpel/` does **not** exist: creates it with the full default configuration scaffold (~20 files including policies, audit log, license directory, and response configuration).
- If `.code-scalpel/` **already exists**: adds only the files that are missing — all existing customisations are preserved. This is the recommended upgrade path for users moving between Code Scalpel versions.

**Examples:**
```bash
# First-time setup
codescalpel init

# After upgrading Code Scalpel — add any new files without touching existing ones
codescalpel init --dir /path/to/project

# Verify what was added
codescalpel check --dir /path/to/project
```

---

### check

Audit an existing `.code-scalpel/` directory and report which expected configuration files are present, missing, or corrupt.

**Usage:**
```bash
codescalpel check [options]
```

**Options:**
- `--dir, -d <path>` — Target directory (default: current directory)
- `--json, -j` — Machine-readable JSON output
- `--fix, -F` — Add any missing files before reporting (safe — never overwrites existing files)

**Exit codes:**
- `0` — All required files present and valid (recommended/optional files may still be missing)
- `1` — One or more required files are missing or have parse errors

**Integrity checking:**

All present files are validated on every run:
- JSON files are parsed; malformed JSON is flagged as `[PARSE ERROR]`
- YAML files are parsed; malformed YAML is flagged as `[PARSE ERROR]`
- Rego policy files are checked for a `package` declaration
- Zero-byte files are flagged as `[EMPTY FILE]`

Required files with integrity failures cause `exit 1` just like absent required files.

**Examples:**
```bash
# Quick audit of current project
codescalpel check

# Audit and automatically fill in any gaps
codescalpel check --fix

# Machine-readable output for CI
codescalpel check --json

# Full check + fix in JSON (CI upgrade workflow)
codescalpel check --fix --json | jq '.summary'
```

**JSON output structure:**
```json
{
  "success": true,
  "config_dir": "/path/to/.code-scalpel",
  "fix_applied": null,
  "summary": {
    "required_missing": 0,
    "recommended_missing": 0,
    "optional_missing": 1,
    "total_present": 19
  },
  "integrity": {
    "ok": true,
    "errors": [],
    "warnings": [],
    "files_validated": ["config.json", "policy.yaml", ...]
  },
  "files": {
    "config.json": {
      "present": true,
      "level": "required",
      "description": "Core settings (tier, paths, feature flags)",
      "integrity": { "empty": false, "parse_error": null, "ok": true }
    }
  }
}
```

**File tiers:**

| Level | Files | Effect if missing |
|-------|-------|-------------------|
| Required | `config.json`, `policy.yaml`, `budget.yaml`, `response_config.json` | Some features will not work; `exit 1` |
| Recommended | `dev-governance.yaml`, `project-structure.yaml`, `response_config.schema.json`, `policy.manifest.json`, `audit.log`, `license/README.md`, policy Rego files | Degraded functionality; `exit 0` |
| Optional | `.gitignore`, `README.md`, `ide-extension.json`, `HOOKS_README.md`, `.env.example` | Informational only; `exit 0` |

---

### verify-policies

Verify the cryptographic integrity of policy files using the HMAC manifest.

**Usage:**
```bash
codescalpel verify-policies [options]
```

**Options:**
- `--dir, -d <path>` — Target directory (default: current directory)
- `--manifest-source` — Source of the manifest (`file` or `env`)

**Example:**
```bash
codescalpel verify-policies
codescalpel verify-policies --dir /path/to/project
```

---

### regenerate-manifest

Regenerate the `policy.manifest.json` cryptographic manifest after modifying policy files.

**Usage:**
```bash
codescalpel regenerate-manifest [options]
```

**Options:**
- `--dir, -d <path>` — Target directory (default: current directory)
- `--signed-by` — Name/identifier to record in the manifest

**Example:**
```bash
# After editing a .rego policy file
codescalpel regenerate-manifest --signed-by "dev@example.com"
```

---

## Tips & Best Practices

### 1. Use JSON Output for Automation
```bash
# Parse results in scripts
codescalpel analyze src/ --json | jq '.functions[] | .name'
```

### 2. Combine Tools for Workflows
```bash
# Extract, analyze, then generate tests
codescalpel extract-code src/api.py --function handler -o extracted.py
codescalpel analyze extracted.py --json
codescalpel generate-unit-tests extracted.py
```

### 3. Use Project Root Consistently
```bash
# Set project root for accurate analysis
codescalpel get-symbol-references MyClass --project-root /path/to/project
```

### 4. Leverage Tier-Aware Features
```bash
# Check what's available at your tier
codescalpel capabilities --tool extract_code
```

### 5. Save Output for Review
```bash
# Save analysis results
codescalpel cross-file-security-scan --json > security-report.json
```

---

## Troubleshooting

### Command Not Found
```bash
# Ensure Code Scalpel is installed
pip install --upgrade code-scalpel

# Or install in development mode
pip install -e .
```

### Tier Limit Errors
```
Error: Feature 'cross_file_deps' requires PRO tier.
```

**Solution**: Upgrade your license or use the feature within Community tier limits.

### Import Errors
```
Error: Tool 'extract_code' not found
```

**Solution**: Reinstall Code Scalpel or check your Python environment.

---

## Getting Help

- **Command Help**: `codescalpel <command> --help`
- **List All Commands**: `codescalpel --help`
- **Check Capabilities**: `codescalpel capabilities`
- **GitHub Issues**: https://github.com/cyanheads/code-scalpel/issues
- **Documentation**: https://code-scalpel.ai/docs

---

**Last Updated**: 2026-02-24
**Version**: 1.4.1+
**Author**: Code Scalpel Team
