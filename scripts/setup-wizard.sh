#!/bin/bash
# Code Scalpel Quick Setup Wizard
# For non-technical users, especially those using Claude Code
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/tescolopio/code-scalpel/main/scripts/setup-wizard.sh | bash
#   OR
#   ./setup-wizard.sh [--license <path>] [--tier pro|enterprise] [--claude-hooks]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print functions
print_header() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  Code Scalpel Setup Wizard${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

print_step() {
    echo -e "${GREEN}[STEP $1]${NC} $2"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Default values
LICENSE_PATH=""
TIER=""
INSTALL_CLAUDE_HOOKS=false
PROJECT_DIR="."
INTERACTIVE=true

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --license)
            LICENSE_PATH="$2"
            shift 2
            ;;
        --tier)
            TIER="$2"
            shift 2
            ;;
        --claude-hooks)
            INSTALL_CLAUDE_HOOKS=true
            shift
            ;;
        --dir)
            PROJECT_DIR="$2"
            shift 2
            ;;
        --non-interactive)
            INTERACTIVE=false
            shift
            ;;
        --help|-h)
            echo "Code Scalpel Setup Wizard"
            echo ""
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --license <path>     Path to license JWT file (Pro/Enterprise)"
            echo "  --tier <tier>        Tier to use: community, pro, enterprise"
            echo "  --claude-hooks       Install Claude Code governance hooks"
            echo "  --dir <path>         Project directory (default: current directory)"
            echo "  --non-interactive    Skip interactive prompts"
            echo "  --help, -h           Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

print_header

# Check if code-scalpel is installed
print_step "1/5" "Checking Code Scalpel installation..."

if command -v code-scalpel &> /dev/null; then
    VERSION=$(code-scalpel version 2>/dev/null | head -1)
    print_success "Found: $VERSION"
else
    print_warning "Code Scalpel not found in PATH"

    if $INTERACTIVE; then
        echo ""
        echo "Would you like to install Code Scalpel? (requires pip)"
        read -p "[Y/n]: " INSTALL_CHOICE

        if [[ "$INSTALL_CHOICE" != "n" && "$INSTALL_CHOICE" != "N" ]]; then
            echo "Installing Code Scalpel..."
            pip install code-scalpel
            print_success "Code Scalpel installed successfully"
        else
            print_error "Cannot continue without Code Scalpel installed"
            exit 1
        fi
    else
        echo "Installing Code Scalpel..."
        pip install code-scalpel
        print_success "Code Scalpel installed successfully"
    fi
fi

# Initialize .code-scalpel directory
print_step "2/5" "Initializing configuration directory..."

cd "$PROJECT_DIR"

if [ -d ".code-scalpel" ]; then
    print_warning ".code-scalpel directory already exists"

    if $INTERACTIVE; then
        read -p "Keep existing configuration? [Y/n]: " KEEP_CONFIG
        if [[ "$KEEP_CONFIG" == "n" || "$KEEP_CONFIG" == "N" ]]; then
            rm -rf .code-scalpel
            code-scalpel init
            print_success "Configuration directory re-initialized"
        else
            print_info "Keeping existing configuration"
        fi
    else
        print_info "Keeping existing configuration"
    fi
else
    code-scalpel init > /dev/null 2>&1
    print_success "Created .code-scalpel directory with default configuration"
fi

# License setup
print_step "3/5" "Configuring license..."

if [ -n "$LICENSE_PATH" ]; then
    # License provided via argument
    if [ -f "$LICENSE_PATH" ]; then
        code-scalpel license install "$LICENSE_PATH" --force
        print_success "License installed from: $LICENSE_PATH"
    else
        print_error "License file not found: $LICENSE_PATH"
        exit 1
    fi
elif $INTERACTIVE; then
    echo ""
    echo "License options:"
    echo "  1) Community (free) - Basic features, no license needed"
    echo "  2) Pro - Enhanced features (requires license file)"
    echo "  3) Enterprise - Full features (requires license file)"
    echo ""
    read -p "Select tier [1/2/3] (default: 1): " TIER_CHOICE

    case $TIER_CHOICE in
        2|3)
            echo ""
            read -p "Enter path to your license.jwt file: " USER_LICENSE_PATH

            if [ -f "$USER_LICENSE_PATH" ]; then
                code-scalpel license install "$USER_LICENSE_PATH"
                print_success "License installed successfully"
            else
                print_error "License file not found: $USER_LICENSE_PATH"
                print_warning "Continuing with Community tier"
            fi
            ;;
        *)
            print_info "Using Community tier (no license required)"
            ;;
    esac
