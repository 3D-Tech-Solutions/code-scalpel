# Code Scalpel Enhancement Roadmap & Versioning Strategy

## Enhancement Difficulty Matrix

 ### Tier 1: Quick Wins (1-2 weeks each)

| Enhancement | Effort | Impact | Notes |

|-------------|--------|--------|-------|

| **Float/Real support** | 3-5 days | Medium | Z3 RealSort already exists; type_inference.py:36 has FLOAT enum |

| **String concatenation** | 3-5 days | Low | Z3 string theory is slow but functional |

| **Configurable loop bounds** | 1-2 days | Low | Already parameterized; just expose in MCP |

| **Better error messages** | 3-5 days | Medium | Help LLMs understand analysis failures |

 

### Tier 2: Significant Work (2-4 weeks each)

 
| Enhancement | Effort | Impact | Notes |

|-------------|--------|--------|-------|

| **LibCST for Python comments** | 2-3 weeks | Medium | Replace ast with LibCST for full fidelity |

| **Basic inter-procedural (1 level)** | 3-4 weeks | High | Inline called functions, no recursion |

| **Loop invariant hints** | 2-3 weeks | Medium | User-provided invariants to help solver |

| **Smarter loop bounds** | 2-3 weeks | Medium | Detect `range(n)` and use symbolic n |

 
### Tier 3: Major Engineering (1-3 months each)

 

| Enhancement | Effort | Impact | Notes |

|-------------|--------|--------|-------|

| **Full inter-procedural SE** | 6-8 weeks | Critical | Function calls, return values, recursion |

| **State merging/widening** | 4-6 weeks | High | Abstract interpretation basics |

| **Custom type/class support** | 6-10 weeks | Medium | Object fields, method dispatch |

| **Query language (CodeQL-like)** | 8-12 weeks | High | DSL for custom analysis rules |

 

### Tier 4: Research-Level (3-6+ months)

 

| Enhancement | Effort | Impact | Notes |

|-------------|--------|--------|-------|

| **Full abstract interpretation** | 3-4 months | High | Requires domain theory expertise |

| **Automatic invariant generation** | 4-6 months | High | Template-based synthesis |

| **Incremental analysis** | 3-4 months | Medium | Only re-analyze changed code |

| **Concolic execution** | 4-6 months | High | Hybrid concrete+symbolic |

 



## Recommended Path to "Best in Class"

### Phase 1: Solid v1.0.0 Launch (Current + 2 weeks)

**Do now:**

1. Fork to v1.0.0 for public launch

2. Update marketing to match verified claims

3. Quick wins: Float support, better errors

 

**Marketing message:** "The first MCP-native code analysis toolkit for AI agents"

 

### Phase 2: v1.5.0 - Inter-procedural Lite (6-8 weeks)

 

**Add:**

1. Single-level function inlining (no recursion)

2. Return value tracking

3. LibCST for Python comment preservation

 

**Marketing message:** "Now analyzes function calls - see how changes propagate"

 

### Phase 3: v2.0.0 - Full Semantic Analysis (3-4 months)


**Add:**

1. Full inter-procedural symbolic execution

2. Recursion handling with bounds

3. State merging for loop acceleration

4. Basic custom type support

 
---


New versioning:

  v1.0.0 - Current capabilities (honest "first public release")

  v1.5.0 - Inter-procedural lite

  v2.0.0 - Full semantic analysis (the "real" v2)

 

Benefits:

  - Sets appropriate expectations

  - Leaves room for dramatic v2.0 announcement

  - Standard industry practice

  - Avoids "why can't your v2 do X?" questions

`
### Week 1-2: Quick Wins

- Add Float support (already 90% done)

- Improve error messages for LLM consumption

- Add "limitations" section to docs (builds trust)

 

| Investment | ~6-8 weeks |

|------------|------------|

| **Float support** | 1 week |

| **LibCST comments** | 2 weeks |

| **Basic inter-procedural** | 3-4 weeks |

 

| Benefit | Assessment |

|---------|------------|

| **Differentiation** | Significant - few tools do even basic inter-procedural |

| **Credibility** | High - can say "analyzes function calls" |

| **Risk reduction** | Addresses main technical criticism |


## Executive Summary

 

**Key Decision:** Single unified toolkit vs separate language-specific packages

 

**Recommendation: Unified Core + Optional Language Packs**

 

```

code-scalpel (core)           ← Always installed, includes Python

code-scalpel[web]             ← Adds JavaScript, TypeScript

code-scalpel[enterprise]      ← Adds Java, C#

code-scalpel[systems]         ← Adds C, C++, Rust, Go

