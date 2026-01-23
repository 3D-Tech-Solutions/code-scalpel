# update_symbol Tool Roadmap

**Tool Name:** `update_symbol`  
**Tool Version:** v1.0  
**Code Scalpel Version:** v3.3.0  
**Current Status:** Stable  
**Primary Module:** `src/code_scalpel/surgery/surgical_patcher.py`  
**Tier Availability:** All tiers (Community, Pro, Enterprise)

---

## Configuration Files

| File | Purpose |
|------|---------|
| `src/code_scalpel/licensing/features.py` | Tier capability definitions |
| `.code-scalpel/limits.toml` | Numeric limits (updates per session) |
| `.code-scalpel/response_config.json` | Output filtering |

---

## Overview

The `update_symbol` tool safely replaces functions, classes, or methods in files with new code while preserving surrounding code. Includes automatic backup creation and syntax validation.

**Why AI Agents Need This:**
- **Surgical precision:** Replace exactly one symbol without touching other code
- **Safety guarantees:** Syntax validation prevents broken code
- **Audit trail:** Enterprise tier tracks all modifications
- **Atomic operations:** Pro tier ensures multi-file consistency
- **Reversibility:** Automatic backups enable easy rollback

---

## Research Queries for Future Development

### Foundational Research
| Topic | Query | Purpose |
|-------|-------|---------|
| AST Surgery | "AST-based code modification preserving formatting" | Better formatting retention |
| Semantic Patching | "semantic code patching techniques" | Smarter replacements |
| Incremental Parsing | "incremental parsing code modification IDE" | Faster updates |
| Transactional | "transactional code modification rollback" | Better atomicity |

### Language-Specific Research
| Topic | Query | Purpose |
|-------|-------|---------|
| Python | "python ast codegen formatting preservation" | Better Python support |
| JavaScript | "javascript AST manipulation formatting tools" | JS/TS support |
| Java | "java refactoring library eclipse JDT" | Enterprise Java |
| Multi-Language | "polyglot code transformation tools" | Unified API |

### Advanced Techniques
| Topic | Query | Purpose |
|-------|-------|---------|
| AI-Assisted | "AI code generation integration IDE tools" | Better AI support |
| Validation | "code modification validation automated testing" | Stronger validation |
| Diffing | "semantic diff algorithms code changes" | Better change detection |
| Merging | "AST-based merge conflict resolution" | Handle conflicts |

---

## Current Capabilities (v1.0)

### Community Tier
- ✅ Replace functions by name
- ✅ Replace classes by name
- ✅ Replace methods in classes
- ✅ Automatic backup creation
- ✅ Syntax validation before write
- ✅ Supports Python, JavaScript, TypeScript, Java
- ⚠️ **Limits:** 10 updates per session

### Pro Tier
- ✅ All Community features (unlimited updates)
- ✅ Atomic multi-file updates
- ✅ Rollback on failure
- ✅ Pre/post update hooks
- ✅ Preservation of formatting
- ✅ Import auto-adjustment

### Enterprise Tier
- ✅ All Pro features
- ✅ Require code review approval before update
- ✅ Compliance-checked updates
- ✅ Audit trail for all modifications
- ✅ Custom validation rules
- ✅ Policy-gated mutations

---

## Return Model: UpdateResult

```python
class UpdateResult(BaseModel):
    # Core fields (All Tiers)
    success: bool                              # Whether update succeeded
    file_path: str                             # File that was modified
    symbol_name: str                           # Symbol that was replaced
    symbol_type: str                           # "function" | "class" | "method"
    backup_path: str | None                    # Path to backup file
    lines_changed: int                         # Number of lines modified
    syntax_valid: bool                         # Post-update syntax check
    
    # Pro Tier
    files_affected: list[str]                  # Multi-file updates
    imports_adjusted: list[ImportChange]       # Import statement changes
    rollback_available: bool                   # Can be rolled back
    formatting_preserved: bool                 # Original style maintained
    
    # Enterprise Tier
    approval_status: str | None                # "pending" | "approved" | "rejected"
    compliance_check: ComplianceResult         # Compliance validation
    audit_id: str | None                       # Audit trail identifier
    mutation_policy: str                       # Applied policy name
    
    error: str | None                          # Error message if failed
```

---

## Usage Examples

