# rename_symbol Tool Roadmap

**Tool Name:** `rename_symbol`  
**Tool Version:** v1.0  
**Code Scalpel Version:** v3.3.0  
**Current Status:** Stable  
**Primary Module:** `src/code_scalpel/ast_tools/transformer.py`  
**Tier Availability:** All tiers (Community, Pro, Enterprise)

---

## Configuration Files

| File | Purpose |
|------|---------|
| `src/code_scalpel/licensing/features.py` | Tier capability definitions |
| `.code-scalpel/limits.toml` | Numeric limits (file scope) |
| `.code-scalpel/response_config.json` | Output filtering |

---

## Overview

The `rename_symbol` tool safely renames functions, classes, or methods in a file while ensuring consistent changes throughout the codebase.

**Why AI Agents Need This:**
- **Safe refactoring:** Automated reference updates prevent broken code
- **Consistency:** All occurrences renamed atomically
- **Auditability:** Enterprise tier tracks all renames for compliance
- **Reduced errors:** Syntax validation prevents invalid renames
- **Batch operations:** Pro tier enables bulk refactoring workflows

---

## Polyglot Architecture Definition

**Polyglot Shape** means the `rename_symbol` tool provides **linguistically-agnostic symbol renaming** with a unified API across all supported languages.

### Requirements for Polyglot Shape

#### 1. Language Support Matrix
The tool must support all major programming languages with consistent behavior:

| Language | Community | Pro | Enterprise | Status |
|----------|-----------|-----|------------|--------|
| Python | ✅ | ✅ | ✅ | v1.0 |
| JavaScript | 🔄 | 🔄 | 🔄 | v1.2 (Q2 2026) |
| TypeScript | 🔄 | 🔄 | 🔄 | v1.2 (Q2 2026) |
| Java | 📋 | 📋 | 📋 | v1.2 (Q2 2026) |
| Go | 📋 | 📋 | 📋 | v1.3 (Q3 2026) |
| C/C++ | 📋 | 📋 | 📋 | v1.3 (Q3 2026) |
| Rust | 📋 | 📋 | 📋 | v1.3 (Q3 2026) |
| Ruby | 📋 | 📋 | 📋 | v1.3 (Q3 2026) |

**Legend:** ✅ Stable | 🔄 In Development | 📋 Planned

#### 2. Unified API Contract

All language implementations must conform to this interface:

```python
async def rename_symbol(
    file_path: str,
    target_type: str,              # "function" | "class" | "method"
    target_name: str,              # Current name (e.g., "oldFunc" or "Class.method")
    new_name: str,                 # New name (e.g., "newFunc" or "newMethod")
    create_backup: bool = True,    # Auto-backup before modification
    ctx: Context | None = None,
) -> PatchResultModel:
    """
    Rename a symbol safely across the project.
    
    Returns identical response structure regardless of language.
    """
```

**Key Constraint:** The response model `PatchResultModel` is **language-agnostic** - the same structure for Python, Java, JavaScript, etc.

#### 3. Language-Specific Refactorer Pattern

Each language requires a dedicated `RenameRefactorer` class that implements:

```python
class RenameRefactorer(ABC):
    """Base class for all language-specific symbol renaming."""
    
    @abstractmethod
    def is_valid_identifier(self, name: str) -> bool:
        """Validate identifier per language conventions."""
    
    @abstractmethod
    def rename_definition(self, target_type: str, old_name: str, new_name: str) -> bool:
        """Rename the symbol definition in current file."""
    
    @abstractmethod
    def find_references(self, symbol_name: str, project_root: Path) -> list[ReferenceLocation]:
        """Find all references to symbol across project."""
    
    @abstractmethod
    def rename_reference(self, file_path: Path, location: ReferenceLocation, new_name: str) -> bool:
        """Rename a specific reference in a file."""
    
    @abstractmethod
    def get_naming_conventions(self) -> dict[str, str]:
        """Return naming convention rules (snake_case, camelCase, etc.)."""
    
    @abstractmethod
    def get_file_pattern(self) -> str:
        """Return glob pattern for files to scan (e.g., '**/*.py')."""
```

