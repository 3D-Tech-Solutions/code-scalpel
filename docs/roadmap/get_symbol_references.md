# get_symbol_references Tool Roadmap

**Tool Name:** `get_symbol_references`  
**Tool Version:** v1.0  
**Code Scalpel Version:** v3.3.0 
**Current Status:** Stable  
**Primary Module:** `src/code_scalpel/mcp/server.py`  
**Tier Availability:** All tiers (Community, Pro, Enterprise)

---

## Configuration Files

| File | Purpose |
|------|---------|
| `src/code_scalpel/licensing/features.py` | Tier capability definitions |
| `.code-scalpel/limits.toml` | Numeric limits (max_files_searched, max_references) |
| `.code-scalpel/response_config.json` | Output filtering |
| `CODEOWNERS` | Ownership attribution (Enterprise) |

---

## Overview

The `get_symbol_references` tool finds all references to a symbol (function, class, variable) across the project for safe refactoring and impact analysis.

**Why AI Agents Need This:**
- **Safe refactoring:** Know all call sites before changing signatures
- **Impact analysis:** Understand blast radius of changes
- **No hallucination:** Real references from AST parsing, not guessed
- **Risk-aware changes:** Enterprise risk scoring prevents blind modifications
- **Team coordination:** CODEOWNERS integration identifies stakeholders

---

## Research Queries for Future Development

### Foundational Research
| Topic | Query | Purpose |
|-------|-------|---------|
| Name Resolution | "identifier resolution algorithms programming languages" | Improve accuracy |
| Scope Analysis | "lexical scoping static analysis implementation" | Better shadowing detection |
| Incremental Parsing | "incremental symbol table construction IDE" | Real-time updates |
| Cross-Language | "cross-language reference finding polyglot projects" | Multi-lang support |

### Language-Specific Research
| Topic | Query | Purpose |
|-------|-------|---------|
| Python Imports | "python import resolution dynamic vs static" | Better import handling |
| JavaScript | "javascript hoisting symbol resolution challenges" | Improve JS accuracy |
| TypeScript | "typescript declaration merging reference finding" | TS module support |
| Dynamic Languages | "dynamic typing static reference analysis approaches" | Ruby/Python/JS |

### Advanced Techniques
| Topic | Query | Purpose |
|-------|-------|---------|
| Type-Aware | "type-directed reference finding static analysis" | Precision improvement |
| ML Enhancement | "machine learning identifier resolution code" | AI-assisted finding |
| Change Impact | "change impact analysis prediction models software" | Better risk scoring |
| Ownership | "code ownership prediction machine learning" | Auto-owner detection |

---

## Current Capabilities (v1.0)

### Community Tier (World-Class Base Features)
- ✅ Find definition location (`definition_location`)
- ✅ Find all usage references (`ast_based_find_usages`)
- ✅ Exact reference matching (`exact_reference_matching`)
- ✅ Comment/string exclusion (`comment_string_exclusion`)
- ✅ Line number, column, and context snippet
- ✅ Test file detection
- ✅ Supports Python (.py files)

**Capability Keys:** `ast_based_find_usages`, `exact_reference_matching`, `comment_string_exclusion`, `definition_location`

**Limits (from limits.toml):**
- `max_files_searched: 10`
- `max_references: 50`

### Pro Tier (Reference Intelligence)
- ✅ All Community features (unlimited)
- ✅ **Project-wide search** (`project_wide_search`)
- ✅ **Reference categorization** (`usage_categorization`)
  - definition, import, call, read, write, method_call
  - instance_method_call, class_method_call, static_method_call
  - decorator, type_annotation, first_assignment, reassignment
- ✅ **Read/write classification** (`read_write_classification`)
- ✅ **Import classification** (`import_classification`)
- ✅ **Scope filtering** (`scope_filtering`) - limit to path prefix
- ✅ **Test file filtering** (`test_file_filtering`) - include/exclude tests
- ✅ Category counts in response

**Capability Keys:** All Community + `project_wide_search`, `usage_categorization`, `read_write_classification`, `import_classification`, `scope_filtering`, `test_file_filtering`

**Limits:** Unlimited (no caps on files or references)

### Enterprise Tier (Impact & Ownership)
- ✅ All Pro features
- ✅ **Impact analysis** (`impact_analysis`)
  - `risk_score`: Weighted 0-100 score
  - `risk_factors`: List of contributing factors
  - `blast_radius`: Number of unique files affected
  - `test_coverage_ratio`: Ratio of references in test files
  - `complexity_hotspots`: High-complexity files with references
  - `impact_mermaid`: Mermaid diagram of reference distribution
- ✅ **CODEOWNERS integration** (`codeowners_integration`)
  - `owners`: Per-reference owner attribution
  - `owner_counts`: Counts by owner
  - `codeowners_coverage`: Ratio of owned references
