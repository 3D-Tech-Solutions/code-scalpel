#!/usr/bin/env bash
# Code Scalpel × Claude Code Integration Setup
#
# Usage:
#   bash setup.sh                 # Install to current directory
#   bash setup.sh /path/to/project    # Install to specific project
#
# Or pipe from GitHub:
#   curl -fsSL https://raw.githubusercontent.com/3D-Tech-Solutions/code-scalpel/main/integration/claude-code/setup.sh | bash

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}🔬 Code Scalpel × Claude Code Integration${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Get script directory (works when piped from curl too)
if [ -f "$(dirname "${BASH_SOURCE[0]}")/CLAUDE.md" ]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
else
    # If run via curl, download files to temp directory
    SCRIPT_DIR=$(mktemp -d)
    cd "$SCRIPT_DIR"
    curl -fsSL https://api.github.com/repos/3D-Tech-Solutions/code-scalpel/contents/integration/claude-code \
        | jq -r '.[] | select(.type=="file") | .download_url' \
        | xargs -I {} curl -fsSL -O {}
    for skill in cs-setup cs-extract cs-analyze cs-security cs-tests cs-refactor cs-map cs-policy; do
        mkdir -p "skills/$skill"
        curl -fsSL -o "skills/$skill/SKILL.md" \
            "https://raw.githubusercontent.com/3D-Tech-Solutions/code-scalpel/main/integration/claude-code/skills/$skill/SKILL.md"
    done
fi

PROJECT_DIR="${1:-.}"
SKILLS_DIR="$PROJECT_DIR/.claude/skills"

# Ensure PROJECT_DIR exists
if [ ! -d "$PROJECT_DIR" ]; then
    print_error "Project directory does not exist: $PROJECT_DIR"
    exit 1
fi

print_header
echo ""

# Step 1: Check if Claude Code is installed
print_info "Checking for Claude Code CLI..."
if ! command -v claude &> /dev/null; then
    print_error "Claude Code CLI not found. Install it from: https://github.com/anthropics/claude-code"
    echo "  curl -fsSL https://install.anthropic.com | bash"
    exit 1
fi
print_success "Claude Code CLI found: $(claude --version)"
echo ""

# Step 2: Check if MCP is already installed
print_info "Checking if Code Scalpel MCP is already installed..."
if claude mcp list 2>/dev/null | grep -q "codescalpel"; then
    print_success "Code Scalpel MCP already installed"
else
    print_warning "Code Scalpel MCP not found, installing..."

    # Optional: Prompt for license path
    read -p "Do you have a license file? (y/n) " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter path to license.jwt file: " LICENSE_PATH
        if [ ! -f "$LICENSE_PATH" ]; then
            print_error "License file not found: $LICENSE_PATH"
            exit 1
        fi
        print_info "Installing with license..."
        claude mcp add codescalpel \
            -e "CODE_SCALPEL_LICENSE_PATH=$LICENSE_PATH" \
            uvx codescalpel mcp 2>/dev/null || true
    else
        print_info "Installing Community edition..."
        claude mcp add codescalpel uvx codescalpel mcp 2>/dev/null || true
    fi

    # Verify installation
    if claude mcp list 2>/dev/null | grep -q "codescalpel"; then
        print_success "Code Scalpel MCP installed successfully"
    else
        print_warning "MCP installation may require a Claude Code reload"
    fi
fi
echo ""

# Step 3: Create skills directory structure
print_info "Setting up skills directory..."
mkdir -p "$SKILLS_DIR"
print_success "Skills directory created: $SKILLS_DIR"
echo ""

# Step 4: Copy skill files
print_info "Installing 8 Code Scalpel skills..."
for skill in cs-setup cs-extract cs-analyze cs-security cs-tests cs-refactor cs-map cs-policy; do
    if [ -d "$SCRIPT_DIR/skills/$skill" ]; then
        cp -r "$SCRIPT_DIR/skills/$skill" "$SKILLS_DIR/"
        print_success "Installed: /$skill"
    else
        print_warning "Skill directory not found: $skill (skipping)"
    fi
done
echo ""

# Step 5: Copy CLAUDE.md if not present
print_info "Checking for CLAUDE.md in project root..."
if [ -f "$PROJECT_DIR/CLAUDE.md" ]; then
    print_warning "CLAUDE.md already exists in $PROJECT_DIR (not overwriting)"
else
    if [ -f "$SCRIPT_DIR/CLAUDE.md" ]; then
        cp "$SCRIPT_DIR/CLAUDE.md" "$PROJECT_DIR/CLAUDE.md"
        print_success "CLAUDE.md installed to project root"
    else
        print_warning "CLAUDE.md template not found (skipping)"
    fi
fi
echo ""

# Step 6: Final verification
print_info "Verifying installation..."
SKILLS_COUNT=$(ls -1 "$SKILLS_DIR" 2>/dev/null | wc -l)
if [ "$SKILLS_COUNT" -ge 8 ]; then
    print_success "All skills installed: $SKILLS_COUNT skills found"
else
    print_warning "Expected 8 skills, found $SKILLS_COUNT"
fi

# Verify MCP connection
if command -v python3 &> /dev/null; then
    print_info "Attempting MCP connection test..."
    # This is a best-effort test; don't fail if it doesn't work
    python3 -c "from code_scalpel.mcp.server import FastMCPServer; print('✓ Code Scalpel MCP is accessible')" 2>/dev/null || print_warning "Could not verify MCP connection (this is OK)"
fi
echo ""

# Summary
print_header
echo ""
echo -e "${GREEN}✅ Installation Complete!${NC}"
echo ""
echo "Next steps:"
echo ""
echo "1. ${BLUE}Reload Claude Code${NC}"
echo "   Close and reopen Claude Code to discover new skills"
echo ""
echo "2. ${BLUE}Verify installation${NC}"
echo "   Run: /cs-setup"
echo "   This will show your license tier and available tools"
echo ""
echo "3. ${BLUE}Try your first extraction${NC}"
echo "   Run: /cs-extract [path/to/file] function [function_name]"
echo "   Example: /cs-extract src/utils.py function validate_email"
echo ""
echo "4. ${BLUE}Read the guide${NC}"
echo "   Open $PROJECT_DIR/CLAUDE.md for complete documentation"
echo ""
echo "Documentation:"
echo "  • Tool Reference: https://github.com/3D-Tech-Solutions/code-scalpel/tree/main/docs"
echo "  • GitHub: https://github.com/3D-Tech-Solutions/code-scalpel"
echo "  • Issues: https://github.com/3D-Tech-Solutions/code-scalpel/issues"
echo ""
echo -e "${GREEN}Happy analyzing! 🔬${NC}"
echo ""
