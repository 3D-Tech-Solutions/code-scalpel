# validate_paths Test Suite - Quick Reference

## 🚀 Quick Start

### Run All Tests
```bash
pytest tests/tools/validate_paths/ -v
```

### Run Specific Test Category
```bash
# Core functionality tests
pytest tests/tools/validate_paths/test_core.py -v

# Tier enforcement tests  
pytest tests/tools/validate_paths/tiers/test_tier_enforcement.py -v

# MCP interface tests
pytest tests/tools/validate_paths/mcp/test_mcp_interface.py -v

# License validation tests
pytest tests/tools/validate_paths/licensing/test_license_validation.py -v
```

### Run Single Test
```bash
pytest tests/tools/validate_paths/test_core.py::TestValidatePathsCore::test_validate_single_valid_path -v
```

---

## 📊 Test Suite Overview

| Category | Tests | Location |
|----------|-------|----------|
| Core Functionality | 15 | `test_core.py` |
| Tier Enforcement | 21 | `tiers/test_tier_enforcement.py` |
| MCP Interface | 48 | `mcp/test_mcp_interface.py` |
| **TOTAL** | **84** | - |

---

## 🗂️ Directory Structure

```
tests/tools/validate_paths/
├── conftest.py                      # Shared fixtures
├── test_core.py                     # Core tests (15)
├── licensing/
│   ├── __init__.py
│   └── test_license_validation.py  # License tests
├── tiers/
│   ├── __init__.py
│   └── test_tier_enforcement.py    # Tier tests (21)
├── mcp/
│   ├── __init__.py
│   └── test_mcp_interface.py        # MCP tests (48)
├── TEST_SUMMARY.md                  # Comprehensive documentation
├── COMPLETION_REPORT.md             # Implementation details
└── QUICK_REFERENCE.md               # This file
```

---

## 🎯 Key Test Areas

### 1. Core Functionality (`test_core.py`)
- Path validation (exists, accessible)
- Single and multiple paths
- Relative/absolute path handling
- Error scenarios
- Edge cases

### 2. Tier Enforcement (`tiers/test_tier_enforcement.py`)
- **Community Tier** (5 tests)
  - Core features available
  - 100 path limit enforced
  - No Pro/Enterprise features
  
- **Pro Tier** (5 tests)
  - All Community features
  - Advanced features available
  - Unlimited paths
  - No Enterprise features
  
- **Enterprise Tier** (4 tests)
  - All features available
  - Unlimited paths
  - Security features
  
- **Feature Gating** (3 tests)
  - Tier progression
  - Feature availability
  
- **Limit Enforcement** (4 tests)
  - Path limits per tier
  - Invalid tier handling

### 3. MCP Interface (`mcp/test_mcp_interface.py`)
- Tool registration (3 tests)
- Tool invocation (6 tests)
- Response format (7 tests)
- Error handling (5 tests)
- Tier filtering (7 tests)
- Envelope format (8 tests)
- Community interface (4 tests)
- Pro interface (4 tests)
- Enterprise interface (4 tests)

---

## 🔧 Common Test Patterns

### Testing with Tier Mocking
```python
@pytest.mark.usefixtures("mock_community_tier")
def test_community_feature():
    # Test runs with Community tier
    pass

@pytest.mark.usefixtures("mock_pro_tier")
def test_pro_feature():
    # Test runs with Pro tier
    pass

@pytest.mark.usefixtures("mock_enterprise_tier")
def test_enterprise_feature():
    # Test runs with Enterprise tier
    pass
```

### Testing MCP Tools
```python
from code_scalpel.mcp.server import mcp

def test_tool_registered():
    tools = mcp._tool_manager._tools
    assert "validate_paths" in tools
    
def test_tool_invocation():
    tool = mcp._tool_manager._tools["validate_paths"]
    # Test tool.fn() invocation
```

### Testing Error Handling
```python
def test_error_scenario():
    with pytest.raises(ValueError, match="expected error"):
        # Code that should raise error
        pass
```

---

## 🐛 Debugging Failed Tests

### View Full Error Details
```bash
pytest tests/tools/validate_paths/test_core.py -v --tb=long
```

### Run with Print Statements
```bash
pytest tests/tools/validate_paths/test_core.py -v -s
```

### Run Failed Tests Only
```bash
pytest tests/tools/validate_paths/ --lf
```

### Stop on First Failure
```bash
pytest tests/tools/validate_paths/ -x
```

---

## 📝 Adding New Tests

### 1. Core Functionality Test
Add to `test_core.py`:
```python
def test_new_core_feature():
    """Test description."""
    # Arrange
    paths = ["/test/path"]
    
    # Act
    result = validate_paths(paths)
    
    # Assert
    assert result["success"] is True
```

### 2. Tier Enforcement Test
Add to `tiers/test_tier_enforcement.py`:
```python
@pytest.mark.usefixtures("mock_pro_tier")
def test_new_pro_feature():
    """Test Pro tier specific feature."""
    caps = get_tool_capabilities("validate_paths", "pro")
    assert "new_feature" in caps["features"]
```

### 3. MCP Interface Test
Add to `mcp/test_mcp_interface.py`:
```python
def test_new_mcp_behavior():
    """Test MCP integration behavior."""
    tool = mcp._tool_manager._tools["validate_paths"]
    # Test tool behavior
```

---

## ✅ Pre-Commit Checklist

Before committing changes:
- [ ] All tests pass: `pytest tests/tools/validate_paths/ -v`
- [ ] No new warnings introduced
- [ ] Test coverage maintained or improved
- [ ] New tests documented with docstrings
- [ ] Updated TEST_SUMMARY.md if needed

---

## 🎓 Best Practices

### DO
✅ Write descriptive test names  
✅ Use AAA pattern (Arrange-Act-Assert)  
✅ Keep tests independent  
✅ Use fixtures for common setup  
✅ Document with docstrings  
✅ Test error cases  
✅ Mock external dependencies  

### DON'T
❌ Mix unit and integration tests  
❌ Test implementation details  
❌ Create test interdependencies  
❌ Use real file I/O when mocks suffice  
❌ Skip error case testing  
❌ Commit failing tests  

---

## 📚 Documentation

- **[TEST_SUMMARY.md](TEST_SUMMARY.md)** - Comprehensive test documentation
- **[COMPLETION_REPORT.md](COMPLETION_REPORT.md)** - Implementation details
- **[conftest.py](conftest.py)** - Shared fixtures documentation

---

## 🆘 Getting Help

### Issues?
1. Check [TEST_SUMMARY.md](TEST_SUMMARY.md) for coverage details
2. Check [COMPLETION_REPORT.md](COMPLETION_REPORT.md) for known issues
3. Review test code for examples
4. Ask the Code Scalpel team

### Contributing?
1. Follow the structure in this directory
2. Use existing tests as templates
3. Update documentation
4. Run full test suite before committing

---

## 📊 Current Status

**✅ ALL TESTS PASSING: 84/84 (100%)**

Last verified: 2025-01-02  
Python: 3.10.19  
Pytest: 7.4.3  
Runtime: ~1.5 seconds

---

**Maintained by:** Code Scalpel Test Team  
**Last updated:** 2025-01-02