- ✅ **Change risk assessment** (`change_risk_assessment`)
  - `change_risk`: "low" | "medium" | "high"

**Capability Keys:** All Pro + `impact_analysis`, `codeowners_integration`, `ownership_attribution`, `change_risk_assessment`

**Limits:** Unlimited

---

## Return Model: SymbolReferencesResult

```python
class SymbolReferencesResult(BaseModel):
    # Core fields (All Tiers)
    success: bool                           # Whether search succeeded
    symbol_name: str                        # Name of the searched symbol
    definition_file: str | None             # File where symbol is defined
    definition_line: int | None             # Line where symbol is defined
    references: list[SymbolReference]       # References found (may be truncated)
    total_references: int                   # Total before truncation
    files_scanned: int                      # Number of files scanned
    total_files: int                        # Total candidate files
    files_truncated: bool                   # Whether file scan was truncated
    file_truncation_warning: str | None     # Warning if truncated
    references_truncated: bool              # Whether references were truncated
    truncation_warning: str | None          # Warning if truncated
    
    # Pro Tier
    category_counts: dict[str, int] | None  # Counts by reference category
    
    # Enterprise Tier
    owner_counts: dict[str, int] | None     # Counts by CODEOWNERS owner
    change_risk: str | None                 # "low" | "medium" | "high"
    risk_score: int | None                  # 0-100 weighted score
    risk_factors: list[str] | None          # Contributing factors
    blast_radius: int | None                # Unique files affected
    test_coverage_ratio: float | None       # References in test files
    complexity_hotspots: list[str] | None   # High-complexity files
    impact_mermaid: str | None              # Mermaid diagram
    codeowners_coverage: float | None       # Ratio of owned references
```

### SymbolReference Model

```python
class SymbolReference(BaseModel):
    file: str                               # File path
    line: int                               # Line number
    column: int                             # Column number
    context: str                            # Code snippet
    is_definition: bool                     # Whether this is the definition
    reference_type: str | None              # Category (Pro+)
    is_test_file: bool                      # Whether in test file
    owners: list[str] | None                # CODEOWNERS (Enterprise)
```

---

## Usage Examples

### Community Tier
```python
result = await get_symbol_references("process_order")
# Returns: definition_file, definition_line, references (max 50),
#          files_scanned (max 10), truncation info
```

### Pro Tier
```python
result = await get_symbol_references(
    "process_order",
    scope_prefix="src/services/",  # Only search in this path
    include_tests=False             # Exclude test files
)
# Additional: category_counts populated
# e.g., {"call": 15, "import": 3, "read": 7, "definition": 1}
```

### Enterprise Tier
```python
result = await get_symbol_references("process_order")
# Additional:
# - risk_score: 45
# - risk_factors: ["Multiple files affected (12 files)", "Moderate test coverage (28.5%)"]
# - blast_radius: 12
# - change_risk: "medium"
# - owner_counts: {"@backend-team": 8, "@api-team": 4}
# - impact_mermaid: "graph TD\n    SYMBOL[\"process_order\"]\n    ..."
```

---

## Response Configuration

Output verbosity is controlled by `.code-scalpel/response_config.json`:

```json
{
  "get_symbol_references": {
    "profile": "minimal",
    "exclude_fields": ["search_metadata", "file_scan_order"]
  }
}
```

**Limits Configuration:** Numerical limits are defined in `.code-scalpel/limits.toml`:

```toml
[community.get_symbol_references]
max_files_searched = 10
max_references = 50

[pro.get_symbol_references]
# Unlimited - omit keys

[enterprise.get_symbol_references]
# Unlimited - omit keys
```

---

## MCP Request/Response Examples

