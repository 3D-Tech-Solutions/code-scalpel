#!/usr/bin/env bash
# [20251218_FEATURE] Migration script from .scalpel/ to .code-scalpel/
# 
# This script helps existing users migrate from the old .scalpel/ directory
# to the new unified .code-scalpel/ directory structure in v3.0.0+.

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "================================================================="
echo "Code Scalpel: .scalpel/ → .code-scalpel/ Migration Tool"
echo "================================================================="
echo ""

# Check if .scalpel exists
if [[ ! -d ".scalpel" ]]; then
    echo -e "${YELLOW}⚠ No .scalpel/ directory found.${NC}"
    echo "Nothing to migrate. You're all set!"
    exit 0
fi

# Check if .code-scalpel already exists
if [[ -d ".code-scalpel" ]]; then
    echo -e "${YELLOW}⚠ .code-scalpel/ directory already exists.${NC}"
    read -p "Do you want to merge files? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Migration cancelled."
        exit 1
    fi
    MERGE_MODE=true
else
    MERGE_MODE=false
    mkdir -p .code-scalpel
    echo -e "${GREEN}✓ Created .code-scalpel/ directory${NC}"
fi

# Function to copy file if it doesn't exist in destination
copy_if_not_exists() {
    local src="$1"
    local dest="$2"
    
    if [[ -f "$src" ]]; then
        if [[ -f "$dest" ]] && [[ "$MERGE_MODE" == "true" ]]; then
            echo -e "${YELLOW}  ⚠ $dest already exists, skipping${NC}"
        else
            cp "$src" "$dest"
            echo -e "${GREEN}  ✓ Copied $(basename "$src")${NC}"
        fi
    fi
}

# 1. Migrate policy files
echo ""
echo "1. Migrating policy files..."
mkdir -p ".code-scalpel/templates"
copy_if_not_exists ".scalpel/policy.yaml" ".code-scalpel/policy.yaml"
copy_if_not_exists ".scalpel/policy.yaml.example" ".code-scalpel/templates/policy.yaml.example"
copy_if_not_exists ".scalpel/policy_override.yaml" ".code-scalpel/templates/policy_override.yaml"
copy_if_not_exists ".scalpel/policy_test.yaml" ".code-scalpel/templates/policy_test.yaml"

# 2. Migrate config.json with merge check
echo ""
echo "2. Migrating configuration..."
if [[ -f ".scalpel/config.json" ]]; then
    if [[ -f ".code-scalpel/config.json" ]]; then
        echo -e "${YELLOW}  ⚠ .code-scalpel/config.json already exists${NC}"
        echo "  → Backing up .scalpel/config.json to .scalpel/config.json.backup"
        cp ".scalpel/config.json" ".scalpel/config.json.backup"
    else
        cp ".scalpel/config.json" ".code-scalpel/config.json"
        echo -e "${GREEN}  ✓ Copied config.json${NC}"
    fi
fi

# 3. Migrate audit files
echo ""
echo "3. Migrating audit files..."
if [[ -f ".scalpel/audit.log" ]]; then
    if [[ -f ".code-scalpel/audit.log" ]]; then
        # Append old audit log to new one
        echo -e "${YELLOW}  ⚠ Merging audit logs${NC}"
        cat ".scalpel/audit.log" >> ".code-scalpel/audit.log"
        echo -e "${GREEN}  ✓ Merged audit.log${NC}"
    else
        cp ".scalpel/audit.log" ".code-scalpel/audit.log"
        echo -e "${GREEN}  ✓ Copied audit.log${NC}"
    fi
fi

# 4. Migrate autonomy_audit directory
echo ""
echo "4. Migrating autonomy audit directory..."
if [[ -d ".scalpel/autonomy_audit" ]]; then
    if [[ -d ".code-scalpel/autonomy_audit" ]]; then
        echo -e "${YELLOW}  ⚠ Merging autonomy audit files${NC}"
        cp -r ".scalpel/autonomy_audit/"* ".code-scalpel/autonomy_audit/" 2>/dev/null || true
        echo -e "${GREEN}  ✓ Merged autonomy_audit/${NC}"
    else
        cp -r ".scalpel/autonomy_audit" ".code-scalpel/"
        echo -e "${GREEN}  ✓ Copied autonomy_audit/${NC}"
    fi
fi

# 5. Copy README if it doesn't exist
echo ""
echo "5. Checking README..."
if [[ -f ".scalpel/README.md" ]] && [[ ! -f ".code-scalpel/README.md" ]]; then
    cp ".scalpel/README.md" ".code-scalpel/README.md"
    echo -e "${GREEN}  ✓ Copied README.md${NC}"
else
    echo "  → README.md already exists or not needed"
fi

# 6. Verify migration
echo ""
echo "6. Verification..."
echo ""
echo "  .code-scalpel/ contents:"
ls -1 .code-scalpel/ | sed 's/^/    /'

# 7. Backup and archive old directory
echo ""
echo "7. Cleaning up..."
read -p "Archive .scalpel/ directory? (creates .scalpel.backup/) (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [[ -d ".scalpel.backup" ]]; then
        rm -rf ".scalpel.backup"
    fi
    mv ".scalpel" ".scalpel.backup"
    echo -e "${GREEN}  ✓ Archived .scalpel/ → .scalpel.backup/${NC}"
    echo ""
    echo -e "${YELLOW}  Note: You can delete .scalpel.backup/ after verification${NC}"
else
    echo -e "${YELLOW}  → Keeping .scalpel/ directory${NC}"
    echo ""
    echo -e "${YELLOW}  Note: Both .scalpel/ and .code-scalpel/ will coexist${NC}"
    echo -e "${YELLOW}  Code Scalpel v3.0.0+ uses .code-scalpel/ by default${NC}"
fi

# 8. Environment variable check
echo ""
echo "8. Environment variable check..."
if [[ -n "${SCALPEL_CONFIG:-}" ]]; then
    echo -e "${YELLOW}  ⚠ SCALPEL_CONFIG is set: $SCALPEL_CONFIG${NC}"
    echo "  → Update to: .code-scalpel/config.json"
    echo "  → Or unset to use default"
fi

if [[ -n "${SCALPEL_CONFIG_HASH:-}" ]]; then
    echo -e "${YELLOW}  ⚠ SCALPEL_CONFIG_HASH is set${NC}"
    echo "  → Regenerate hash for .code-scalpel/config.json:"
    echo "    export SCALPEL_CONFIG_HASH=\"sha256:\$(sha256sum .code-scalpel/config.json | cut -d' ' -f1)\""
fi

# 9. Success message
echo ""
echo "================================================================="
echo -e "${GREEN}✓ Migration complete!${NC}"
echo "================================================================="
echo ""
echo "Next steps:"
echo "  1. Verify files in .code-scalpel/ are correct"
echo "  2. Update environment variables if needed"
echo "  3. Test with: python -m code_scalpel --validate-config"
echo "  4. Remove .scalpel.backup/ when satisfied"
echo ""
echo "Documentation:"
echo "  - .code-scalpel/README.md - Complete configuration guide"
echo "  - docs/Configuration_Guide.md"
echo "  - docs/policy_engine_guide.md"
echo ""