else
    print_info "Using Community tier (no license provided)"
fi

# Set tier in config if specified
if [ -n "$TIER" ]; then
    print_step "3b/5" "Setting tier to: $TIER"

    # Update config.json with tier
    CONFIG_FILE=".code-scalpel/config.json"
    if [ -f "$CONFIG_FILE" ]; then
        # Use Python to update JSON (portable)
        python3 -c "
import json
with open('$CONFIG_FILE', 'r') as f:
    config = json.load(f)
config['tier'] = '$TIER'
with open('$CONFIG_FILE', 'w') as f:
    json.dump(config, f, indent=2)
" 2>/dev/null && print_success "Tier set to: $TIER" || print_warning "Could not update config.json"
    fi
fi

# Claude Code hooks setup
print_step "4/5" "Configuring Claude Code integration..."

if $INSTALL_CLAUDE_HOOKS; then
    code-scalpel install-hooks --force 2>/dev/null && \
        print_success "Claude Code hooks installed" || \
        print_warning "Could not install Claude Code hooks (may not be in a Claude Code environment)"
elif $INTERACTIVE; then
    echo ""
    echo "Claude Code hooks provide:"
    echo "  - Pre-tool governance (validate operations before execution)"
    echo "  - Post-tool audit logging (track all AI agent operations)"
    echo ""
    read -p "Install Claude Code governance hooks? [y/N]: " INSTALL_HOOKS_CHOICE

    if [[ "$INSTALL_HOOKS_CHOICE" == "y" || "$INSTALL_HOOKS_CHOICE" == "Y" ]]; then
        code-scalpel install-hooks 2>/dev/null && \
            print_success "Claude Code hooks installed" || \
            print_warning "Could not install hooks (Claude Code may not be configured)"
    else
        print_info "Skipping Claude Code hooks"
    fi
else
    print_info "Skipping Claude Code hooks (use --claude-hooks to install)"
fi

# MCP server configuration
print_step "5/5" "Configuring MCP server..."

# Create a quick-start script
cat > .code-scalpel/start-mcp.sh << 'SCRIPT_EOF'
#!/bin/bash
# Quick start script for Code Scalpel MCP server
# Run this to start the MCP server for Claude Desktop or other MCP clients

echo "Starting Code Scalpel MCP Server..."
echo "Press Ctrl+C to stop"
echo ""

# Check for license
if [ -f ~/.config/code-scalpel/license.jwt ]; then
    code-scalpel mcp --license-file ~/.config/code-scalpel/license.jwt
else
    code-scalpel mcp
fi
SCRIPT_EOF
chmod +x .code-scalpel/start-mcp.sh

print_success "Created .code-scalpel/start-mcp.sh for quick MCP server startup"

# Final summary
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Setup Complete!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Configuration created in: $(pwd)/.code-scalpel/"
echo ""
echo "Quick start commands:"
echo ""
echo "  Start MCP server (for Claude Desktop):"
echo "    code-scalpel mcp"
echo ""
echo "  Analyze a file:"
echo "    code-scalpel analyze myfile.py"
echo ""
echo "  Security scan:"
echo "    code-scalpel scan myfile.py"
echo ""

# Check if Claude Desktop config exists and offer to update it
CLAUDE_CONFIG_DIR=""
if [ -d "$HOME/.config/claude" ]; then
    CLAUDE_CONFIG_DIR="$HOME/.config/claude"
elif [ -d "$HOME/Library/Application Support/Claude" ]; then
    CLAUDE_CONFIG_DIR="$HOME/Library/Application Support/Claude"
fi

if [ -n "$CLAUDE_CONFIG_DIR" ]; then
    echo "Detected Claude Desktop at: $CLAUDE_CONFIG_DIR"
    echo ""
    echo "To add Code Scalpel to Claude Desktop, add this to your config:"
    echo ""
    echo '  "mcpServers": {'
    echo '    "code-scalpel": {'
    echo '      "command": "code-scalpel",'
    echo '      "args": ["mcp"]'
    echo '    }'
    echo '  }'
    echo ""
fi

echo "For more help: code-scalpel --help"
echo "Documentation: https://github.com/tescolopio/code-scalpel"
echo ""
