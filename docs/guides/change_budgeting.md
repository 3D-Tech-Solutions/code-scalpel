# Change Budgeting (Blast Radius Control)

**Version:** 2.2.0+  
**Status:** Production Ready  
**Last Updated:** December 16, 2025

## Overview

Change Budgeting is a P0 feature that limits the scope of agent modifications to prevent runaway changes. It provides fine-grained control over:

- Number of files modified per operation
- Lines changed per file and total
- Cyclomatic complexity increases
- Allowed file patterns (e.g., only `*.py`, `*.ts`)
- Forbidden paths (e.g., `.git/`, `node_modules/`)

## Key Features

### 1. Multi-Dimensional Budget Constraints

The system enforces multiple types of constraints simultaneously:

| Constraint | Purpose | Default |
|------------|---------|---------|
| `max_files` | Limit files per operation | 5 |
| `max_lines_per_file` | Limit lines changed in any single file | 100 |
| `max_total_lines` | Limit total lines changed | 300 |
| `max_complexity_increase` | Limit cyclomatic complexity increase | 10 |
| `allowed_file_patterns` | Whitelist file types | `["*.py", "*.ts", "*.java"]` |
| `forbidden_paths` | Blacklist system/generated files | `[".git/", "node_modules/", "__pycache__/"]` |

### 2. Severity Levels

Violations are classified by severity:

- **CRITICAL**: Forbidden paths, immediate blocking
- **HIGH**: File count, total lines, pattern mismatches
- **MEDIUM**: Per-file lines, complexity increases
- **LOW**: Informational warnings

### 3. Actionable Error Messages

When operations are denied, the system provides:

- Clear explanation of each violation
- Specific limits and actual values
- Actionable suggestions to reduce scope

Example error message:

```
Budget constraints violated

Violations:
  - [HIGH] Operation affects 5 files, exceeds limit of 3 (limit: 3, actual: 5)

Suggestions to reduce scope:
  - Split operation into smaller batches affecting fewer files
```

## Usage

### Basic Example

```python
from code_scalpel.policy import ChangeBudget, Operation, FileChange

# Create budget with constraints
budget = ChangeBudget({
    "max_files": 5,
    "max_lines_per_file": 100,
    "max_total_lines": 300,
    "max_complexity_increase": 10,
    "allowed_file_patterns": ["*.py", "*.ts"],
    "forbidden_paths": [".git/", "node_modules/"]
})

# Create operation
operation = Operation(
    changes=[
        FileChange(
            file_path="src/utils.py",
            added_lines=["def helper():", "    return 42"],
            original_code="",
            modified_code="def helper():\n    return 42"
        )
    ],
    description="Add helper function"
)

# Validate
decision = budget.validate_operation(operation)

if decision.allowed:
    print(f"[COMPLETE] Operation allowed: {decision.reason}")
else:
    print(f"[FAILED] Operation denied: {decision.reason}")
    print(decision.get_error_message())
```

### Policy-Based Configuration

Define different budgets for different contexts:

```python
# Default budget (permissive)
default_budget = ChangeBudget({
    "max_files": 5,
    "max_lines_per_file": 100,
    "max_total_lines": 300
})

# Critical files budget (strict)
critical_budget = ChangeBudget({
    "max_files": 1,
    "max_lines_per_file": 20,
    "max_total_lines": 20,
    "max_complexity_increase": 0  # No complexity increases allowed
})

# Apply appropriate budget based on file path
if file_path.startswith("src/security/"):
    decision = critical_budget.validate_operation(operation)
else:
    decision = default_budget.validate_operation(operation)
```

## Configuration File Support

Budget configurations can be loaded from YAML files:

### `.code-scalpel/budget.toml`

```toml
[default]
max_files = 5
max_lines_per_file = 100
max_total_lines = 300
max_complexity_increase = 10
allowed_file_patterns = [
  "src/**/*.py",
  "src/**/*.ts",
  "src/**/*.java"
]
forbidden_paths = [
  ".git/",
  "node_modules/",
  "venv/",
  "target/",
  "build/"
]

[critical_files]
# Stricter budget for sensitive files
max_files = 1
max_lines_per_file = 20
max_total_lines = 20
max_complexity_increase = 0
files = [
  "src/security/**",
  "src/authentication/**",
  "config/production.yaml"
]
```

