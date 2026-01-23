# Integrations Module

**Purpose:** External framework and API integrations

## TODO ITEMS: integrations/README.md

### COMMUNITY TIER - Core Documentation
1. Add overview of supported frameworks
2. Add quick start guide for each framework
3. Add installation instructions
4. Add configuration examples
5. Add basic usage patterns
6. Add code examples for common tasks
7. Add troubleshooting section
8. Add frequently asked questions
9. Add API reference documentation
10. Add error message explanations
11. Add supported versions table
12. Add compatibility matrix
13. Add feature parity table
14. Add framework comparison
15. Add migration guide from one framework to another
16. Add best practices guide
17. Add performance tips
18. Add cost optimization tips
19. Add security checklist
20. Add tool support matrix
21. Add model support per framework
22. Add language support
23. Add platform support (Windows, Mac, Linux)
24. Add container support (Docker, Kubernetes)
25. Add cloud platform support (AWS, Azure, GCP)

### PRO TIER - Advanced Documentation
26. Add advanced configuration guide
27. Add performance tuning documentation
28. Add scaling strategies
29. Add optimization patterns
30. Add caching strategies
31. Add rate limiting configuration
32. Add custom integration development
33. Add plugin development guide
34. Add middleware creation
35. Add authentication mechanisms
36. Add authorization patterns
37. Add compliance configurations
38. Add security hardening guide
39. Add monitoring setup
40. Add logging configuration
41. Add metrics collection
42. Add observability setup
43. Add debugging guide
44. Add troubleshooting advanced issues
45. Add performance benchmarks
46. Add cost analysis
47. Add resource management
48. Add capacity planning
49. Add load testing guide
50. Add integration testing guide

### ENTERPRISE TIER - Advanced Guidance
51. Add enterprise deployment architecture
52. Add high availability setup
53. Add disaster recovery procedures
54. Add multi-region deployment
55. Add failover mechanisms
56. Add backup strategies
57. Add encryption setup
58. Add key management
59. Add audit logging configuration
60. Add compliance documentation (HIPAA, SOC2, GDPR, CCPA)
61. Add regulatory requirements
62. Add data residency options
63. Add data governance
64. Add retention policies
65. Add deletion procedures
66. Add access control setup
67. Add role-based access configuration
68. Add single sign-on setup
69. Add multi-factor authentication
70. Add network security
71. Add firewall configuration
72. Add VPC setup
73. Add private link configuration
74. Add DDoS protection
75. Add enterprise support SLA

## Supported Frameworks

## Key Components

### rest_api_server.py (16,710 LOC)
REST API wrapper for MCP tools:
- `MCPServerConfig` - Server configuration
- `create_app()` - Flask app factory
- `run_server()` - Server launcher
- Exposes all 22 MCP tools as HTTP endpoints

**Endpoints:**
- `POST /analyze_code` - Analyze code structure
- `POST /extract_code` - Extract functions/classes
- `POST /security_scan` - Scan for vulnerabilities
- ... (20 total)

**Example:**
```python
from code_scalpel.integrations import create_app, run_server

# Create Flask app
app = create_app()

# Run server
run_server(port=8080, host="0.0.0.0")
```

### autogen.py (8,193 LOC)
AutoGen framework integration:
- `AutogenScalpel` - Wrapper class for AutoGen agents
- Tool registration for MCP functions
- Async execution support
- Multi-agent code analysis workflows

**Example:**
```python
from code_scalpel.integrations import AutogenScalpel
import autogen

scalpel = AutogenScalpel()
agent = autogen.AssistantAgent(
    name="CodeAnalyzer",
    llm_config={"tools": scalpel.get_tools()}
)
```

### crewai.py (20,465 LOC)
CrewAI framework integration:
- `CrewAIScalpel` - Wrapper for CrewAI crews
- Task definitions for code analysis
- Agent role definitions (Analyzer, Security Auditor, Refactorer)
- Multi-step analysis pipelines

**Example:**
```python
from code_scalpel.integrations import CrewAIScalpel
from crewai import Crew

scalpel = CrewAIScalpel()
crew = Crew(
    agents=scalpel.get_agents(),
    tasks=scalpel.get_tasks()
)
result = crew.kickoff()
```

### claude.py (Placeholder)
Future: Direct Claude API integration

### langchain.py (Placeholder)
Future: LangChain tool integration

## Usage Patterns

### REST API Server
```bash
# Start server
python -m code_scalpel.integrations.rest_api_server

# Make request
curl -X POST http://localhost:8080/analyze_code \
  -H "Content-Type: application/json" \
  -d '{"code": "def foo(): return 1"}'
```

### AutoGen Agent
```python
from code_scalpel.integrations import AutogenScalpel
import autogen

scalpel = AutogenScalpel()
assistant = autogen.AssistantAgent(
    name="CodeReviewer",
    system_message="You are a code reviewer using Code Scalpel tools",
    llm_config={"tools": scalpel.get_tools()}
)

user_proxy = autogen.UserProxyAgent(name="User")
user_proxy.initiate_chat(
    assistant,
    message="Analyze this file for security issues: app.py"
)
```

### CrewAI Crew
```python
from code_scalpel.integrations import CrewAIScalpel

scalpel = CrewAIScalpel()
crew = scalpel.create_analysis_crew()
result = crew.kickoff(inputs={"file_path": "src/main.py"})
```

## Integration

Used by:
- External AI frameworks (AutoGen, CrewAI)
- HTTP clients (curl, Postman, frontend apps)
- CI/CD pipelines (GitHub Actions, Jenkins)

## v3.0.5 Status

- REST API: Stable, 100% coverage
- AutoGen: Beta, 80% coverage
- CrewAI: Beta, 75% coverage
- Claude/LangChain: Planned for v3.1.0