#### 4. Parser Integration Requirements

Each language must have:
- **Primary Parser:** Reliable AST parser for the language
- **Refactorer:** Safe rename implementation for that language
- **Test Coverage:** ≥90% accuracy on representative codebase
- **Performance Target:** <2s per 1,000 files scanned

| Language | Primary Parser | Refactorer | Naming Convention | Status |
|----------|---|---|---|---|
| Python | `ast` stdlib + `tokenize` | `rename_symbol_refactor.py` | snake_case | ✅ |
| JavaScript | `tree-sitter-javascript` | `JavaScriptRefactorer` | camelCase | 🔄 |
| TypeScript | `tree-sitter-typescript` | `TypeScriptRefactorer` | camelCase | 🔄 |
| Java | `tree-sitter-java` | `JavaRefactorer` | camelCase | 📋 |
| Go | `tree-sitter-go` | `GoRefactorer` | camelCase | 📋 |
| C/C++ | `clang` (libclang) | `CppRefactorer` | snake_case/camelCase | 📋 |
| Rust | `tree-sitter-rust` | `RustRefactorer` | snake_case | 📋 |
| Ruby | `tree-sitter-ruby` | `RubyRefactorer` | snake_case | 📋 |

#### 5. Naming Convention Rules by Language

Each language has standard identifier conventions that must be enforced:

| Language | Function Naming | Class Naming | Constant Naming | Validation |
|----------|---|---|---|---|
| Python | `snake_case` | `PascalCase` | `UPPER_SNAKE_CASE` | `[a-z_][a-z0-9_]*` |
| JavaScript | `camelCase` | `PascalCase` | `UPPER_SNAKE_CASE` | `[a-zA-Z$_][a-zA-Z0-9$_]*` |
| TypeScript | `camelCase` | `PascalCase` | `UPPER_SNAKE_CASE` | `[a-zA-Z$_][a-zA-Z0-9$_]*` |
| Java | `camelCase` | `PascalCase` | `UPPER_SNAKE_CASE` | `[a-zA-Z$_][a-zA-Z0-9$_]*` |
| Go | `camelCase` (exported) | `PascalCase` | `const names` | `[a-zA-Z_][a-zA-Z0-9_]*` |
| C/C++ | `snake_case`/`camelCase` | `PascalCase` | `UPPER_SNAKE_CASE` | `[a-zA-Z_][a-zA-Z0-9_]*` |
| Rust | `snake_case` | `PascalCase` | `UPPER_SNAKE_CASE` | `[a-z_][a-z0-9_]*` or `[A-Z][A-Z0-9_]*` |
| Ruby | `snake_case` | `PascalCase` | `UPPER_SNAKE_CASE` | `[a-z_][a-z0-9_]*` or `[A-Z][A-Z0-9_]*` |

**Validation Algorithm:**
```python
def is_valid_identifier(language: str, name: str) -> bool:
    """Validate name against language-specific pattern."""
    if not name:
        return False
    
    patterns = {
        "python": r"^[a-z_][a-z0-9_]*$",
        "javascript": r"^[a-zA-Z$_][a-zA-Z0-9$_]*$",
        "typescript": r"^[a-zA-Z$_][a-zA-Z0-9$_]*$",
        "java": r"^[a-zA-Z_$][a-zA-Z0-9_$]*$",
        "go": r"^[a-zA-Z_][a-zA-Z0-9_]*$",
        "cpp": r"^[a-zA-Z_][a-zA-Z0-9_]*$",
        "rust": r"^[a-z_][a-z0-9_]*$",
        "ruby": r"^[a-z_][a-z0-9_]*$",
    }
    return bool(re.match(patterns.get(language, r"^\w+$"), name))
```