code-scalpel[all]             ← Everything

```

 

This gives you:

- **Marketing simplicity** - "Code Scalpel" is one brand

- **Install flexibility** - Users only get what they need

- **Dependency management** - tree-sitter bindings only when needed

- **Enterprise upsell path** - Premium language packs possible

 

---

 

## Current State Assessment

 

### Language Maturity Matrix

 

| Language | Parser | Normalizer | Semantics | SE Support | Overall |

|----------|--------|------------|-----------|------------|---------|

| **Python** | ast (native) | 846 LOC | Complete | Full | Production |

| **JavaScript** | tree-sitter | 1,570 LOC | Complete | Partial | Production |

| **TypeScript** | tree-sitter | 360 LOC | Inherits JS | Partial | Production |

| **Java** | tree-sitter | 839 LOC | Missing | None | Beta |

| **C/C++** | Not added | - | - | - | Not started |

| **C#** | Not added | - | - | - | Not started |

| **Go** | Not added | - | - | - | Not started |

| **Rust** | Not added | - | - | - | Not started |

 

### Architecture Strength

 

The IR (Intermediate Representation) layer is **well-designed for expansion**:

- Structure vs Semantics separation

- BaseNormalizer interface for consistency

- TreeSitterVisitor reduces boilerplate by 60%

- Adding a new language: ~300-800 LOC

 

---

## Strategic Options Analysis

### Option A: Separate Packages (NOT Recommended)

 

```

code-scalpel-python    (PyPI)

code-scalpel-java      (PyPI)

code-scalpel-cpp       (PyPI)

```


| Pros | Cons |

|------|------|

| Clear language focus | Brand fragmentation |

| Independent versioning | Duplicated core code |

| Smaller installs | Complex cross-language analysis |

| | Multiple repos to maintain |

| | Confusing for users |

 

**Verdict:** Creates maintenance nightmare, fragments community.


### Option B: Monolithic Package (Partial Recommendation)

 

```

code-scalpel           (everything bundled)

```

 

| Pros | Cons |

|------|------|

| Simple to understand | Large install size |

| One version number | Unused dependencies |

| Easy cross-language | tree-sitter bindings bloat |

 

**Verdict:** Good for simplicity, but install size becomes issue.

### Option C: Core + Extras (RECOMMENDED)


```

pip install code-scalpel                    # Python only (core)

pip install code-scalpel[web]               # + JS, TS

pip install code-scalpel[enterprise]        # + Java, C#

pip install code-scalpel[systems]           # + C, C++, Rust, Go

pip install code-scalpel[all]               # Everything

```

 

| Pros | Cons |

|------|------|

| One brand, one repo | Slightly more complex packaging |

| Users choose languages | Optional deps management |

| Small default install | |

| Upsell path for premium | |

| Easy cross-language | |

 

**Verdict:** Best balance of simplicity and flexibility.

 

---

 

## Recommended Versioning Strategy

 

### Fork to v1.0.0 for Public Launch

 

```

Internal History          Public Launch

─────────────────         ─────────────────

v2.0.0 "Polyglot"    →    v1.0.0 "Foundation"

 

Future:

v1.1.0 - Float support, better errors

v1.2.0 - C/C++ support (systems pack)

v1.5.0 - Basic inter-procedural

v2.0.0 - Full inter-procedural SE

```

 

### Why v1.0.0?

 

1. **Sets appropriate expectations** - "First public release"

2. **Leaves room for v2.0.0** - Major milestone for full SE

3. **Industry standard** - Internal versions often reset

4. **Avoids awkward questions** - "Why can't v2 do X?"

 

---

 

## Multi-Language Expansion Roadmap

 

### Phase 1: v1.0.0 Foundation (Now)

 

**Languages:** Python, JavaScript, TypeScript, Java (current)

 

**Actions:**

1. Fork to v1.0.0

2. Create `[web]` extra for JS/TS

3. Mark Java as "beta" in docs

4. Marketing focus: Python + Web stack

 

**Package structure:**

```toml

[project.optional-dependencies]

web = ["tree-sitter-javascript>=0.21", "tree-sitter-typescript>=0.21"]

enterprise = ["tree-sitter-java>=0.21"]

```

 

---

 

### Phase 2: v1.2.0 Systems Languages (4-6 weeks)

 

**Add:** C, C++

 

**Why C/C++ first:**

- Massive market (embedded, systems, games)

- tree-sitter-cpp exists and is mature

- Differentiator from pure web analysis tools

- Enterprise/security market wants this

 

**Effort estimate:**

| Task | LOC | Days |

|------|-----|------|

| CppNormalizer | 600-800 | 3-4 |

| CppSemantics | 400-500 | 2-3 |

| Tests | 300-400 | 2 |

| Documentation | - | 1 |

| **Total** | **1,300-1,700** | **8-10 days** |

 

**Package addition:**

```toml

