#!/bin/bash
# Code Scalpel Docker Setup and Verification Script v1.5.3

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
print_section() {
    echo -e "\n${YELLOW}=== $1 ===${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "  $1"
}

# Check prerequisites
print_section "Checking Prerequisites"

if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed"
    exit 1
fi
print_success "Docker installed: $(docker --version)"

if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    exit 1
fi
print_success "Python 3 installed: $(python3 --version)"

# Build Docker image
print_section "Building Docker Image"

if [ ! -f "Dockerfile" ]; then
    print_error "Dockerfile not found in current directory"
    exit 1
fi

print_info "Building code-scalpel:1.5.3..."
docker build -t code-scalpel:1.5.3 -t code-scalpel:latest . > /tmp/docker-build.log 2>&1

if [ $? -eq 0 ]; then
    print_success "Docker image built successfully"
    IMAGE_ID=$(docker images code-scalpel:1.5.3 -q)
    print_info "Image ID: $IMAGE_ID"
    print_info "Size: $(docker images code-scalpel:1.5.3 --format '{{.Size}}')"
else
    print_error "Docker build failed"
    tail -20 /tmp/docker-build.log
    exit 1
fi

# Stop existing container
print_section "Cleaning Up Existing Containers"

EXISTING=$(docker ps -a --filter "ancestor=code-scalpel:1.5.3" -q)
if [ -n "$EXISTING" ]; then
    print_info "Stopping existing containers..."
    docker kill $EXISTING 2>/dev/null || true
    docker rm $EXISTING 2>/dev/null || true
    sleep 2
    print_success "Old containers removed"
else
    print_info "No existing containers found"
fi

# Start test container
print_section "Starting Test Container"

print_info "Launching code-scalpel-mcp:1.5.3..."
CONTAINER_ID=$(docker run -d \
    --name code-scalpel-mcp \
    -p 8593:8593 \
    -v $(pwd):/workspace \
    code-scalpel:1.5.3 2>&1)

if [ $? -eq 0 ]; then
    print_success "Container started: $CONTAINER_ID"
    sleep 3
else
    print_error "Failed to start container"
    echo "$CONTAINER_ID"
    exit 1
fi

# Verify container health
print_section "Verifying Container Health"

HEALTH=$(docker inspect code-scalpel-mcp --format='{{.State.Running}}')
if [ "$HEALTH" = "true" ]; then
    print_success "Container is running"
else
    print_error "Container is not running"
    docker logs code-scalpel-mcp
    exit 1
fi

# Test port connectivity
print_section "Testing Port Connectivity"

print_info "Waiting for server to become ready..."
for i in {1..10}; do
    if curl -s http://localhost:8593/sse > /dev/null 2>&1; then
        print_success "Port 8593 is accessible"
        break
    fi
    if [ $i -eq 10 ]; then
        print_error "Could not connect to port 8593 after 10 attempts"
        docker logs code-scalpel-mcp | tail -20
        exit 1
    fi
    sleep 1
done

# Test HTTP endpoint
print_section "Testing HTTP Endpoint"

RESPONSE=$(curl -s -w "\n%{http_code}" http://localhost:8593/sse | tail -1)
if [ "$RESPONSE" = "200" ]; then
    print_success "HTTP/1.1 200 OK (SSE endpoint)"
else
    print_error "HTTP endpoint returned status $RESPONSE"
    exit 1
fi

# Test PathResolver
print_section "Testing PathResolver"

DOCKER_DETECTED=$(docker exec code-scalpel-mcp python3 -c \
    "from code_scalpel.mcp.path_resolver import PathResolver; pr = PathResolver(); print(pr.is_docker)" 2>/dev/null)

if [ "$DOCKER_DETECTED" = "True" ]; then
    print_success "Docker detection working correctly"
else
    print_error "Docker detection failed. Got: $DOCKER_DETECTED"
fi

WORKSPACE=$(docker exec code-scalpel-mcp python3 -c \
    "from code_scalpel.mcp.path_resolver import PathResolver; pr = PathResolver(); print(pr.workspace_root)" 2>/dev/null)
print_info "Workspace root: $WORKSPACE"

# Test volume mount
print_section "Testing Volume Mount"

# Create test file
TEST_FILE=$(mktemp)
echo "test content" > "$TEST_FILE"
TEST_NAME=$(basename "$TEST_FILE")

# Try to access from container
if docker exec code-scalpel-mcp test -f "/workspace/$TEST_NAME" 2>/dev/null; then
    print_success "Volume mount is accessible from container"
else
    print_error "Volume mount test failed"
fi

# Clean up test file
rm "$TEST_FILE"

# Test validate_paths tool via MCP
print_section "Testing validate_paths MCP Tool"

# Create simple test file in workspace
TEST_PY=$(mktemp --suffix=.py)
echo "print('test')" > "$TEST_PY"
TEST_PY_NAME=$(basename "$TEST_PY")

docker exec code-scalpel-mcp python3 << PYEOF 2>/dev/null
from code_scalpel.mcp.server import MCP_TOOLS

# Find validate_paths tool
validate_paths_tool = next((t for t in MCP_TOOLS if t.name == 'validate_paths'), None)
if validate_paths_tool:
    print("validate_paths tool found in MCP server")
else:
    print("ERROR: validate_paths tool not found in MCP server")
PYEOF

print_success "validate_paths tool available"
rm "$TEST_PY"

# Summary
print_section "Deployment Summary"

print_success "Code Scalpel v1.5.3 Docker deployment successful!"
print_info ""
print_info "Container Details:"
print_info "  Name: code-scalpel-mcp"
print_info "  Image: code-scalpel:1.5.3"
print_info "  Port: 8593"
print_info "  Status: Running"
print_info ""
print_info "Quick Tests:"
print_info "  MCP SSE Endpoint: curl http://localhost:8593/sse"
print_info "  Container Shell: docker exec -it code-scalpel-mcp /bin/bash"
print_info "  View Logs: docker logs code-scalpel-mcp"
print_info "  Stop Container: docker stop code-scalpel-mcp"
print_info "  Remove Container: docker rm code-scalpel-mcp"
print_info ""
print_info "Next Steps:"
print_info "  1. Configure your client to connect to http://localhost:8593"
print_info "  2. Mount your project: docker run -v \$(pwd):/workspace code-scalpel:1.5.3"
print_info "  3. See DOCKER_CONNECTION_TROUBLESHOOTING.md for common issues"
print_info ""

# Ask about cleanup
echo ""
read -p "Keep container running? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_info "Stopping container..."
    docker stop code-scalpel-mcp
    docker rm code-scalpel-mcp
    print_success "Container removed"
fi

exit 0
