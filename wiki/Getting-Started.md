# Getting Started

This guide walks you through your first Code Scalpel operations using natural conversation with your AI assistant.

## Your First Interaction

Once Code Scalpel is installed and configured (see [Installation](Installation)), talk to your AI assistant—it will use Code Scalpel tools behind the scenes.

### Example 1: Extract a Function

Instead of asking for an entire file, request a specific function:

**You say:**
> "Extract the calculate_tax function from utils.py"

**AI Assistant (using Code Scalpel):**
> "Here's the calculate_tax function extracted from utils.py:
> ```python
> def calculate_tax(amount: float, tax_rate: float = 0.08) -> float:
>     return amount * tax_rate
> ```
> This was extracted surgically—just the function plus any necessary imports. This approach uses 99% fewer tokens than reading the entire file."

**What happened behind the scenes:**
- Code Scalpel parsed the Python AST
- Located the function by name
- Extracted only the function + required imports
- Your AI assistant returned just what you need

### Example 2: Understand Code Structure

**You say:**
> "What's in the payment.py file? What are the main functions and classes?"

**AI Assistant (using Code Scalpel):**
> "The payment.py file contains:
>
> **Functions:**
> - process_payment(order) - Main payment processor
> - validate_card(card_data) - Card validation
> - refund(transaction_id) - Handles refunds
>
> **Classes:**
> - PaymentProcessor - Main payment service (complexity: 8/10)
> - PaymentError - Custom exception
>
> **Imports:**
> - stripe - Payment gateway integration
> - decimal.Decimal - Precise amount calculations
> - datetime - Transaction timestamps
>
> This file has 245 lines of code total."

**What happened behind the scenes:**
- Code Scalpel analyzed the code structure
- Returned functions, classes, imports, and metrics
- Your AI assistant formatted it for easy reading

### Example 3: Security Check

**You say:**
> "Check this code for security vulnerabilities before I use it"
> [paste code snippet]

**AI Assistant (using Code Scalpel):**
> "⚠️ **Security Issues Found (1 HIGH severity):**
>
> **SQL Injection** (CWE-89) at line 12:
> ```python
> query = f"SELECT * FROM users WHERE id = {user_id}"
> cursor.execute(query)
> ```
>
> **Issue:** The user_id variable flows directly into SQL without parameterization.
>
> **Fix:**
> ```python
> query = "SELECT * FROM users WHERE id = %s"
> cursor.execute(query, (user_id,))
> ```
>
> This uses parameterized queries which prevent SQL injection."

**What happened behind the scenes:**
- Code Scalpel performed taint analysis
- Traced data flow from user input to SQL execution
- Identified the dangerous pattern
- Your AI assistant provided remediation

## Common Workflows

### Workflow 1: Safe Refactoring

**You say:**
> "I want to refactor the process_order function. Here's my new version. Is it safe?"
> [paste original and new code]

**AI Assistant (using Code Scalpel):**
> "✅ **Refactoring is safe!**
>
> Analysis:
> - No new security vulnerabilities introduced
> - Function signature unchanged (all callers compatible)
> - All exception handling preserved
> - No performance regression detected
>
> Ready to apply. I can update it in your code if you'd like."

**What happened behind the scenes:**
- Code Scalpel simulated the refactoring
- Checked for security issues
- Verified structural compatibility
- Your AI assistant gave you confidence before making changes

### Workflow 2: Find All Usages

**You say:**
> "Before I rename the calculate_tax function, show me everywhere it's used"

**AI Assistant (using Code Scalpel):**
> "The calculate_tax function is used in 7 places:
>
> 1. **handlers/api.py** (line 156) - Direct call: `result = calculate_tax(order_data)`
> 2. **tests/test_order.py** (line 23) - In test: `assert calculate_tax(100) == 8.0`
> 3. **services/billing.py** (line 89) - Imported: `from utils import calculate_tax`
> 4. **utils.py** (line 42) - Definition (this is the function itself)
> ... and 3 more
>
> I can safely rename this across all files."

**What happened behind the scenes:**
- Code Scalpel found all symbol references
- Tracked definitions, imports, and calls
- Your AI assistant showed you the usage context

### Workflow 3: Generate Tests

**You say:**
> "Generate comprehensive tests for this function covering all branches"
> [paste function]

**AI Assistant (using Code Scalpel):**
> "Here are tests covering all execution paths:
>
> ```python
> import pytest
> from utils import calculate_tax
>
> def test_calculate_tax_normal_case():
>     assert calculate_tax(100, 0.08) == 8.0
>
> def test_calculate_tax_zero_amount():
>     assert calculate_tax(0, 0.08) == 0.0
>
> def test_calculate_tax_default_rate():
>     assert calculate_tax(100) == 8.0
>
> def test_calculate_tax_high_rate():
>     assert calculate_tax(100, 0.25) == 25.0
> ```
>
> These tests cover the normal case, edge cases (zero), default parameters, and boundary conditions."

**What happened behind the scenes:**
- Code Scalpel performed symbolic execution
- Explored all execution paths through the function
- Generated test cases for each path
- Your AI assistant provided ready-to-use pytest code