### MCP Request Format

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "mcp_code-scalpel_get_symbol_references",
    "arguments": {
      "symbol_name": "process_order",
      "project_root": "/home/user/my-project"
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
    "symbol_name": "process_order",
    "definition_file": "services/order.py",
    "definition_line": 45,
    "references": [
      {
        "file": "services/order.py",
        "line": 45,
        "column": 4,
        "context": "def process_order(order_data: dict) -> Order:",
        "is_definition": true,
        "reference_type": null,
        "is_test_file": false,
        "owners": null
      },
      {
        "file": "handlers/api.py",
        "line": 78,
        "column": 12,
        "context": "    result = process_order(validated_data)",
        "is_definition": false,
        "reference_type": null,
        "is_test_file": false,
        "owners": null
      },
      {
        "file": "tests/test_order.py",
        "line": 23,
        "column": 8,
        "context": "        process_order(mock_data)",
        "is_definition": false,
        "reference_type": null,
        "is_test_file": true,
        "owners": null
      }
    ],
    "total_references": 35,
    "files_scanned": 10,
    "total_files": 125,
    "files_truncated": true,
    "file_truncation_warning": "Community tier: scanned 10/125 files (upgrade to Pro for full search)",
    "references_truncated": false,
    "truncation_warning": null,
    "category_counts": null,
    "owner_counts": null,
    "change_risk": null,
    "risk_score": null,
    "risk_factors": null,
    "blast_radius": null,
    "test_coverage_ratio": null,
    "complexity_hotspots": null,
    "impact_mermaid": null,
    "codeowners_coverage": null
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
    "symbol_name": "process_order",
    "definition_file": "services/order.py",
    "definition_line": 45,
    "references": [
      {
        "file": "services/order.py",
        "line": 45,
        "column": 4,
        "context": "def process_order(order_data: dict) -> Order:",
        "is_definition": true,
        "reference_type": "definition",
        "is_test_file": false,
        "owners": null
      },
      {
        "file": "services/__init__.py",
        "line": 5,
        "column": 0,
        "context": "from .order import process_order",
        "is_definition": false,
        "reference_type": "import",
        "is_test_file": false,
        "owners": null
      },
      {
        "file": "handlers/api.py",
        "line": 78,
        "column": 12,
        "context": "    result = process_order(validated_data)",
        "is_definition": false,
        "reference_type": "call",
        "is_test_file": false,
        "owners": null
      }
    ],
    "total_references": 35,
    "files_scanned": 125,
    "total_files": 125,
    "files_truncated": false,
    "file_truncation_warning": null,
    "references_truncated": false,
    "truncation_warning": null,
    "category_counts": {
      "definition": 1,
      "import": 8,
      "call": 18,
      "read": 3,
      "type_annotation": 5
    },
    "owner_counts": null,
    "change_risk": null,
    "risk_score": null,
    "risk_factors": null,
    "blast_radius": null,
    "test_coverage_ratio": null,
    "complexity_hotspots": null,
    "impact_mermaid": null,
    "codeowners_coverage": null
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
    "symbol_name": "process_order",
    "definition_file": "services/order.py",
    "definition_line": 45,
    "references": [
      {
        "file": "services/order.py",
        "line": 45,
        "column": 4,
        "context": "def process_order(order_data: dict) -> Order:",
        "is_definition": true,
        "reference_type": "definition",
        "is_test_file": false,
        "owners": ["@backend-team", "@alice"]
      },
      {
        "file": "handlers/api.py",
        "line": 78,
        "column": 12,
        "context": "    result = process_order(validated_data)",
        "is_definition": false,
        "reference_type": "call",
        "is_test_file": false,
        "owners": ["@api-team"]
      }
    ],
    "total_references": 35,
    "files_scanned": 125,
    "total_files": 125,
    "files_truncated": false,
    "file_truncation_warning": null,
    "references_truncated": false,
    "truncation_warning": null,
    "category_counts": {
      "definition": 1,
      "import": 8,
      "call": 18,
      "read": 3,
      "type_annotation": 5
    },
    "owner_counts": {
      "@backend-team": 15,
      "@api-team": 12,
      "@test-team": 8
    },
    "change_risk": "medium",
    "risk_score": 45,
    "risk_factors": [
      "Multiple files affected (12 files)",
      "Moderate test coverage (28.5%)",
      "High-complexity callers detected"
    ],
    "blast_radius": 12,
    "test_coverage_ratio": 0.285,
    "complexity_hotspots": [
      "handlers/api.py",
      "services/order.py"
    ],
    "impact_mermaid": "graph TD\n    subgraph Impact\n        SYMBOL[\"process_order\"]\n        F1[\"handlers/api.py (3 refs)\"]\n        F2[\"services/order.py (2 refs)\"]\n        F3[\"tests/ (10 refs)\"]\n        SYMBOL --> F1\n        SYMBOL --> F2\n        SYMBOL --> F3\n    end",
    "codeowners_coverage": 0.92
  },
  "id": 1
}
```

---

## Polyglot Architecture Definition

**Polyglot Shape** means the `get_symbol_references` tool provides **linguistically-agnostic symbol finding** with a unified API across all supported languages.

### Requirements for Polyglot Shape

#### 1. Language Support Matrix
The tool must support all major programming languages with consistent behavior:

| Language | Community | Pro | Enterprise | Status |
|----------|-----------|-----|------------|--------|
| Python | ✅ | ✅ | ✅ | v1.0 |
| Java | 🔄 | 🔄 | 🔄 | v1.1 (Q1 2026) |
| JavaScript | 🔄 | 🔄 | 🔄 | v1.2 (Q2 2026) |
| TypeScript | 🔄 | 🔄 | 🔄 | v1.2 (Q2 2026) |
| Go | 📋 | 📋 | 📋 | v1.4 (Q4 2026) |
| C/C++ | 📋 | 📋 | 📋 | v1.4 (Q4 2026) |
| Rust | 📋 | 📋 | 📋 | v1.4 (Q4 2026) |
| Ruby | 📋 | 📋 | 📋 | v1.4 (Q4 2026) |

**Legend:** ✅ Stable | 🔄 In Development | 📋 Planned

#### 2. Unified API Contract

All language implementations must conform to this interface:

```python
async def get_symbol_references(
    symbol_name: str,
    project_root: str | None = None,
    scope_prefix: str | None = None,        # Language-agnostic path filtering
    include_tests: bool = True,              # Language-agnostic test detection
    ctx: Context | None = None,
) -> SymbolReferencesResult:
    """
    Find all references to a symbol across the project.
    
    Returns identical response structure regardless of language.
    """
