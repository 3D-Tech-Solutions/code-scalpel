# Code Scalpel Agents

**Internal specialized agents for automated code analysis and recommendations**

---

## Overview

This directory contains Code Scalpel's **core analysis agents**. These agents implement the **OODA Loop** pattern (Observe → Orient → Decide → Act) to autonomously analyze code and provide actionable recommendations.

Unlike the integrations in `autonomy/integrations/`, these agents are **Code Scalpel's own implementations** that:
- Extend `BaseCodeAnalysisAgent` (OODA loop framework)
- Use MCP tools for code analysis
- Provide specialized analysis capabilities
- Can be used standalone via MCP protocol
- Can be embedded in external AI frameworks

---

## Agent Types (8 Total)

### Core Agents (Stable - ✅)

| Agent | Purpose | Key Methods | Status |
|-------|---------|------------|--------|
| **CodeReviewAgent** | Code quality analysis | `analyze_code_quality()`, `suggest_refactorings()` | ✅ Stable |
| **SecurityAgent** | Vulnerability detection | `analyze_security()`, `find_exploits()` | ✅ Stable |
| **OptimizationAgent** | Performance optimization | `analyze_performance()`, `suggest_optimizations()` | ✅ Stable |
| **BaseCodeAnalysisAgent** | OODA loop framework | `execute_ooda_loop()`, `observe()`, `orient()`, `decide()`, `act()` | ✅ Stable |

### New Agents (v3.0.0 - Stub Implementation - 🆕)

| Agent | Purpose | Key Methods | Status |
|-------|---------|------------|--------|
| **RefactoringAgent** | Code restructuring & design patterns | `analyze_structure()`, `detect_pattern_violations()` | 🆕 TODO |
| **TestingAgent** | Test generation & coverage analysis | `analyze_coverage()`, `identify_edge_cases()` | 🆕 TODO |
| **DocumentationAgent** | Documentation generation | `analyze_docstring_coverage()`, `suggest_api_docs()` | 🆕 TODO |
| **MetricsAgent** | Code metrics & analytics | `calculate_complexity_metrics()`, `analyze_coupling()` | 🆕 TODO |

---

## OODA Loop Pattern

All agents follow this **observe → orient → decide → act** cycle:

```python
# In BaseCodeAnalysisAgent.execute_ooda_loop():

1. OBSERVE: Gather data
   - observe_file() - Get file structure
   - find_symbol_usage() - Trace usage
   - analyze_code_security() - Check security
   
2. ORIENT: Analyze & classify
   - Run analysis tools (analyzer, security_scan, etc.)
   - Classify issues by severity
   - Prioritize findings
   
3. DECIDE: Plan actions
   - Select recommendations
   - Estimate impact
   - Check safety constraints
   
4. ACT: Apply changes
   - Use MCP tools (simulate_refactor, update_symbol)
   - Verify results
   - Report status
```

---

## Usage Examples

### Standalone (Direct Instantiation)

```python
from code_scalpel.agents import SecurityAgent

agent = SecurityAgent(
    quality_threshold=0.8,
    risk_level="high"
)

# Execute full OODA loop
results = agent.execute_ooda_loop(
    file_path="src/handlers.py",
    max_iterations=3
)

print(results.recommendations)
```

### Via MCP Protocol (Recommended)

```python
# Claude/Copilot calls Code Scalpel MCP server
# Server instantiates agents internally
# Agents perform analysis using MCP tools
```

### Integrated in External Frameworks

```python
# See autonomy/integrations/ for:
# - AutoGen integration
# - CrewAI integration
# - LangGraph integration
```

---

## Agent Configuration

Each agent accepts configuration parameters:

