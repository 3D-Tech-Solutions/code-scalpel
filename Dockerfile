# Code Scalpel MCP Server Dockerfile
# Multi-stage build for smaller image size
#
# This container runs the MCP-compliant server using streamable-http transport.
# For local development, use stdio transport directly (no container needed).
#
# [20251215_FEATURE] HTTPS Support:
# Mount SSL certificates and set environment variables:
#   -v /path/to/certs:/certs:ro
#   -e SSL_CERT=/certs/cert.pem
#   -e SSL_KEY=/certs/key.pem

FROM python:3.10-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Install the package
COPY . .
RUN pip install --no-cache-dir --user -e .

# Production stage
FROM python:3.10-slim

WORKDIR /app

# Install curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
COPY --from=builder /app /app

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Expose the MCP server port (8593) and health port (8594)
EXPOSE 8593 8594

# [20251215_FEATURE] SSL certificate paths (optional, for HTTPS)
# Set these environment variables to enable HTTPS:
#   SSL_CERT=/certs/cert.pem
#   SSL_KEY=/certs/key.pem
ENV SSL_CERT=""
ENV SSL_KEY=""

# [20251215_BUGFIX] Health check using dedicated /health endpoint
# The SSE endpoint stays open indefinitely, causing health checks to timeout.
# The health endpoint returns immediately with server status.
# Health server runs on MCP port + 1 (8594 by default)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8594/health || exit 1

# Default project root inside container
ENV SCALPEL_ROOT=/app/code

# [20251215_FEATURE] Entrypoint script to handle SSL configuration
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
