# Code Scalpel: Quick Deployment Guide

**Fast, one-liner deployment methods for every environment**

---

## 🚀 Claude Desktop / Claude Code

### One-Liner Installation
```bash
claude mcp add codescalpel uvx codescalpel mcp
```

### Manual Configuration
```bash
# Install Code Scalpel
uvx codescalpel mcp

# Or with pip
pip install codescalpel
```

**Config file location:**
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

**Config content:**
```json
{
  "mcpServers": {
    "code-scalpel": {
      "command": "uvx",
      "args": ["codescalpel", "mcp"]
    }
  }
}
```

**With Pro/Enterprise license:**
```json
{
  "mcpServers": {
    "code-scalpel": {
      "command": "uvx",
      "args": ["codescalpel", "mcp"],
      "env": {
        "CODE_SCALPEL_LICENSE_PATH": "/path/to/license.jwt"
      }
    }
  }
}
```

**Restart Claude Desktop completely** (quit and reopen, not just reload)

---

## 🐳 Docker

**Available Pre-Built Images:**
- **Docker Hub**: `3dtechsolutions/code-scalpel:latest`
- **GitHub Container Registry**: `ghcr.io/3d-tech-solutions/code-scalpel:latest`

### Option 1: Pull Pre-Built Image (Recommended)

**From Docker Hub:**
```bash
# Pull latest version
docker pull 3dtechsolutions/code-scalpel:latest

# Run with stdio transport (interactive)
docker run -it --rm \
  -v $(pwd):/app/code \
  3dtechsolutions/code-scalpel:latest

# Run as HTTP server (background)
docker run -d --name codescalpel \
  -p 8593:8593 \
  -v $(pwd):/app/code \
  3dtechsolutions/code-scalpel:latest
```

**From GitHub Container Registry:**
```bash
# Pull from GHCR
docker pull ghcr.io/3d-tech-solutions/code-scalpel:latest

# Run
docker run -it --rm \
  -v $(pwd):/app/code \
  ghcr.io/3d-tech-solutions/code-scalpel:latest
```

**With Pro/Enterprise License:**
```bash
docker run -d --name codescalpel \
  -p 8593:8593 \
  -v $(pwd):/app/code \
  -v /path/to/license.jwt:/app/.code-scalpel/license.jwt:ro \
  -e CODE_SCALPEL_LICENSE_PATH=/app/.code-scalpel/license.jwt \
  3dtechsolutions/code-scalpel:latest
```

**Listener Check:**
```bash
# [20260310_DOCS] The MCP runtime exposes /mcp, not a native /health endpoint.
# Verify the MCP listener is reachable
python - <<'PY'
import socket
s = socket.create_connection(("127.0.0.1", 8593), 2)
s.close()
print("MCP listener reachable on 127.0.0.1:8593")
PY
```

### Option 2: Docker Compose
```yaml
# docker-compose.yml
version: '3.8'
services:
  codescalpel:
    image: 3dtechsolutions/code-scalpel:latest
    ports:
      - "8593:8593"  # MCP server
    volumes:
      - ./:/app/code
      - ./.code-scalpel/license.jwt:/app/.code-scalpel/license.jwt:ro
    environment:
      - CODE_SCALPEL_LICENSE_PATH=/app/.code-scalpel/license.jwt
      - SCALPEL_ROOT=/app/code
    restart: unless-stopped
```

```bash
docker-compose up -d
```

### Option 3: Quick Build from Pip (No Pre-Built Image)
```bash
# One-liner for quick testing
docker run -it --rm \
  -v $(pwd):/workspace \
  python:3.11-slim \
  sh -c "pip install codescalpel && codescalpel mcp"
```

### Option 4: Build Custom Image
```bash
# Clone repository
git clone https://github.com/3DTechSolutions/code-scalpel.git
cd code-scalpel

# Build from Dockerfile
docker build -t codescalpel:custom .

# Run custom build
docker run -d -p 8593:8593 -v $(pwd):/app/code codescalpel:custom
```

---

## 💻 VS Code (Cline/Roo Code)