```python
# Common parameters
CodeReviewAgent(
    quality_threshold=0.85,      # Quality target
    risk_level="medium",         # Risk tolerance
    max_iterations=5,            # Max refinement loops
    timeout_seconds=300          # Execution timeout
)

# Agent-specific parameters
SecurityAgent(
    severity_threshold="high",   # Min severity to report
    check_dependencies=True,     # Scan CVEs
    enable_exploit_check=True    # Check exploitability
)

RefactoringAgent(
    preserve_behavior=True,      # Safety constraint
    min_impact_score=0.7,        # Impact threshold
    enable_auto_fix=False        # Manual review required
)
```

---

## Agent Capabilities by Type

### CodeReviewAgent ✅
- Cyclomatic complexity analysis
- Code duplication detection
- Style enforcement (Black, Ruff)
- Quick fix suggestions
- Code smell detection

**TODOs (5):**
- [ ] Custom metrics plugins
- [ ] Linter integration hooks
- [ ] CI/CD reporting
- [ ] Code smell patterns
- [ ] Style guide enforcement

### SecurityAgent ✅
- SQL Injection detection
- XSS vulnerability scanning
- Command injection detection
- Dependency CVE scanning
- Taint flow analysis

**TODOs (5):**
- [ ] CVSS scoring
- [ ] Exploit reachability assessment
- [ ] Threat database integration
- [ ] Threat modeling
- [ ] Exploit test generation

### OptimizationAgent ✅
- Complexity hotspot identification
- Performance pattern suggestions
- Memory profiling hooks
- Bottleneck detection
- Parallelization opportunities

**TODOs (5):**
- [ ] Profiler integration
- [ ] Complexity-aware refactoring
- [ ] Memory leak detection
- [ ] Benchmark integration
- [ ] Parallelization suggestions

### RefactoringAgent 🆕
- Code structure analysis
- Design pattern detection
- Modularization suggestions
- Refactoring impact estimation

**TODOs (6):**
- [ ] Extract method suggestions
- [ ] Extract class patterns
- [ ] Move fields/methods
- [ ] Compose methods
- [ ] Introduce parameter object
- [ ] Replace temp with query

### TestingAgent 🆕
- Test coverage analysis
- Edge case identification
- Integration test suggestions
- Test performance analysis

**TODOs (8):**
- [ ] Unit test generation
- [ ] Edge case exploration
- [ ] Mock suggestion
- [ ] Integration test patterns
- [ ] Performance test generation
- [ ] Mutation testing
- [ ] Coverage gap analysis
- [ ] Test data generation

### DocumentationAgent 🆕
- Docstring coverage analysis
- Type hint suggestions
- API documentation generation
- Example code generation

**TODOs (8):**
- [ ] Auto docstring generation
- [ ] Type hint inference
- [ ] API reference generation
- [ ] Usage example generation
- [ ] Changelog generation
- [ ] README suggestion
- [ ] Doctest generation
- [ ] Documentation linting

### MetricsAgent 🆕
- Code complexity metrics
- Coupling analysis
- Cohesion metrics
- Churn analysis

**TODOs (10):**
- [ ] LCOM calculation
- [ ] DIT analysis
- [ ] Response set metrics
- [ ] Instability metrics
- [ ] Abstractness metrics
- [ ] Code churn tracking
- [ ] Technical debt estimation
- [ ] Maintainability index
- [ ] Architecture metrics
- [ ] Trend analysis

---

## How Agents Use MCP Tools

Agents act as **intelligent wrappers** around MCP tools:

```
Agent.execute_ooda_loop()
    ↓
    OBSERVE: Call MCP tools
    ├── get_file_context()        # File structure
    ├── get_symbol_references()   # Usage tracking
    ├── security_scan()           # Vulnerabilities
    └── analyze_code()            # Metrics
    
    ↓
    ORIENT: Analyze results
    ├── Classify by severity
    ├── Filter by threshold
    └── Prioritize findings
    
    ↓
    DECIDE: Plan changes
    ├── simulate_refactor()       # Test change safety
    └── estimate_impact()         # Calculate effects
    
    ↓
    ACT: Apply changes
    ├── extract_code()            # Get target
    ├── update_symbol()           # Apply safely
    └── verify_results()          # Confirm success
```

