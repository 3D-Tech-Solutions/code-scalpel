# Code Scalpel Autonomy Integration Quickstart

[20251217_DOCS] Quickstart guide for LangGraph, CrewAI, and AutoGen integrations.

## Overview

Code Scalpel provides native integrations with popular AI agent frameworks to enable autonomous code fixing:

- **LangGraph**: StateGraph-based fix loops with conditional routing
- **CrewAI**: Multi-agent collaborative fixing with specialized agents
- **AutoGen**: Function-calling agents with Docker sandbox execution

## Installation

Install Code Scalpel with autonomy dependencies:

```bash
pip install -r requirements.txt
```

Or install specific frameworks:

```bash
# LangGraph
pip install langgraph

# CrewAI
pip install crewai

# AutoGen
pip install pyautogen
```

## LangGraph Integration

### Quick Start

```python
from code_scalpel.autonomy.integrations.langgraph import create_scalpel_fix_graph

# Create the fix graph
graph = create_scalpel_fix_graph()

# Run the fix loop
result = graph.invoke({
    "code": buggy_code,
    "language": "python",
    "error": error_message,
    "fix_attempts": [],
    "success": False,
})

print(f"Fix successful: {result['success']}")
print(f"Fix attempts: {len(result['fix_attempts'])}")
```

### Graph Structure

The LangGraph integration creates a StateGraph with:

- **analyze_error**: Analyzes errors using AST parsing
- **generate_fix**: Generates fixes using symbolic execution
- **validate_fix**: Validates fixes in sandbox
- **apply_fix**: Applies validated fixes
- **escalate**: Escalates to human when automatic fix fails

**Conditional Routing:**
- `generate_fix` → `validate_fix` (if fix available) or `escalate` (if no fix)
- `validate_fix` → `apply_fix` (if validation passes) or `escalate` (if validation fails)

### Example: Syntax Error Fix

```python
from code_scalpel.autonomy.integrations.langgraph import create_scalpel_fix_graph

buggy_code = """
def calculate_sum(a, b)
    return a + b
"""

graph = create_scalpel_fix_graph()
result = graph.invoke({
    "code": buggy_code,
    "language": "python",
    "error": "SyntaxError: invalid syntax at line 2",
    "fix_attempts": [],
    "success": False,
})

# Check results
for attempt in result["fix_attempts"]:
    print(f"{attempt['step']}: {attempt.get('analysis', {})}")
```

## CrewAI Integration

### Quick Start

```python
from code_scalpel.autonomy.integrations.crewai import create_scalpel_fix_crew

# Create the crew (requires LLM configuration)
crew = create_scalpel_fix_crew()

# Run the crew
result = crew.kickoff(inputs={
    "code": buggy_code,
    "error": error_message
})
```

### Crew Structure

The CrewAI integration creates a multi-agent crew with:

**Agents:**
1. **Error Analyzer**: Identifies root causes using AST analysis
2. **Fix Generator**: Generates code fixes
3. **Fix Validator**: Validates fixes in sandbox

**Tools:**
- `scalpel_analyze`: AST-based code analysis
- `scalpel_error_to_diff`: Convert errors to actionable diffs
- `scalpel_generate_fix`: Generate code fixes
- `scalpel_validate_ast`: Validate AST structure
- `scalpel_sandbox`: Test code in sandbox
- `scalpel_security_scan`: Scan for vulnerabilities

### Example: Security Vulnerability Fix

```python
from code_scalpel.autonomy.integrations.crewai import create_scalpel_fix_crew

vulnerable_code = """
def run_query(user_input):
    query = f"SELECT * FROM users WHERE name = '{user_input}'"
    cursor.execute(query)
"""

crew = create_scalpel_fix_crew()
result = crew.kickoff(inputs={
    "code": vulnerable_code,
    "error": "Security: SQL injection vulnerability (CWE-89)"
})
```

**Note:** CrewAI requires LLM configuration (e.g., `OPENAI_API_KEY` environment variable).

## AutoGen Integration

### Quick Start

```python
from code_scalpel.autonomy.integrations.autogen import create_scalpel_autogen_agents

# Create agents with LLM configuration
coder, reviewer = create_scalpel_autogen_agents(
    llm_config={
        "config_list": [{"model": "gpt-4", "api_key": "your-key"}]
    }
)

# Initiate chat
reviewer.initiate_chat(
    coder,
    message="Fix this syntax error: def foo( return 42"
)
```

### Agent Structure

The AutoGen integration creates two agents:

**ScalpelCoder (AssistantAgent):**
- Analyzes errors
- Generates fixes
- Validates fixes

