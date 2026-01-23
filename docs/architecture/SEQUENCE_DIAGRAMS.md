<!-- [20251215_DOCS] Architecture: Sequence Diagrams -->

# Code Scalpel Sequence Diagrams

This document provides detailed sequence diagrams for key Code Scalpel operations.

---

## 1. Code Extraction Workflow

```mermaid
sequenceDiagram
    participant Agent as AI Agent
    participant MCP as MCP Server
    participant Extractor as SurgicalExtractor
    participant Parser as AST Parser
    participant Cache as Analysis Cache
    participant FS as File System

    Agent->>MCP: extract_code(file_path, "function", "calculate_tax")
    MCP->>MCP: Validate parameters
    
    MCP->>Cache: Check cache(file_hash + target)
    alt Cache Hit
        Cache-->>MCP: Return cached extraction
    else Cache Miss
        MCP->>FS: Read file content
        FS-->>MCP: File bytes
        
        MCP->>Parser: Parse to AST
        Parser-->>MCP: AST tree
        
        MCP->>Extractor: Extract symbol
        Extractor->>Extractor: Walk AST
        Extractor->>Extractor: Find target node
        Extractor->>Extractor: Extract source range
        Extractor-->>MCP: Extracted code + metadata
        
        MCP->>Cache: Store result
    end
    
    MCP-->>Agent: {success: true, code: "...", dependencies: [...]}
```

---

## 2. Security Scan Workflow

```mermaid
sequenceDiagram
    participant Agent as AI Agent
    participant MCP as MCP Server
    participant Analyzer as SecurityAnalyzer
    participant Taint as TaintTracker
    participant Sink as SinkDetector
    participant Z3 as Z3 Solver

    Agent->>MCP: security_scan(code)
    MCP->>MCP: Parse code to AST
    
    MCP->>Analyzer: Analyze(ast)
    
    Analyzer->>Taint: Initialize tracker
    
    loop For each statement
        Analyzer->>Taint: Check for taint sources
        alt Is taint source
            Taint->>Taint: Mark variable tainted
        end
        
        Analyzer->>Taint: Propagate taint through assignments
        
        Analyzer->>Sink: Check for dangerous sinks
        alt Is sink with tainted data
            Sink->>Sink: Check for sanitizers
            alt No sanitizer
                Sink->>Analyzer: Report vulnerability
            end
        end
    end
    
    Analyzer-->>MCP: SecurityResult(vulnerabilities, taint_flows)
    MCP-->>Agent: {vulnerabilities: [...], summary: "..."}
```

---

## 3. Symbolic Execution Workflow

```mermaid
sequenceDiagram
    participant Agent as AI Agent
    participant MCP as MCP Server
    participant Engine as SymbolicEngine
    participant Interp as IRInterpreter
    participant State as SymbolicState
    participant Z3 as Z3 Solver

    Agent->>MCP: symbolic_execute(code)
    MCP->>MCP: Parse code to AST
    
    MCP->>Engine: Execute(ast)
    Engine->>State: Create initial state
    
    loop For each statement
        Engine->>Interp: Interpret statement
        
        alt Assignment
            Interp->>State: Update variable (symbolic)
        else If statement
            Interp->>State: Fork state
            State-->>Interp: (true_state, false_state)
            
            Interp->>Z3: Check feasibility (true branch)
            Z3-->>Interp: SAT/UNSAT
            
            Interp->>Z3: Check feasibility (false branch)
            Z3-->>Interp: SAT/UNSAT
        else Loop
            Interp->>Interp: Execute with fuel limit
        end
    end
    
    Engine->>Engine: Collect feasible paths
    
    loop For each path
        Engine->>Z3: Get concrete model
        Z3-->>Engine: {x: 5, y: 10, ...}
    end
    
    Engine-->>MCP: AnalysisResult(paths, inputs)
    MCP-->>Agent: {paths: [...], reproduction_inputs: [...]}
```

---

## 4. Cross-File Dependency Resolution

```mermaid
sequenceDiagram
    participant Agent as AI Agent
    participant MCP as MCP Server
    participant Resolver as ImportResolver
    participant Extractor as CrossFileExtractor
    participant FS as File System

    Agent->>MCP: extract_code(..., include_cross_file_deps=True)
    MCP->>MCP: Extract primary symbol
    MCP->>MCP: Identify unresolved symbols
    
    MCP->>Resolver: Resolve imports
    
    loop For each import
        Resolver->>FS: Find module file
        alt Module found
            FS-->>Resolver: Module path
            Resolver->>Resolver: Map import to file
        else Module not found
            Resolver->>Resolver: Mark as unresolved
        end
    end
    
    Resolver-->>MCP: Import map
    
    loop For each unresolved symbol
        MCP->>Extractor: Extract from external file
        Extractor->>FS: Read external file
        FS-->>Extractor: File content
        Extractor->>Extractor: Find symbol in file
        Extractor-->>MCP: External symbol code
    end
    
    MCP-->>Agent: {code: "...", external_dependencies: {...}}
```

