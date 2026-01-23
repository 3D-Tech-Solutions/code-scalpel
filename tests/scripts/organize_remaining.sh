#!/bin/bash
# [20251227_REFACTOR] Organize remaining test files

# Core analysis tests
mv test_code_analyzer*.py test_alias_resolver*.py test_decorator_analyzer*.py test_import_resolver*.py test_incremental_analyzer*.py core/ 2>/dev/null || true

# Graph engine tests
mv test_graph_engine*.py test_call_graph*.py tools/individual/ 2>/dev/null || true

# IR/Parser tests  
mv test_ir*.py test_jsx_tsx*.py test_graphql*.py test_grpc*.py core/parsers/ 2>/dev/null || true

# Framework tests
mv test_framework*.py test_frontend*.py core/parsers/ 2>/dev/null || true

# Security/taint tests
mv test_taint*.py test_sink*.py security/ 2>/dev/null || true

# Governance tests
mv test_governance*.py test_crypto*.py autonomy/ 2>/dev/null || true

# Dynamic import tests
mv test_dynamic*.py test_fix_loop*.py integration/ 2>/dev/null || true

# Coverage push tests (consolidate)
mv test_*95*.py test_final*.py test_deep*.py coverage/ 2>/dev/null || true

# Error handling tests
mv test_error*.py integration/ 2>/dev/null || true

# Move all remaining test files to appropriate places
for file in test_*.py; do
  if [ -f "$file" ]; then
    # Check content to determine best location
    if grep -q "mcp\|MCP\|transport" "$file" 2>/dev/null; then
      mv "$file" mcp/
    elif grep -q "tier\|Tier\|TIER" "$file" 2>/dev/null; then
      mv "$file" tools/tiers/
    elif grep -q "autonomy\|policy\|governance" "$file" 2>/dev/null; then
      mv "$file" autonomy/
    elif grep -q "agent\|Agent" "$file" 2>/dev/null; then
      mv "$file" agents/
    elif grep -q "security\|vulnerability\|taint" "$file" 2>/dev/null; then
      mv "$file" security/
    elif grep -q "symbolic\|constraint\|z3" "$file" 2>/dev/null; then
      mv "$file" symbolic/
    elif grep -q "parser\|Parser\|AST\|ast" "$file" 2>/dev/null; then
      mv "$file" core/parsers/
    elif grep -q "coverage\|branch" "$file" 2>/dev/null; then
      mv "$file" coverage/
    else
      mv "$file" integration/
    fi
  fi
done

echo "Remaining tests organized!"
echo ""
echo "Final counts:"
for dir in mcp tools/tiers tools/individual autonomy agents core core/ast core/pdg core/parsers core/cache security symbolic cli integration coverage; do
  count=$(find $dir -maxdepth 1 -name "test_*.py" 2>/dev/null | wc -l)
  if [ $count -gt 0 ]; then
    echo "  $dir: $count tests"
  fi
done
echo ""
remaining=$(ls -1 test_*.py 2>/dev/null | wc -l)
echo "Remaining in root: $remaining tests"
