<!-- [20251215_DOCS] Architecture: Component Diagrams -->

# Code Scalpel Component Diagrams

This document provides visual representations of Code Scalpel's architecture using Mermaid diagrams.

---

## High-Level Architecture

```mermaid
graph TB
    subgraph "AI Agents"
        Claude[Claude]
        Copilot[GitHub Copilot]
        ChatGPT[ChatGPT]
    end
    
    subgraph "MCP Layer"
        MCPServer[MCP Server]
        Tools[Tool Definitions]
    end
    
    subgraph "Core Engine"
        Parser[Multi-Language Parser]
        IR[IR Normalizer]
        Security[Security Analyzer]
        Symbolic[Symbolic Executor]
        Surgical[Surgical Tools]
    end
    
    subgraph "Storage"
        Cache[Analysis Cache]
        Workspace[User Workspace]
    end
    
    Claude --> MCPServer
    Copilot --> MCPServer
    ChatGPT --> MCPServer
    
    MCPServer --> Tools
    Tools --> Parser
    Tools --> Security
    Tools --> Symbolic
    Tools --> Surgical
    
    Parser --> IR
    IR --> Security
    IR --> Symbolic
    
    Surgical --> Workspace
    Parser --> Cache
```

---

## MCP Tool Request Flow

```mermaid
sequenceDiagram
    participant Agent as AI Agent
    participant MCP as MCP Server
    participant Tool as Tool Handler
    participant Parser as Parser
    participant Cache as Cache
    participant FS as File System
    
    Agent->>MCP: extract_code(file_path, target_name)
    MCP->>Tool: Dispatch to extract_code
    Tool->>Cache: Check cache
    alt Cache Hit
        Cache-->>Tool: Return cached result
    else Cache Miss
        Tool->>FS: Read file
        FS-->>Tool: File content
        Tool->>Parser: Parse code
        Parser-->>Tool: AST
        Tool->>Cache: Store result
    end
    Tool-->>MCP: Extraction result
    MCP-->>Agent: JSON response
```

---

## Security Analysis Pipeline

```mermaid
flowchart LR
    subgraph "Input"
        Source[Source Code]
    end
    
    subgraph "Parsing"
        AST[AST Parser]
        IR[IR Normalizer]
    end
    
    subgraph "Analysis"
        Taint[Taint Tracker]
        Sink[Sink Detector]
        Sanitizer[Sanitizer Check]
    end
    
    subgraph "Output"
        Vulns[Vulnerabilities]
        Report[Security Report]
    end
    
    Source --> AST
    AST --> IR
    IR --> Taint
    Taint --> Sink
    Sink --> Sanitizer
    Sanitizer --> Vulns
    Vulns --> Report
```

---

## Symbolic Execution Engine

```mermaid
flowchart TB
    subgraph "Input"
        Code[Python Code]
    end
    
    subgraph "Initialization"
        Parse[Parse AST]
        Infer[Type Inference]
        State[Create Initial State]
    end
    
    subgraph "Execution"
        Interp[IR Interpreter]
        Fork[State Forking]
        Constraint[Constraint Collection]
    end
    
    subgraph "Solving"
        Z3[Z3 Solver]
        Model[Model Extraction]
    end
    
    subgraph "Output"
        Paths[Feasible Paths]
        Inputs[Test Inputs]
    end
    
    Code --> Parse
    Parse --> Infer
    Infer --> State
    State --> Interp
    Interp --> Fork
    Fork --> Constraint
    Constraint --> Z3
    Z3 --> Model
    Model --> Paths
    Paths --> Inputs
```

---

## Multi-Language Parser Architecture

```mermaid
flowchart TB
    subgraph "Source Files"
        PY[.py files]
        JS[.js/.jsx files]
        TS[.ts/.tsx files]
        JAVA[.java files]
    end
    
    subgraph "Parsers"
        AST[Python ast module]
        TSJS[tree-sitter-javascript]
        TSTS[tree-sitter-typescript]
        TSJ[tree-sitter-java]
    end
    
    subgraph "Normalizers"
        PyNorm[Python Normalizer]
        JSNorm[JavaScript Normalizer]
        TSNorm[TypeScript Normalizer]
        JavaNorm[Java Normalizer]
    end
    
    subgraph "Common IR"
        IRNodes[IR Node Tree]
    end
    
    PY --> AST --> PyNorm --> IRNodes
    JS --> TSJS --> JSNorm --> IRNodes
    TS --> TSTS --> TSNorm --> IRNodes
    JAVA --> TSJ --> JavaNorm --> IRNodes
```

---

## Surgical Extraction Flow

```mermaid
flowchart LR
    subgraph "Request"
        Req[extract_code request]
    end
    
    subgraph "Extraction"
        Find[Find Symbol]
        Extract[Extract Code]
        Deps[Resolve Dependencies]
    end
    
    subgraph "Cross-File"
        Imports[Analyze Imports]
        Resolve[Resolve Modules]
        ExtDeps[Extract External Deps]
    end
    
    subgraph "Response"
        Code[Extracted Code]
        Context[Context Dependencies]
        Tokens[Token Estimate]
    end
    
    Req --> Find
    Find --> Extract
    Extract --> Deps
    Deps --> Imports
    Imports --> Resolve
    Resolve --> ExtDeps
    ExtDeps --> Code
    Code --> Context
    Context --> Tokens
```

---

## Cache Architecture

```mermaid
flowchart TB
    subgraph "Cache Layer"
        LRU[LRU Cache]
        Hash[Content Hash]
    end
    
    subgraph "Cache Types"
        AST[AST Cache]
        PDG[PDG Cache]
        Security[Security Cache]
        Symbolic[Symbolic Cache]
    end
    
    subgraph "Invalidation"
        ContentChange[Content Change]
        OptionsChange[Options Change]
        TTL[TTL Expiry]
        Manual[Manual Clear]
    end
    
    Hash --> LRU
    LRU --> AST
    LRU --> PDG
    LRU --> Security
    LRU --> Symbolic
    
    ContentChange --> Hash
    OptionsChange --> Hash
    TTL --> LRU
    Manual --> LRU
```

---

## Deployment Options

```mermaid
flowchart TB
    subgraph "Local Deployment"
        Local[Local MCP Server]
        LocalFS[Local Filesystem]
    end
    
    subgraph "Docker Deployment"
        Container[Docker Container]
        Volume[Mounted Volume]
    end
    
    subgraph "REST API"
        Flask[Flask Server]
        API[REST Endpoints]
    end
    
    subgraph "Clients"
        VSCode[VS Code + Copilot]
        Claude[Claude Desktop]
        Custom[Custom Agents]
    end
    
    VSCode --> Local
    Claude --> Local
    Local --> LocalFS
    
    Custom --> Container
    Container --> Volume
    
    Custom --> Flask
    Flask --> API
```