#### 6. Reference Finding Strategy by Language

Different languages require different approaches for finding references:

| Language | Strategy | Import Tracking | Dynamic Refs | String Literals |
|----------|----------|---|---|---|
| Python | AST walk + tokenize | Full support (import/from) | Limited (getattr) | Opt-in |
| JavaScript | tree-sitter queries | Full support (import/export) | Limited (eval) | Opt-in |
| TypeScript | tree-sitter queries | Full support + type imports | Limited (eval) | Opt-in |
| Java | tree-sitter + reflection hints | Full support (import) | Limited (reflection) | Not supported |
| Go | tree-sitter + import analysis | Full support (import) | Limited (reflect) | Not supported |
| C/C++ | Clang AST | Full support (#include) | Not supported | Not supported |
| Rust | tree-sitter + use analysis | Full support (use) | Limited (macro) | Not supported |
| Ruby | tree-sitter + require analysis | Full support (require/load) | High (send/method_missing) | Opt-in |

#### 7. Cross-File Rename Strategy

For Pro/Enterprise cross-file renames:

**Community Tier (Definition-Only):**
- Single file only
- Rename definition + local references
- No import/export updates

**Pro Tier (Project-Scoped):**
- Scan bounded # of files (configurable per language)
- Update imports/exports
- Update local references in other files
- Bounded limits: `max_files_searched`, `max_files_updated`

**Enterprise Tier (Organization-Wide):**
- Unlimited cross-file search and update
- Multi-repository coordination
- Audit trail logging
- Approval workflow integration

#### 8. Polyglot Completion Criteria

The tool is in **polyglot shape** when:

- [ ] **API Unified:** Single `rename_symbol()` call works for all 8 languages
- [ ] **Response Identical:** Same `PatchResultModel` structure for all languages
- [ ] **Language Auto-Detection:** Automatically detects language from file extension
- [ ] **Coverage Equivalent:** Each language ≥90% accuracy on test corpus
- [ ] **Feature Parity:** All languages support same tier features (Community/Pro/Enterprise)
- [ ] **Performance Consistent:** <2s response time for all languages on typical codebase
- [ ] **Naming Convention Enforced:** Each language validates per-convention rules
- [ ] **Import Tracking Complete:** All import/export forms tracked per language
- [ ] **Test Coverage:** ≥95% test coverage across all language implementations
- [ ] **Documentation Complete:** Each language documented with examples and limitations

---

## Research Queries for Future Development

### Foundational Research
| Topic | Query | Purpose |
|-------|-------|---------|
| AST Transformation | "AST-preserving code transformation techniques" | Maintain formatting |
| Rename Semantics | "identifier renaming semantic correctness verification" | Ensure correctness |
| Breaking Changes | "breaking change detection automated refactoring" | Prevent regressions |
| Undo/Redo | "transactional code modifications rollback strategies" | Better recovery |

### Language-Specific Research
| Topic | Query | Purpose |
|-------|-------|---------|
| Python Scoping | "python nonlocal global variable renaming challenges" | Better scope handling |
| JavaScript | "javascript variable hoisting rename complications" | Improve JS support |
| TypeScript | "typescript type alias renaming declaration files" | TS module support |
| Java | "java refactoring reflection-safe renaming" | Reflection handling |

### Advanced Techniques
| Topic | Query | Purpose |
|-------|-------|---------|
| AI-Suggested Names | "machine learning variable naming suggestions code" | Smart name hints |
| Test Impact | "test case selection after refactoring" | Validate renames |
| Documentation Sync | "automated documentation update code changes" | Doc consistency |
| Cross-Repository | "cross-repository refactoring coordination" | Multi-repo renames |

---

## Current Capabilities (v1.0)

### CURRENT STATUS: PYTHON-ONLY

The v1.0 implementation provides complete rename support for **Python only**. Multi-language support is planned for v1.2+.

### Community Tier
- ✅ Rename Python functions by name
- ✅ Rename Python classes by name
- ✅ Rename Python methods in classes
- ✅ Automatic reference updates in same file (tokenize-based)
- ✅ Syntax validation via AST parsing
- ✅ Python identifier validation (snake_case enforcement)
- ❌ **NOT SUPPORTED:** Cross-file renames (single file only)
- ❌ **NOT SUPPORTED:** Import statement updates
- ❌ **NOT SUPPORTED:** Non-Python languages (Java, JavaScript, etc.)

### Pro Tier
- ✅ All Community features
- ✅ Cross-file rename propagation (Python only)
- ✅ Import statement updates (`from X import Y`, `import X as Y`)
- ✅ Documentation string reference updates (docstrings)
- ✅ Limited test file synchronization
- ✅ Backup and rollback support
- ❌ **NOT SUPPORTED:** Non-Python languages

### Enterprise Tier
- ✅ All Pro features
- ✅ Repository-wide renames (Python only)
- ✅ Audit trail for all renames
- ✅ Compliance-checked renames
- ❌ **NOT SUPPORTED:** Multi-repository coordination
- ❌ **NOT SUPPORTED:** Non-Python languages

---

## Current Limitations (v1.0)

---

## Return Model: RenameResult

```python
class RenameResult(BaseModel):
    # Core fields (All Tiers)
    success: bool                           # Whether rename succeeded
    old_name: str                           # Original symbol name
    new_name: str                           # New symbol name
    file_path: str                          # File that was modified
    changes_made: int                       # Number of occurrences renamed
    backup_path: str | None                 # Path to backup file
    
    # Pro Tier
    files_updated: list[str]                # Cross-file renames
    imports_updated: int                    # Import statements changed
    docstrings_updated: int                 # Documentation strings changed
    tests_updated: list[str]                # Test files modified
    
    # Enterprise Tier
    approval_required: bool                 # Whether approval workflow triggered
    approval_status: str | None             # "pending" | "approved" | "rejected"
    compliance_check: ComplianceResult      # Compliance validation result
    audit_id: str | None                    # Audit trail identifier
    
    error: str | None                       # Error message if failed
```

---

## Usage Examples

### Community Tier
```python
result = await rename_symbol(
    file_path="/src/utils.py",
    old_name="process_data",
    new_name="transform_data"
)
# Returns: success, old_name, new_name, changes_made, backup_path
# Single file only
```

### Pro Tier
```python
result = await rename_symbol(
    file_path="/src/utils.py",
    old_name="process_data",
    new_name="transform_data",
    include_imports=True,
    include_tests=True
)
# Additional: files_updated, imports_updated, docstrings_updated, tests_updated
# Cross-file rename propagation
```

### Enterprise Tier
```python
result = await rename_symbol(
    file_path="/src/utils.py",
    old_name="process_data",
    new_name="transform_data",
    require_approval=True,
    compliance_check=True
)
# Additional: approval_required, approval_status, compliance_check, audit_id
# Repository-wide with governance
```

---

## MCP Request/Response Examples

### MCP Request Format

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "mcp_code-scalpel_rename_symbol",
    "arguments": {
      "file_path": "/home/user/project/src/utils.py",
      "old_name": "process_data",
      "new_name": "transform_data"
    }
  },
  "id": 1
}
```

### Community Tier Response

```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "old_name": "process_data",
    "new_name": "transform_data",
    "file_path": "/home/user/project/src/utils.py",
    "changes_made": 4,
    "backup_path": "/home/user/project/src/utils.py.bak",
    "files_updated": null,
    "imports_updated": null,
    "docstrings_updated": null,
    "tests_updated": null,
    "approval_required": null,
    "approval_status": null,
    "compliance_check": null,
    "audit_id": null,
    "error": null
  },
  "id": 1
}
```

### Pro Tier Response

```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "old_name": "process_data",
    "new_name": "transform_data",
    "file_path": "/home/user/project/src/utils.py",
    "changes_made": 12,
    "backup_path": "/home/user/project/.code-scalpel/backups/rename_20251229_143022/",
    "files_updated": [
      "/home/user/project/src/utils.py",
      "/home/user/project/src/handlers.py",
      "/home/user/project/src/api/routes.py",
      "/home/user/project/tests/test_utils.py"
    ],
    "imports_updated": 3,
    "docstrings_updated": 2,
    "tests_updated": [
      "/home/user/project/tests/test_utils.py",
      "/home/user/project/tests/test_handlers.py"
    ],
    "approval_required": null,
    "approval_status": null,
    "compliance_check": null,
    "audit_id": null,
    "error": null
  },
  "id": 1
}
```

### Enterprise Tier Response

```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "old_name": "process_data",
    "new_name": "transform_data",
    "file_path": "/home/user/project/src/utils.py",
    "changes_made": 28,
    "backup_path": "/home/user/project/.code-scalpel/backups/rename_20251229_143022/",
    "files_updated": [
      "/home/user/project/src/utils.py",
      "/home/user/project/src/handlers.py",
      "/home/user/project/src/api/routes.py",
      "/home/user/project/tests/test_utils.py",
      "/home/user/shared-lib/src/compat.py"
    ],
    "imports_updated": 8,
    "docstrings_updated": 5,
    "tests_updated": [
      "/home/user/project/tests/test_utils.py",
      "/home/user/project/tests/test_handlers.py",
      "/home/user/project/tests/integration/test_api.py"
    ],
    "approval_required": true,
    "approval_status": "approved",
    "compliance_check": {
      "passed": true,
      "rules_checked": ["naming-convention", "breaking-change-review"],
      "warnings": [],
      "violations": []
    },
    "audit_id": "audit-rename-20251229-143022-abc123",
    "error": null
  },
  "id": 1
}
```

### Enterprise Tier Response (Approval Pending)

```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": false,
    "old_name": "process_data",
    "new_name": "transform_data",
    "file_path": "/home/user/project/src/utils.py",
    "changes_made": 0,
    "backup_path": null,
    "files_updated": [],
    "imports_updated": 0,
    "docstrings_updated": 0,
    "tests_updated": [],
    "approval_required": true,
    "approval_status": "pending",
    "compliance_check": {
      "passed": false,
      "rules_checked": ["naming-convention", "breaking-change-review"],
      "warnings": ["Symbol is part of public API"],
      "violations": ["Breaking change requires team lead approval"]
    },
    "audit_id": "audit-rename-20251229-143025-def456",
    "error": "Approval required: Breaking change to public API symbol"
  },
  "id": 1
}
```

---

## Integration Points

### Related Tools
| Tool | Relationship |
|------|--------------|
| `get_symbol_references` | Find all references before rename |
| `update_symbol` | Code body changes (rename is name-only) |
| `simulate_refactor` | Preview rename impact |
| `get_call_graph` | Understand callers before rename |

### Export Formats
| Format | Status | Use Case |
|--------|--------|----------|
| **Diff** | ✅ v1.0 | Preview changes |
| **JSON** | ✅ v1.0 | Programmatic results |
| **Patch** | 🔄 v1.1 | Git-compatible patches |

---

## Competitive Analysis

| Tool | Strengths | Weaknesses | Our Differentiation |
|------|-----------|------------|---------------------|
| **IDE Rename** | Fast, integrated | Single IDE | Cross-tool, MCP-native |
| **rope (Python)** | Mature, accurate | Python-only | Multi-language support |
| **jscodeshift** | JS ecosystem | JS/TS only | Unified API |
| **Sourcery** | AI-powered | Limited scope | Broader refactoring |
| **LSP Rename** | Standard | Implementation varies | Consistent behavior |

---

## Roadmap

### v1.1 (Q1 2026): Enhanced Safety & Same-File References

#### Community Tier
- [ ] Same-file reference updates (local variable/call site renames)
- [ ] Preview mode (show changes before applying)
- [ ] Dry-run option (return diff without modifying)
- [ ] Conflict detection (shadowing, name collisions)

#### Pro Tier
- [ ] Documentation string updates (references in docstrings)
- [ ] Type hint updates (forward references)
- [ ] Automated test execution after rename
- [ ] Breaking change detection

#### Enterprise Tier
- [ ] Multi-stage approval workflow
- [ ] Automated rollback on test failure
- [ ] Risk scoring for renames
- [ ] Audit trail logging

### v1.2 (Q2 2026): Language Expansion - Polyglot Foundation (JavaScript, TypeScript, Java)

**Effort:** 24 hours | **Tests:** 18 new + 15 existing = 33 total  
**Scope:** Add JavaScript, TypeScript, and Java support to establish polyglot foundation

#### JavaScript Support
- [ ] JavaScript identifier validation (camelCase for functions, PascalCase for classes)
- [ ] Function and variable renaming using tree-sitter-javascript
- [ ] Export/import statement updates (`export`, `export default`, `import`)
- [ ] CommonJS module tracking (`module.exports`, `require()`)
- [ ] Method and property renaming in objects and classes
- [ ] Test file detection (`.test.js`, `.spec.js`, `__tests__/`)

**Files:**
- `src/code_scalpel/surgery/refactorers/javascript_refactorer.py` (NEW)
- Tests: `test_javascript_rename.py` (4 tests)

#### TypeScript Support
- [ ] TypeScript identifier validation (camelCase/PascalCase rules)
- [ ] Function, class, and interface renaming
- [ ] Type alias and enum renaming
- [ ] Import/export statement updates (including type imports)
- [ ] Declaration file (.d.ts) tracking
- [ ] Generic type parameter renaming
- [ ] Test file detection (`.test.ts`, `.spec.ts`)

**Files:**
- `src/code_scalpel/surgery/refactorers/typescript_refactorer.py` (NEW)
- Tests: `test_typescript_rename.py` (4 tests)

#### Java Support
- [ ] Java identifier validation (camelCase for methods, PascalCase for classes)
- [ ] Method and class renaming using tree-sitter-java
- [ ] Import statement updates (`import`, `import static`)
- [ ] Package-level scope handling
- [ ] Constructor renaming
- [ ] Inner class renaming
- [ ] Test file detection (`*Test.java`, `*Tests.java`)

**Files:**
- `src/code_scalpel/surgery/refactorers/java_refactorer.py` (NEW)
- Tests: `test_java_rename.py` (4 tests)

#### Core Refactorer Infrastructure
- [ ] `RenameRefactorer` abstract base class
- [ ] Language auto-detection from file extension
- [ ] Unified refactorer factory pattern
- [ ] Per-language naming convention validation
- [ ] Per-language file pattern detection

**Files:**
- `src/code_scalpel/surgery/refactorers/__init__.py` (NEW)
- `src/code_scalpel/surgery/refactorer_base.py` (NEW)
- `src/code_scalpel/surgery/refactorer_factory.py` (NEW)

#### Test Coverage (Net New)
- `test_javascript_rename` (4 tests) - JS function/class/export renaming
- `test_typescript_rename` (4 tests) - TS type alias and interface renaming
- `test_java_rename` (4 tests) - Java method/class/import renaming
- `test_language_auto_detection` (2 tests) - File extension detection
- `test_polyglot_unified_response` (2 tests) - Same response model for all languages
- `test_naming_conventions_enforced` (2 tests) - Per-language validation

#### Success Criteria for v1.2
- [x] JavaScript, TypeScript, Java symbol finding working
- [x] Import/export tracking accurate per language (>95% precision)
- [x] Per-language naming conventions enforced
- [x] All reference types found (definitions, calls, imports, exports)
- [x] All 18 new tests passing + zero regressions in existing tests
- [x] <2s response time on 1,000-file codebase per language
- [x] Same `PatchResultModel` structure returned for all languages

### v1.3 (Q3 2026): Language Expansion & Advanced Features (Go, C/C++, Rust, Ruby)

**Effort:** 32 hours | **Tests:** 18 new + 33 existing = 51 total  
**Scope:** Add remaining languages (Go, C/C++, Rust, Ruby) to achieve full polyglot shape

#### Go Support
- [ ] Go identifier validation (camelCase for exported, lowercase for unexported)
- [ ] Function, method, and type renaming using tree-sitter-go
- [ ] Import statement updates (`import`, `import "package as alias"`)
- [ ] Package-level scope handling
- [ ] Struct field renaming
- [ ] Interface method renaming
- [ ] Test file detection (`*_test.go`)

**Files:**
- `src/code_scalpel/surgery/refactorers/go_refactorer.py` (NEW)
- Tests: `test_go_rename.py` (4 tests)

#### C/C++ Support
- [ ] C/C++ identifier validation (snake_case or camelCase)
- [ ] Function and class renaming using clang/libclang
- [ ] Include directive handling (`#include "file.h"`, `#include <system>`)
- [ ] Macro renaming with expansion handling
- [ ] Type definition renaming (typedef, struct, class)
- [ ] Namespace scope handling (C++)
- [ ] Template parameter renaming
- [ ] Header/source file coordination