```

**Key Constraint:** The response model `SymbolReferencesResult` is **language-agnostic** - the same structure for Python, Java, JavaScript, etc.

#### 3. Language-Specific Implementation Pattern

Each language requires a dedicated `SymbolExtractor` class in `src/code_scalpel/ast_tools/symbol_extractors.py`:

```python
class LanguageSymbolExtractor(ABC):
    """Base class for all language-specific symbol extraction."""
    
    @abstractmethod
    def find_definition(self, symbol_name: str, file_path: str) -> SymbolDefinition | None:
        """Find where symbol is defined in a single file."""
    
    @abstractmethod
    def find_references(self, symbol_name: str, file_path: str) -> list[SymbolReference]:
        """Find all references to symbol in a single file."""
    
    @abstractmethod
    def categorize_reference(self, ref: SymbolReference) -> str:
        """Classify reference type (call, import, definition, etc.)."""
    
    @abstractmethod
    def is_test_file(self, file_path: str) -> bool:
        """Detect if file is a test file by convention."""
    
    @abstractmethod
    def get_file_pattern(self) -> str:
        """Return glob pattern for files to scan (e.g., '**/*.py')."""
```

#### 4. Parser Integration Requirements

Each language must have:
- **Primary Parser:** Reliable AST parser for the language
- **Fallback Parser:** Text-based parser for edge cases
- **Test Coverage:** ≥90% accuracy on representative codebase
- **Performance Target:** <1s per 100 files scanned

| Language | Primary Parser | Fallback | Status |
|----------|---|---|---|
| Python | `ast` stdlib | `ast_tools/python_analyzer.py` | ✅ |
| Java | `javalang` | regex-based | 🔄 |
| JavaScript | `esprima`/`acorn` | regex-based | 🔄 |
| TypeScript | `typescript` (via node) | regex-based | 🔄 |
| Go | `go/parser` (via cgo) | regex-based | 📋 |
| C/C++ | `clang` (via libclang) | regex-based | 📋 |
| Rust | `syn` (via wasm) | regex-based | 📋 |
| Ruby | `parser` gem (via subprocess) | regex-based | 📋 |

#### 5. Scope Filtering by Language

Scope filtering must be language-aware:

```python
# Python: Module path format
scope_prefix = "services"           # Expands to services/**/*.py
scope_prefix = "services.order"     # Expands to services/order/*.py

# Java: Package format
scope_prefix = "com.example"        # Expands to com/example/**/*.java
scope_prefix = "com.example.order"  # Expands to com/example/order/*.java

# JavaScript/TypeScript: Path format
scope_prefix = "src/services"       # Expands to src/services/**/*.{js,ts,jsx,tsx}

# Go: Import path format
scope_prefix = "github.com/user/pkg"  # Expands to matching go.mod imports

# C/C++: Include path or directory
scope_prefix = "src/core"           # Expands to src/core/**/*.{c,cpp,h,hpp}

# Rust: Module path format
scope_prefix = "crate::services"    # Expands to src/services/*.rs

# Ruby: Require path format
scope_prefix = "lib/services"       # Expands to lib/services/**/*.rb
```

#### 6. Test File Detection by Language

Each language has standard test file conventions:

| Language | Test Patterns | Directory Patterns |
|----------|---|---|
| Python | `test_*.py`, `*_test.py` | `tests/`, `test/` |
| Java | `*Test.java`, `*Tests.java` | `src/test/`, `src/test/java/` |
| JavaScript | `*.test.js`, `*.spec.js` | `__tests__/`, `test/` |
| TypeScript | `*.test.ts`, `*.spec.ts` | `__tests__/`, `test/` |
| Go | `*_test.go` | `*_test.go` (co-located) |
| C/C++ | `*_test.c`, `test_*.cpp` | `test/`, `tests/`, `gtest/` |
| Rust | `#[cfg(test)]`, `mod tests` | `tests/`, `src/*/tests` |
| Ruby | `*_test.rb`, `*_spec.rb` | `test/`, `spec/` |