### Workflow 4: Cross-File Analysis

**You say:**
> "What are all the dependencies of the billing service? What might break if I modify it?"

**AI Assistant (using Code Scalpel):**
> "The billing service has these dependencies:
>
> **Direct imports:**
> - utils.py (calculate_tax, format_currency)
> - models.py (Invoice, Transaction)
> - stripe (payment gateway)
>
> **Services that depend on billing:**
> - api/handlers.py (3 endpoints)
> - tasks/email.py (sends billing emails)
> - admin/reports.py (generates reports)
>
> If you modify the calculate_tax signature, you'll need to update 4 locations across 3 files."

**What happened behind the scenes:**
- Code Scalpel analyzed the import graph
- Built the dependency tree
- Identified impact radius
- Your AI assistant showed you the scope of changes

## Understanding AI Responses

## Token Efficiency

Code Scalpel dramatically reduces token usage:

| Operation | Traditional | Code Scalpel | Savings |
|-----------|-------------|--------------|---------|
| Extract function | Read 10K LOC file | Extract 50 LOC | **99%** |
| Find usages | Grep entire codebase | Symbol references | **95%** |
| Security scan | Manual review | Taint analysis | **90%** |

**Example:**
- Reading a 10,000-line file: ~10,000 tokens
- Extracting one function: ~50 tokens
- **Savings: 9,950 tokens (99%)**

## Language Support

### Python (Full Support)

All features available:
- AST parsing ✅
- PDG analysis ✅
- Taint analysis ✅
- Symbolic execution ✅
- Test generation ✅

### JavaScript/TypeScript

Core features:
- AST parsing ✅
- Function extraction ✅
- Call graphs ✅
- Type evaporation scan ✅
- Basic security scanning ⚠️

### Java, Go, Rust, Ruby, PHP

Limited support:
- AST parsing ✅
- Code extraction ✅
- Structure analysis ✅

## Interactive Examples

### Example: E-commerce Refactor

**Scenario:** Refactor payment processing to handle multiple currencies.

```python
# Step 1: Understand current implementation
context = get_file_context(file_path="payment.py")
print(context.functions)  # ['process_payment', 'validate_card']

# Step 2: Extract the payment function
current = extract_code(
    file_path="payment.py",
    target_name="process_payment"
)

# Step 3: Find all places it's called
refs = get_symbol_references(symbol_name="process_payment")
print(f"Used in {len(refs.references)} places")

# Step 4: Check for security issues
security = security_scan(code=current)
if security.vulnerabilities:
    print("Warning: Fix security issues first!")

# Step 5: Simulate the refactor
new_code = """
def process_payment(amount, currency='USD'):
    if currency not in SUPPORTED_CURRENCIES:
        raise ValueError(f"Unsupported currency: {currency}")
    # ... enhanced logic
"""

safe = simulate_refactor(original_code=current, new_code=new_code)
if safe.is_safe:
    # Step 6: Apply the change
    update_symbol(
        file_path="payment.py",
        target_name="process_payment",
        new_code=new_code
    )
```

## Best Practices

### 1. Always Extract Before Analyzing

Don't read entire files unnecessarily:

❌ **Inefficient:**
```python
# Reads entire 5000-line file
full_file = read_file("services.py")
# Parse to find one function
```

✅ **Efficient:**
```python
# Extracts just 50 lines
function = extract_code(file_path="services.py", target_name="process")
```

### 2. Verify Before Modifying

Use `simulate_refactor` before `update_symbol`:

```python
# Always check safety first
result = simulate_refactor(original, new_code)
if result.is_safe and not result.security_issues:
    update_symbol(...)
```

### 3. Find All References Before Renaming

```python
# Check impact before renaming
refs = get_symbol_references("old_function")
print(f"Will update {len(refs.references)} locations")
# Then rename
rename_symbol(...)
```

### 4. Use Security Scanning Early

Catch vulnerabilities before they reach production:

```python
# Scan as you write
scan_result = security_scan(new_code)
if scan_result.vulnerabilities:
    # Fix issues before committing
```

## Next Steps

- **[MCP Tools Reference](MCP-Tools-Reference)** - Complete documentation of all 22 tools
- **[Configuration](Configuration)** - Environment variables and settings
- **[Examples](Examples)** - More complex use cases and patterns
- **[Security](Security)** - Policy enforcement and integrity verification

## Troubleshooting

### "Symbol not found"

```python
# Use get_file_context first to see what's available
context = get_file_context(file_path="myfile.py")
print(context.functions)  # See actual function names
```

### "Token limit exceeded"

Code Scalpel tools are designed to minimize tokens, but:
- Use `extract_code` instead of reading full files
- Use `get_file_context` for quick overviews
- Use `max_depth` parameters to limit recursion

### "Unsupported language"

Check [Language Support](#language-support) above. For unsupported languages:
- Basic extraction may still work via tree-sitter
- Advanced features (symbolic execution, PDG) are Python-only

---

**Ready for advanced features?** → [MCP Tools Reference](MCP-Tools-Reference)