systems = ["tree-sitter-c>=0.21", "tree-sitter-cpp>=0.21"]

```

 

---

 

### Phase 3: v1.3.0 Enterprise Languages (6-8 weeks)

 

**Enhance:** Java (to production)

**Add:** C#, Kotlin

 

**Why these:**

- Enterprise market demand

- C# for .NET shops

- Kotlin for Android/modern JVM

 

**Effort estimate:**

| Language | LOC | Days | Notes |

|----------|-----|------|-------|

| Java (enhance) | 400 | 3 | Add semantics, generics |

| C# | 700 | 5 | Similar to Java |

| Kotlin | 500 | 4 | JVM, tree-sitter exists |

| **Total** | **1,600** | **12 days** |

 

**Package addition:**

```toml

enterprise = [

    "tree-sitter-java>=0.21",

    "tree-sitter-c-sharp>=0.21",

    "tree-sitter-kotlin>=0.21"

]

```

 

---

 

### Phase 4: v1.5.0 Modern Languages (8-12 weeks)

 

**Add:** Go, Rust

 

**Why:**

- Developer mindshare is high

- Modern, well-designed languages

- Good for cloud-native/DevOps market

 

**Effort estimate:**

| Language | LOC | Days | Notes |

|----------|-----|------|-------|

| Go | 500 | 4 | Clean syntax, easy |

| Rust | 800 | 6 | Borrow checker concepts |

| **Total** | **1,300** | **10 days** |

 

**Package addition:**

```toml

modern = ["tree-sitter-go>=0.21", "tree-sitter-rust>=0.21"]

```

 

---

 

### Phase 5: v2.0.0 Full Analysis (3-4 months)

 

**Focus:** Inter-procedural symbolic execution across ALL languages

 

**This is the "real" v2.0:**

- Function call analysis

- Cross-file dependencies

- Full taint tracking

- State merging for performance

 

**Marketing:** "Code Scalpel 2.0: True Program Understanding"

 

---

 

## Language-Specific Considerations

 

### Systems Languages (C/C++)

 

**Unique challenges:**

| Challenge | Solution | Effort |

|-----------|----------|--------|

| Pointers | Track as type annotation, not semantic | Low |

| Headers | Single-file focus initially | Deferred |

| Macros | Pre-process or ignore | Medium |

| Templates | Metadata extension to IR | Medium |

| Memory model | Document as limitation | None |

 

**Recommended scope for v1.2.0:**

- Functions, classes, structs

- Basic pointers (syntax only)

- No templates initially

- No header resolution

 

### Enterprise Languages (Java/C#/Kotlin)

 

**Unique challenges:**

| Challenge | Solution | Effort |

|-----------|----------|--------|

| Generics | Add type_params to IR | Medium |

| Annotations | Map to metadata | Low |

| Packages/namespaces | Already in IR | Done |

| Access modifiers | Store as metadata | Low |

 

**Recommended scope:**

- Full OOP support

- Generics as strings initially

- Annotations tracked

- No bytecode analysis

 

### Modern Languages (Go/Rust)

 

**Unique challenges:**

| Challenge | Solution | Effort |

|-----------|----------|--------|

| Go interfaces | Map to IRClassDef | Low |

| Go goroutines | Track as function calls | Low |

| Rust ownership | Document as limitation | None |

| Rust traits | Map to IRClassDef | Low |

| Rust macros | Ignore initially | None |

 

**Recommended scope:**

- Basic syntax coverage

- No borrow checker emulation

- No macro expansion

 

---

 

## Package Architecture

 

### Recommended pyproject.toml Structure

 

```toml

[project]

name = "code-scalpel"

version = "1.0.0"

description = "MCP-native code analysis toolkit for AI agents"

 

dependencies = [

    "z3-solver>=4.8.12",

    "networkx>=2.6",

    "astor>=0.8",

    # Python analysis is always included

]

 

[project.optional-dependencies]

web = [

    "tree-sitter>=0.21",

    "tree-sitter-javascript>=0.21",

    "tree-sitter-typescript>=0.21",

]

systems = [

    "tree-sitter>=0.21",

    "tree-sitter-c>=0.21",

    "tree-sitter-cpp>=0.21",

]