### Cline Extension
1. Install Cline extension from VS Code marketplace
2. Open Cline settings (⚙️ icon)
3. Go to "MCP Servers" section
4. Add server:
   ```json
   {
     "mcpServers": {
       "code-scalpel": {
         "command": "uvx",
         "args": ["codescalpel", "mcp"]
       }
     }
   }
   ```
5. Reload VS Code window

### Roo Code Extension
Similar to Cline - configure in extension settings under "MCP Servers"

---

## 🎯 Cursor IDE

**Config file location:**
- **macOS**: `~/Library/Application Support/Cursor/User/mcp_settings.json`
- **Windows**: `%APPDATA%\Cursor\User\mcp_settings.json`
- **Linux**: `~/.config/Cursor/User/mcp_settings.json`

**Config content:**
```json
{
  "mcpServers": {
    "code-scalpel": {
      "command": "uvx",
      "args": ["codescalpel", "mcp"]
    }
  }
}
```

**Restart Cursor IDE**

---

## 🐍 Python/Jupyter (Programmatic)

### Direct Python Usage
```python
import asyncio
from code_scalpel.mcp.server import CodeScalpelServer

async def main():
    server = CodeScalpelServer(project_root="/path/to/project")
    
    # Analyze code
    result = await server.analyze_code(
        code="""
        def hello(name: str) -> str:
            return f'Hello, {name}!'
        """
    )
    print(result.data)

asyncio.run(main())
```

### Using MCP Client
```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server_params = StdioServerParameters(
        command="uvx",
        args=["codescalpel", "mcp"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Call analyze_code tool
            result = await session.call_tool(
                "analyze_code",
                arguments={"code": "def hello(): return 'Hi'"}
            )
            print(result)

asyncio.run(main())
```

---

## 🤖 AI Agent Frameworks

### LangChain
```python
from langchain.agents import initialize_agent, Tool
from langchain_anthropic import ChatAnthropic
from code_scalpel.integrations.langchain import CodeScalpelToolkit

llm = ChatAnthropic(model="claude-3-5-sonnet-20241022")
toolkit = CodeScalpelToolkit(project_root="/path/to/project")

agent = initialize_agent(
    tools=toolkit.get_tools(),
    llm=llm,
    agent="zero-shot-react-description",
    verbose=True
)

result = agent.run("Extract the calculate_tax function from utils.py")
print(result)
```

### LangGraph
```python
from langgraph.prebuilt import create_react_agent
from langchain_anthropic import ChatAnthropic
from code_scalpel.integrations.langgraph import get_code_scalpel_tools

llm = ChatAnthropic(model="claude-3-5-sonnet-20241022")
tools = get_code_scalpel_tools(project_root="/path/to/project")

agent = create_react_agent(llm, tools)

result = agent.invoke({
    "messages": [("user", "Analyze security issues in auth.py")]
})
print(result)
```

### AutoGen
```python
from autogen import ConversableAgent
from code_scalpel.integrations.autogen import register_code_scalpel_tools

agent = ConversableAgent(
    name="code_analyzer",
    llm_config={"model": "gpt-4"},
)

register_code_scalpel_tools(agent, project_root="/path/to/project")

agent.initiate_chat(
    message="Extract the User class from models.py and check for security issues"
)
```

### CrewAI
```python
from crewai import Agent, Task, Crew
from code_scalpel.integrations.crewai import CodeScalpelTool

code_tool = CodeScalpelTool(project_root="/path/to/project")

agent = Agent(
    role="Code Analyst",
    goal="Analyze and improve code quality",
    tools=[code_tool],
    allow_delegation=False
)

task = Task(
    description="Extract calculate_tax from utils.py and check security",
    agent=agent
)

crew = Crew(agents=[agent], tasks=[task])
result = crew.kickoff()
print(result)
```

---

## ☁️ Cloud Deployments

### Fly.io
```bash
# Create fly.toml
cat > fly.toml << 'EOF'
app = "codescalpel"
primary_region = "sjc"

[build]
  image = "3dtechsolutions/code-scalpel:latest"

[http_service]
  internal_port = 8593
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 0

[[http_service.checks]]
  interval = "10s"
  timeout = "2s"
  path = "/health"

[env]
  SCALPEL_ROOT = "/app/code"
EOF

# Deploy
fly launch
fly deploy

# With volume for persistence
fly volumes create code_workspace --size 10
fly deploy
```