#### 7. Reference Type Categorization by Language

Supported categories vary by language capability:

**All Languages:**
- `definition` - Where symbol is defined
- `import` - Module/package import statement
- `call` - Function/method invocation

**With Method Support (Python, Java, JavaScript, TypeScript, Go, C++, Rust, Ruby):**
- `method_call` - Generic method invocation
- `instance_method_call` - Method on instance
- `class_method_call` - Class/static method
- `static_method_call` - Explicitly static method

**With OOP Support (Java, JavaScript, TypeScript, C++, Rust, Ruby):**
- `constructor_call` - New instance creation
- `property_access` - Field or property access
- `field_access` - Direct field access

**Advanced (TypeScript, Go, C++, Rust):**
- `type_annotation` - Used in type declaration
- `type_alias` - Alias for another type
- `interface_implementation` - Implements interface
- `trait_implementation` - Implements trait

**Data Access (All):**
- `read` - Variable/field read access
- `write` - Variable/field write assignment

**Declaration (All):**
- `first_assignment` - Initial declaration with assignment
- `reassignment` - Subsequent assignment
- `parameter` - Function/method parameter
- `return_type` - Function return type
- `decorator` - Used as decorator/annotation

#### 8. Polyglot Completion Criteria

The tool is in **polyglot shape** when:

- [ ] **API Unified:** Single `get_symbol_references()` call works for all 8 languages
- [ ] **Response Identical:** Same `SymbolReferencesResult` structure for all languages
- [ ] **Language Auto-Detection:** Automatically detects language from file extension
- [ ] **Coverage Equivalent:** Each language ≥90% accuracy on test corpus
- [ ] **Feature Parity:** All languages support same tier features (Community/Pro/Enterprise)
- [ ] **Performance Consistent:** <2s response time for all languages on typical codebase
- [ ] **Test Coverage:** ≥95% test coverage across all language implementations
- [ ] **Documentation Complete:** Each language documented with examples and limitations

---

## Roadmap

### v1.1 (Q1 2026): Community Tier - Multi-Language Foundation (Python + Java)

**Effort:** 14 hours | **Tests:** 5 new + 22 existing = 27 total  
**Scope:** Add Java support with language auto-detection

#### Core Requirements
- [x] ~~Test file detection~~ (Done in v1.0)
- [ ] **Language auto-detection** from file extension (.py, .java)
- [ ] **Java symbol finding** using java_parsers_javalang.py
  - [ ] Method definitions (static, instance, constructors)
  - [ ] Class definitions and field access
  - [ ] Annotation and enum constant tracking
- [ ] **File walking** for both Python and Java
- [ ] **Community tier limits enforcement**
  - Max files: 100 files per language
  - Max references: 50 references
  - Timeout: 30 seconds

#### Implementation Files
- `src/code_scalpel/mcp/server.py` - Extend `get_symbol_references()` signature
- `src/code_scalpel/ast_tools/symbol_extractors.py` (NEW) - Language-specific extractors
- `src/code_scalpel/code_parsers/factory.py` - Ensure Java parser integration

#### Test Coverage
- `test_community_python_basic_finding` - Existing Python functionality
- `test_community_java_basic_finding` - New Java support
- `test_community_file_limit_100` - File truncation
- `test_community_reference_limit_50` - Reference truncation
- `test_community_unsupported_language` - Error handling

#### Success Criteria
- [x] Finds Python and Java symbols with same accuracy
- [x] Community tier limits enforced (100 files, 50 refs)
- [x] All 5 new Community tests passing
- [x] Zero performance regression from v1.0

---

### v1.2 (Q2 2026): Pro Tier - Reference Intelligence (JavaScript, TypeScript, Enhanced Filtering)

**Effort:** 20 hours | **Tests:** 17 new + 27 existing = 44 total  
**Scope:** Add JavaScript/TypeScript + reference categorization and filtering

#### Core Requirements
- [ ] **JavaScript/TypeScript support**
  - [ ] Function and class declarations
  - [ ] Arrow functions and const declarations
  - [ ] React component detection
  - [ ] Export/import statement tracking
  - [ ] Type annotation references (TypeScript)
- [ ] **Reference categorization** (Pro+)
  - definition, import, call, read, write, method_call
  - instance_method_call, class_method_call, static_method_call
  - decorator, type_annotation, first_assignment, reassignment
- [ ] **Read/write classification** for variables
- [ ] **Import classification** (default/named/namespace)
- [ ] **Scope filtering** - limit to path prefix
  - Python: module/path format ("services" → services/*.py)
  - Java: package format ("com.example" → com/example/*.java)
  - JS/TS: path format ("src/components" → src/components/**/*.{js,ts,jsx,tsx})