**Files:**
- `src/code_scalpel/surgery/refactorers/cpp_refactorer.py` (NEW)
- Tests: `test_cpp_rename.py` (4 tests)

#### Rust Support
- [ ] Rust identifier validation (snake_case for functions, PascalCase for types)
- [ ] Function, struct, and trait renaming using tree-sitter-rust
- [ ] Use statement updates (`use`, `use as`)
- [ ] Module and submodule scope handling
- [ ] Generic type parameter renaming
- [ ] Trait method renaming
- [ ] Macro invocation renaming
- [ ] Test module detection (`#[cfg(test)]`)

**Files:**
- `src/code_scalpel/surgery/refactorers/rust_refactorer.py` (NEW)
- Tests: `test_rust_rename.py` (4 tests)

#### Ruby Support
- [ ] Ruby identifier validation (snake_case for methods/variables, PascalCase for classes)
- [ ] Method and class renaming using tree-sitter-ruby
- [ ] Require statement updates (`require`, `require_relative`)
- [ ] Module and nested class scope handling
- [ ] Instance variable renaming (`@var`, `@@var`)
- [ ] Dynamic method handling (attr_accessor, define_method)
- [ ] Test file detection (`*_test.rb`, `*_spec.rb`)

**Files:**
- `src/code_scalpel/surgery/refactorers/ruby_refactorer.py` (NEW)
- Tests: `test_ruby_rename.py` (4 tests)

