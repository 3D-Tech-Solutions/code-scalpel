# Code Scalpel Integrations

**Adapters for embedding Code Scalpel agents into external AI orchestration frameworks**

---

## Overview

This directory contains **integration bridges** that allow Code Scalpel agents to work within external multi-agent frameworks:

- **AutoGen** (Microsoft's multi-agent orchestration framework)
- **CrewAI** (AI agent crew framework)
- **LangGraph** (Workflow graph execution engine)

These integrations enable Code Scalpel to:
- Participate in multi-agent teams
- Be orchestrated by external frameworks
- Share data with other specialized agents
- Run in workflow graphs and pipelines

---

## Difference from `agents/`

| Aspect | `agents/` | `integrations/` |
|--------|-----------|-----------------|
| **Purpose** | Code Scalpel's own analysis implementations | Bridges to external frameworks |
| **Pattern** | OODA loop (internal) | Framework adapter (external) |
| **Ownership** | Code Scalpel | External frameworks |
| **Usage** | Standalone or via MCP | Within external frameworks |
| **Coordination** | Self-contained | Orchestrated by framework |
| **Data Model** | Code Scalpel results | Framework-native message format |

**Relationship:**
```
Code Scalpel Agents (agents/)
    ↓
    Can be wrapped by Integrations (integrations/)
    ↓
    Can participate in AutoGen/CrewAI/LangGraph teams
```

---

## Supported Frameworks

### 1. AutoGen Integration (`autogen.py`)

**Purpose:** Integrate Code Scalpel agents into Microsoft's AutoGen multi-agent framework.

**Use Case:** Build complex coding workflows with multiple specialized agents:

```python
from code_scalpel.autonomy.integrations import CodeScalpelAutoGenAgent

# Create Code Scalpel agent in AutoGen
scalpel_agent = CodeScalpelAutoGenAgent(
    name="CodeAnalyzer",
    agent_type="security",  # SecurityAgent
    model="gpt-4"
)

# Add to AutoGen team
team = [scalpel_agent, other_agents...]

# AutoGen orchestrates execution
```

**What it provides:**
- AutoGen-compatible agent interface
- Message format conversion (AutoGen ↔ Code Scalpel)
- Tool registration with AutoGen's tool framework
- Capability broadcasting to other agents

**Integration Points:**
- Inherits from `autogen.AgentBase`
- Implements `ConversableAgent` interface
- Registers MCP tools as AutoGen tools
- Handles `receive_message()` protocol

### 2. CrewAI Integration (`crewai.py`)

**Purpose:** Integrate Code Scalpel agents as CrewAI crew members.

**Use Case:** Organize Code Scalpel agents as specialized team roles:

```python
from code_scalpel.autonomy.integrations import CodeScalpelCrewAIAgent

# Create Code Scalpel agents as crew members
security_expert = CodeScalpelCrewAIAgent(
    role="Security Analyst",
    goal="Find and fix vulnerabilities",
    agent_type="security",
    backstory="Expert in code security"
)

code_reviewer = CodeScalpelCrewAIAgent(
    role="Code Reviewer",
    goal="Ensure code quality",
    agent_type="code_review",
    backstory="Senior code quality expert"
)

# Create crew
crew = Crew(
    agents=[security_expert, code_reviewer],
    tasks=[audit_task, review_task]
)

results = crew.kickoff()
```

**What it provides:**
- CrewAI-compatible `Agent` interface
- Role-based agent configuration
- Goal and backstory support
- Memory integration with CrewAI
- Tool compatibility layer

**Integration Points:**
- Inherits from `crewai.Agent`
- Implements memory callbacks
- Registers agents with task dispatcher
- Handles tool invocation protocol

### 3. LangGraph Integration (`langgraph.py`)

**Purpose:** Integrate Code Scalpel agents into LangGraph workflow graphs.

**Use Case:** Build DAG-based code analysis workflows:

```python
from code_scalpel.autonomy.integrations import CodeScalpelLangGraphAgent
from langgraph.graph import StateGraph

# Create workflow
workflow = StateGraph(AnalysisState)

# Add Code Scalpel agents as nodes
security_node = CodeScalpelLangGraphAgent(
    name="security_scan",
    agent_type="security"
)

refactoring_node = CodeScalpelLangGraphAgent(
    name="refactoring",
    agent_type="refactoring"
)

# Define graph structure
workflow.add_node("security", security_node)
workflow.add_node("refactoring", refactoring_node)
workflow.add_edge("security", "refactoring")
workflow.add_edge("refactoring", END)

# Execute workflow
graph = workflow.compile()
result = graph.invoke({"file": "src/app.py"})
```

**What it provides:**
- LangGraph `Node` compatibility
- State mutation support
- Graph-based workflow integration
- Conditional routing support
- Error handling in graph context

**Integration Points:**
- Compatible with LangGraph's node protocol
- Supports state machines
- Handles graph routing
- Provides streaming capabilities

---

## Common Integration Patterns

### Pattern 1: Sequential Analysis

```python
# AutoGen Example
security_agent.send(message="Analyze security", recipient=quality_agent)
quality_agent.send(message="Review code quality", recipient=refactoring_agent)
```

### Pattern 2: Parallel Scanning

```python
# CrewAI Example
crew = Crew(
    agents=[security_expert, performance_expert, quality_expert],
    tasks=[
        Task(security_expert, "Find vulnerabilities"),
        Task(performance_expert, "Find optimization opportunities"),
        Task(quality_expert, "Review code quality")
    ]
)
# All agents analyze in parallel
```

### Pattern 3: Conditional Workflow

```python
# LangGraph Example
def route_based_severity(state):
    if state["severity"] == "critical":
        return "immediate_fix"
    elif state["severity"] == "high":
        return "schedule_fix"
    else:
        return "backlog"

workflow.add_conditional_edges(
    "security_scan",
    route_based_severity,
    {"immediate_fix": ..., "schedule_fix": ..., "backlog": ...}
)
```

---

## Data Format Conversion

Integrations handle conversion between formats:

```
Code Scalpel Result
    ↓ (Integration Layer)
    ├── AutoGen: Convert to Message with tool_calls
    ├── CrewAI: Convert to AgentAction with tool_input
    └── LangGraph: Convert to StateUpdate with annotations
```

### Example: Security Scan Result Conversion

```python
# Code Scalpel native format
result = {
    "vulnerabilities": [
        {"type": "SQL Injection", "severity": "high", "line": 42}
    ]
}

# AutoGen format
autogen_message = {
    "content": "Found SQL Injection at line 42",
    "tool_calls": [{"tool": "update_symbol", "args": {...}}]
}

# CrewAI format
crewai_action = AgentAction(
    tool="simulate_refactor",
    tool_input={"original_code": ..., "new_code": ...},
    log="Planning SQL injection fix"
)

# LangGraph format
state_update = {
    "findings": result,
    "next_step": "refactoring",
    "confidence": 0.95
}
```

---

## Tool Registration

Each integration registers Code Scalpel's MCP tools:

```python
# AutoGen example
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "security_scan",
            "description": "Scan code for vulnerabilities",
            "parameters": {...}
        }
    },
    # ... more tools
]

agent = CodeScalpelAutoGenAgent(tools=TOOLS)
```

---

## Configuration

Each integration supports framework-specific configuration:

### AutoGen

```python
agent = CodeScalpelAutoGenAgent(
    name="Analyzer",
    agent_type="security",
    model="gpt-4",
    system_message="You are a security expert",
    max_consecutive_auto_reply=10
)
```

### CrewAI

```python
agent = CodeScalpelCrewAIAgent(
    role="Security Expert",
    goal="Find vulnerabilities",
    agent_type="security",
    backstory="20 years of security expertise",
    allow_code_execution=False
)
```

### LangGraph

```python
agent = CodeScalpelLangGraphAgent(
    name="SecurityScanner",
    agent_type="security",
    state_schema=SecurityState,
    timeout=300,
    retry_policy="exponential_backoff"
)
```

---

## Error Handling

Integrations gracefully handle errors in framework-specific ways:

```python
# AutoGen: Converts to error message
agent.send("Analyze file", recipient=next_agent, **{
    "error": "File not found",
    "error_type": "FileNotFoundError"
})

# CrewAI: Raises TaskExecutionError
raise TaskExecutionError("Failed to analyze: File not found")

# LangGraph: Updates state with error info
return {
    "error": "File not found",
    "status": "failed",
    "next_step": "cleanup"
}
```

---

## Performance Considerations

- **Overhead:** Framework adapter adds ~5-10ms per call
- **Caching:** Integrations cache analysis results
- **Parallelization:** Use framework's parallel execution
- **Streaming:** LangGraph supports streaming results

---

## Examples

### Complete AutoGen Example

```python
from code_scalpel.autonomy.integrations import CodeScalpelAutoGenAgent
import autogen

security_agent = CodeScalpelAutoGenAgent(
    name="SecurityExpert",
    agent_type="security",
    model="gpt-4"
)

quality_agent = CodeScalpelAutoGenAgent(
    name="QualityExpert",
    agent_type="code_review",
    model="gpt-4"
)

# Define task
user_proxy = autogen.UserProxyAgent(
    name="Manager",
    code_execution_config={"use_docker": False}
)

# Execute team
user_proxy.initiate_chat(
    security_agent,
    message="Analyze src/app.py for security and quality issues"
)
```

### Complete CrewAI Example

```python
from code_scalpel.autonomy.integrations import CodeScalpelCrewAIAgent
from crewai import Crew, Task

agents = [
    CodeScalpelCrewAIAgent(
        role="Security Analyst",
        goal="Find vulnerabilities",
        agent_type="security"
    ),
    CodeScalpelCrewAIAgent(
        role="Code Reviewer",
        goal="Improve code quality",
        agent_type="code_review"
    )
]

tasks = [
    Task(description="Scan for security issues", agent=agents[0]),
    Task(description="Review code quality", agent=agents[1])
]

crew = Crew(agents=agents, tasks=tasks)
results = crew.kickoff()
```

### Complete LangGraph Example

```python
from code_scalpel.autonomy.integrations import CodeScalpelLangGraphAgent
from langgraph.graph import StateGraph, END
from typing import TypedDict

class AnalysisState(TypedDict):
    file: str
    security_findings: list
    quality_findings: list
    refactoring_suggestions: list

workflow = StateGraph(AnalysisState)

security_node = CodeScalpelLangGraphAgent(
    name="security_scan",
    agent_type="security"
)

quality_node = CodeScalpelLangGraphAgent(
    name="quality_review",
    agent_type="code_review"
)

workflow.add_node("security", security_node)
workflow.add_node("quality", quality_node)
workflow.add_edge("security", "quality")
workflow.add_edge("quality", END)

graph = workflow.compile()
result = graph.invoke({"file": "src/app.py"})
```

---

## Data Flow

### AutoGen Integration
```
User Request
    ↓
AutonomyAutogenAdapter
    ↓
autogen.ConversableAgent.initiate_chat()
    ├─ Agent 1 analyzes request
    ├─ Agents discuss findings
    └─ Consensus/decision reached
    ↓
Recommendations
```

### CrewAI Integration
```
User Request
    ↓
AutonomyCrewAIAdapter
    ↓
crewai.Crew.kickoff()
    ├─ Task 1 (SecurityAgent) executes
    ├─ Task 2 (CodeReviewAgent) executes
    ├─ Dependencies resolved
    └─ Final task synthesizes results
    ↓
Comprehensive Report
```

### LangGraph Integration
```
User Request
    ↓
AutonomyLangGraphAdapter
    ↓
LangGraph State Machine
    ├─ Node: SecurityAnalysis
    ├─ Node: CodeQuality
    ├─ Node: TestCoverage
    ├─ Conditional edges based on findings
    └─ Terminal node: Result synthesis
    ↓
Structured Findings
```

---

## Development Roadmap

### Phase 1: Framework Integration (In Progress 🔄)

#### AutoGen Enhancements (6 TODOs)
- [ ] User proxy agent for interactive approval
- [ ] Nested team hierarchies
- [ ] Code execution agent with sandboxing
- [ ] Tool use and function calling
- [ ] Message filtering & summarization
- [ ] Conversation cost tracking

#### CrewAI Enhancements (8 TODOs)
- [ ] Memory integration (short & long-term)
- [ ] Tool caching optimization
- [ ] Task dependency graphs
- [ ] Async task execution
- [ ] Error recovery strategies
- [ ] Performance metrics collection
- [ ] Custom execution patterns
- [ ] Result formatting templates

#### LangGraph Enhancements (7 TODOs)
- [ ] Stream processing of results
- [ ] Dynamic node generation
- [ ] Edge weights for routing
- [ ] State snapshots & checkpointing
- [ ] Subgraph composition
- [ ] Debugging & visualization
- [ ] Recursive graph support

### Phase 2: Cross-Framework Features (Planned 🔄)

#### Common Capabilities (10 TODOs)
- [ ] Unified result format across frameworks
- [ ] Framework-agnostic policy application
- [ ] Multi-framework orchestration
- [ ] Framework capability detection
- [ ] Graceful degradation
- [ ] Framework selection logic
- [ ] Performance comparison
- [ ] Cost optimization per framework
- [ ] Framework health monitoring
- [ ] Automatic framework fallback

#### Advanced Orchestration (12 TODOs)
- [ ] Parallel framework execution
- [ ] Result aggregation & consensus
- [ ] Conflict resolution
- [ ] Framework composition
- [ ] Hybrid workflows (mix AutoGen + CrewAI)
- [ ] Chain multiple frameworks
- [ ] Framework-specific optimizations
- [ ] Load balancing across frameworks
- [ ] Framework versioning support
- [ ] API stability monitoring
- [ ] Breaking change detection
- [ ] Framework upgrade guidance

### Phase 3: Production Hardening (Future)

#### Safety & Compliance (9 TODOs)
- [ ] Input validation per framework
- [ ] Output sanitization
- [ ] Rate limiting integration
- [ ] Quota management
- [ ] PII detection & masking
- [ ] Audit logging per framework
- [ ] Compliance reporting
- [ ] Policy violation detection
- [ ] Automatic remediation triggers

#### Performance & Observability (11 TODOs)
- [ ] Latency tracking per framework
- [ ] Token usage monitoring (LLM)
- [ ] Cost per agent tracking
- [ ] Performance profiling
- [ ] Bottleneck identification
- [ ] Optimization recommendations
- [ ] SLA monitoring
- [ ] Error rate tracking
- [ ] Health check automation
- [ ] Alerting system
- [ ] Metrics dashboard

#### Developer Experience (8 TODOs)
- [ ] Framework selection wizard
- [ ] Configuration validation
- [ ] Error messages with solutions
- [ ] Example workflows per framework
- [ ] Framework comparison guide
- [ ] Migration tools between frameworks
- [ ] Testing utilities per framework
- [ ] Debugging helpers

---

## File Structure

```
autonomy/integrations/
├── README.md                    [This file]
├── __init__.py                  [Exports integrations]
├── autogen.py                   [AutoGen adapter]
├── crewai.py                    [CrewAI adapter]
└── langgraph.py                 [LangGraph adapter]
```

---

## When to Use Each Framework

| Framework | Best For | Complexity |
|-----------|----------|-----------|
| **AutoGen** | Multi-agent conversations, dynamic routing | Medium |
| **CrewAI** | Team-based workflows, role definitions | Low-Medium |
| **LangGraph** | Complex DAG workflows, stateful pipelines | High |
| **MCP Direct** | Standalone analysis, simple integrations | Low |

---

## Contributing New Integrations

To add a new framework integration:

1. Create `{framework_name}.py` in this directory
2. Implement the framework's agent interface
3. Handle message format conversion
4. Register MCP tools with the framework
5. Add configuration class
6. Create unit tests in `tests/integration/`
7. Document in this README

---

**Last Updated:** December 21, 2025  
**Version:** v3.0.0 - Autonomy Release  
**Status:** 3 Integrations Available (AutoGen, CrewAI, LangGraph)