enterprise = [

    "tree-sitter>=0.21",

    "tree-sitter-java>=0.21",

    "tree-sitter-c-sharp>=0.21",

    "tree-sitter-kotlin>=0.21",

]

modern = [

    "tree-sitter>=0.21",

    "tree-sitter-go>=0.21",

    "tree-sitter-rust>=0.21",

]

all = [

    "code-scalpel[web]",

    "code-scalpel[systems]",

    "code-scalpel[enterprise]",

    "code-scalpel[modern]",

]

```

 

### Directory Structure

 

```

src/code_scalpel/

├── __init__.py

├── ir/

│   ├── nodes.py              # Shared IR (all languages)

│   ├── operators.py          # Shared operators

│   ├── semantics.py          # Language semantics

│   └── normalizers/

│       ├── __init__.py

│       ├── base.py           # BaseNormalizer

│       ├── python_normalizer.py      # Core

│       ├── javascript_normalizer.py  # [web]

│       ├── typescript_normalizer.py  # [web]

│       ├── java_normalizer.py        # [enterprise]

│       ├── csharp_normalizer.py      # [enterprise]

│       ├── kotlin_normalizer.py      # [enterprise]

│       ├── c_normalizer.py           # [systems]

│       ├── cpp_normalizer.py         # [systems]

│       ├── go_normalizer.py          # [modern]

│       └── rust_normalizer.py        # [modern]

```

 

---

 

## Marketing Strategy by Language Pack

 

### Core (Python)

 

**Target:** AI/ML developers, data scientists, Python shops

**Message:** "The analysis toolkit built for AI agents"

**Channels:** r/Python, r/MachineLearning, PyData

 

### Web Pack (JS/TS)

 

**Target:** Full-stack developers, React/Vue/Angular shops

**Message:** "Finally, semantic analysis for your JavaScript"

**Channels:** r/javascript, r/typescript, Dev.to

 

### Systems Pack (C/C++)

 

**Target:** Embedded, games, systems programmers

**Message:** "Security analysis for systems code"

**Channels:** r/cpp, r/embedded, Hacker News

 

### Enterprise Pack (Java/C#/Kotlin)

 

**Target:** Enterprise architects, .NET/JVM shops

**Message:** "Enterprise-grade code intelligence"

**Channels:** LinkedIn, DZone, InfoQ

 

### Modern Pack (Go/Rust)

 

**Target:** Cloud-native, DevOps, Rust evangelists

**Message:** "Modern analysis for modern languages"

**Channels:** r/golang, r/rust, CNCF community

 

---

 

## Timeline Summary

 

```

2024 Q1 (Now)

├── v1.0.0 Launch (Python + Web)

└── Marketing push on LinkedIn/Reddit

 

2024 Q2

├── v1.2.0 Systems Pack (C/C++)

└── Security market positioning

 

2024 Q3

├── v1.3.0 Enterprise Pack (Java/C#/Kotlin)

├── v1.5.0 Inter-procedural (basic)

└── Enterprise sales motion

 

2024 Q4

├── v1.6.0 Modern Pack (Go/Rust)

└── Cloud-native positioning

 

2025 Q1

├── v2.0.0 Full Analysis

└── "True program understanding" launch

```

 

---

 

## Investment Summary

 

| Phase | Languages | Effort | Timeline | Market |

|-------|-----------|--------|----------|--------|

| **v1.0.0** | Python, JS, TS, Java | Done | Now | AI/Web |

| **v1.2.0** | + C, C++ | 2 weeks | +6 weeks | Security |

| **v1.3.0** | + C#, Kotlin (Java++) | 2 weeks | +8 weeks | Enterprise |

| **v1.5.0** | Inter-procedural | 4 weeks | +12 weeks | All |

| **v1.6.0** | + Go, Rust | 2 weeks | +16 weeks | Cloud |

| **v2.0.0** | Full SE | 8 weeks | +24 weeks | All |

 

**Total new code for all languages:** ~5,000-6,000 LOC

**Total time:** ~20 weeks of focused development

**Result:** 10 languages, full symbolic execution, unified brand

 

---

 

## Recommendation

 

1. **Fork to v1.0.0** - Do this immediately

2. **Launch with Python + Web** - Your strongest offering

3. **Add C/C++ in v1.2.0** - Huge market, moderate effort

4. **Save "v2.0" for inter-procedural** - Make it a real milestone

5. **One brand, optional language packs** - Best of both worlds

 

The unified toolkit approach with optional extras gives you:

- Simple brand ("Code Scalpel")

- Flexible installs (users choose languages)

- Clear upgrade path (v1.x → v2.0)

- Enterprise upsell potential (premium language packs)