#### Advanced Features (All Languages)
- [ ] String literal analysis for references (opt-in per tier)
- [ ] Configuration file updates (JSON, YAML config file references)
- [ ] Cross-language FFI tracking (Python ↔ C/C++)
- [ ] Breaking change detection (public API renames)
- [ ] Test impact analysis (which tests to run post-rename)

**Files:**
- `src/code_scalpel/surgery/renamer_advanced.py` (NEW)
- Tests: `test_advanced_rename_features.py` (6 tests)

#### Test Coverage (Net New)
- `test_go_rename` (4 tests) - Go function/type/import renaming
- `test_cpp_rename` (4 tests) - C/C++ function/class/include renaming
- `test_rust_rename` (4 tests) - Rust function/struct/use renaming
- `test_ruby_rename` (4 tests) - Ruby method/class/require renaming
- `test_string_literal_detection` (2 tests) - String-based reference detection
- `test_config_file_updates` (2 tests) - Configuration file updating
- `test_polyglot_unified_api` (2 tests) - Unified API across 8 languages

#### Polyglot Shape Completion Checklist

**API Unification:**
- [ ] Single `rename_symbol()` supports all 8 languages
- [ ] Language auto-detection from file extension
- [ ] Identical `PatchResultModel` response for all languages
- [ ] Feature parity across Community/Pro/Enterprise tiers

