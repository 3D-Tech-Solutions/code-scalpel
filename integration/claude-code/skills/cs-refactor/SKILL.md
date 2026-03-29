---
name: cs-refactor
description: |
  Safe refactoring workflow: find all usages, trace dependencies, simulate changes,
  generate baseline tests, then apply with backup. Behavior-preserving refactor.
allowed-tools:
  - mcp__codescalpel__get_symbol_references
  - mcp__codescalpel__get_cross_file_dependencies
  - mcp__codescalpel__extract_code
  - mcp__codescalpel__generate_unit_tests
  - mcp__codescalpel__simulate_refactor
  - mcp__codescalpel__update_symbol
preamble-tier: 1
---

# /cs-refactor — Safe Code Refactoring Workflow

Refactor code with confidence. The workflow:
1. Finds all usages (impact zone)
2. Traces all dependencies (what it depends on)
3. Extracts current implementation
4. Generates test baseline (safety net)
5. Simulates the change (verify behavior preserved)
6. Applies with backup (automatic rollback available)

## Usage

```bash
/cs-refactor src/utils.py function validate_email
/cs-refactor src/auth.ts function authenticate
```

## The Safety Pipeline

### Step 1: Find Impact
Show all places where this symbol is called. Understand scope of change.

### Step 2: Trace Dependencies
Show everything this function depends on. Understand what it touches.

### Step 3: Extract Current Code
Get the full current implementation for comparison.

### Step 4: Create Test Baseline
Generate unit tests for the current behavior. If the refactored code passes these tests,
behavior is preserved.

### Step 5: Simulate the Change
Run a "dry run" of the refactor:
- Parse old code
- Parse new code
- Compare ASTs (abstract syntax trees)
- Detect behavior changes
- Flag breaking changes before applying

### Step 6: Apply Safely
If simulation passes:
- Creates automatic backup of original file
- Replaces function with new code
- Validates syntax
- Preserves surrounding code

## Refactoring Examples

**Rename a variable:**
```python
# Old
def process(data):
    result = compute(data)
    return result

# New
def process(data):
    output = compute(data)
    return output
```

**Extract a helper:**
```python
# Old
def validate(email):
    if not email or '@' not in email:
        raise ValueError("Invalid email")
    return True

# New
def is_valid_email(email):
    return email and '@' in email

def validate(email):
    if not is_valid_email(email):
        raise ValueError("Invalid email")
    return True
```

**Simplify logic:**
```python
# Old (over-complex)
def needs_retry(status_code):
    if status_code == 429:
        return True
    elif status_code == 503:
        return True
    elif status_code == 504:
        return True
    else:
        return False

# New (clear and simple)
def needs_retry(status_code):
    return status_code in (429, 503, 504)
```

## When Simulation Detects Issues

If `simulate_refactor` finds a behavior change:
- It shows you the exact difference
- You revise your new code
- Run simulation again until it passes
- Then apply

## After Refactoring

```bash
# Run your test suite to double-check
pytest tests/

# If something broke, revert (backup file exists)
# Then use /cs-extract to debug the issue
/cs-extract src/utils.py function validate_email
```

## Pro Tips

- **Generate tests FIRST** — Creates safety baseline before any changes
- **Small refactors** — One function at a time is safer than bulk changes
- **Simulate before applying** — It's free (simulation doesn't touch files)
- **Keep backups** — Automatic, but you can git diff to see exact changes

## Languages Supported

- Python (.py)
- JavaScript (.js)
- TypeScript (.ts, .tsx)
- Java (.java)
- JSX/TSX (React components)

See `CLAUDE.md` for the complete safe refactor workflow.
