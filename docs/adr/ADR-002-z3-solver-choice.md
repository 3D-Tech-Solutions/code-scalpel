<!-- [20251215_DOCS] ADR-002: Z3 SMT Solver Selection -->

# ADR-002: Z3 SMT Solver Selection

**Status:** Accepted  
**Date:** 2025-12-15  
**Authors:** Code Scalpel Team  
**Supersedes:** None

---

## Context

Code Scalpel's symbolic execution engine requires an SMT (Satisfiability Modulo Theories) solver to:

1. Determine path feasibility (can a branch be reached?)
2. Generate concrete test inputs that trigger specific paths
3. Prove assertions about program behavior

### Requirements

| Requirement | Priority |
|-------------|----------|
| Support for integers, booleans, strings | Must Have |
| Python bindings | Must Have |
| Active maintenance | Must Have |
| Performance on typical code analysis queries | Should Have |
| Support for bitvectors and arrays | Nice to Have |

---

## Decision

We will use **Z3** from Microsoft Research as our SMT solver.

### Alternatives Considered

| Solver | Pros | Cons | Decision |
|--------|------|------|----------|
| **Z3** | Best Python bindings, excellent documentation, industry standard | Large dependency (~50MB) | **Selected** |
| CVC5 | Modern, good performance | Weaker Python bindings | Rejected |
| Yices2 | Fast for certain theories | Limited string support | Rejected |
| STP | Lightweight | No string theory | Rejected |

### Rationale

1. **Python Integration:** `z3-solver` PyPI package provides native Python bindings with Pythonic API
2. **Theory Support:** Z3 supports Int, Bool, String, Real, BitVec, Array - covering all our needs
3. **Maturity:** Used by KLEE, Angr, Manticore, and other symbolic execution tools
4. **Documentation:** Extensive tutorials and academic papers

---

## Implementation Details

### Installation

```bash
pip install z3-solver
```

### Usage Pattern

```python
from z3 import Int, Bool, String, Solver, sat

# Create symbolic variables
x = Int('x')
y = Int('y')

# Add constraints (path conditions)
solver = Solver()
solver.add(x > 10)
solver.add(y == x * 2)

# Check satisfiability
if solver.check() == sat:
    model = solver.model()
    print(f"x = {model[x]}, y = {model[y]}")
```

### Timeout Configuration

```python
solver.set("timeout", 5000)  # 5 second timeout per query
```

---

## Consequences

### Positive

1. **Robust Integration:** Z3's Python API is well-designed and maintained
2. **Feature Complete:** All required theories available out of the box
3. **Performance:** Highly optimized for typical SMT queries
4. **Ecosystem:** Large community and tooling support

### Negative

1. **Dependency Size:** Adds ~50MB to installation
2. **Native Code:** Requires platform-specific binaries
3. **Learning Curve:** SMT concepts can be complex for contributors

### Mitigations

- Document Z3 usage patterns in codebase
- Provide abstraction layer (`ConstraintSolver`) to hide Z3 specifics
- Include timeout handling to prevent solver hangs

---

## References

- [Z3 Documentation](https://z3prover.github.io/api/html/z3.html)
- [Z3 Python Tutorial](https://ericpony.github.io/z3py-tutorial/guide-examples.htm)
- [RFC-001: Symbolic Execution](../architecture/RFC-001-SYMBOLIC-EXECUTION.md)
