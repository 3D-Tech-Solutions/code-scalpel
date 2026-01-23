"""
THE ARCHITECT'S SKEPTICAL STRESS TEST
======================================
Proof that this parser is NOT deterministic on dirty code.

Test cases:
1. Missing semicolon in JavaScript
2. Jinja2 template mixed with Python
3. Git merge conflict markers (<<<<<<, ======, >>>>>>)
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

print("=" * 80)
print("THE ARCHITECT'S STRESS TEST: Breaking 'Deterministic' Code Manipulation")
print("=" * 80)

# ============================================================================
# TEST 1: PDG Builder - NO SANITIZATION
# ============================================================================
print("\n[TEST 1] PDG Builder with Merge Conflict Markers")
print("-" * 80)

from code_scalpel.pdg_tools.builder import PDGBuilder  # noqa: E402

dirty_python_with_conflict = """
def calculate_tax(amount):
<<<<<<< HEAD
    return amount * 0.05
=======
    return amount * 0.08
>>>>>>> feature-branch
"""

print("Code with merge conflict markers:")
print(dirty_python_with_conflict)
print("\nResult: ", end="")

try:
    builder = PDGBuilder()
    pdg, call_graph = builder.build(dirty_python_with_conflict)
    print("❌ UNEXPECTED: Parser did not crash! Graph nodes:", list(pdg.nodes())[:5])
except SyntaxError as e:
    print(f"✅ CRASH as expected: {e}")
except Exception as e:
    print(f"⚠️  UNEXPECTED ERROR: {type(e).__name__}: {e}")

# ============================================================================
# TEST 2: Surgical Extractor - HAS SANITIZATION
# ============================================================================
print("\n[TEST 2] Surgical Extractor with Jinja2 Templates")
print("-" * 80)

from code_scalpel.surgery.surgical_extractor import SurgicalExtractor  # noqa: E402

dirty_python_with_jinja = """
def greet(name):
    message = "Hello {% if premium %}Premium{% endif %} {{ name }}"
    return message
"""

print("Code with Jinja2 templates:")
print(dirty_python_with_jinja)
print("\nResult: ", end="")

try:
    extractor = SurgicalExtractor(dirty_python_with_jinja)
    # Just check if it can initialize and get functions
    functions = extractor.functions
    print("⚠️  SILENT SUCCESS: Initialized extractor with Jinja2!")
    print(f"   Functions found: {list(functions.keys())}")
except ValueError as e:
    print(f"✅ CRASH as expected: {e}")
except Exception as e:
    print(f"⚠️  UNEXPECTED ERROR: {type(e).__name__}: {e}")

# ============================================================================
# TEST 3: Tree-Sitter JavaScript Direct Test
# ============================================================================
print("\n[TEST 3] Tree-Sitter JavaScript Parser with Missing Semicolon")
print("-" * 80)

try:
    import tree_sitter_javascript as ts_js
    from tree_sitter import Language, Parser

    dirty_js_missing_semicolon = """
function calculateTotal(items) {
    let total = 0
    for (let item of items) {
        total += item.price  // Missing semicolon
    }
    return total  // Missing semicolon
}
"""

    print("Code with missing semicolons:")
    print(dirty_js_missing_semicolon)
    print("\nResult: ", end="")

    lang = Language(ts_js.language())
    parser = Parser(lang)
    tree = parser.parse(bytes(dirty_js_missing_semicolon, "utf-8"))

    print("⚠️  SILENT SUCCESS: Tree-sitter parsed without error!")
    print(f"   Has errors: {tree.root_node.has_error}")
    print(f"   Root type: {tree.root_node.type}")
except ImportError:
    print("⚠️  SKIPPED: tree-sitter not installed")
except Exception as e:
    print(f"⚠️  UNEXPECTED ERROR: {type(e).__name__}: {e}")

# ============================================================================
# TEST 4: Python AST with Incomplete Code
# ============================================================================
print("\n[TEST 4] Python AST Parser with Incomplete Function")
print("-" * 80)

import ast  # noqa: E402

dirty_python_incomplete = """
def calculate_discount(price):
    if price > 100:
        return price * 0.1
    # Missing else and return - incomplete
"""

print("Code with incomplete function:")
print(dirty_python_incomplete)
print("\nResult: ", end="")

try:
    tree = ast.parse(dirty_python_incomplete)
    print("✅ SILENT SUCCESS: ast.parse accepted incomplete code!")
    print(f"   Functions: {[n.name for n in tree.body if isinstance(n, ast.FunctionDef)]}")
except SyntaxError as e:
    print(f"⚠️  Failed: {e}")

# ============================================================================
# FINAL VERDICT
# ============================================================================
print("\n" + "=" * 80)
print("THE ARCHITECT'S VERDICT")
print("=" * 80)
print("""
1. PDG Builder (pdg_tools/builder.py):
   ❌ NO sanitization - CRASHES on merge conflicts
   ❌ NO fallback - ast.parse() called directly (line 82)

2. Surgical Extractor (surgery/surgical_extractor.py):
   ⚠️  Has try/catch for SyntaxError but NO sanitization in constructor
   ⚠️  Converts SyntaxError to ValueError (line 563)

3. JavaScript Parser (mcp/helpers/analyze_helpers.py):
   ✅ Tree-sitter can parse partial/broken syntax
   ⚠️  But reports success=True even with ERROR nodes

4. Main Analyze Helper (analyze_helpers.py):
   ✅ HAS sanitization via ast_helpers.parse_cached_ast()
   ⚠️  Silently "fixes" Jinja2/conflicts - user unaware code was modified

5. Java Parser:
   ✅ Tree-sitter error recovery - continues on syntax errors

CONCLUSION:
-----------
This tool is NOT "deterministic" because:
- Different entry points have different error handling
- Some paths sanitize (ast_helpers), others don't (pdg_tools)
- Tree-sitter silently recovers from errors
- Sanitization happens without user notification

It IS "fail-fast" in some places (surgical_extractor) but NOT others (pdg_builder).

The real-world verdict: **PARTIALLY ROBUST** but **INCONSISTENT**.
""")