- [ ] **Test file filtering**
  - Python: test_*.py, *_test.py, /tests/ directory
  - Java: *Test.java, *Tests.java, src/test/ directory
  - JS/TS: *.test.{js,ts}, *.spec.{js,ts}, __tests__/ directory
- [ ] **Pro tier limits relaxed**
  - Max files: 5,000
  - Max references: 10,000
  - Timeout: 120 seconds

#### Implementation Files
- `src/code_scalpel/mcp/server.py` - Add scope_prefix and include_tests parameters
- `src/code_scalpel/ast_tools/symbol_extractors.py` - JavaScriptSymbolExtractor, TypeScriptSymbolExtractor
- `src/code_scalpel/code_parsers/factory.py` - Ensure JavaScript/TypeScript parser integration

#### Parameter Additions
```python
async def get_symbol_references(
    symbol_name: str,
    project_root: str | None = None,
    scope_prefix: str | None = None,        # NEW: Filter to path prefix
    include_tests: bool = True,              # NEW: Include/exclude test files
    ctx: Context | None = None,
) -> SymbolReferencesResult:
```

#### Response Model Additions
```python
class SymbolReferencesResult(BaseModel):
    # ... existing fields ...
    category_counts: dict[str, int] | None  # {"call": 15, "import": 3}
    reference_categories: list[str] | None  # Available categories for filter
```

#### Test Coverage (Net New)
- `test_pro_javascript_support` (2 tests) - Function/class finding in JS
- `test_pro_typescript_support` (2 tests) - Type annotation tracking
- `test_pro_reference_categorization` (3 tests) - Category accuracy
- `test_pro_read_write_classification` (2 tests) - Read vs write tracking
- `test_pro_scope_filtering_python` (2 tests) - Module-based filtering
- `test_pro_scope_filtering_java` (2 tests) - Package-based filtering
- `test_pro_test_file_filtering` (2 tests) - Include/exclude test files
- `test_pro_limits_relaxed` (2 tests) - Verify 5K files / 10K references

#### Success Criteria
- [x] JavaScript and TypeScript symbol finding working
- [x] Reference categorization accurate (>95% precision)
- [x] Scope filtering working for all languages
- [x] All 17 Pro tier tests passing
- [x] No regression in Community tier tests

---

### v1.3 (Q3 2026): Enterprise Tier - Impact Analysis & Ownership

**Effort:** 16 hours | **Tests:** 13 new + 44 existing = 57 total  
**Scope:** CODEOWNERS integration, impact analysis, risk scoring, dependency mapping

#### Core Requirements
- [ ] **CODEOWNERS integration**
  - [ ] Parse CODEOWNERS from standard locations (root, .github/, docs/)
  - [ ] GitHub CODEOWNERS format support
  - [ ] Glob pattern matching (*, **, ?)
  - [ ] Ownership confidence scoring (0.0-1.0)
  - [ ] Ownership attribution per reference
- [ ] **Impact analysis**
  - [ ] Estimate affected files count
  - [ ] Calculate file complexity per reference
  - [ ] Effort estimation ("Low", "Medium", "High")
  - [ ] Risk level classification
  - [ ] Identify high-complexity callers
- [ ] **Change risk assessment**
  - [ ] Risk score calculation (0-100)
  - [ ] Risk factor enumeration
  - [ ] Public API/core library detection
- [ ] **Dependency mapping**
  - [ ] Build import dependency graphs per language
  - [ ] Transitive dependency detection
  - [ ] Reference count per dependent
- [ ] **Cyclic dependency detection**
  - [ ] Detect circular dependencies
  - [ ] Provide refactoring suggestions
  - [ ] Warning in response if detected
- [ ] **Enterprise tier limits**
  - Max files: Unlimited
  - Max references: Unlimited
  - Timeout: 600 seconds

#### Implementation Files
- `src/code_scalpel/ast_tools/codeowners.py` (NEW) - CODEOWNERS parsing and matching
- `src/code_scalpel/ast_tools/impact_analyzer.py` (NEW) - Impact analysis and risk scoring
- `src/code_scalpel/mcp/server.py` - Add Enterprise response fields

#### Response Model Additions
```python
class SymbolReferencesResult(BaseModel):
    # ... existing fields ...
    # Enterprise fields
    owners: list[str] | None                # Per-reference owners
    owner_counts: dict[str, int] | None     # Counts by owner
    ownership_confidence: float | None      # 0.0-1.0
    change_risk: str | None                 # "low" | "medium" | "high"
    risk_score: int | None                  # 0-100
    risk_factors: list[str] | None          # Contributing factors
    blast_radius: int | None                # Unique files affected
    affected_teams: list[str] | None        # Teams owning affected files
    affected_complexity: int | None         # Total complexity score
    test_coverage_ratio: float | None       # Ratio in test files
    complexity_hotspots: list[str] | None   # High-complexity files
    dependencies: list[DependencyNode] | None
    cyclic_dependencies_detected: bool | None
    cyclic_dependency_warning: str | None
    impact_mermaid: str | None              # Mermaid impact diagram
    codeowners_coverage: float | None       # Ratio of owned references
```

