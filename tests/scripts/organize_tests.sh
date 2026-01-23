#!/bin/bash
# [20251227_REFACTOR] Organize tests into logical subdirectories

# Create subdirectories
mkdir -p mcp tools/{tiers,individual} autonomy agents core/{ast,pdg,parsers,cache} security symbolic cli integration coverage

# MCP server and transport tests
mv test_mcp*.py mcp/ 2>/dev/null || true

# Tool-specific tier tests
mv test_*_tiers.py tools/tiers/ 2>/dev/null || true

# Individual tool tests (non-tier)
mv test_analyze_code*.py test_extract_code*.py test_security_scan*.py test_simulate_refactor*.py test_generate_unit_tests*.py test_crawl_project*.py test_scan_dependencies*.py test_get_*.py test_code_policy*.py test_type_evaporation*.py test_update_symbol*.py test_validate_paths*.py tools/individual/ 2>/dev/null || true

# Autonomy engine tests
mv test_autonomy*.py autonomy/ 2>/dev/null || true
mv test_sandbox*.py autonomy/ 2>/dev/null || true
mv test_policy_engine*.py autonomy/ 2>/dev/null || true
mv test_change_budgeting*.py autonomy/ 2>/dev/null || true

# Agent framework tests
mv test_agents*.py test_*agent*.py agents/ 2>/dev/null || true
mv test_autogen*.py test_crewai*.py test_langchain*.py test_langgraph*.py agents/ 2>/dev/null || true

# AST tests
mv test_ast*.py core/ast/ 2>/dev/null || true

# PDG tests
mv test_pdg*.py core/pdg/ 2>/dev/null || true

# Parser tests
mv test_*parser*.py test_polyglot*.py test_java*.py test_javascript*.py test_typescript*.py test_python*.py core/parsers/ 2>/dev/null || true

# Cache tests
mv test_cache*.py test_*cache*.py core/cache/ 2>/dev/null || true

# Security tests
mv test_security*.py test_adversarial*.py test_taint*.py test_vulnerability*.py test_sink*.py test_cross_file_security*.py security/ 2>/dev/null || true

# Symbolic execution tests
mv test_symbolic*.py test_constraint*.py symbolic/ 2>/dev/null || true

# CLI tests
mv test_cli*.py cli/ 2>/dev/null || true

# Integration tests
mv test_*integration*.py integration/ 2>/dev/null || true

# Coverage/quality tests (consolidate)
mv test_coverage*.py test_acceptance*.py test_branch*.py coverage/ 2>/dev/null || true

# Contract/compliance tests
mv test_contract*.py test_compliance*.py coverage/ 2>/dev/null || true

# Reproduction tests
mv test_repro*.py test_reproduction*.py integration/ 2>/dev/null || true

# Cross-file tests
mv test_cross_file*.py tools/individual/ 2>/dev/null || true

# Config tests
mv test_config*.py core/ 2>/dev/null || true

echo "Test organization complete!"
echo ""
echo "Directory structure:"
find . -maxdepth 2 -type d | sort
echo ""
echo "Files per directory:"
for dir in mcp tools/tiers tools/individual autonomy agents core/ast core/pdg core/parsers core/cache security symbolic cli integration coverage; do
  count=$(find $dir -maxdepth 1 -name "test_*.py" 2>/dev/null | wc -l)
  if [ $count -gt 0 ]; then
    echo "  $dir: $count tests"
  fi
done
