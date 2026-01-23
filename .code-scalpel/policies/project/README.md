# Project Structure Policies

This directory contains policies that enforce consistent code organization and documentation standards for the Code Scalpel project.

## Overview

The project structure policy ensures:
- **Consistent file placement** - Similar code in similar directories
- **Complete documentation** - README.md in every meaningful directory
- **Clean architecture** - Core analysis isolated from integrations
- **Naming conventions** - PEP 8 compliance and project standards
- **Module boundaries** - Preventing circular dependencies

## Policy: structure.rego

Enforces Code Scalpel's project structure conventions:

### File Location Rules
- PDG tools → `src/code_scalpel/pdg_tools/`
- Graph engine → `src/code_scalpel/graph_engine/`
- Policy engine → `src/code_scalpel/policy_engine/`
- Integrations → `src/code_scalpel/integrations/`
- MCP server → `src/code_scalpel/mcp/`
- Unit tests → `tests/unit/`
- Integration tests → `tests/integration/`
- Policy templates → `.code-scalpel/policies/`

### README Requirements
Every directory must have README.md with:
- **Overview** - What this directory contains
- **Usage** - How to use the components
- **Additional sections** - Directory-specific requirements

Excluded: `__pycache__`, `.pytest_cache`, `node_modules`, `.venv`, etc.

### Naming Conventions
- **Python modules**: `snake_case.py`
- **Python packages**: `snake_case/`
- **Test files**: `test_*.py`
- **Rego policies**: `snake_case.rego`
- **Documentation**: `UPPERCASE_WITH_UNDERSCORES.md`

### Cohabitation Rules
| Directory | Allowed | Forbidden |
|-----------|---------|-----------|
| `pdg_tools/` | PDG analysis, utilities | Tests, integrations, policies |
| `graph_engine/` | Graph analysis, utilities | Tests, integrations, MCP |
| `integrations/` | AI integrations only | PDG, graph, tests |
| `mcp/` | MCP server components | PDG, graph, integrations |
| `policy_engine/` | Policy logic, models | Tests, integrations |
| `tests/unit/` | Unit tests, fixtures | Integration tests |
| `tests/integration/` | Integration tests | Unit tests |

### Module Dependency Rules
Clean architecture enforcement:
- **Core modules** (`pdg_tools/`, `graph_engine/`, `policy_engine/`) CANNOT import integrations
- **Graph engine** has minimal dependencies (only `ir/`, `utilities/`)
- **Policy engine** is security-isolated (no external integrations)
- **Integrations** can import core, but not each other
- **MCP server** can import core, but not integrations

### File Size Limits
- Python: 500 lines max (warn at 300)
- Rego: 300 lines max (warn at 200)
- Markdown: 1000 lines max

Encourages modular design and maintainability.

## Configuration

Configuration file: [.code-scalpel/project-structure.yaml](../../project-structure.yaml)

Key sections:
```yaml
project_config:
  name: "code-scalpel"
  type: "python-library"
  strictness: high
  
  file_locations:
    pdg_tool: "src/code_scalpel/pdg_tools/"
    # ... more rules
  
  readme_requirements:
    sections: ["Overview", "Usage"]
    # ... directory-specific requirements
  
  naming_conventions:
    "Python Module": "^[a-z_][a-z0-9_]*\\.py$"
    # ... more patterns
  
  cohabitation:
    "src/code_scalpel/pdg_tools/":
      allowed: ["pdg_tool", "utility_function"]
      forbidden: ["test_file", "integration"]
    # ... more rules
  
  dependency_rules:
    "src/code_scalpel/pdg_tools/":
      can_import: ["graph_engine/", "ir/"]
      cannot_import: ["integrations/", "mcp/"]
    # ... more rules
```

## Usage

### Validate Project Structure

```bash
# Check all files
code-scalpel validate-structure

# Output example:
# ❌ src/code_scalpel/new_feature.py should be in src/code_scalpel/pdg_tools/
# ❌ src/code_scalpel/custom/ missing README.md
# ❌ tests/integration/test_pdg.py has forbidden import 'code_scalpel.integrations'
# ✅ 245 files correctly organized
```

### Check Specific Directory

```bash
code-scalpel validate-structure --directory=src/code_scalpel/pdg_tools/
```

### Auto-Fix Issues

```bash
# Preview changes
code-scalpel fix-structure --dry-run

# Apply fixes
code-scalpel fix-structure --apply
```

### Generate Missing READMEs

```bash
# Generate all missing READMEs
code-scalpel generate-readmes --all

# Generate for specific directory
code-scalpel generate-readmes --directory=src/code_scalpel/new_module/
```

### AI Agent Integration