**CodeReviewer (UserProxyAgent):**
- Executes code in Docker sandbox
- Reviews fixes
- Provides feedback

**Available Functions:**
- `scalpel_analyze_error`: Analyze error and get fix suggestions
- `scalpel_apply_fix`: Apply fix to code
- `scalpel_validate`: Validate fix in sandbox

### Example: Direct Function Calls

```python
from code_scalpel.autonomy.integrations.autogen import (
    scalpel_analyze_error_impl,
    scalpel_apply_fix_impl,
    scalpel_validate_impl,
)

# 1. Analyze error
analysis = scalpel_analyze_error_impl(
    code=buggy_code,
    error="SyntaxError: invalid syntax"
)

# 2. Apply fix
fixed = scalpel_apply_fix_impl(
    code=buggy_code,
    fix="Add colon after function definition"
)

# 3. Validate fix
validation = scalpel_validate_impl(fixed["fixed_code"])
print(f"Safe to apply: {validation['safe_to_apply']}")
```

### Docker Sandbox Configuration

AutoGen uses Docker for isolated code execution:

```python
coder, reviewer = create_scalpel_autogen_agents()

# Sandbox configuration
# - Work directory: .scalpel_sandbox
# - Docker: Enabled
# - Human input: Disabled (NEVER)
```

## Comparison Matrix

| Feature | LangGraph | CrewAI | AutoGen |
|---------|-----------|--------|---------|
| **Execution Model** | StateGraph | Multi-agent crew | Function-calling |
| **Conditional Routing** | [COMPLETE] | [COMPLETE] (via tasks) | [COMPLETE] (via LLM) |
| **Multi-agent** | [FAILED] | [COMPLETE] | [COMPLETE] |
| **Docker Sandbox** | [FAILED] | [FAILED] | [COMPLETE] |
| **LLM Required** | [FAILED] | [COMPLETE] | [COMPLETE] |
| **Best For** | Structured workflows | Collaborative fixing | Interactive debugging |

## Advanced Usage

### Custom LangGraph Nodes

```python
from code_scalpel.autonomy.integrations.langgraph import (
    ScalpelState,
    StateGraph,
    END,
)

def custom_analysis_node(state: ScalpelState) -> ScalpelState:
    # Custom analysis logic
    return state

graph = StateGraph(ScalpelState)
graph.add_node("custom_analysis", custom_analysis_node)
# ... add more nodes and edges
compiled = graph.compile()
```

### Custom CrewAI Tools

```python
from code_scalpel.autonomy.integrations.crewai import (
    ScalpelAnalyzeTool,
    Agent,
    Crew,
)

custom_agent = Agent(
    role="Custom Analyzer",
    goal="Perform specialized analysis",
    tools=[ScalpelAnalyzeTool(), custom_tool],
)
```

### Custom AutoGen Functions

```python
def custom_analysis_impl(code: str) -> dict:
    # Custom analysis logic
    return {"success": True, "analysis": "..."}

reviewer.register_function(
    function_map={
        "custom_analysis": custom_analysis_impl,
    }
)
```

## Troubleshooting

### LangGraph: "Module not found"

```bash
pip install langgraph
```

### CrewAI: "OPENAI_API_KEY is required"

Set your OpenAI API key:

```bash
export OPENAI_API_KEY="your-key"
```

Or use another LLM provider (see CrewAI documentation).

### AutoGen: "api_key client option must be set"

Provide API key in configuration:

```python
llm_config = {
    "config_list": [{"model": "gpt-4", "api_key": "your-key"}]
}
```

### Docker: "Cannot connect to Docker daemon"

Ensure Docker is running:

```bash
docker ps
```

Or disable Docker execution:

```python
reviewer = UserProxyAgent(
    name="CodeReviewer",
    code_execution_config={"use_docker": False},
)
```

## Examples

Full working examples are available in the `examples/` directory:

- `examples/langgraph_example.py` - LangGraph integration demo
- `examples/crewai_autonomy_example.py` - CrewAI integration demo
- `examples/autogen_autonomy_example.py` - AutoGen integration demo

## Next Steps

- Explore the [API documentation](../README.md)
- Learn about [symbolic execution](../docs/symbolic_execution.md)
- Understand [security analysis](../docs/security_analysis.md)
- Check out [MCP integration](../docs/mcp_integration.md)

## Support

For issues, questions, or contributions:
- GitHub Issues: https://github.com/3D-Tech-Solutions/code-scalpel/issues
- Documentation: https://github.com/3D-Tech-Solutions/code-scalpel/tree/main/docs
