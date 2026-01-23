#!/bin/bash
# [20251227_REFACTOR] Create __init__.py files for all test subdirectories

for dir in mcp tools tools/tiers tools/individual autonomy agents core core/ast core/pdg core/parsers core/cache security symbolic cli integration coverage; do
  if [ -d "$dir" ] && [ ! -f "$dir/__init__.py" ]; then
    cat > "$dir/__init__.py" << 'INIT'
"""
Test suite organization.

[20251227_REFACTOR] Tests organized by functionality for easier maintenance.
"""
INIT
    echo "Created $dir/__init__.py"
  fi
done

echo ""
echo "All __init__.py files created!"