### Loading Configuration

```python
from code_scalpel.policy import load_budget_config, ChangeBudget

# Load from default location
config = load_budget_config()

# Create budget from config
budget = ChangeBudget(config["default"])
critical_budget = ChangeBudget(config["critical_files"])
```

## Complexity Measurement

The system uses AST-based cyclomatic complexity measurement:

### Complexity Calculation

Base complexity starts at 1, with +1 for each decision point:

- `if` statements: +1
- `for` loops: +1
- `while` loops: +1
- `except` handlers: +1
- Boolean operators (`and`, `or`): +1 per operator

### Example

```python
# Complexity = 1 (base)
def simple():
    return 42

# Complexity = 5 (base + 4 decision points)
def complex():
    if x > 0:  # +1
        for i in range(10):  # +1
            if y > 0:  # +1
                if z > 0:  # +1
                    return i
    return 0
```

The budget tracks the **delta** (change) in complexity:

```python
# If original complexity = 1 and modified complexity = 5
# Then complexity_delta = 4
# This would violate a max_complexity_increase of 3
```

## File Pattern Matching

### Allowed Patterns

Patterns use glob-style matching:

```python
allowed_file_patterns = [
    "*.py",           # Any Python file
    "*.ts",           # Any TypeScript file
    "src/**/*.java"   # Java files in src/ (checks filename)
]
```

The system checks both full path and filename for matches.

### Forbidden Paths

Forbidden paths block modifications to system and generated files:

```python
forbidden_paths = [
    ".git/",           # Git metadata
    "node_modules/",   # Node.js dependencies
    "__pycache__/",    # Python cache
    "venv/",           # Python virtual environment
    "target/",         # Maven/Gradle build output
    "build/",          # Generic build output
]
```

Paths are matched as prefixes or anywhere in the full path.

## Best Practices

### 1. Start with Strict Budgets

Begin with conservative limits and relax as needed:

```python
budget = ChangeBudget({
    "max_files": 3,           # Very conservative
    "max_lines_per_file": 50,
    "max_total_lines": 150
})
```

### 2. Use Different Budgets for Different Contexts

Apply stricter budgets to critical code:

```python
def get_budget_for_file(file_path: str) -> ChangeBudget:
    if any(critical in file_path for critical in ["security", "auth", "crypto"]):
        return critical_budget
    return default_budget
```

### 3. Monitor and Adjust

Track violations to tune budget limits:

```python
decision = budget.validate_operation(operation)
if not decision.allowed:
    log_violation(decision.violations)
    # Analyze patterns and adjust budgets
```

### 4. Provide Clear Feedback

When operations are denied, explain why and suggest alternatives:

```python
if not decision.allowed:
    print("Operation denied:")
    print(decision.get_error_message())
    # Suggest alternative approach
    print("\nConsider breaking this into smaller operations:")
    print("1. First, modify files A and B")
    print("2. Then, modify files C and D")
```

## Integration with Agents

### Example: Agent Operation Wrapper

```python
class BudgetedAgent:
    def __init__(self, budget: ChangeBudget):
        self.budget = budget
    
    def apply_changes(self, operation: Operation) -> bool:
        decision = self.budget.validate_operation(operation)
        
        if not decision.allowed:
            print(f"[FAILED] Operation blocked by budget: {decision.reason}")
            print(decision.get_error_message())
            return False
        
        # Apply changes
        print(f"[COMPLETE] Operation allowed: {decision.reason}")
        # ... actual modification logic ...
        return True
```

### Example: MCP Tool Integration

```python
@mcp_tool
async def modify_code_with_budget(
    file_path: str,
    changes: str,
    budget_config: dict
) -> dict:
    """Modify code with budget constraints."""
    budget = ChangeBudget(budget_config)
    
    operation = create_operation(file_path, changes)
    decision = budget.validate_operation(operation)
    
    if not decision.allowed:
        return {
            "success": False,
            "error": decision.get_error_message(),
            "violations": [str(v) for v in decision.violations]
        }
    
    # Apply modifications
    result = apply_modifications(operation)
    return {
        "success": True,
        "files_modified": len(operation.affected_files),
        "lines_changed": operation.total_lines_changed
    }
```