```python
from code_scalpel.governance import ProjectStructureEnforcer

enforcer = ProjectStructureEnforcer()

# Before AI creates a file
proposed_change = ProposedChange(
    operation="create_file",
    path="src/code_scalpel/new_feature.py",
    content=new_code
)

validation = enforcer.validate_proposed_change(proposed_change)
if not validation.allowed:
    print(f"❌ {validation.reason}")
    print(f"💡 Suggestion: {validation.suggestion}")
    # AI corrects the path automatically
    proposed_change.path = validation.suggestion

# Get guidance for file placement
guidance = enforcer.guide_ai_placement(new_code)
print(f"Create in: {guidance['recommended_directory']}")
print(f"Name like: {guidance['example_filename']}")

# After AI work session
organized_changes = enforcer.auto_organize(ai_proposed_changes)
enforcer.generate_missing_readmes()
```

## Examples

### Example 1: Wrong File Location

**Violation:**
```
src/code_scalpel/UserService.py
```

**Corrected:**
```
src/code_scalpel/integrations/user_service.py
```

**Reason:** AI integrations belong in `integrations/`, and Python modules use `snake_case`.

### Example 2: Missing README

**Violation:**
```
src/code_scalpel/custom_analyzer/
├── analyzer.py
└── utils.py
```

**Corrected:**
```
src/code_scalpel/custom_analyzer/
├── README.md          # ← Added
├── __init__.py        # ← Added
├── analyzer.py
└── utils.py
```

**README.md content:**
```markdown
# Custom Analyzer

## Overview

This module provides custom analysis capabilities for [specific functionality].

## Components

- `analyzer.py` - Main analysis logic
- `utils.py` - Utility functions

## Usage

```python
from code_scalpel.custom_analyzer import CustomAnalyzer

analyzer = CustomAnalyzer()
result = analyzer.analyze(code)
```
```

### Example 3: Forbidden Import

**Violation:**
```python
# src/code_scalpel/pdg_tools/slicer.py
from code_scalpel.integrations.crewai import CrewAITool  # ❌ Forbidden

class Slicer:
    def slice(self):
        tool = CrewAITool()  # Core analysis shouldn't depend on integrations
```

**Corrected:**
```python
# src/code_scalpel/pdg_tools/slicer.py
from code_scalpel.graph_engine import Graph  # ✅ Allowed

class Slicer:
    def slice(self):
        graph = Graph()  # Core depends only on other core modules
```

**Reason:** Core analysis modules must remain independent of AI framework integrations to maintain clean architecture.

### Example 4: Test Cohabitation

**Violation:**
```
src/code_scalpel/pdg_tools/
├── builder.py
├── slicer.py
└── test_builder.py    # ❌ Tests don't belong in source
```

**Corrected:**
```
src/code_scalpel/pdg_tools/
├── builder.py
└── slicer.py

tests/unit/pdg_tools/
└── test_builder.py    # ✅ Tests in tests/
```

### Example 5: Large File Warning

**Violation:**
```python
# src/code_scalpel/monolithic_analyzer.py (650 lines)
class MonolithicAnalyzer:
    # ... 650 lines of code
```

**Corrected:**
```python
# src/code_scalpel/analyzer/
# ├── README.md
# ├── __init__.py
# ├── core.py (200 lines)
# ├── parsers.py (180 lines)
# └── transformers.py (200 lines)
```

**Reason:** Files over 500 lines should be refactored into smaller, focused modules.

## Benefits

### For AI Agents
- **Clear guidance** on where to place files
- **Automatic corrections** for misplaced code
- **Template generation** for new modules
- **Prevents duplicates** like 33 summary files

### For Developers
- **Consistent structure** across the codebase
- **Easy navigation** with predictable organization
- **Complete documentation** in every directory
- **Clean architecture** enforcement

### For Teams
- **Onboarding efficiency** - new developers find code easily
- **Code review quality** - violations caught automatically
- **Technical debt prevention** - architecture maintained
- **Documentation completeness** - no undocumented modules

## CI/CD Integration

```yaml
# .github/workflows/structure-check.yml
name: Project Structure Check

on: [push, pull_request]

jobs:
  structure:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Validate Structure
        run: |
          code-scalpel validate-structure --fail-on-violation
      
      - name: Check for Missing READMEs
        run: |
          code-scalpel check-readmes --fail-on-missing
      
      - name: Verify Clean Architecture
        run: |
          code-scalpel check-dependencies --fail-on-violation
```

## Customization

To adjust rules for your team:

1. Edit [.code-scalpel/project-structure.yaml](../../project-structure.yaml)
2. Modify `file_locations`, `naming_conventions`, or `cohabitation` rules
3. Update `enforcement` levels (DENY, WARN, INFO)
4. Test changes: `code-scalpel validate-structure --dry-run`

## Resources

- [Configuration File](../../project-structure.yaml) - Full configuration
- [Policy Engine](../../../src/code_scalpel/policy_engine/README.md) - Policy engine docs
- [Contributing Guide](../../../CONTRIBUTING.md) - Development guidelines

---

**Version:** v3.2.0  
**Last Updated:** December 21, 2025