### AWS Lambda

**Option 1: Container Image (Recommended)**
```bash
# Pull and tag image for ECR
docker pull 3dtechsolutions/code-scalpel:latest
docker tag 3dtechsolutions/code-scalpel:latest \
  AWS_ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/codescalpel:latest

# Push to ECR
aws ecr get-login-password --region REGION | docker login --username AWS --password-stdin AWS_ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com
aws ecr create-repository --repository-name codescalpel --region REGION
docker push AWS_ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/codescalpel:latest

# Create Lambda function from container
aws lambda create-function \
  --function-name codescalpel \
  --package-type Image \
  --code ImageUri=AWS_ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/codescalpel:latest \
  --role arn:aws:iam::AWS_ACCOUNT_ID:role/lambda-execution-role \
  --timeout 30 \
  --memory-size 512
```

**Option 2: Serverless Framework (Python Runtime)**
```bash
# Install serverless framework
npm install -g serverless

# Create serverless.yml
cat > serverless.yml << 'EOF'
service: codescalpel

provider:
  name: aws
  runtime: python3.11
  region: us-east-1

functions:
  mcp:
    handler: handler.mcp_handler
    timeout: 30
    events:
      - http:
          path: /
          method: any
EOF

# Create handler.py
cat > handler.py << 'EOF'
import json
from code_scalpel.mcp.server import handle_http_request

def mcp_handler(event, context):
    return handle_http_request(event)
EOF

# Deploy
serverless deploy
```

### Google Cloud Run
```bash
# Option 1: Deploy pre-built image from Docker Hub
gcloud run deploy codescalpel \
  --image docker.io/3dtechsolutions/code-scalpel:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8593

# Option 2: Mirror to GCR first (for private deployments)
docker pull 3dtechsolutions/code-scalpel:latest
docker tag 3dtechsolutions/code-scalpel:latest gcr.io/PROJECT_ID/codescalpel:latest
docker push gcr.io/PROJECT_ID/codescalpel:latest

gcloud run deploy codescalpel \
  --image gcr.io/PROJECT_ID/codescalpel:latest \
  --platform managed \
  --region us-central1 \
  --port 8593
```

### Kubernetes
```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: codescalpel
spec:
  replicas: 3
  selector:
    matchLabels:
      app: codescalpel
  template:
    metadata:
      labels:
        app: codescalpel
    spec:
      containers:
      - name: codescalpel
        image: 3dtechsolutions/code-scalpel:latest
        # Or use GHCR: ghcr.io/3d-tech-solutions/code-scalpel:latest
        ports:
        - containerPort: 8593
          name: mcp
        - containerPort: 8594
          name: health
        env:
        - name: CODE_SCALPEL_LICENSE_PATH
          value: "/etc/codescalpel/license.jwt"
        - name: SCALPEL_ROOT
          value: "/app/code"
        volumeMounts:
        - name: license
          mountPath: /etc/codescalpel
          readOnly: true
        - name: workspace
          mountPath: /app/code
        livenessProbe:
          httpGet:
            path: /health
            port: 8594
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8594
          initialDelaySeconds: 5
          periodSeconds: 10
      volumes:
      - name: license
        secret:
          secretName: codescalpel-license
      - name: workspace
        persistentVolumeClaim:
          claimName: codescalpel-workspace
---
apiVersion: v1
kind: Service
metadata:
  name: codescalpel
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8593
    protocol: TCP
    name: mcp
  selector:
    app: codescalpel
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: codescalpel-workspace
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 10Gi
```

```bash
kubectl apply -f deployment.yaml
```

---

## 🔐 License Configuration

### Community (Free)
No configuration needed - automatically activates on first run.

### Pro/Enterprise

**Method 1: Environment Variable**
```bash
export CODE_SCALPEL_LICENSE_PATH="/path/to/license.jwt"
```

**Method 2: Standard Location (Recommended)**
```bash
# Create license directory
mkdir -p ~/.code-scalpel/

# Copy license file
cp license.jwt ~/.code-scalpel/license.jwt
```