**Implementation:**
- [ ] 8 language-specific `RenameRefactorer` classes
- [ ] 8 corresponding parsers integrated (ast, tree-sitter, clang, etc.)
- [ ] Unified refactorer factory for auto-detection
- [ ] Per-language naming convention validation
- [ ] Per-language identifier validation
- [ ] Per-language import/export tracking

**Quality:**
- [ ] ≥90% accuracy per language on test corpus
- [ ] <2s response time on 1,000-file codebase
- [ ] ≥95% test coverage across all implementations
- [ ] Zero breaking changes from v1.0/v1.2 API

**Documentation:**
- [ ] Language support matrix in README
- [ ] Per-language examples and limitations
- [ ] Naming convention guide per language
- [ ] Import/export behavior per language
- [ ] Scope handling per language

#### Success Criteria for v1.3
- [x] All 8 languages supported with ≥90% accuracy
- [x] Unified API and response model across all languages
- [x] All reference types supported per language capability
- [x] All naming conventions enforced per language
- [x] <2s response time for all languages
- [x] All 18 new tests passing + zero regressions
- [x] Polyglot shape achieved

#### Polyglot Shape Validation

After completing v1.3, run the polyglot validation script:

```python
# Pseudo-code for validation
async def validate_polyglot_shape():
    """Verify tool meets polyglot shape criteria."""
    languages = ["python", "java", "javascript", "typescript", "go", "cpp", "rust", "ruby"]
    
    for lang in languages:
        # 1. Create test codebase in language
        # 2. Call rename_symbol() on known symbols
        # 3. Verify response structure matches template
        # 4. Verify accuracy ≥90%
        # 5. Verify performance <2s
        # 6. Verify naming conventions enforced
        # 7. Verify cross-file renames work
        
    # All checks pass = Polyglot shape achieved
    return all_checks_passed
```

