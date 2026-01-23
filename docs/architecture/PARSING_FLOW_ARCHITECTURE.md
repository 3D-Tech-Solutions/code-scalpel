# AST Parsing Architecture: Error Handling Flow

```mermaid
graph TD
    A[User Code Input] --> B{Entry Point?}
    
    B -->|PDG Builder| C[pdg_tools/builder.py:82]
    C --> D[ast.parse - NO PROTECTION]
    D -->|Syntax Error| E[❌ CRASH - SyntaxError]
    D -->|Success| F[✅ PDG Graph]
    
    B -->|Surgical Extractor| G[surgery/surgical_extractor.py:560]
    G --> H[ast.parse with try/catch]
    H -->|Syntax Error| I[❌ CRASH - ValueError]
    H -->|Success| J[✅ Extracted Code]
    
    B -->|MCP Analyze Helper| K[mcp/helpers/ast_helpers.py:54]
    K --> L[ast.parse]
    L -->|Success| M[✅ Analysis Result]
    L -->|Syntax Error| N[sanitize_python_source]
    N --> O{Changed?}
    O -->|No| P[❌ Return None]
    O -->|Yes| Q[⚠️ SILENT FIX]
    Q --> R[ast.parse on sanitized]
    R --> M
    
    B -->|JavaScript/TypeScript| S[mcp/helpers/analyze_helpers.py:431]
    S --> T[tree_sitter Parser.parse]
    T --> U{Check has_error?}
    U -->|Not Checked| V[⚠️ SILENT SUCCESS]
    U -->|Checked| W{Has Error?}
    W -->|Yes| X[❌ Fail]
    W -->|No| Y[✅ Success]
    
    B -->|JS Normalizer| Z[ir/normalizers/javascript_normalizer.py:236]
    Z --> AA[tree_sitter Parser.parse]
    AA --> AB{Check has_error?}
    AB -->|Yes - Checked| AC[❌ Raise SyntaxError]
    AB -->|No| AD[✅ Normalize]
    
    style E fill:#ff6b6b
    style I fill:#ff6b6b
    style P fill:#ff6b6b
    style Q fill:#ffd93d
    style V fill:#ffd93d
    style X fill:#ff6b6b
    style AC fill:#ff6b6b
    style M fill:#6bcf7f
    style F fill:#6bcf7f
    style J fill:#6bcf7f
    style Y fill:#6bcf7f
    style AD fill:#6bcf7f
    
    subgraph Legend
        L1[❌ Hard Crash]
        L2[⚠️ Silent Fix/Success]
        L3[✅ Success]
    end
    
    style L1 fill:#ff6b6b
    style L2 fill:#ffd93d
    style L3 fill:#6bcf7f
```

## Code Path Comparison Matrix

| Entry Point | File | Line | Sanitization | Error Check | Failure Mode |
|-------------|------|------|--------------|-------------|--------------|
| **PDG Builder** | `pdg_tools/builder.py` | 82 | ❌ NO | ❌ NO | **CRASH** |
| **Surgical Extractor** | `surgery/surgical_extractor.py` | 560 | ❌ NO | ✅ try/catch | **CRASH (ValueError)** |
| **MCP AST Helper** | `mcp/helpers/ast_helpers.py` | 54 | ✅ YES | ✅ try/catch | **SILENT FIX** |
| **MCP Analyze (Python)** | `mcp/helpers/analyze_helpers.py` | - | ✅ Via AST Helper | ✅ YES | **SILENT FIX** |
| **MCP Analyze (JS/TS)** | `mcp/helpers/analyze_helpers.py` | 431 | ⚠️ Tree-sitter | ❌ NO | **SILENT SUCCESS** |
| **JS Normalizer** | `ir/normalizers/javascript_normalizer.py` | 236 | ⚠️ Tree-sitter | ✅ YES | **PROPER FAIL** |

## Sanitization Flow

```mermaid
sequenceDiagram
    participant User
    participant Parser as AST Parser
    participant Sanitizer as Source Sanitizer
    participant Result as Analysis Result
    
    User->>Parser: Code with merge conflict
    Parser->>Parser: ast.parse(code)
    Parser-->>Parser: SyntaxError!
    Parser->>Sanitizer: sanitize_python_source(code)
    
    Sanitizer->>Sanitizer: Strip "<<<<<<< HEAD"
    Sanitizer->>Sanitizer: Strip "======="
    Sanitizer->>Sanitizer: Strip ">>>>>>>"
    Sanitizer->>Sanitizer: Replace "{{ var }}" → None
    Sanitizer->>Sanitizer: Strip "{% ... %}"
    
    Sanitizer-->>Parser: (sanitized_code, changed=True)
    Parser->>Parser: ast.parse(sanitized_code)
    Parser-->>Result: ✅ Success (no warning!)
    Result-->>User: Analysis of MODIFIED code
    
    Note over User,Result: ⚠️ User unaware code was modified!
```

