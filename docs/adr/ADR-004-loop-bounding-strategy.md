<!-- [20251215_DOCS] ADR-004: Loop Bounding Strategy for Symbolic Execution -->

# ADR-004: Loop Bounding Strategy for Symbolic Execution

**Status:** Accepted  
**Date:** 2025-12-15  
**Authors:** Code Scalpel Team  
**Supersedes:** None

---

## Context

Symbolic execution explores program paths by treating variables as symbolic values. Loops present a challenge because:

1. **Unbounded Loops:** A loop like `while x > 0: x -= 1` has infinitely many paths
2. **Path Explosion:** Each iteration doubles the number of paths (in the worst case)
3. **Non-Termination:** Without bounds, the engine may never complete

### Problem Statement

How do we handle loops in symbolic execution without:
- Hanging on infinite loops
- Missing important paths
- Producing excessive false positives

---

## Decision

We will implement **Fuel-Based Loop Bounding** with configurable limits.

### Strategy

```python
DEFAULT_LOOP_FUEL = 10  # Maximum iterations per loop

def execute_while(self, node, state):
    fuel = self.loop_fuel
    while fuel > 0:
        condition = self.eval(node.test, state)
        if solver.is_definitely_false(condition):
            break
        # Execute loop body
        state = self.execute_body(node.body, state)
        fuel -= 1
    
    if fuel == 0:
        # Mark path as "bounded" (may miss deeper paths)
        state.add_annotation("loop_bounded", node.lineno)
```

### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `max_loop_iterations` | 10 | Maximum iterations per loop |
| `max_total_paths` | 100 | Maximum total paths to explore |
| `loop_unroll_limit` | 3 | Iterations before summarization |

---

## Alternatives Considered

| Strategy | Pros | Cons | Decision |
|----------|------|------|----------|
| **Fuel-Based** | Simple, predictable | May miss deep bugs | **Selected** |
| Loop Invariants | Complete coverage | Requires inference | Future work |
| Concolic Execution | Concrete + symbolic | Complex implementation | Rejected |
| Path Merging | Reduces explosion | Loses precision | Rejected |

---

## Implementation Details

### Fuel Tracking

```python
class SymbolicState:
    def __init__(self):
        self.loop_fuel = {}  # {loop_id: remaining_fuel}
        self.bounded_loops = []  # Loops that hit fuel limit
```

### Path Annotations

When a loop exhausts fuel, we annotate the path:

```python
{
    "path_id": 42,
    "status": "bounded",
    "bounded_loops": [
        {"line": 15, "iterations": 10}
    ],
    "note": "Path may have additional behaviors beyond bound"
}
```

### Test Generation Impact

Bounded paths still generate test cases, but with a warning:

```python
def test_loop_example():
    # WARNING: Loop at line 15 was bounded at 10 iterations
    # This test may not cover all loop behaviors
    result = loop_example(x=5)
    assert result == expected
```

---

## Consequences

### Positive

1. **Termination Guarantee:** Analysis always completes
2. **Predictable Performance:** Bounded by max_paths × max_iterations
3. **Transparency:** Users know which paths were bounded
4. **Configurability:** Limits adjustable per-analysis

### Negative

1. **Incompleteness:** Deep loop bugs may be missed
2. **False Confidence:** Bounded paths might seem "covered"
3. **Tuning Required:** Default limits may not suit all code

### Mitigations

- Warn users when loops are bounded
- Suggest increasing limits for loop-heavy code
- Document limitations clearly in output

---

## Future Work

1. **Loop Summarization:** Infer loop invariants to generalize beyond bounds
2. **Adaptive Bounding:** Increase fuel for "interesting" loops
3. **Concolic Mode:** Use concrete execution to guide symbolic exploration

---

## References

- [RFC-001: Symbolic Execution](../architecture/RFC-001-SYMBOLIC-EXECUTION.md)
- [ADR-002: Z3 Solver Choice](ADR-002-z3-solver-choice.md)
