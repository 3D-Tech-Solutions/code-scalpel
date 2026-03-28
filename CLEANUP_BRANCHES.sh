#!/bin/bash
# Branch Cleanup Script for Code-Scalpel Repository
# This script safely removes stale branches based on analysis
# Generated: 2026-03-28

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Code-Scalpel Branch Cleanup ===${NC}"
echo "Generated from BRANCH_AND_PR_ANALYSIS.md"
echo ""

# Verify we're in the right repository
if [ ! -f "pyproject.toml" ] || ! grep -q "code-scalpel" pyproject.toml 2>/dev/null; then
    echo -e "${RED}ERROR: Not in code-scalpel repository root${NC}"
    exit 1
fi

# Get current branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo -e "${RED}ERROR: Not on main branch (currently on $CURRENT_BRANCH)${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Verified: in code-scalpel repo on main branch${NC}"
echo ""

# Function to delete local branch
delete_local_branch() {
    local branch=$1
    if git show-ref --verify --quiet "refs/heads/$branch"; then
        echo -n "  Deleting local: $branch ... "
        if git branch -d "$branch" 2>/dev/null; then
            echo -e "${GREEN}✓${NC}"
            return 0
        else
            echo -e "${RED}✗ (in use or not found)${NC}"
            return 1
        fi
    fi
}

# Function to delete remote branch
delete_remote_branch() {
    local branch=$1
    if git ls-remote --heads origin "$branch" | grep -q .; then
        echo -n "  Deleting remote: $branch ... "
        if git push origin --delete "$branch" 2>/dev/null; then
            echo -e "${GREEN}✓${NC}"
            return 0
        else
            echo -e "${RED}✗ (failed)${NC}"
            return 1
        fi
    fi
}

# Phase 1: Delete stale refactor branches (17 branches)
echo -e "${YELLOW}Phase 1: Delete Stale Refactor Branches (Created 2026-02-03 and 2026-02-18)${NC}"
echo "These branches are 40-65 commits behind main and were never merged."
echo ""

STALE_BRANCHES=(
    "refactor/foo_20260203_142024"
    "refactor/foo_20260203_142053"
    "refactor/foo_20260203_142123"
    "refactor/foo_20260203_142151"
    "refactor/add_numbers_20260203_142235"
    "refactor/add_numbers_20260218_155925"
    "refactor/add_numbers_20260218_160326"
    "refactor/add_numbers_20260218_160555"
    "refactor/add_numbers_20260218_160608"
    "refactor/add_numbers_20260218_161203"
    "refactor/add_numbers_20260218_161650"
    "refactor/add_numbers_20260218_161831"
    "refactor/add_numbers_20260218_161954"
    "refactor/foo_20260218_162017"
    "refactor/foo_20260218_162053"
    "refactor/foo_20260218_162126"
)

echo "Deleting ${#STALE_BRANCHES[@]} stale branches..."
for branch in "${STALE_BRANCHES[@]}"; do
    delete_local_branch "$branch"
done

echo ""
echo -e "${GREEN}✓ Phase 1 complete: ${#STALE_BRANCHES[@]} stale branches deleted${NC}"
echo ""

# Phase 2: Delete merged refactor branch
echo -e "${YELLOW}Phase 2: Delete Merged Refactor Branch${NC}"
echo "refactor/foo_20260218_162159 was merged via PR #5. Work is already on main."
echo ""

delete_local_branch "refactor/foo_20260218_162159"
delete_remote_branch "refactor/foo_20260218_162159"

echo ""
echo -e "${GREEN}✓ Phase 2 complete${NC}"
echo ""

# Phase 3: Prune old remote tracking branches
echo -e "${YELLOW}Phase 3: Prune Merged Remote Branches${NC}"
echo "Cleaning up remote branches for merged PRs."
echo ""

delete_remote_branch "dependabot/npm_and_yarn/vscode-extension/qs-6.14.2"

echo ""
echo -e "${GREEN}✓ Phase 3 complete${NC}"
echo ""

# Phase 4: Optional - Delete release variant branches
echo -e "${YELLOW}Phase 4: Optional - Delete Release Variant Branches${NC}"
echo ""
echo "These are local test/backup variants of release-2.1.2:"
echo "  - release-2.1.2-clean"
echo "  - release-2.1.2-mainbase"
echo ""
read -p "Delete release variant branches? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    delete_local_branch "release-2.1.2-clean"
    delete_local_branch "release-2.1.2-mainbase"
    echo -e "${GREEN}✓ Release variant branches deleted${NC}"
else
    echo "Skipped release variant deletion"
fi

echo ""

# Summary
echo -e "${BLUE}=== Cleanup Summary ===${NC}"
echo ""
echo "Local branches remaining:"
git branch | wc -l
echo ""

echo "Remote branches tracked:"
git branch -r | wc -l
echo ""

echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo "1. Verify branch list looks clean:"
echo "   git branch -a"
echo ""
echo "2. If you have local changes ahead of origin/main, push them:"
echo "   git push origin main"
echo ""
echo "3. Optionally, enable auto-pruning in git config:"
echo "   git config --global fetch.prune true"
echo ""
echo "4. Update your local tracking:"
echo "   git fetch --prune"
echo ""
echo -e "${GREEN}✓ Cleanup complete!${NC}"