### Community Tier
```python
result = await update_symbol(
    file_path="/src/utils.py",
    target_type="function",
    target_name="calculate_tax",
    new_code='''
def calculate_tax(amount: float, rate: float = 0.1) -> float:
    """Calculate tax with improved accuracy."""
    return round(amount * rate, 2)
'''
)
# Returns: success, backup_path, lines_changed, syntax_valid
# Max 10 updates per session
```

### Pro Tier
```python
result = await update_symbol(
    file_path="/src/utils.py",
    target_type="function",
    target_name="calculate_tax",
    new_code=new_implementation,
    update_imports=True,
    preserve_formatting=True
)
# Additional: files_affected, imports_adjusted, rollback_available,
#             formatting_preserved
# Unlimited updates, atomic multi-file
```

### Enterprise Tier
```python
result = await update_symbol(
    file_path="/src/utils.py",
    target_type="function",
    target_name="calculate_tax",
    new_code=new_implementation,
    require_approval=True,
    compliance_check=True
)
# Additional: approval_status, compliance_check, audit_id, mutation_policy
# Repository-wide with governance
```

---

## Integration Points

### Related Tools
| Tool | Relationship |
|------|--------------|
| `extract_code` | Get current symbol before update |
| `rename_symbol` | Name changes (update is body changes) |
| `simulate_refactor` | Validate changes before applying |
| `get_symbol_references` | Understand update impact |

### Export Formats
| Format | Status | Use Case |
|--------|--------|----------|
| **Diff** | ✅ v1.0 | Preview changes |
| **JSON** | ✅ v1.0 | Programmatic results |
| **Backup** | ✅ v1.0 | Recovery files |

---

## Competitive Analysis

| Tool | Strengths | Weaknesses | Our Differentiation |
|------|-----------|------------|---------------------|
| **IDE Refactoring** | Integrated | Limited scope | Scriptable, MCP-native |
| **libcst (Python)** | Preserves formatting | Python only | Multi-language |
| **jscodeshift** | JS ecosystem | JS/TS only | Unified API |
| **recast** | AST preservation | Complex API | Simple interface |
| **Comby** | Pattern-based | Limited validation | Syntax validation |

---

## MCP Request/Response Examples