## Tree-Sitter Error Recovery

```mermaid
graph LR
    A[JavaScript Code] --> B[Tree-Sitter Parse]
    B --> C{Has ERROR nodes?}
    C -->|Missing Semicolon| D[ERROR: Expected ';']
    C -->|Missing Brace| E[ERROR: Expected '}']
    C -->|Merge Conflict| F[ERROR: Unexpected token]
    
    D --> G[⚠️ But parse succeeds!]
    E --> G
    F --> G
    
    G --> H{Analyzer checks has_error?}
    H -->|NO Check| I[⚠️ Reports success=True]
    H -->|Checks| J[❌ Reports error]
    
    style I fill:#ffd93d
    style J fill:#ff6b6b
    style G fill:#ffd93d
```

## Recommended Architecture

```mermaid
graph TD
    A[User Code] --> B{Parsing Mode}
    
    B -->|Strict Mode| C[Direct AST Parse]
    C -->|Syntax Error| D[❌ Fail with detailed error]
    C -->|Success| E[✅ Continue]
    
    B -->|Permissive Mode| F[Try AST Parse]
    F -->|Syntax Error| G[Attempt Sanitization]
    F -->|Success| E
    
    G --> H[sanitize_python_source]
    H --> I{Changed?}
    I -->|No| J[❌ Fail - unfixable]
    I -->|Yes| K[⚠️ WARN USER]
    K --> L[Parse sanitized code]
    L --> M{Success?}
    M -->|Yes| N[✅ Continue with warning]
    M -->|No| O[❌ Fail even after sanitization]
    
    E --> P[Analysis]
    N --> Q[Analysis + Sanitization Report]
    
    style D fill:#ff6b6b
    style J fill:#ff6b6b
    style O fill:#ff6b6b
    style K fill:#ffd93d
    style N fill:#ffd93d
    style E fill:#6bcf7f
    style Q fill:#ffd93d
```

## Key Recommendations

### 1. Add Configuration Flag

```python
from dataclasses import dataclass

@dataclass
class ParsingConfig:
    strict_mode: bool = True
    allow_templates: bool = False
    allow_merge_conflicts: bool = False
    warn_on_sanitization: bool = True
    tree_sitter_check_errors: bool = True
```

### 2. Standardize Entry Points

All parsers should use the same config:

```python
def parse_python_code(
    code: str,
    *,
    config: ParsingConfig | None = None
) -> tuple[ast.AST, list[str]]:
    """
    Parse Python code with configurable error handling.
    
    Returns:
        (ast_tree, warnings_list)
    """
    config = config or get_default_config()
    warnings = []
    
    if config.strict_mode:
        return ast.parse(code), warnings
    
    try:
        return ast.parse(code), warnings
    except SyntaxError:
        sanitized, changed = sanitize_python_source(code)
        if not changed:
            raise
        
        if config.warn_on_sanitization:
            warnings.append(
                "Code was sanitized: removed merge conflicts and templates"
            )
        
        return ast.parse(sanitized), warnings
```

### 3. Add Tree-Sitter Error Detection

```python
def parse_javascript_code(
    code: str,
    *,
    is_typescript: bool = False,
    config: ParsingConfig | None = None
) -> tuple[Tree, list[str]]:
    config = config or get_default_config()
    warnings = []
    
    # Parse
    parser = get_js_parser(is_typescript)
    tree = parser.parse(bytes(code, "utf-8"))
    
    # Check for errors
    if config.tree_sitter_check_errors and tree.root_node.has_error:
        error_node = find_first_error_node(tree.root_node)
        loc = f"line {error_node.start_point[0]+1}"
        raise SyntaxError(f"JavaScript parse error at {loc}")
    
    return tree, warnings
```

### 4. Return Sanitization Report

```python
@dataclass
class AnalysisResult:
    success: bool
    functions: list[str]
    classes: list[str]
    warnings: list[str]  # ✅ Add this!
    code_was_modified: bool  # ✅ Add this!
    sanitization_changes: list[str] | None  # ✅ Add this!
```

Example usage:
```python
result = analyze_code(dirty_code)
if result.code_was_modified:
    print("⚠️ Warning: Code was sanitized before analysis!")
    print("Changes:", result.sanitization_changes)
    # ['Removed merge conflict markers on lines 3-5',
    #  'Replaced Jinja2 expression on line 7']
```

---

**Architecture Review Summary**:

Current state:
- 🔴 **Inconsistent** - Different code paths, different behaviors
- 🟡 **Partially robust** - Some paths handle errors well
- 🔴 **Silent modifications** - User unaware of changes
- 🟢 **Good engineering** - Sanitization helpers exist

Recommended state:
- 🟢 **Consistent** - All paths use same config
- 🟢 **Transparent** - Always notify on modifications
- 🟢 **Configurable** - User controls strict vs. permissive
- 🟢 **Well-documented** - Clear behavior expectations
