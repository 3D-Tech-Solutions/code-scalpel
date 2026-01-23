#!/bin/bash
# Code Scalpel Docker Entrypoint
# [20251215_FEATURE] Handles SSL/HTTPS configuration for production deployments

set -e

# Build the command with required arguments
CMD="code-scalpel mcp --http --host 0.0.0.0 --port 8593 --allow-lan"

# Add root path if SCALPEL_ROOT is set
if [ -n "$SCALPEL_ROOT" ]; then
    CMD="$CMD --root $SCALPEL_ROOT"
elif [ -d "/workspace" ]; then
    CMD="$CMD --root /workspace"
else
    CMD="$CMD --root /app/code"
fi

# Add SSL certificates if both are provided
if [ -n "$SSL_CERT" ] && [ -n "$SSL_KEY" ]; then
    if [ -f "$SSL_CERT" ] && [ -f "$SSL_KEY" ]; then
        echo "HTTPS enabled: Using SSL certificates"
        echo "  Certificate: $SSL_CERT"
        echo "  Private Key: $SSL_KEY"
        CMD="$CMD --ssl-cert $SSL_CERT --ssl-key $SSL_KEY"
    else
        echo "WARNING: SSL_CERT or SSL_KEY file not found, falling back to HTTP"
        echo "  SSL_CERT=$SSL_CERT (exists: $([ -f "$SSL_CERT" ] && echo yes || echo no))"
        echo "  SSL_KEY=$SSL_KEY (exists: $([ -f "$SSL_KEY" ] && echo yes || echo no))"
    fi
else
    echo "HTTP mode: No SSL certificates configured"
    echo "  For HTTPS, set SSL_CERT and SSL_KEY environment variables"
fi

echo "Starting Code Scalpel MCP Server..."
echo "Command: $CMD"
echo ""

# Execute the command
exec $CMD
