---
name: cs-map
description: |
  Map project architecture: discover modules, build call graphs, visualize structure,
  trace critical paths. Complete architecture overview with dependency flows.
allowed-tools:
  - mcp__codescalpel__crawl_project
  - mcp__codescalpel__get_call_graph
  - mcp__codescalpel__get_project_map
  - mcp__codescalpel__get_cross_file_dependencies
preamble-tier: 1
---

# /cs-map — Project Architecture Mapping

Discover your entire project structure: modules, call graphs, dependencies, and
complexity hotspots. Visualize how everything connects.

## Usage

```bash
/cs-map
/cs-map src/
/cs-map src/api/
```

## The Complete Architecture Workflow

### Step 1: Crawl Project
Discover all modules and files:
- List all Python, JavaScript, TypeScript, Java files
- Identify entry points and main modules
- Group by package/directory structure
- Calculate total metrics (files, functions, classes)

### Step 2: Build Call Graph
Map function-to-function calls:
- How does main() call other functions?
- What functions call authenticate()?
- What are the circular dependencies?
- Call paths from entry point to critical functions

### Step 3: Visualize Structure
High-level project map:
- Package hierarchy
- Module roles (API layer, data layer, utilities)
- Complexity hotspots (functions with highest cyclomatic complexity)
- Import patterns (what imports what)
- Service boundaries (loosely coupled domains)

### Step 4: Trace Critical Paths
For important symbols:
- All functions that call it (incoming)
- All functions it calls (outgoing)
- Full dependency chain (what else gets pulled in)
- Impact zone (what breaks if you change it)

## What You Learn

**Project Structure**
- How many modules/packages?
- Which files are largest/most complex?
- What are the natural boundaries?

**Dependency Flow**
- How does data flow through the system?
- What are the entry points?
- Where are the bottlenecks?

**Complexity Hotspots**
- Which functions are most complex?
- Which files have the most dependencies?
- Where should you invest in refactoring?

**Call Patterns**
- Is the code layered (API → Services → Data)?
- Are there circular dependencies?
- How deep are the call chains?

## Example Output

```
Project Structure:
├── src/
│   ├── api/ (HTTP handlers, 12 functions)
│   │   ├── users.py
│   │   └── products.py
│   ├── services/ (business logic, 34 functions)
│   │   ├── auth.py
│   │   ├── payment.py
│   │   └── notifications.py
│   ├── models/ (data models, 8 classes)
│   ├── utils/ (helpers, 15 functions)
│   └── main.py (entry point)

Call Graph (from main):
main()
  ├─→ setup_api()
  │    └─→ register_routes()
  │         ├─→ api.users.list_users()
  │         └─→ api.products.get_product()
  └─→ run_server()

Complexity Hotspots:
1. services/payment.py — process_payment() [CC: 8]
2. api/users.py — validate_request() [CC: 7]
3. models/user.py — User.save() [CC: 6]
```

## When to Use This

✅ Onboarding to a new codebase
✅ Planning a major refactor
✅ Understanding system boundaries
✅ Finding where to add features
✅ Identifying technical debt
✅ Documenting architecture
✅ Preparing for code review

## Next Steps

1. **Review the map** — Understand overall structure
2. **Use `/cs-extract`** — Dive into specific functions
3. **Use `/cs-analyze`** — Understand a module
4. **Use `/cs-refactor`** — Improve the structure
5. **Use `/cs-security`** — Check for vulnerabilities

## Languages Supported

- Python (full analysis)
- JavaScript/TypeScript (full analysis)
- Java (full analysis)
- Go, Rust, C++ (basic analysis)

See `CLAUDE.md` for the complete architecture mapping workflow.