### v1.4 (Q4 2026): Integration & Advanced Workflows

#### Community Tier
- [ ] IDE integration
- [ ] Git commit automation
- [ ] Pre-commit hook support

#### Pro Tier
- [ ] Continuous rename monitoring
- [ ] Automated PR creation
- [ ] Slack/Teams notifications

#### Enterprise Tier
- [ ] ServiceNow change management
- [ ] CMDB synchronization
- [ ] Compliance gate enforcement

---

## Known Issues & Limitations

### Current Limitations
- **Dynamic references:** Cannot update string-based references
- **External usage:** Cannot update external package references
- **Complex generics:** Some complex type parameters may need manual update

### Planned Fixes
- v1.1: String literal analysis (opt-in)
- v1.2: External package scanning (Enterprise)
- v1.3: Better generic handling

---

## Success Metrics

### Performance Targets
- **Rename time:** <1s for single file
- **Accuracy:** >99% correct reference updates
- **Success rate:** >98% successful renames

### Adoption Metrics
- **Usage:** 50K+ renames per month by Q4 2026
- **Time saved:** Average 30 minutes per rename vs manual

---

## Dependencies

### Internal Dependencies
- `ast_tools/transformer.py` - AST transformation
- `ast_tools/validator.py` - Validation
- `ast_tools/call_graph.py` - Reference finding

### External Dependencies
- None

---

## Breaking Changes

None planned for v1.x series.

**API Stability Promise:**
- Tool signature stable
- Backup behavior guaranteed
- Validation always performed

---

**Last Updated:** December 30, 2025  
**Next Review:** March 31, 2026