---

## 5. Safe Symbol Update Workflow

```mermaid
sequenceDiagram
    participant Agent as AI Agent
    participant MCP as MCP Server
    participant Patcher as SurgicalPatcher
    participant Validator as Validator
    participant FS as File System

    Agent->>MCP: update_symbol(file_path, "function", name, new_code)
    
    MCP->>FS: Read original file
    FS-->>MCP: Original content
    
    MCP->>Validator: Validate new code syntax
    alt Syntax error
        Validator-->>MCP: SyntaxError
        MCP-->>Agent: {success: false, error: "Invalid syntax"}
    end
    
    MCP->>Validator: Check code type matches target
    alt Type mismatch
        Validator-->>MCP: TypeError
        MCP-->>Agent: {success: false, error: "Expected function, got class"}
    end
    
    MCP->>Patcher: Find symbol location
    Patcher->>Patcher: Walk AST
    Patcher-->>MCP: (start_line, end_line)
    
    MCP->>FS: Create backup (.bak)
    FS-->>MCP: Backup created
    
    MCP->>Patcher: Apply replacement
    Patcher->>Patcher: Splice new code
    Patcher-->>MCP: Modified content
    
    MCP->>FS: Write modified file
    FS-->>MCP: Write complete
    
    MCP-->>Agent: {success: true, backup: "file.py.bak", lines_changed: 5}
```

---

## 6. Project Crawl Workflow

```mermaid
sequenceDiagram
    participant Agent as AI Agent
    participant MCP as MCP Server
    participant Crawler as ProjectCrawler
    participant Parser as Parser
    participant Metrics as MetricsCalculator

    Agent->>MCP: crawl_project(root_path)
    
    MCP->>Crawler: Crawl(root_path)
    
    Crawler->>Crawler: Walk directory tree
    
    loop For each Python file
        Crawler->>Parser: Parse file
        Parser-->>Crawler: AST
        
        Crawler->>Metrics: Calculate complexity
        Metrics-->>Crawler: Cyclomatic complexity
        
        Crawler->>Crawler: Extract functions/classes
        Crawler->>Crawler: Check complexity threshold
        
        alt High complexity
            Crawler->>Crawler: Add to warnings
        end
    end
    
    Crawler->>Crawler: Generate summary
    Crawler-->>MCP: CrawlResult(files, summary, warnings)
    
    MCP-->>Agent: {total_files: 50, functions: 200, complexity_warnings: [...]}
```

---

## 7. Dependency Vulnerability Scan

```mermaid
sequenceDiagram
    participant Agent as AI Agent
    participant MCP as MCP Server
    participant Scanner as DependencyScanner
    participant OSV as OSV API

    Agent->>MCP: scan_dependencies(project_root)
    
    MCP->>Scanner: Scan(root)
    
    Scanner->>Scanner: Find requirements.txt
    Scanner->>Scanner: Find pyproject.toml
    Scanner->>Scanner: Find package.json
    
    Scanner->>Scanner: Parse dependency files
    
    loop For each dependency
        Scanner->>OSV: Query vulnerability database
        OSV-->>Scanner: Vulnerability list
        
        alt Vulnerabilities found
            Scanner->>Scanner: Add to findings
        end
    end
    
    Scanner->>Scanner: Calculate severity summary
    Scanner-->>MCP: ScanResult(dependencies, vulnerabilities, summary)
    
    MCP-->>Agent: {dependencies: [...], vulnerabilities: [...], severity: {...}}
```

---

## 8. Test Generation Workflow

```mermaid
sequenceDiagram
    participant Agent as AI Agent
    participant MCP as MCP Server
    participant Generator as TestGenerator
    participant Engine as SymbolicEngine
    participant Z3 as Z3 Solver

    Agent->>MCP: generate_unit_tests(code)
    
    MCP->>MCP: Parse code
    MCP->>MCP: Detect main function
    
    MCP->>Engine: Symbolic execution
    Engine-->>MCP: Execution paths
    
    MCP->>Generator: Generate tests from paths
    
    loop For each feasible path
        Generator->>Z3: Get concrete inputs
        Z3-->>Generator: Input values
        
        Generator->>Generator: Create test case
        Generator->>Generator: Add assertions
    end
    
    Generator->>Generator: Format as pytest/unittest
    Generator-->>MCP: GeneratedTests(code, cases)
    
    MCP-->>Agent: {test_code: "...", test_count: 5}
```