## Testing

The Change Budgeting feature includes 42 comprehensive tests covering:

- All constraint types (max_files, max_lines, max_complexity)
- File pattern matching (allowed and forbidden)
- Policy configuration (default and critical)
- Error message clarity and actionability
- Complexity measurement accuracy
- Edge cases and boundary conditions

Run tests:

```bash
pytest tests/test_change_budgeting.py -v
```

## Troubleshooting

### Issue: Operations Always Fail Pattern Check

**Symptom:** All operations fail with "does not match allowed patterns"

**Solution:** Check that patterns include file extensions:

```python
# Wrong: Missing extension
allowed_file_patterns = ["src/**/*"]

# Correct: Include extension
allowed_file_patterns = ["src/**/*.py"]

# Or use generic pattern
allowed_file_patterns = ["*.py", "*.ts", "*.java"]
```

### Issue: Complexity Measurement Fails

**Symptom:** Syntax errors cause unexpected behavior

**Solution:** The system handles syntax errors gracefully by treating unparseable code as 0 complexity. Ensure both original and modified code are provided:

```python
FileChange(
    file_path="src/example.py",
    original_code=original,  # Must be valid Python
    modified_code=modified,  # Must be valid Python
)
```

### Issue: Forbidden Path Not Blocking

**Symptom:** Files in forbidden paths are not blocked

**Solution:** In your `.code-scalpel/budget.toml` configuration file, ensure paths end with `/`:

```toml
# Wrong: Missing trailing slash
forbidden_paths = [".git", "node_modules"]

# Correct: Include trailing slash
forbidden_paths = [".git/", "node_modules/"]
```

## API Reference

### Classes

#### `ChangeBudget`

Budget constraints for agent operations.

**Constructor:**
```python
ChangeBudget(config: Dict[str, Any])
```

**Methods:**
- `validate_operation(operation: Operation) -> BudgetDecision`
- `_calculate_complexity_delta(operation: Operation) -> int`
- `_measure_complexity(code: str) -> int`
- `_matches_allowed_pattern(file_path: str) -> bool`
- `_matches_forbidden_path(file_path: str) -> bool`

#### `Operation`

Represents a code modification operation.

**Attributes:**
- `changes: List[FileChange]`
- `description: str`
- `affected_files: List[str]` (property)
- `total_lines_changed: int` (property)

#### `FileChange`

Changes to a single file.

**Attributes:**
- `file_path: str`
- `added_lines: List[str]`
- `removed_lines: List[str]`
- `original_code: str`
- `modified_code: str`
- `lines_changed: int` (property)

#### `BudgetDecision`

Result of budget validation.

**Attributes:**
- `allowed: bool`
- `reason: str`
- `violations: List[BudgetViolation]`
- `requires_review: bool`
- `has_critical_violations: bool` (property)

**Methods:**
- `get_error_message() -> str`

#### `BudgetViolation`

Specific budget constraint violation.

**Attributes:**
- `rule: str`
- `severity: str` (CRITICAL, HIGH, MEDIUM, LOW)
- `message: str`
- `limit: Optional[int]`
- `actual: Optional[int]`
- `file: Optional[str]`

### Functions

#### `load_budget_config`

```python
load_budget_config(config_path: Optional[str] = None) -> Dict[str, Any]
```

Load budget configuration from YAML file.

**Parameters:**
- `config_path`: Path to budget.yaml file (default: `.code-scalpel/budget.yaml`)

**Returns:** Dictionary with budget configuration

## Examples

See `examples/change_budgeting_example.py` for complete working examples.

## See Also

- [Agent Integration Guide](agent_integration.md)
- [MCP Server Documentation](../architecture/mcp_server.md)
- [Security Analysis](../modules/security_analyzer.md)

## References

- [DEVELOPMENT_ROADMAP.md](../../DEVELOPMENT_ROADMAP.md) - Feature roadmap
- [Release Notes](../release_notes/) - Version-specific changes