---

## Best Practices

### When to Use Each Agent

| Task | Agent | Example |
|------|-------|---------|
| Quality assurance | CodeReviewAgent | "Review src/handlers.py for code quality" |
| Security audit | SecurityAgent | "Find security vulnerabilities in app.py" |
| Performance improvement | OptimizationAgent | "Suggest performance optimizations" |
| Code restructuring | RefactoringAgent | "Identify design pattern violations" |
| Test coverage | TestingAgent | "Generate tests for missing coverage" |
| Documentation gaps | DocumentationAgent | "Improve API documentation" |
| Metrics collection | MetricsAgent | "Calculate project complexity metrics" |

### Chaining Agents

For comprehensive analysis, chain multiple agents:

```python
# Phase 1: Find issues
security_results = security_agent.execute_ooda_loop(file)
quality_results = review_agent.execute_ooda_loop(file)

# Phase 2: Plan fixes
refactoring_results = refactoring_agent.execute_ooda_loop(file)

# Phase 3: Verify improvements
testing_results = testing_agent.execute_ooda_loop(file)

# Phase 4: Document changes
doc_results = documentation_agent.execute_ooda_loop(file)
```

### Safety Constraints

All agents respect safety parameters:

```python
agent = SecurityAgent(
    preserve_behavior=True,    # Never change semantics
    max_changes_per_file=10,   # Limit modifications
    require_tests=True,        # Require test coverage
    human_approval=True        # Need approval for breaking changes
)
```

---

## Integration Points

### With MCP Server
Agents are instantiated by `mcp_server.py` when clients request analysis:
```
Claude → MCP Tool Call → mcp_server.py → Agent → Analysis Results
```

### With External Frameworks
See [`autonomy/integrations/`](../autonomy/integrations/) for:
- AutoGen integration
- CrewAI integration  
- LangGraph integration

### With Autonomy Engine
See [`autonomy/engine.py`](../autonomy/engine.py) for orchestration.

---

## File Structure

```
agents/
├── README.md                          [This file]
├── __init__.py                        [Exports all agents]
├── base_agent.py                      [OODA loop framework]
├── code_review_agent.py               [Quality analysis]
├── security_agent.py                  [Vulnerability detection]
├── optimazation_agent.py              [Performance optimization]
├── refactoring_agent.py               [Code restructuring]
├── testing_agent.py                   [Test generation]
├── documentation_agent.py             [Documentation]
└── metrics_agent.py                   [Code metrics]
```

---

---

## Data Flow

### Input (FROM)
```
MCP Server (mcp_server.py)
    ↓ (agent instantiation)
User Request
    ↓ (file path, options)
Autonomy Engine (autonomy/engine.py)
    ↓ (orchestration signals)
External Frameworks (AutoGen, CrewAI, LangGraph)
```

### Processing (WITHIN)
```
Agent.execute_ooda_loop()
    ↓ (OBSERVE)
MCP Tools (security_scan, analyze_code, get_file_context, etc.)
    ↓ (ORIENT)
Internal Analysis (classify, prioritize findings)
    ↓ (DECIDE)
Decision Engine (plan actions, estimate impact)
    ↓ (ACT)
MCP Tools (simulate_refactor, update_symbol, generate_unit_tests)
```

### Output (TO)
```
Analysis Results
    ├─ Recommendations (severity-ranked)
    ├─ Findings (with locations)
    ├─ Suggested Changes (with impact estimates)
    └─ Safety Assessments (verify before applying)
    ↓
Autonomy Engine
    ↓
External Frameworks
    ↓
User / Claude / Copilot
```

---

## Development Roadmap

### Phase 1: Enhance Stable Agents (44 TODOs)
- **CodeReviewAgent (5 TODOs)**
  - [ ] Custom metrics plugins
  - [ ] Linter integration hooks
  - [ ] CI/CD reporting
  - [ ] Code smell patterns
  - [ ] Style guide enforcement

