# limits.toml Behavior Analysis

## Question: What happens if a user doesn't have limits.toml?

## Answer: **Enterprise tier is STILL UNLIMITED** ✅

The system has a **safe fallback chain** that ensures enterprise tier always gets unlimited capabilities.

## Test Results

### Scenario 1: limits.toml EXISTS (current state)
```
COMMUNITY    - max_k: 1,    max_nodes: 20    (LIMITED)
PRO          - max_k: 5,    max_nodes: 100   (LIMITED)
ENTERPRISE   - max_k: None, max_nodes: None  (UNLIMITED)
```

### Scenario 2: limits.toml MISSING (no file at all)
```
COMMUNITY    - max_k: 1,    max_nodes: 20    (LIMITED)
PRO          - max_k: 5,    max_nodes: 100   (LIMITED)
ENTERPRISE   - max_k: None, max_nodes: None  (UNLIMITED)
```

**Result: IDENTICAL BEHAVIOR** ✅

## How It Works

### Configuration Priority Chain
1. **Environment variable**: `CODE_SCALPEL_LIMITS_FILE`
2. **Project config**: `.code-scalpel/limits.toml`
3. **User config**: `~/.code-scalpel/limits.toml`
4. **System config**: `/etc/code-scalpel/limits.toml`
5. **Package default**: (bundled with distribution)
6. **Hardcoded defaults**: `src/code_scalpel/licensing/features.py` ⭐

### The Safety Net

When NO config file is found, the system falls back to **hardcoded defaults** in `features.py`:

```python
"get_graph_neighborhood": {
    "enterprise": {
        "enabled": True,
        "capabilities": {...},
        "limits": {
            "max_k": None,      # None means UNLIMITED
            "max_nodes": None,  # None means UNLIMITED
        },
    },
}
```

### The Merge Logic

```python
def merge_limits(defaults, overrides):
    merged = defaults.copy()
    merged.update(overrides)  # Only overwrites keys present in overrides
    return merged
```

**Key insight**: 
- If `overrides` is empty `{}`, the `None` values from defaults are preserved
- If `overrides` has `{"max_k": 10}`, it would OVERRIDE the unlimited default

### MCP Server Application

```python
max_k_hops = limits.get("max_k")
if max_k_hops is not None and k > max_k_hops:  # Only limits if NOT None
    k = int(max_k_hops)
```

When `max_k_hops` is `None`, the condition is false → **no limit applied**

## Recommendations

### For Enterprise Users

**Option 1: Omit the file entirely**
- Safe and simple
- Falls back to hardcoded defaults
- Enterprise gets unlimited automatically

**Option 2: Create limits.toml with empty enterprise section** (current)
```toml
[enterprise.get_graph_neighborhood]
# max_k and max_nodes unlimited - omit
```
- Explicitly documents the unlimited nature
- Same result as omitting the file
- Preferred for clarity

**Option 3: Use explicit comments only**
```toml
[enterprise.get_graph_neighborhood]
# Enterprise tier has unlimited k and max_nodes
# Omitting values preserves None (unlimited) from features.py
```

### What NOT to Do

❌ **DON'T add explicit numeric limits in enterprise section:**
```toml
[enterprise.get_graph_neighborhood]
max_k = 1000      # ❌ This LIMITS enterprise to 1000!
max_nodes = 5000  # ❌ This LIMITS enterprise to 5000!
```

This would **override** the `None` defaults and impose limits on enterprise tier.

## Conclusion

**Missing limits.toml is SAFE** - Enterprise tier will always be unlimited due to the hardcoded defaults fallback. The current approach of having an empty section with a comment is clearer but functionally equivalent.
