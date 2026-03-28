# Code Scalpel MCP Deployment Guide

**Complete guide for deploying Code Scalpel across IDEs, AI agents, and cloud infrastructure**

**Version**: 1.0
**Last Updated**: 2026-02-06
**Code Scalpel Version**: 1.3.4+

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Desktop IDE Deployment](#desktop-ide-deployment)
   - [Claude Desktop](#claude-desktop)
   - [VS Code (Cline/Roo Code)](#vs-code-clineroo-code)
   - [Cursor](#cursor)
   - [JetBrains IDEs](#jetbrains-ides)
   - [Zed Editor](#zed-editor)
4. [AI Agent Framework Integration](#ai-agent-framework-integration)
   - [OpenAI Agents SDK](#openai-agents-sdk)
   - [LangChain/LangGraph](#langchainlanggraph)
   - [Google Agent Development Kit](#google-agent-development-kit)
   - [Claude Agent SDK](#claude-agent-sdk)
5. [Remote Infrastructure Deployment](#remote-infrastructure-deployment)
   - [Fly.io](#flyio)
   - [AWS Lambda](#aws-lambda)
   - [Docker Containers](#docker-containers)
   - [Kubernetes](#kubernetes)
6. [Configuration Reference](#configuration-reference)
7. [Troubleshooting](#troubleshooting)
8. [Security Best Practices](#security-best-practices)

---

## Prerequisites

### System Requirements

**Required**:
- **Python**: 3.10 or higher
- **Package Manager**: `uv` (recommended) or `pip`
- **Operating System**: Linux, macOS, or Windows with WSL2

**Optional** (for advanced features):
- **Docker**: For containerized deployment
- **Node.js**: v16+ (if using TypeScript-based MCP clients)

### Install Code Scalpel

```bash
# Using uv (recommended)
uv pip install codescalpel

# Using pip
pip install codescalpel

# Verify installation
codescalpel --version
# Should output: code-scalpel v1.3.4 (or later)

# Test MCP server
uvx code-scalpel mcp
# Should start the MCP server without errors
```

### License Configuration

Code Scalpel operates in three tiers:

1. **Community** (Free) - All tools available with basic limits
2. **Pro** ($19/month) - Enhanced capabilities and expanded limits
3. **Enterprise** (Custom) - Pro-scale limits plus governance, audit, and compliance features

**Configure your tier** (optional - defaults to Community):

```bash
# Set license key (Pro/Enterprise only)
export CODE_SCALPEL_LICENSE_KEY="your-license-key-here"

# Verify tier
codescalpel tier-info
```

**Tier configuration file** (for persistence):

Create `.code-scalpel/license.json` in your project root:

```json
{
  "tier": "pro",
  "license_key": "your-license-key-here",
  "email": "your-email@example.com"
}
```

---

## Quick Start

### 1. Test the MCP Server

```bash
# Start the server manually
uvx code-scalpel mcp

# You should see:
# Code Scalpel MCP Server v1.3.4
# Tier: community
# Tools: 22 available
# Listening on stdio...
```

Press `Ctrl+C` to stop.

### 2. Test a Tool

Create a test Python file:

```bash
cat > test.py << 'EOF'
def hello(name: str) -> str:
    """Greet someone."""
    return f"Hello, {name}!"

class Greeter:
    def __init__(self, prefix: str):
        self.prefix = prefix

    def greet(self, name: str) -> str:
        return f"{self.prefix} {name}!"
EOF
```

Test the `analyze_code` tool:

```bash
# Using the MCP inspector
uvx @modelcontextprotocol/inspector uvx code-scalpel mcp
```

This opens a web UI at `http://localhost:6274` where you can:
- See all 22+ tools
- Test `analyze_code` on `test.py`
- Verify Code Scalpel is working correctly

---

## Desktop IDE Deployment

### Claude Desktop

**Official Anthropic IDE with native MCP support**

#### Configuration

1. **Locate config file**:
   ```bash
   # macOS
   open ~/Library/Application\ Support/Claude/

   # Windows
   explorer %APPDATA%\Claude\

   # Linux (if available)
   xdg-open ~/.config/Claude/
   ```

2. **Edit `claude_desktop_config.json`**:

   ```json
   {
     "mcpServers": {
       "code-scalpel": {
         "command": "uvx",
         "args": ["code-scalpel", "mcp"],
         "env": {
           "CODE_SCALPEL_LICENSE_KEY": "your-license-key-here"
         }
       }
     }
   }
   ```

3. **For custom project root**:

   ```json
   {
     "mcpServers": {
       "code-scalpel-myproject": {
         "command": "uvx",
         "args": ["code-scalpel", "mcp", "--project-root", "/path/to/myproject"]
       }
     }
   }
   ```

4. **Restart Claude Desktop** (fully quit and reopen)

5. **Verify**:
   - Open Claude Desktop
   - Type: "List available Code Scalpel tools"
   - You should see all 22+ tools listed

#### Project-Specific Configuration

**Best Practice**: Use one Code Scalpel server per project for proper isolation.

```json
{
  "mcpServers": {
    "code-scalpel-backend": {
      "command": "uvx",
      "args": ["code-scalpel", "mcp", "--project-root", "/Users/you/projects/backend"]
    },
    "code-scalpel-frontend": {
      "command": "uvx",
      "args": ["code-scalpel", "mcp", "--project-root", "/Users/you/projects/frontend"]
    }
  }
}
```

#### Troubleshooting

**Server not appearing**:
1. Check logs: `~/Library/Logs/Claude/mcp-server-code-scalpel.log` (macOS)
2. Verify `uvx code-scalpel mcp` works in terminal
3. Ensure JSON syntax is correct (no trailing commas)
4. Fully restart Claude (not just reload)

**Tools not working**:
1. Check tier limits: "Run `codescalpel tier-info` to see current tier"
2. Verify file paths are absolute, not relative
3. Check file permissions on project directory

---

### VS Code (Cline/Roo Code)

**Popular VS Code extensions with MCP support**

#### Using Cline Extension

1. **Install Cline**:
   - Open VS Code
   - Extensions → Search "Cline"
   - Install and reload

2. **Configure MCP Server**:
   - Open Command Palette (`Cmd+Shift+P` / `Ctrl+Shift+P`)
   - Search "Cline: Open MCP Settings"
   - Edit `mcp_settings.json`:

   ```json
   {
     "mcpServers": {
       "code-scalpel": {
         "command": "uvx",
         "args": ["code-scalpel", "mcp", "--project-root", "${workspaceFolder}"]
       }
     }
   }
   ```

3. **Using Workspace Variable**:
   ```json
   {
     "mcpServers": {
       "code-scalpel": {
         "command": "uvx",
         "args": [
           "code-scalpel",
           "mcp",
           "--project-root",
           "${workspaceFolder}"
         ],
         "env": {
           "CODE_SCALPEL_LICENSE_KEY": "${env:CODE_SCALPEL_LICENSE_KEY}"
         }
       }
     }
   }
   ```

4. **Reload Cline**: Command Palette → "Cline: Reload MCP Servers"

5. **Verify**:
   - Open Cline panel
   - Ask: "What Code Scalpel tools are available?"
   - Should list all tools

#### Using Roo Code Extension

Similar to Cline but with different settings location:

1. Install "Roo Code" extension
2. Settings → "Roo Code: MCP Servers"
3. Add Code Scalpel with same JSON structure as above

---

### Cursor

**AI-first IDE with native MCP support**

#### Configuration

1. **Open Cursor Settings**:
   - `Cmd+,` (macOS) or `Ctrl+,` (Windows/Linux)
   - Search "MCP"

2. **Add Code Scalpel Server**:
   - Navigate to "Features" → "Model Context Protocol"
   - Click "Add Server"
   - Fill in:
     - **Name**: `code-scalpel`
     - **Command Type**: `uvx`
     - **Command**: `code-scalpel`
     - **Args**: `mcp --project-root ${workspaceFolder}`

3. **Alternative: Manual JSON**:

   Edit Cursor's MCP config file (location varies by OS):

   ```json
   {
     "mcpServers": {
       "code-scalpel": {
         "command": "uvx",
         "args": ["code-scalpel", "mcp"]
       }
     }
   }
   ```

4. **Enable in Composer**:
   - Cursor's Composer agent will auto-discover Code Scalpel tools
   - Try: `@code-scalpel analyze this file`

#### Cursor-Specific Features

**Agent Rules Integration**:

Create `.cursorrules` in project root to guide Cursor on Code Scalpel usage:

```
When analyzing code:
- Use code-scalpel's analyze_code tool for structure analysis
- Use extract_code to get specific functions/classes
- Use security_scan before suggesting security-related changes
- Always check cross-file dependencies with get_cross_file_dependencies
```

**Tab Autocomplete**:
Cursor will suggest Code Scalpel tools in its autocomplete when relevant.

---

### JetBrains IDEs

**IntelliJ IDEA, PyCharm, WebStorm, etc.**

#### Using OpenMCP Client Plugin

1. **Install Plugin**:
   - File → Settings → Plugins
   - Search "OpenMCP Client"
   - Install and restart IDE

2. **Configure Server**:
   - Tools → MCP Servers
   - Add Server:
     - **Name**: Code Scalpel
     - **Command**: `uvx code-scalpel mcp`
     - **Working Directory**: `${PROJECT_DIR}`

3. **Access Tools**:
   - Right-click on file → "MCP Tools" → "Code Scalpel"
   - Or use the MCP tool window (View → Tool Windows → MCP)

#### Alternative: AI Assistant Integration

If using JetBrains AI Assistant:

1. Settings → Tools → AI Assistant → Advanced
2. Enable "External Tools Integration"
3. Add Code Scalpel as external tool with MCP protocol

---

### Zed Editor

**High-performance collaborative editor**

#### Configuration

Zed supports MCP via its settings file.

1. **Open Zed Settings**:
   - `Cmd+,` (macOS) or `Ctrl+,` (Windows/Linux)

2. **Edit `settings.json`**:

   ```json
   {
     "mcp": {
       "servers": {
         "code-scalpel": {
           "command": "uvx",
           "args": ["code-scalpel", "mcp"]
         }
       }
     }
   }
   ```

3. **Restart Zed**

4. **Access Tools**:
   - Open command palette (`Cmd+Shift+P`)
   - Type "MCP: Code Scalpel"
   - Select tool to run

---

## AI Agent Framework Integration

### OpenAI Agents SDK

**Build autonomous agents with Code Scalpel as tools**

#### Installation

```bash
pip install openai-agents-sdk code-scalpel
```

#### Basic Integration

```python
from agents import Agent
from code_scalpel.mcp.client import CodeScalpelMCPClient

# Initialize Code Scalpel MCP client
scalpel_client = CodeScalpelMCPClient(project_root="/path/to/project")

# Create agent with Code Scalpel tools
agent = Agent(
    name="Code Analyst",
    model="gpt-4o",
    instructions="""
    You are a code analysis expert. Use Code Scalpel tools to:
    - Analyze code structure
    - Extract specific functions/classes
    - Perform security scans
    - Generate call graphs
    """,
    tools=scalpel_client.get_tools()  # Auto-converts MCP tools to Agent tools
)

# Run agent
response = agent.run(
    "Analyze the user authentication module and identify security issues"
)

print(response.messages)
```

#### Advanced: Multi-Agent System

```python
from agents import Agent, handoff

# Security analyst agent
security_agent = Agent(
    name="Security Analyst",
    model="gpt-4o",
    tools=scalpel_client.get_tools(categories=["security"])
)

# Code refactoring agent
refactor_agent = Agent(
    name="Refactoring Expert",
    model="gpt-4o",
    tools=scalpel_client.get_tools(categories=["refactoring"])
)

# Master orchestrator
orchestrator = Agent(
    name="Code Review Orchestrator",
    model="gpt-4o",
    instructions="""
    Coordinate security analysis and refactoring:
    1. Hand off to Security Analyst for vulnerability scan
    2. If issues found, hand off to Refactoring Expert
    3. Verify fixes with another security scan
    """,
    tools=[
        handoff(security_agent),
        handoff(refactor_agent)
    ]
)

# Execute workflow
orchestrator.run("Review and fix authentication.py")
```

---

### LangChain/LangGraph

**Build stateful agents with Code Scalpel**

#### Installation

```bash
pip install langchain langchain-mcp langgraph code-scalpel
```

#### LangChain Integration

```python
from langchain_mcp import MCPToolkit
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

# Initialize Code Scalpel MCP toolkit
toolkit = MCPToolkit(
    server_command="uvx code-scalpel mcp",
    project_root="/path/to/project"
)

# Get LangChain tools
tools = toolkit.get_tools()

# Create agent
llm = ChatOpenAI(model="gpt-4o", temperature=0)
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a code analysis expert using Code Scalpel tools."),
    ("user", "{input}"),
    ("assistant", "{agent_scratchpad}")
])

agent = create_openai_functions_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# Execute
result = agent_executor.invoke({
    "input": "Find all security vulnerabilities in the payment processing module"
})

print(result["output"])
```

#### LangGraph State Machine

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
import operator

# Define state
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    project_root: str
    analysis_results: dict

# Define nodes
def analyze_code(state: AgentState):
    """Use Code Scalpel to analyze code."""
    toolkit = MCPToolkit(
        server_command="uvx code-scalpel mcp",
        project_root=state["project_root"]
    )
    analyze_tool = toolkit.get_tool("analyze_code")

    result = analyze_tool.run({
        "file_path": f"{state['project_root']}/main.py"
    })

    return {
        "analysis_results": result,
        "messages": [("assistant", f"Analysis complete: {result}")]
    }

def security_scan(state: AgentState):
    """Run security scan."""
    toolkit = MCPToolkit(
        server_command="uvx code-scalpel mcp",
        project_root=state["project_root"]
    )
    scan_tool = toolkit.get_tool("security_scan")

    result = scan_tool.run({
        "directory": state["project_root"]
    })

    return {
        "messages": [("assistant", f"Security scan: {result}")]
    }

# Build graph
workflow = StateGraph(AgentState)
workflow.add_node("analyze", analyze_code)
workflow.add_node("security", security_scan)

workflow.set_entry_point("analyze")
workflow.add_edge("analyze", "security")
workflow.add_edge("security", END)

# Compile and run
app = workflow.compile()

result = app.invoke({
    "project_root": "/path/to/project",
    "messages": []
})

print(result["messages"])
```

---

### Google Agent Development Kit

**Model-agnostic agent framework**

#### Installation

```bash
pip install google-adk code-scalpel
```

#### Configuration

```python
from adk import Agent
from adk.tools import MCPTool

# Define Code Scalpel as MCP tool
code_scalpel = MCPTool(
    name="code-scalpel",
    transport="stdio",
    command="uvx code-scalpel mcp",
    description="Advanced code analysis and manipulation tools"
)

# Create agent
agent = Agent(
    name="Code Reviewer",
    model="gemini-1.5-pro",
    tools=[code_scalpel],
    instructions="""
    You review code for quality, security, and maintainability.
    Use Code Scalpel tools to perform deep analysis.
    """
)

# Run
response = agent.run(
    "Review the codebase in /path/to/project for security issues"
)

print(response.text)
```

---

### Claude Agent SDK

**Build agents using Anthropic's Agent SDK**

#### Installation

```bash
pip install claude-agent-sdk code-scalpel
```

#### Basic Integration

```python
from claude_agent_sdk import Agent, Tool
from code_scalpel.mcp.tools import get_all_tools

# Get Code Scalpel tools
scalpel_tools = get_all_tools(project_root="/path/to/project")

# Create agent
agent = Agent(
    model="claude-sonnet-4-5",
    tools=scalpel_tools,
    system_prompt="""
    You are an expert code analyst. Use Code Scalpel tools to:
    - Analyze code architecture
    - Extract and refactor code
    - Perform security analysis
    - Generate documentation
    """
)

# Execute task
result = agent.execute(
    "Analyze the authentication system and suggest improvements"
)

print(result.output)
```

---

## Remote Infrastructure Deployment

### Fly.io

**Recommended for production deployments**

#### Single-Tenant Architecture (Recommended)

Deploy one lightweight VM per user/project for isolation.

**1. Create Fly App**:

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login
flyctl auth login

# Create app
flyctl apps create code-scalpel-user1
```

**2. Create `fly.toml`**:

```toml
app = "code-scalpel-user1"
primary_region = "sjc"

[build]
  image = "ghcr.io/your-org/code-scalpel:latest"

[env]
  CODE_SCALPEL_TIER = "pro"
  PROJECT_ROOT = "/app/workspace"

[mounts]
  source = "code_workspace"
  destination = "/app/workspace"

[[services]]
  internal_port = 8080
  protocol = "tcp"

  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]

  [[services.http_checks]]
    interval = "10s"
    timeout = "2s"
    path = "/health"
```

**3. Create Dockerfile**:

```dockerfile
FROM python:3.11-slim

# Install dependencies
RUN pip install uv
RUN uv pip install codescalpel

# Setup workspace
RUN mkdir -p /app/workspace
WORKDIR /app/workspace

# Expose MCP server over HTTP
EXPOSE 8080

# Start server
CMD ["uvx", "code-scalpel", "mcp", "--http", "--port", "8080"]
```

**4. Deploy**:

```bash
flyctl deploy

# Create volume for persistence
flyctl volumes create code_workspace --size 10

# Scale
flyctl scale count 1
```

**5. Router App (Multi-User)**:

Create a router to handle auth and route to user-specific VMs:

```python
# router.py
from fastapi import FastAPI, Header, HTTPException
import httpx

app = FastAPI()

USER_VMS = {
    "user1": "https://code-scalpel-user1.fly.dev",
    "user2": "https://code-scalpel-user2.fly.dev",
}

@app.post("/mcp")
async def route_mcp(
    request: dict,
    authorization: str = Header(None)
):
    # Extract user from auth token
    user_id = verify_token(authorization)

    # Get user's VM
    vm_url = USER_VMS.get(user_id)
    if not vm_url:
        raise HTTPException(404, "User VM not found")

    # Forward request
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{vm_url}/mcp",
            json=request,
            headers={"Authorization": authorization}
        )

    return response.json()
```

---

### AWS Lambda

**Serverless deployment for cost efficiency**

#### Architecture: API Gateway + Lambda + DynamoDB

**1. Lambda Function**:

```python
# lambda_handler.py
import json
import boto3
from code_scalpel.mcp.server import MCPServer

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('mcp-sessions')

def lambda_handler(event, context):
    """
    Handle MCP JSON-RPC over HTTP
    """
    # Parse request
    body = json.loads(event['body'])
    session_id = event['headers'].get('x-session-id', 'default')

    # Load session state from DynamoDB
    response = table.get_item(Key={'session_id': session_id})
    session_state = response.get('Item', {}).get('state', {})

    # Initialize MCP server with state
    server = MCPServer(
        project_root="/tmp/workspace",
        initial_state=session_state
    )

    # Handle JSON-RPC request
    result = server.handle_request(body)

    # Save session state
    table.put_item(Item={
        'session_id': session_id,
        'state': server.get_state()
    })

    return {
        'statusCode': 200,
        'body': json.dumps(result),
        'headers': {
            'Content-Type': 'application/json'
        }
    }
```

**2. SAM Template** (`template.yaml`):

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Resources:
  CodeScalpelFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: ./
      Handler: lambda_handler.lambda_handler
      Runtime: python3.11
      Timeout: 300
      MemorySize: 1024
      Environment:
        Variables:
          CODE_SCALPEL_TIER: pro
      Events:
        MCPApi:
          Type: HttpApi
          Properties:
            Path: /mcp
            Method: post

  SessionTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: mcp-sessions
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: session_id
          AttributeType: S
      KeySchema:
        - AttributeName: session_id
          KeyType: HASH
```

**3. Deploy**:

```bash
sam build
sam deploy --guided
```

---

### Docker Containers

**For self-hosted or Kubernetes deployment**

#### Dockerfile

```dockerfile
FROM python:3.11-slim

# Install dependencies
RUN pip install uv
RUN uv pip install codescalpel

# Create workspace
RUN mkdir -p /workspace
WORKDIR /workspace

# Expose ports
EXPOSE 8080

# [20260310_DOCS] Use a port-level liveness probe for MCP; the runtime does not expose a native /health endpoint.
# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import socket; s = socket.create_connection(('127.0.0.1', 8080), 2); s.close()" || exit 1

# Start MCP server in streamable HTTP mode
CMD ["uvx", "code-scalpel", "mcp", "--transport", "streamable-http", "--port", "8080", "--project-root", "/workspace"]
```

#### Docker Compose

```yaml
version: '3.8'

services:
  code-scalpel:
    build: .
    ports:
      - "8080:8080"
    environment:
      - CODE_SCALPEL_TIER=pro
      - CODE_SCALPEL_LICENSE_KEY=${LICENSE_KEY}
    volumes:
      - ./workspace:/workspace:rw
      - ./config:/root/.code-scalpel:ro
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import socket; s = socket.create_connection(('127.0.0.1', 8080), 2); s.close()"]
      interval: 30s
      timeout: 3s
      retries: 3
```

**Run**:

```bash
docker-compose up -d

# Test listener reachability
python - <<'PY'
import socket
s = socket.create_connection(("127.0.0.1", 8080), 2)
s.close()
print("MCP listener reachable on 127.0.0.1:8080")
PY
```

---

### Kubernetes

**For enterprise-scale deployment**

#### Deployment Manifest

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: code-scalpel
  namespace: mcp-servers
spec:
  replicas: 3
  selector:
    matchLabels:
      app: code-scalpel
  template:
    metadata:
      labels:
        app: code-scalpel
    spec:
      containers:
      - name: code-scalpel
        image: ghcr.io/your-org/code-scalpel:1.3.4
        ports:
        - containerPort: 8080
        env:
        - name: CODE_SCALPEL_TIER
          value: "enterprise"
        - name: CODE_SCALPEL_LICENSE_KEY
          valueFrom:
            secretKeyRef:
              name: code-scalpel-license
              key: license-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 10
        volumeMounts:
        - name: workspace
          mountPath: /workspace
      volumes:
      - name: workspace
        persistentVolumeClaim:
          claimName: code-scalpel-pvc

---
apiVersion: v1
kind: Service
metadata:
  name: code-scalpel-service
  namespace: mcp-servers
spec:
  type: LoadBalancer
  selector:
    app: code-scalpel
  ports:
  - port: 443
    targetPort: 8080
    protocol: TCP

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: code-scalpel-pvc
  namespace: mcp-servers
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 50Gi
```

**Deploy**:

```bash
kubectl apply -f deployment.yaml

# Check status
kubectl get pods -n mcp-servers

# Get service endpoint
kubectl get svc code-scalpel-service -n mcp-servers
```

---

## Configuration Reference

### Environment Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `CODE_SCALPEL_TIER` | License tier | `community` | `pro`, `enterprise` |
| `CODE_SCALPEL_LICENSE_KEY` | License key | None | `cs_sk_abc123...` |
| `CODE_SCALPEL_PROJECT_ROOT` | Default project directory | `.` | `/path/to/project` |
| `CODE_SCALPEL_CONFIG_DIR` | Config directory | `./.code-scalpel` | `/etc/code-scalpel` |
| `CODE_SCALPEL_LOG_LEVEL` | Logging level | `INFO` | `DEBUG`, `WARNING` |
| `CODE_SCALPEL_CACHE_DIR` | Cache directory | `./.code-scalpel/cache` | `/tmp/cache` |

### Project Configuration

Create `.code-scalpel/config.toml` in your project:

```toml
[general]
tier = "pro"
license_key = "cs_sk_..."

[limits]
# Override default limits (Enterprise only)
max_file_size_mb = 100
max_analysis_depth = 20

[features]
# Enable/disable specific tools
enable_refactoring = true
enable_security_scans = true

[integrations]
# External tool integration
sonarqube_url = "https://sonar.example.com"
github_token = "${env:GITHUB_TOKEN}"
```

---

## Troubleshooting

### Common Issues

#### 1. "Server not starting"

**Symptom**: MCP server fails to start or crashes immediately.

**Solutions**:
```bash
# Check Python version
python --version  # Should be 3.10+

# Reinstall Code Scalpel
pip uninstall code-scalpel
pip install codescalpel

# Test manually
uvx code-scalpel mcp --debug

# Check for port conflicts (if using HTTP mode)
lsof -i :8080
```

#### 2. "Tools not appearing in IDE"

**Symptom**: IDE doesn't show Code Scalpel tools.

**Solutions**:
1. Verify MCP config syntax (no trailing commas in JSON)
2. Check logs in IDE-specific location:
   - Claude Desktop: `~/Library/Logs/Claude/mcp*.log`
   - VS Code/Cline: Output panel → "Cline MCP"
   - Cursor: Developer Tools → Console
3. Restart IDE completely (not just reload)
4. Test server manually: `uvx code-scalpel mcp`

#### 3. "Tier limit errors"

**Symptom**: Tools fail with "tier limit exceeded" errors.

**Solutions**:
```bash
# Check current tier
codescalpel tier-info

# Verify license key
echo $CODE_SCALPEL_LICENSE_KEY

# Set license key
export CODE_SCALPEL_LICENSE_KEY="your-key-here"

# Or configure in project
cat > .code-scalpel/license.json << 'EOF'
{
  "tier": "pro",
  "license_key": "your-key-here"
}
EOF
```

#### 4. "File permission errors"

**Symptom**: Cannot read/write files in project.

**Solutions**:
```bash
# Check file ownership
ls -la /path/to/project

# Fix permissions
chmod -R u+rw /path/to/project

# If using Docker, fix user
docker run --user $(id -u):$(id -g) ...
```

#### 5. "Slow performance"

**Symptom**: Tools take too long to execute.

**Solutions**:
1. Enable caching:
   ```bash
   export CODE_SCALPEL_CACHE_ENABLED=true
   ```
2. Exclude large directories in `.code-scalpel/config.toml`:
   ```toml
   [general]
   exclude_dirs = ["node_modules", ".git", "build", "dist"]
   ```
3. Use tier-appropriate limits (Pro/Enterprise for large projects)

### Debug Mode

Enable verbose logging:

```bash
# CLI
codescalpel mcp --debug --log-file debug.log

# Environment variable
export CODE_SCALPEL_LOG_LEVEL=DEBUG
uvx code-scalpel mcp
```

Check logs:

```bash
# Default log location
tail -f ./.code-scalpel/logs/mcp-server.log

# With debug flag
tail -f debug.log
```

---

## Security Best Practices

### 1. License Key Protection

**DO NOT** commit license keys to version control.

**Good**:
```bash
# Use environment variables
export CODE_SCALPEL_LICENSE_KEY="cs_sk_..."

# Or secret management
aws secretsmanager get-secret-value --secret-id code-scalpel-license
```

**Bad**:
```json
{
  "mcpServers": {
    "code-scalpel": {
      "env": {
        "CODE_SCALPEL_LICENSE_KEY": "cs_sk_hardcoded_key_here"  // NEVER DO THIS
      }
    }
  }
}
```

### 2. Project Isolation

Use separate server instances per project:

```json
{
  "mcpServers": {
    "scalpel-project-a": {
      "command": "uvx",
      "args": ["code-scalpel", "mcp", "--project-root", "/path/to/project-a"]
    },
    "scalpel-project-b": {
      "command": "uvx",
      "args": ["code-scalpel", "mcp", "--project-root", "/path/to/project-b"]
    }
  }
}
```

### 3. Network Security (Remote Deployments)

**Use HTTPS**:
```nginx
server {
    listen 443 ssl;
    server_name code-scalpel.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location /mcp {
        proxy_pass http://localhost:8080;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**Implement authentication**:
```python
# In your MCP server wrapper
from fastapi import FastAPI, Header, HTTPException

app = FastAPI()

@app.post("/mcp")
async def mcp_endpoint(
    request: dict,
    authorization: str = Header(None)
):
    if not verify_token(authorization):
        raise HTTPException(401, "Unauthorized")

    # Forward to Code Scalpel
    return await handle_mcp_request(request)
```

### 4. File Access Control

Restrict Code Scalpel to specific directories:

```toml
# .code-scalpel/config.toml
[security]
allowed_paths = [
    "/workspace/src",
    "/workspace/tests"
]

denied_paths = [
    "/workspace/secrets",
    "/workspace/.env"
]
```

### 5. Rate Limiting (Remote Deployments)

```python
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

@app.post("/mcp")
@limiter.limit("100/minute")  # 100 requests per minute
async def mcp_endpoint(request: dict):
    # ...
```

---

## Next Steps

1. **Choose your deployment**: Desktop IDE, agent framework, or remote infrastructure
2. **Follow the guide**: Use the specific section for your environment
3. **Test thoroughly**: Verify all tools work as expected
4. **Configure tier**: Set up Pro/Enterprise license if needed
5. **Monitor usage**: Check logs and performance
6. **Join community**: [GitHub Discussions](https://github.com/your-org/code-scalpel/discussions)

---

## Additional Resources

- **Code Scalpel Documentation**: [https://codescalpel.dev](https://codescalpel.dev)
- **MCP Protocol Spec**: [https://modelcontextprotocol.io](https://modelcontextprotocol.io)
- **GitHub Repository**: [https://github.com/your-org/code-scalpel](https://github.com/your-org/code-scalpel)
- **Support**: support@codescalpel.dev

---

**Version History**:
- v1.0 (2026-02-06): Initial comprehensive deployment guide