- **SecurityAgent (5 TODOs)**
  - [ ] CVSS scoring
  - [ ] Exploit reachability assessment
  - [ ] Threat database integration
  - [ ] Threat modeling
  - [ ] Exploit test generation

- **OptimizationAgent (5 TODOs)**
  - [ ] Profiler integration
  - [ ] Complexity-aware refactoring
  - [ ] Memory leak detection
  - [ ] Benchmark integration
  - [ ] Parallelization suggestions

- **BaseAgent (8 TODOs)**
  - [ ] Context persistence across loops
  - [ ] Agent versioning & compatibility
  - [ ] State serialization
  - [ ] Execution loop timeouts
  - [ ] Telemetry & metrics
  - [ ] Circuit breaker pattern
  - [ ] Human approval gates
  - [ ] Decision logging & auditability

### Phase 2: Implement New Agents (32 TODOs)
- **RefactoringAgent (6 TODOs)**
  - [ ] Extract method suggestions
  - [ ] Extract class patterns
  - [ ] Move fields/methods
  - [ ] Introduce parameter object
  - [ ] Compose methods
  - [ ] Replace temp with query

- **TestingAgent (8 TODOs)**
  - [ ] Unit test generation
  - [ ] Edge case exploration
  - [ ] Mock suggestion
  - [ ] Integration test patterns
  - [ ] Performance test generation
  - [ ] Mutation testing
  - [ ] Coverage gap analysis
  - [ ] Test data generation

- **DocumentationAgent (8 TODOs)**
  - [ ] Auto docstring generation
  - [ ] Type hint inference
  - [ ] API reference generation
  - [ ] Usage example generation
  - [ ] Changelog generation
  - [ ] README suggestion
  - [ ] Doctest generation
  - [ ] Documentation linting

- **MetricsAgent (10 TODOs)**
  - [ ] LCOM calculation
  - [ ] DIT analysis
  - [ ] Response set metrics
  - [ ] Instability metrics
  - [ ] Abstractness metrics
  - [ ] Code churn tracking
  - [ ] Technical debt estimation
  - [ ] Maintainability index
  - [ ] Architecture metrics
  - [ ] Trend analysis

### Phase 3: Advanced Features (Future)
- Multi-agent coordination
- Cross-agent data sharing
- Performance optimization loops
- Human-in-the-loop workflows
- Agent capability negotiation
- Error recovery & retry strategies
- Learning from feedback loops

---

## Data Flow

### Single Agent Execution
```
User Request / MCP / Framework
    ↓
Agent.execute_ooda_loop()
    ├─ OBSERVE: Get code structure
    │  ├─ read_file()
    │  ├─ analyze_code()
    │  └─ extract_references()
    │
    ├─ ORIENT: Interpret findings
    │  ├─ Pattern matching
    │  ├─ Risk assessment
    │  └─ Recommendation scoring
    │
    ├─ DECIDE: Generate recommendations
    │  ├─ Filter by severity
    │  ├─ Check policies
    │  └─ Prioritize findings
    │
    └─ ACT: Deliver results
       ├─ Format output
       ├─ Attach evidence
       └─ Return to caller
    ↓
Agent Output (Findings + Recommendations)
```

### Multi-Agent Coordination
```
AutonomyEngine Request
    ↓
Policy Engine: Determine required agents
    ├─ SecurityAgent
    ├─ CodeReviewAgent
    ├─ OptimizationAgent
    └─ Other agents...
    ↓
Sequential/Parallel Execution
    ├─ Each agent executes OODA loop
    ├─ Results cached for other agents
    └─ Cross-agent data sharing
    ↓
Result Synthesis
    ├─ Aggregate findings
    ├─ Resolve conflicts
    └─ Apply policies
    ↓
Final Report
```

---

## Development Roadmap

### Phase 1: Stub Completion (In Progress 🔄)