#### Test Coverage (Net New)
- `test_enterprise_codeowners_parsing` (2 tests) - CODEOWNERS format parsing
- `test_enterprise_ownership_attribution` (2 tests) - Ownership per reference
- `test_enterprise_impact_analysis` (2 tests) - File count and complexity
- `test_enterprise_risk_scoring` (2 tests) - Risk calculation accuracy
- `test_enterprise_dependency_mapping` (2 tests) - Dependency graph building
- `test_enterprise_cyclic_detection` (2 tests) - Circular dependency detection
- `test_enterprise_unlimited_limits` (1 test) - Verify unlimited file/reference processing

#### Success Criteria
- [x] CODEOWNERS parsed and applied correctly
- [x] Impact analysis estimates match manual analysis (±10%)
- [x] Cyclic dependency detection accurate
- [x] Risk scoring meaningful and actionable
- [x] All 13 Enterprise tests passing
- [x] No regression in Pro tier tests

---

### v1.4 (Q4 2026): Language Expansion & Advanced Features - Polyglot Completion

**Effort:** 32 hours | **Tests:** 20 new + 44 existing = 64 total  
**Scope:** Add remaining languages (Go, C/C++, Rust, Ruby) to complete polyglot shape

#### Polyglot Completion Deliverables

This release delivers **full polyglot shape** - unified symbol finding across 8 languages.

##### Go Support
- [ ] Go symbol extraction using `go/parser`
- [ ] Function and interface method finding
- [ ] Package-based scope filtering
- [ ] Goroutine-safe reference tracking
- [ ] Test file detection (`*_test.go`)

**Files:**
- `src/code_scalpel/ast_tools/symbol_extractors.py` - Add `GoSymbolExtractor`
- `src/code_scalpel/code_parsers/go_parser.py` - Go AST parsing
- Tests: `test_go_symbol_finding.py` (4 tests)

##### C/C++ Support
- [ ] C/C++ symbol extraction using libclang or clang AST
- [ ] Function and class method finding
- [ ] Macro expansion handling
- [ ] Header file tracking
- [ ] Test file detection patterns

**Files:**
- `src/code_scalpel/ast_tools/symbol_extractors.py` - Add `CppSymbolExtractor`
- `src/code_scalpel/code_parsers/cpp_parser.py` - C/C++ AST parsing
- Tests: `test_cpp_symbol_finding.py` (4 tests)

##### Rust Support
- [ ] Rust symbol extraction using `syn` crate (via WASM or subprocess)
- [ ] Function and method finding
- [ ] Module and crate structure handling
- [ ] Macro invocation tracking
- [ ] Test detection (`#[cfg(test)]`)

**Files:**
- `src/code_scalpel/ast_tools/symbol_extractors.py` - Add `RustSymbolExtractor`
- `src/code_scalpel/code_parsers/rust_parser.py` - Rust AST parsing
- Tests: `test_rust_symbol_finding.py` (4 tests)

##### Ruby Support
- [ ] Ruby symbol extraction using parser gem
- [ ] Method and class definition finding
- [ ] Dynamic method handling (attr_accessor, etc.)
- [ ] Block parameter tracking
- [ ] Test file detection (rspec/minitest)

**Files:**
- `src/code_scalpel/ast_tools/symbol_extractors.py` - Add `RubySymbolExtractor`
- `src/code_scalpel/code_parsers/ruby_parser.py` - Ruby AST parsing
- Tests: `test_ruby_symbol_finding.py` (4 tests)

#### Polyglot Shape Completion Checklist

**API Unification:**
- [ ] Single `get_symbol_references()` supports all 8 languages
- [ ] Language auto-detection from file extension
- [ ] Identical response structure for all languages
- [ ] Feature parity across Community/Pro/Enterprise tiers

**Implementation:**
- [ ] 8 language-specific `SymbolExtractor` classes
- [ ] 8 corresponding parsers integrated
- [ ] Language factory for auto-detection
- [ ] Unified scope filtering for all languages
- [ ] Unified test file detection for all languages

**Quality:**
- [ ] ≥90% accuracy per language on test corpus
- [ ] <2s response time on typical codebase
- [ ] ≥95% test coverage across all implementations
- [ ] Zero breaking changes from v1.0/v1.2/v1.3

**Documentation:**
- [ ] Language support matrix in README
- [ ] Per-language examples and limitations
- [ ] Scope filtering guide per language
- [ ] Test file convention guide per language