**Method 3: Project-Specific**
```bash
# In your project root
mkdir -p .code-scalpel/
cp license.jwt .code-scalpel/license.jwt
```

**Verify License:**
```bash
codescalpel tier-info
# Should show: "Tier: pro" or "Tier: enterprise"
```

---

## 🧪 Testing Your Installation

### Quick Test (CLI)
```bash
# Test analyze_code
echo 'def hello(): return "Hi"' > test.py
uvx codescalpel analyze test.py

# Test extract_code
uvx codescalpel extract test.py --symbol hello --type function
```

### Test with MCP Inspector
```bash
# Start inspector
uvx @modelcontextprotocol/inspector uvx codescalpel mcp

# Open browser to http://localhost:6274
# Test tools interactively
```

### Verify All Tools Available
```bash
# List available tools
uvx codescalpel list-tools

# Should show all 23 tools:
# - analyze_code
# - extract_code
# - security_scan
# - get_call_graph
# - ... and 20 more
```

---

## 📦 Docker Registry Reference

### Available Registries

| Registry | Image Name | Use Case |
|----------|-----------|----------|
| **Docker Hub** | `3dtechsolutions/code-scalpel:latest` | Public deployments, fastest pulls |
| **GitHub Container Registry** | `ghcr.io/3d-tech-solutions/code-scalpel:latest` | GitHub Actions, enterprise registries |

### Version Tags

```bash
# Latest stable release
docker pull 3dtechsolutions/code-scalpel:latest

# Specific version (recommended for production)
docker pull 3dtechsolutions/code-scalpel:1.4.0

# Version with platform
docker pull 3dtechsolutions/code-scalpel:1.4.0-amd64
docker pull 3dtechsolutions/code-scalpel:1.4.0-arm64
```

### Which Registry To Use?

- **Docker Hub** (`3dtechsolutions/code-scalpel`) - Default choice, fastest mirrors worldwide
- **GHCR** (`ghcr.io/3d-tech-solutions/code-scalpel`) - GitHub integration, private enterprise deployments

Both registries have identical images, choose based on your infrastructure.

---

## 🆘 Quick Troubleshooting

### "Command not found: uvx"
```bash
pip install uv
```

### "No module named code_scalpel"
```bash
pip install codescalpel
```

### "License not found" (Pro/Enterprise)
```bash
# Check license path
ls -la ~/.code-scalpel/license.jwt

# Or set environment variable
export CODE_SCALPEL_LICENSE_PATH="/full/path/to/license.jwt"
```

### Claude/Cursor doesn't see tools
1. Verify JSON syntax (no trailing commas)
2. Restart IDE completely (quit and reopen)
3. Check logs:
   - **macOS**: `~/Library/Logs/Claude/`
   - **Windows**: `%APPDATA%\Claude\Logs\`
   - **Linux**: `~/.local/share/Claude/logs/`

### Docker container exits immediately
```bash
# Check logs
docker logs codescalpel

# Run interactively for debugging
docker run -it --rm 3dtechsolutions/code-scalpel:latest

# Check MCP listener
python - <<'PY'
import socket
s = socket.create_connection(("127.0.0.1", 8593), 2)
s.close()
print("MCP listener reachable on 127.0.0.1:8593")
PY
```

### Docker image pull fails
```bash
# Try alternative registry
docker pull ghcr.io/3d-tech-solutions/code-scalpel:latest

# Or specific version
docker pull 3dtechsolutions/code-scalpel:1.4.0
```

---

## 📚 Additional Resources

- **[Full Installation Guide](docs/INSTALLING_FOR_CLAUDE.md)** - Step-by-step installation
- **[MCP Deployment Guide](docs/MCP_DEPLOYMENT_GUIDE.md)** - Comprehensive deployment options
- **[License Setup](docs/LICENSE_SETUP.md)** - Complete license configuration
- **[Troubleshooting](docs/guides/troubleshooting.md)** - Common issues and solutions
- **[Examples](examples/)** - Code examples for all integrations

---

**Last Updated**: February 12, 2026  
**Code Scalpel Version**: 1.4.0