#### RefactoringAgent (12 TODOs)
- [ ] Method extraction detection
- [ ] Parameter object suggestions
- [ ] Duplicate code detection
- [ ] Design pattern violation detection
- [ ] Replace magic numbers
- [ ] Extract method suggestions
- [ ] Extract class patterns
- [ ] Move fields/methods
- [ ] Introduce parameter object
- [ ] Compose methods
- [ ] Replace temp with query
- [ ] Decompose conditional

#### TestingAgent (10 TODOs)
- [ ] Unit test generation
- [ ] Edge case exploration (symbolic execution)
- [ ] Mock suggestion
- [ ] Integration test patterns
- [ ] Performance test generation
- [ ] Mutation testing
- [ ] Coverage gap analysis
- [ ] Test data generation
- [ ] Parameterized test suggestions
- [ ] Test documentation generation

#### DocumentationAgent (10 TODOs)
- [ ] Auto docstring generation
- [ ] Type hint inference
- [ ] API reference generation
- [ ] Usage example generation
- [ ] Changelog generation
- [ ] README suggestion
- [ ] Doctest generation
- [ ] Documentation linting
- [ ] API deprecation documentation
- [ ] Architecture decision documentation

#### MetricsAgent (12 TODOs)
- [ ] LCOM (Lack of Cohesion of Methods)
- [ ] DIT (Depth of Inheritance Tree)
- [ ] Response set metrics
- [ ] Instability metrics
- [ ] Abstractness metrics
- [ ] Code churn tracking
- [ ] Technical debt estimation
- [ ] Maintainability index
- [ ] Architecture metrics
- [ ] Trend analysis
- [ ] Hotspot identification
- [ ] Complexity distribution

### Phase 2: Enhanced Capabilities (Planned)

#### Agent Enhancements (15 TODOs)
- [ ] Caching for repeated analysis
- [ ] Incremental analysis (only changed files)
- [ ] Parallel code analysis
- [ ] Result streaming
- [ ] Progress reporting
- [ ] Cancellation support
- [ ] Timeout handling
- [ ] Memory optimization
- [ ] Batch processing
- [ ] Result filtering
- [ ] Evidence attachment
- [ ] Confidence scoring
- [ ] Explanation generation
- [ ] Interactive mode
- [ ] Custom rule definitions

#### Coordination Framework (14 TODOs)
- [ ] Agent dependency graphs
- [ ] Data sharing between agents
- [ ] Result aggregation
- [ ] Conflict resolution
- [ ] Cross-agent communication
- [ ] Shared cache mechanism
- [ ] Agent capability negotiation
- [ ] Dynamic agent selection
- [ ] Feedback loops
- [ ] Learning from corrections
- [ ] Agent performance tracking
- [ ] Optimization suggestions
- [ ] Team composition optimization
- [ ] Delegation patterns

### Phase 3: Intelligence & Learning (Future)

#### Intelligent Analysis (12 TODOs)
- [ ] Machine learning for priority scoring
- [ ] Anomaly detection in code patterns
- [ ] Auto-tuning of thresholds
- [ ] Context-aware recommendations
- [ ] User preference learning
- [ ] False positive reduction
- [ ] Trend prediction
- [ ] Risk forecasting
- [ ] Impact simulation
- [ ] Root cause analysis
- [ ] Holistic code health scoring
- [ ] AI-guided refactoring

#### Advanced Workflows (10 TODOs)
- [ ] Automated refactoring application
- [ ] Continuous monitoring mode
- [ ] Scheduled analysis runs
- [ ] Change impact analysis
- [ ] Regression test generation
- [ ] Deployment risk assessment
- [ ] A/B testing support
- [ ] Feature flag analysis
- [ ] Security compliance checking
- [ ] Performance SLA enforcement

---

**Last Updated:** December 21, 2025  
**Version:** v3.0.0 - Autonomy Release  
**Status:** 4 Stable ✅ + 4 Stubs 🆕 (Total TODOs: 81)