#### Test Coverage (Net New)
- `test_go_symbol_finding` (4 tests) - Go function/interface finding
- `test_cpp_symbol_finding` (4 tests) - C/C++ function/class finding
- `test_rust_symbol_finding` (4 tests) - Rust function/method finding
- `test_ruby_symbol_finding` (4 tests) - Ruby method/class finding
- `test_polyglot_auto_detection` (2 tests) - Language detection from extension
- `test_polyglot_unified_response` (2 tests) - Same structure for all languages

#### Success Criteria for Polyglot Shape
- [x] All 8 languages supported with ≥90% accuracy
- [x] Unified API and response model across all languages
- [x] All reference type categories supported per language capability
- [x] All scope filtering formats work by language
- [x] All test file conventions detected per language
- [x] <2s response time on 1,000-file codebase per language
- [x] All 20 new tests passing + zero regressions
- [x] Full documentation of polyglot capabilities

#### Polyglot Shape Validation

After completing v1.4, run the polyglot validation script:

```python
# Pseudo-code for validation
async def validate_polyglot_shape():
    """Verify tool meets polyglot shape criteria."""
    languages = ["python", "java", "javascript", "typescript", "go", "cpp", "rust", "ruby"]
    
    for lang in languages:
        # 1. Create test codebase in language
        # 2. Call get_symbol_references() on known symbols
        # 3. Verify response structure matches
        # 4. Verify accuracy ≥90%
        # 5. Verify performance <2s
        # 6. Verify test detection works
        # 7. Verify scope filtering works
        
    # All checks pass = Polyglot shape achieved
    return all_checks_passed
```

---

### v1.5 (Q1 2027): Performance Optimization

#### All Tiers
- [x] ~~AST caching~~ (Done in v1.0)
- [ ] Faster reference search (<1s for 10K files)
- [ ] Incremental reference indexing
- [ ] Parallel reference search across languages

#### Pro Tier
- [ ] Delta reference updates (only changed files)
- [ ] Incremental symbol table updates

#### Enterprise Tier
- [ ] Distributed reference indexing
- [ ] Real-time reference monitoring
- [ ] Reference event streaming

---

### v1.6 (Q2 2027): Advanced Features & Visualization

#### Pro Tier
- [ ] Reference visualization (interactive graphs)
- [ ] Refactoring impact preview
- [ ] Automated rename suggestions
- [ ] Batch reference queries

#### Enterprise Tier
- [ ] Reference policy enforcement
- [ ] Automated API lifecycle tracking
- [ ] Cross-repository reference graphs

---

## Integration Points

### Related Tools
| Tool | Relationship |
|------|--------------|
| `rename_symbol` | Uses references for safe renames |
| `update_symbol` | Impact analysis before updates |
| `get_call_graph` | Complementary: calls vs. all references |
| `simulate_refactor` | Reference count in risk scoring |

### Export Formats
| Format | Status | Use Case |
|--------|--------|----------|
| **JSON** | ✅ v1.0 | Programmatic analysis |
| **Mermaid** | ✅ v1.0 (Enterprise) | Impact visualization |
| **CSV** | 🔄 v1.2 | Spreadsheet analysis |
| **SARIF** | 🔄 v1.3 | IDE integration |

---

## Competitive Analysis

| Tool | Strengths | Weaknesses | Our Differentiation |
|------|-----------|------------|---------------------|
| **IDE Find References** | Fast, integrated | Single-file focus | Project-wide + ownership |
| **LSP Servers** | Standard protocol | Language-specific | Multi-language unified API |
| **CodeQL** | Powerful queries | Complex setup | Zero-config, tier-based |
| **grep/ripgrep** | Fast, simple | Text-only, false positives | AST-based precision |
| **Sourcegraph** | Enterprise-grade | Self-hosted complexity | MCP-native, simpler |

---

## Known Issues & Limitations

### Current Limitations
- **Dynamic symbols:** Cannot find runtime-only references
- **String-based:** References in strings not detected
- **External usage:** Cannot track usage in external packages

### Planned Fixes
- v1.1: Partial dynamic reference inference
- v1.2: String literal analysis (opt-in)
- v1.3: External package scanning (Enterprise)

---

## Success Metrics

### Performance Targets
- **Search time:** <2s for 10K files
- **Accuracy:** >98% correct references
- **False positive rate:** <2%

### Adoption Metrics
- **Usage:** 100K+ reference searches per month by Q4 2026
- **Use case:** Pre-refactoring validation

---

## Dependencies

### Internal Dependencies
- `ast_tools/call_graph.py` - Call graph analysis
- `analysis/project_crawler.py` - Project scanning
- `cache/unified_cache.py` - Caching

### External Dependencies
- None

---

## Breaking Changes

None planned for v1.x series.

---

**Last Updated:** December 30, 2025  
**Next Review:** March 31, 2026