### MCP Request Format

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "mcp_code-scalpel_update_symbol",
    "arguments": {
      "file_path": "/home/user/project/src/utils.py",
      "target_type": "function",
      "target_name": "calculate_tax",
      "new_code": "def calculate_tax(amount: float, rate: float = 0.1) -> float:\n    \"\"\"Calculate tax with improved accuracy.\"\"\"\n    return round(amount * rate, 2)"
    }
  },
  "id": 1
}
```

### Community Tier Response

```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "file_path": "/home/user/project/src/utils.py",
    "symbol_name": "calculate_tax",
    "symbol_type": "function",
    "backup_path": "/home/user/project/src/utils.py.bak",
    "lines_changed": 4,
    "syntax_valid": true,
    "files_affected": null,
    "imports_adjusted": null,
    "rollback_available": null,
    "formatting_preserved": null,
    "approval_status": null,
    "compliance_check": null,
    "audit_id": null,
    "mutation_policy": null,
    "error": null
  },
  "id": 1
}
```

### Pro Tier Response

```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "file_path": "/home/user/project/src/utils.py",
    "symbol_name": "calculate_tax",
    "symbol_type": "function",
    "backup_path": "/home/user/project/.code-scalpel/backups/update_20251229_143022/utils.py",
    "lines_changed": 4,
    "syntax_valid": true,
    "files_affected": [
      "/home/user/project/src/utils.py"
    ],
    "imports_adjusted": [
      {
        "file": "/home/user/project/src/utils.py",
        "action": "added",
        "import": "from typing import Optional"
      }
    ],
    "rollback_available": true,
    "formatting_preserved": true,
    "approval_status": null,
    "compliance_check": null,
    "audit_id": null,
    "mutation_policy": null,
    "error": null
  },
  "id": 1
}
```

### Enterprise Tier Response

```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "file_path": "/home/user/project/src/utils.py",
    "symbol_name": "calculate_tax",
    "symbol_type": "function",
    "backup_path": "/home/user/project/.code-scalpel/backups/update_20251229_143022/utils.py",
    "lines_changed": 4,
    "syntax_valid": true,
    "files_affected": [
      "/home/user/project/src/utils.py"
    ],
    "imports_adjusted": [],
    "rollback_available": true,
    "formatting_preserved": true,
    "approval_status": "approved",
    "compliance_check": {
      "passed": true,
      "rules_checked": ["code-style", "security-scan", "type-safety"],
      "warnings": [],
      "violations": []
    },
    "audit_id": "audit-update-20251229-143022-xyz789",
    "mutation_policy": "standard-update-policy",
    "error": null
  },
  "id": 1
}
```

### Enterprise Tier Response (Approval Required)

```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": false,
    "file_path": "/home/user/project/src/utils.py",
    "symbol_name": "calculate_tax",
    "symbol_type": "function",
    "backup_path": null,
    "lines_changed": 0,
    "syntax_valid": true,
    "files_affected": [],
    "imports_adjusted": [],
    "rollback_available": false,
    "formatting_preserved": false,
    "approval_status": "pending",
    "compliance_check": {
      "passed": false,
      "rules_checked": ["code-style", "security-scan", "public-api-change"],
      "warnings": ["Function is part of public API"],
      "violations": [
        {
          "rule": "public-api-change",
          "message": "Modifying public API function requires team lead approval",
          "severity": "high"
        }
      ]
    },
    "audit_id": "audit-update-20251229-143025-pending",
    "mutation_policy": "public-api-policy",
    "error": "Update blocked: Approval required for public API modification"
  },
  "id": 1
}
```

### Community Tier Response (Syntax Error)

```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": false,
    "file_path": "/home/user/project/src/utils.py",
    "symbol_name": "calculate_tax",
    "symbol_type": "function",
    "backup_path": null,
    "lines_changed": 0,
    "syntax_valid": false,
    "files_affected": null,
    "imports_adjusted": null,
    "rollback_available": null,
    "formatting_preserved": null,
    "approval_status": null,
    "compliance_check": null,
    "audit_id": null,
    "mutation_policy": null,
    "error": "Syntax error in new code: unexpected indent at line 3, column 4"
  },
  "id": 1
}
```

---

## Roadmap

### v1.1 (Q1 2026): Safety Enhancements

#### Community Tier
- [ ] Better conflict detection
- [ ] Enhanced error recovery
- [ ] Improved diff preview

#### Pro Tier
- [ ] Behavior verification (run tests after update)
- [ ] Smart conflict resolution
- [ ] Update impact analysis

#### Enterprise Tier
- [ ] Automated rollback on test failure
- [ ] Multi-stage approval workflow
- [ ] Change risk scoring

### v1.2 (Q2 2026): Language Expansion

#### All Tiers
- [ ] Rust function updates
- [ ] Go function updates
- [ ] C++ function updates

#### Pro Tier
- [ ] Ruby method updates
- [ ] Swift function updates
- [ ] Kotlin function updates

### v1.3 (Q3 2026): Advanced Features

#### Pro Tier
- [ ] Batch update optimization
- [ ] Incremental updates (partial symbol changes)
- [ ] Smart indentation preservation

#### Enterprise Tier
- [ ] Version control integration (auto-commit)
- [ ] Update scheduling and batching
- [ ] Cross-repository updates

### v1.4 (Q4 2026): AI-Assisted Updates

#### Pro Tier
- [ ] AI-suggested refactorings during update
- [ ] Automated test generation for updated code
- [ ] Documentation auto-update

#### Enterprise Tier
- [ ] ML-based risk prediction
- [ ] Automated security review
- [ ] Compliance auto-check

---

## Known Issues & Limitations

### Current Limitations
- **Formatting:** May not preserve all original formatting nuances
- **Comments:** Inline comments within symbols may be lost
- **Complex macros:** C/C++ macro definitions not fully supported

### Planned Fixes
- v1.1: Improved comment preservation
- v1.2: Better formatting retention
- v1.3: Macro support

---

## Success Metrics

### Performance Targets
- **Update time:** <100ms per symbol
- **Success rate:** >99% successful updates
- **No data loss:** Zero incidents of code loss

### Adoption Metrics
- **Usage:** 200K+ updates per month by Q4 2026
- **Rollback rate:** <5% of updates

---

## Dependencies

### Internal Dependencies
- `ast_tools/transformer.py` - AST transformation
- `ast_tools/validator.py` - Syntax validation
- `autonomy/mutation_gate.py` - Mutation approval

### External Dependencies
- Language-specific formatters (optional)

---

## Breaking Changes

None planned for v1.x series.

**API Stability Promise:**
- Tool signature stable
- Backup behavior guaranteed
- Validation always performed

---

**Last Updated:** December 30, 2025  
**Next Review:** March 31, 2026
