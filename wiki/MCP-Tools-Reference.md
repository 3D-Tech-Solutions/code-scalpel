# MCP Tools Reference

This reference documents Code Scalpel's 22 tools. **You don't call these directly**—your AI assistant (Claude, Copilot, Cursor) uses them automatically when you ask for help with code analysis, security scanning, or refactoring.

## Understanding MCP Tools

### How It Works

```
You: "Extract the process_payment function from services.py"
     ↓
AI Assistant: Uses extract_code tool via MCP (you don't see this)
     ↓
You see: The function code extracted cleanly
```

The tools run on Code Scalpel's backend server and return results to your AI assistant, which presents them in conversation.

## Tool Categories

Code Scalpel provides 22 tools across five categories:

1. **Extraction** - Get specific code elements without reading entire files
2. **Analysis** - Understand code structure, dependencies, and metrics
3. **Security** - Detect vulnerabilities using taint analysis
4. **Modification** - Safely refactor, rename, and update code
5. **Verification** - Test changes, generate tests, validate compliance

All tools are available in the Community tier. Higher tiers provide enhanced limits and features.

## Quick Reference

| Tool | Category | What to Ask For |
|------|----------|-----------------|
| [extract_code](#extract_code) | Extraction | "Extract the [function/class] from [file]" |
| [analyze_code](#analyze_code) | Analysis | "What's in this file?" |
| [get_file_context](#get_file_context) | Analysis | "Quick overview of [file]" |
| [get_symbol_references](#get_symbol_references) | Navigation | "Where is [function] used?" |
| [get_call_graph](#get_call_graph) | Navigation | "How does [function] call other functions?" |
| [get_cross_file_dependencies](#get_cross_file_dependencies) | Navigation | "What does [file] import?" |
| [get_project_map](#get_project_map) | Analysis | "Show me project structure" |
| [crawl_project](#crawl_project) | Analysis | "Analyze entire project" |
| [get_graph_neighborhood](#get_graph_neighborhood) | Analysis | "Functions related to [function]" |
| [security_scan](#security_scan) | Security | "Check code for vulnerabilities" |
| [cross_file_security_scan](#cross_file_security_scan) | Security | "Scan entire service for security issues" |
| [unified_sink_detect](#unified_sink_detect) | Security | "Find dangerous functions used" |
| [type_evaporation_scan](#type_evaporation_scan) | Security | "Check TypeScript type boundaries" |
| [scan_dependencies](#scan_dependencies) | Security | "Check for known CVEs in dependencies" |
| [update_symbol](#update_symbol) | Modification | "Replace this function with new code" |
| [rename_symbol](#rename_symbol) | Modification | "Rename [function] everywhere it's used" |
| [simulate_refactor](#simulate_refactor) | Verification | "Is this refactoring safe?" |
| [symbolic_execute](#symbolic_execute) | Verification | "What are all possible code paths?" |
| [generate_unit_tests](#generate_unit_tests) | Verification | "Generate tests for this function" |
| [code_policy_check](#code_policy_check) | Verification | "Check compliance with coding standards" |
| [validate_paths](#validate_paths) | Utility | "Verify file paths are accessible" |
| [verify_policy_integrity](#verify_policy_integrity) | Utility | "Verify policy files are legitimate" |

---

## Code Extraction & Modification

### extract_code

**Surgically extract functions, classes, or methods from files.**

99% token reduction compared to reading entire files. The server reads the file directly—you only pay tokens for the extracted code.

**How to use it:**
> "Extract the calculate_tax function from utils.py"
> 
> AI will return only that function with necessary imports

**Parameters:**
- `target_type` (string, required): `"function"`, `"class"`, or `"method"`
- `target_name` (string, required): Name of the element (for methods: `"ClassName.method_name"`)
- `file_path` (string, optional): Path to source file (RECOMMENDED—server reads file)
- `code` (string, optional): Source code string (fallback if file_path not provided)
- `language` (string, optional): `"python"`, `"javascript"`, `"typescript"`, `"java"` (auto-detected from extension)
- `include_context` (boolean, default: `false`): Extract intra-file dependencies
- `context_depth` (integer, default: `1`): Dependency traversal depth
- `include_cross_file_deps` (boolean, default: `false`): Resolve imports from external files
- `include_token_estimate` (boolean, default: `true`): Include token count estimate

**Returns:**
```json
{
  "success": true,
  "target_name": "calculate_tax",
  "target_code": "def calculate_tax(amount): ...",
  "imports": ["from decimal import Decimal"],
  "dependencies": ["TaxRate"],
  "metadata": {
    "line_start": 42,
    "line_end": 58,
    "token_estimate": 50
  }
}
```

**Example:**
```python
# Efficient: Agent sends ~50 tokens, receives ~200
extract_code(
    file_path="/project/utils.py",
    target_type="function",
    target_name="calculate_tax"
)

# With cross-file dependencies
extract_code(
    file_path="/project/services/order.py",
    target_type="function",
    target_name="process_order",
    include_cross_file_deps=True
)

# JavaScript/TypeScript
extract_code(
    file_path="/src/utils.js",
    target_type="function",
    target_name="formatCurrency"
)

# Java method
extract_code(
    file_path="/src/Calculator.java",
    target_type="method",
    target_name="Calculator.add"
)
```

**Supported Languages:**
- Python ✅ Full support
- JavaScript/TypeScript ✅ Full support (including JSX/TSX React components)
- Java ✅ Methods and classes
- Go, Rust, Ruby, PHP ⚠️ Basic support via tree-sitter

---

### update_symbol

**Atomically replace a function, class, or method with new code.**

Creates backup, validates syntax, preserves surrounding code.

**Parameters:**
- `file_path` (string, required): Path to file containing symbol
- `target_type` (string, required): `"function"`, `"class"`, or `"method"`
- `target_name` (string, required): Name of symbol to update
- `new_code` (string, required): Replacement code
- `operation` (string, default: `"replace"`): `"replace"`, `"insert_before"`, `"insert_after"`
- `create_backup` (boolean, default: `true`): Create `.bak` file before modification

**Returns:**
```json
{
  "success": true,
  "file_path": "/project/utils.py",
  "target_name": "calculate_tax",
  "backup_path": "/project/utils.py.bak",
  "changes_applied": true,
  "syntax_valid": true
}
```

**Example:**
```python
# Safe replacement
update_symbol(
    file_path="app.py",
    target_type="function",
    target_name="process_order",
    new_code="""
def process_order(order_id, currency='USD'):
    '''Enhanced with currency support'''
    if currency not in SUPPORTED_CURRENCIES:
        raise ValueError(f"Unsupported: {currency}")
    # ... implementation
"""
)
```

**Safety Features:**
- ✅ Automatic backup creation
- ✅ Syntax validation before writing
- ✅ Preserves surrounding code
- ✅ Atomic write operation

---

### rename_symbol

**Rename functions, classes, or methods across all references.**

Consistently updates definition and all call sites.

**Parameters:**
- `file_path` (string, required): Path to file containing definition
- `target_type` (string, required): `"function"`, `"class"`, or `"method"`
- `target_name` (string, required): Current name
- `new_name` (string, required): New name
- `create_backup` (boolean, default: `true`): Create backups

**Returns:**
```json
{
  "success": true,
  "file_path": "/project/utils.py",
  "target_name": "calculate_tax",
  "new_name": "compute_tax_amount",
  "references_updated": 7,
  "files_modified": ["utils.py", "services.py", "tests.py"]
}
```

**Example:**
```python
rename_symbol(
    file_path="utils.py",
    target_type="function",
    target_name="old_function",
    new_name="new_function"
)
# Automatically updates all call sites!
```

---

## Code Analysis & Navigation

### analyze_code

**Parse code structure: functions, classes, imports, complexity.**

Understand file architecture before editing.

**Parameters:**
- `code` (string, required): Source code to analyze
- `language` (string, default: `"auto"`): Language detection (auto-detects from content)
- `file_path` (string, optional): File path for better context

**Returns:**
```json
{
  "functions": ["process_payment", "validate_card"],
  "classes": ["PaymentProcessor", "PaymentError"],
  "imports": ["stripe", "decimal.Decimal"],
  "complexity_score": 8,
  "lines_of_code": 245,
  "has_main": true,
  "docstring": "Payment processing module"
}
```

**Example:**
```python
analyze_code(code=file_contents)
```

---

### get_file_context

**Quick file overview without reading full content.**

Returns functions, classes, imports, complexity—no full file read.

**Parameters:**
- `file_path` (string, required): Path to file

**Returns:**
```json
{
  "file_path": "services/payment.py",
  "functions": ["process_payment", "validate_card", "refund"],
  "classes": ["PaymentProcessor", "PaymentError"],
  "imports": ["stripe", "decimal.Decimal"],
  "complexity_score": 8,
  "line_count": 245,
  "has_security_issues": true,
  "security_warnings": ["Potential SQL injection at line 87"],
  "docstring": "Payment processing service"
}
```

**Example:**
```python
# Check what's in a file before extracting
context = get_file_context(file_path="services.py")
print(context.functions)  # See available functions
```

---

### get_symbol_references

**Find all usages of a function, class, or variable.**

Essential for safe refactoring—know all call sites before modifying.

**Parameters:**
- `symbol_name` (string, required): Name to search for
- `project_root` (string, optional): Project directory (default: current)
- `include_tests` (boolean, default: `true`): Include test files
- `scope_prefix` (string, optional): Limit to specific module prefix

**Returns:**
```json
{
  "symbol_name": "process_order",
  "definition_file": "services/order.py",
  "definition_line": 42,
  "total_references": 7,
  "references": [
    {
      "file": "handlers/api.py",
      "line": 156,
      "column": 8,
      "context": "result = process_order(order_data)",
      "is_definition": false
    },
    {
      "file": "tests/test_order.py",
      "line": 23,
      "column": 4,
      "context": "process_order(mock_order)",
      "is_definition": false
    }
  ]
}
```

**Example:**
```python
# Before changing function signature
refs = get_symbol_references("process_order")
print(f"Found in {len(refs.references)} places")
```

**Tier Limits:**
- Community: 100 references
- Pro: Unlimited
- Enterprise: Unlimited

---

### get_call_graph

**Trace function relationships and execution flow.**

**Parameters:**
- `file_path` (string, optional): File to analyze
- `function_name` (string, optional): Specific function to graph
- `max_depth` (integer, default: `3`): Traversal depth
- `include_external` (boolean, default: `false`): Include library calls

**Returns:**
```json
{
  "nodes": [
    {"id": "main", "type": "function", "file": "app.py"},
    {"id": "process", "type": "function", "file": "app.py"},
    {"id": "validate", "type": "function", "file": "utils.py"}
  ],
  "edges": [
    {"from": "main", "to": "process", "type": "calls"},
    {"from": "process", "to": "validate", "type": "calls"}
  ],
  "mermaid_diagram": "graph TD\n  main --> process\n  process --> validate"
}
```

**Tier Limits:**
- Community: 500 nodes
- Pro: 10,000 nodes
- Enterprise: Unlimited

---

### get_cross_file_dependencies

**Resolve imports and dependencies across files.**

**Parameters:**
- `file_path` (string, required): File to analyze
- `resolve_transitive` (boolean, default: `false`): Include indirect dependencies
- `max_depth` (integer, default: `2`): Dependency depth

**Returns:**
```json
{
  "file_path": "services/order.py",
  "direct_imports": ["models.Order", "utils.validate"],
  "transitive_dependencies": ["db.connection", "config.settings"],
  "dependency_graph": {
    "models.Order": ["db.connection"],
    "utils.validate": ["config.settings"]
  }
}
```

---

### get_project_map

**High-level project structure mapping.**

**Parameters:**
- `root_path` (string, required): Project root directory
- `max_depth` (integer, default: `3`): Directory traversal depth
- `include_tests` (boolean, default: `false`): Include test directories

**Returns:**
```json
{
  "project_root": "/project",
  "structure": {
    "src": {
      "services": ["order.py", "payment.py"],
      "models": ["user.py", "order.py"],
      "utils": ["validate.py"]
    },
    "tests": ["test_order.py", "test_payment.py"]
  },
  "languages": ["python"],
  "entry_points": ["main.py", "app.py"],
  "total_files": 45,
  "total_lines": 12500
}
```

**Tier Limits:**
- Community: 1,000 files
- Pro: 10,000 files
- Enterprise: Unlimited

---

### crawl_project

**Comprehensive project-wide analysis.**

Analyzes all files, generates metrics, complexity hotspots.

**Parameters:**
- `project_root` (string, required): Root directory
- `file_pattern` (string, default: `"**/*.py"`): Glob pattern
- `include_metrics` (boolean, default: `true`): Calculate detailed metrics

**Returns:**
```json
{
  "total_files": 150,
  "total_lines": 45000,
  "languages": {"python": 120, "javascript": 30},
  "complexity_hotspots": [
    {"file": "legacy/processor.py", "complexity": 45, "line": 200}
  ],
  "metrics": {
    "avg_complexity": 8.5,
    "max_complexity": 45,
    "test_coverage": 0.82
  }
}
```

---

### get_graph_neighborhood

**Extract k-hop subgraph around a code symbol.**

Prevents graph explosion on large codebases.

**Parameters:**
- `center_node_id` (string, required): Node ID (format: `language::module::type::name`)
- `k` (integer, default: `2`): Maximum hops from center
- `max_nodes` (integer, default: `100`): Node limit
- `direction` (string, default: `"both"`): `"outgoing"`, `"incoming"`, or `"both"`
- `min_confidence` (float, default: `0.0`): Minimum edge confidence (0-1)

**Returns:**
```json
{
  "center_node": "python::services::function::process_order",
  "subgraph": {
    "nodes": [...],
    "edges": [...]
  },
  "truncated": false,
  "mermaid_diagram": "graph TD..."
}
```

---

## Security Analysis

### security_scan

**Taint-based vulnerability detection (12+ CWEs).**

Traces data flow from user input to dangerous sinks.

**Parameters:**
- `code` (string, required): Source code to scan
- `entry_points` (list of strings, optional): Functions to analyze
- `min_confidence` (float, default: `0.7`): Confidence threshold (0-1)
- `include_flow` (boolean, default: `true`): Include taint flow traces

**Detects:**
- SQL Injection (CWE-89)
- Command Injection (CWE-78)
- XSS (CWE-79)
- Path Traversal (CWE-22)
- Code Injection (CWE-94)
- LDAP Injection (CWE-90)
- XXE (CWE-611)
- SSRF (CWE-918)
- Open Redirect (CWE-601)
- Insecure Deserialization (CWE-502)
- +more

**Returns:**
```json
{
  "vulnerabilities": [
    {
      "cwe": "CWE-89",
      "severity": "high",
      "description": "SQL injection via user input",
      "source_line": 45,
      "sink_line": 67,
      "confidence": 0.95,
      "taint_flow": [
        {"line": 45, "code": "user_input = request.GET['id']"},
        {"line": 55, "code": "query_part = user_input"},
        {"line": 67, "code": "cursor.execute(query_part)"}
      ],
      "recommendation": "Use parameterized queries"
    }
  ],
  "total_vulnerabilities": 1,
  "scan_time": 0.45
}
```

**Example:**
```python
security_scan(
    code=source_code,
    entry_points=["handle_request"],
    min_confidence=0.8
)
```

**Tier Limits:**
- Community: 50 findings per scan
- Pro: Unlimited
- Enterprise: Unlimited + compliance reporting

---

### cross_file_security_scan

**Track taint flow across module boundaries.**

Detects vulnerabilities missed by single-file analysis.

**Parameters:**
- `entry_file` (string, required): Starting file path
- `entry_points` (list of strings, required): Entry functions
- `max_depth` (integer, default: `3`): Cross-file traversal depth
- `min_confidence` (float, default: `0.7`): Confidence threshold

**Returns:** Similar to `security_scan` but includes cross-file flows.

**Example:**
```python
cross_file_security_scan(
    entry_file="api/handlers.py",
    entry_points=["handle_request"],
    max_depth=5
)
```

---

### unified_sink_detect

**Polyglot dangerous function detection with CWE mapping.**

**Parameters:**
- `code` (string, required): Source code
- `language` (string, required): `"python"`, `"javascript"`, `"typescript"`, `"java"`
- `min_confidence` (float, default: `0.7`): Confidence threshold

**Returns:**
```json
{
  "sinks": [
    {
      "name": "eval",
      "line": 45,
      "cwe": "CWE-94",
      "confidence": 0.95,
      "severity": "critical",
      "category": "code_injection"
    }
  ],
  "sink_count": 1,
  "coverage": {
    "code_injection": true,
    "sql_injection": false,
    "xss": false
  }
}
```

---

### type_evaporation_scan

**Detect TypeScript/Python type system vulnerabilities at I/O boundaries.**

Identifies where TypeScript compile-time types "evaporate" at serialization boundaries (JSON.stringify, fetch, etc.).

**Parameters:**
- `frontend_code` (string, required): TypeScript/JavaScript code
- `backend_code` (string, required): Python backend code
- `frontend_file` (string, default: `"frontend.ts"`): Filename for errors
- `backend_file` (string, default: `"backend.py"`): Filename for errors

**Returns:**
```json
{
  "frontend_issues": [
    {
      "line": 45,
      "type": "unsafe_type_assertion",
      "description": "type Role = 'admin'|'user' has no runtime enforcement",
      "severity": "high"
    }
  ],
  "backend_issues": [
    {
      "line": 67,
      "type": "unvalidated_input",
      "description": "role = request['role'] # No validation!",
      "severity": "high"
    }
  ],
  "cross_file_vulnerabilities": [
    {
      "frontend_line": 45,
      "backend_line": 67,
      "description": "TypeScript union type not enforced at backend",
      "attack_vector": "Attacker can send any value for 'role'"
    }
  ]
}
```

---

### scan_dependencies

**Check package dependencies for known vulnerabilities (CVEs).**

**Parameters:**
- `project_root` (string, required): Project directory
- `include_dev` (boolean, default: `false`): Include dev dependencies

**Returns:**
```json
{
  "dependencies": [
    {
      "name": "requests",
      "version": "2.25.0",
      "vulnerabilities": [
        {
          "cve": "CVE-2023-32681",
          "severity": "medium",
          "description": "Proxy-Authorization header leak",
          "fixed_in": "2.31.0"
        }
      ]
    }
  ],
  "total_vulnerabilities": 1,
  "critical": 0,
  "high": 0,
  "medium": 1,
  "low": 0
}
```

---

## Verification & Testing

### simulate_refactor

**Verify code changes are safe before applying.**

**Parameters:**
- `original_code` (string, required): Current code
- `new_code` (string, optional): Modified code (or provide `patch`)
- `patch` (string, optional): Unified diff patch
- `strict_mode` (boolean, default: `false`): Treat warnings as unsafe

**Returns:**
```json
{
  "is_safe": true,
  "status": "safe",
  "security_issues": [],
  "structural_changes": [
    {
      "type": "function_signature_changed",
      "name": "process_order",
      "details": "Added parameter: currency"
    }
  ],
  "warnings": []
}
```

**Example:**
```python
result = simulate_refactor(
    original_code=current_function,
    new_code=improved_function
)

if result.is_safe:
    update_symbol(file_path="app.py", new_code=improved_function)
```

---

### symbolic_execute

**Explore execution paths using Z3 theorem prover.**

**Parameters:**
- `code` (string, required): Function to analyze
- `max_paths` (integer, default: `10`): Maximum paths to explore
- `timeout` (integer, default: `30`): Timeout in seconds
- `loop_unroll_depth` (integer, default: `2`): Loop unrolling depth

**Returns:**
```json
{
  "paths": [
    {
      "path_id": 1,
      "constraints": ["x > 0", "y < 10"],
      "branch_decisions": [true, false],
      "covered_lines": [1, 2, 5, 6]
    },
    {
      "path_id": 2,
      "constraints": ["x > 0", "y >= 10"],
      "branch_decisions": [true, true],
      "covered_lines": [1, 2, 5, 7, 8]
    }
  ],
  "total_paths": 2,
  "coverage": 0.95
}
```

---

### generate_unit_tests

**Auto-generate unit tests from symbolic execution paths.**

**Parameters:**
- `code` (string, required): Function to test
- `framework` (string, default: `"pytest"`): `"pytest"` or `"unittest"`
- `max_paths` (integer, default: `10`): Paths to generate tests for

**Returns:**
```python
{
  "test_code": """
import pytest

def test_calculate_tax_positive_amount():
    result = calculate_tax(100)
    assert result == 15.0

def test_calculate_tax_zero_amount():
    result = calculate_tax(0)
    assert result == 0.0

def test_calculate_tax_negative_amount():
    with pytest.raises(ValueError):
        calculate_tax(-100)
""",
  "test_count": 3,
  "coverage_estimate": 0.95
}
```

**Tier Limits:**
- Community: 10 paths
- Pro: 50 paths
- Enterprise: Unlimited

---

### code_policy_check

**Evaluate code against compliance standards.**

**Parameters:**
- `paths` (list of strings, required): Files or directories to check
- `rules` (list of strings, optional): Specific rule IDs (None = all rules for tier)
- `compliance_standards` (list of strings, optional): `["hipaa", "soc2", "gdpr", "pci_dss"]` (Enterprise only)
- `generate_report` (boolean, default: `false`): Generate PDF report (Enterprise only)

**Returns:**
```json
{
  "violations": [
    {
      "rule_id": "PY001",
      "severity": "warning",
      "file": "app.py",
      "line": 45,
      "message": "Bare except clause detected",
      "suggestion": "Catch specific exceptions"
    }
  ],
  "warnings": [],
  "compliance_score": 0.85,
  "total_checks": 150,
  "passed": 128,
  "failed": 22
}
```

**Tiers:**
- **Community**: Style guide checking, basic anti-patterns (100 files, 50 rules)
- **Pro**: Best practices, security patterns, custom rules (unlimited)
- **Enterprise**: Compliance auditing, PDF reports, audit trails

---

## Utility Tools

### validate_paths

**Security boundary enforcement for file access.**

**Parameters:**
- `paths` (list of strings, required): Paths to validate
- `base_path` (string, required): Allowed base directory
- `allow_symlinks` (boolean, default: `false`): Allow symbolic links

**Returns:**
```json
{
  "results": [
    {
      "path": "/project/src/app.py",
      "valid": true,
      "normalized": "/project/src/app.py",
      "is_symlink": false
    },
    {
      "path": "../../../etc/passwd",
      "valid": false,
      "error": "Path traversal detected"
    }
  ]
}
```

---

### verify_policy_integrity

**Cryptographically verify policy files haven't been tampered with.**

**Parameters:**
- `policy_dir` (string, required): Directory containing policies
- `manifest_path` (string, default: `"policy_manifest.json"`): Manifest file

**Requires:** `SCALPEL_MANIFEST_SECRET` environment variable

**Returns:**
```json
{
  "verified": true,
  "policies_checked": 5,
  "integrity_status": "valid",
  "tampered_files": [],
  "signature_valid": true
}
```

**Security Model: FAIL CLOSED**
- Missing secret → DENY ALL
- Invalid signature → DENY ALL
- Hash mismatch → DENY ALL

---

## Tier-Specific Features

### Community Tier
- All 22 tools available ✅
- Baseline limits on results
- MIT License (Free)

### Pro Tier
- Unlimited findings/references
- Cross-file security scanning
- Advanced metrics
- Custom rules

### Enterprise Tier
- All Pro features
- Compliance reporting (HIPAA, SOC2, GDPR, PCI-DSS)
- PDF compliance certificates
- Audit trails
- SLA support

---

**Related Pages:**
- [Getting Started](Getting-Started) - Your first tool calls
- [Examples](Examples) - Practical use cases
- [Configuration](Configuration) - Tool settings and limits
