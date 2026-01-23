# type_evaporation_scan Tool Roadmap

**Tool Name:** `type_evaporation_scan`  
**Tool Version:** v1.0  
**Code Scalpel Version:** v3.3.1  
**Current Status:** Stable  
**Primary Module:** `src/code_scalpel/mcp/server.py` (line 4677)  
**Tier Availability:** All tiers (Community, Pro, Enterprise)

---

## Overview

The `type_evaporation_scan` tool detects Type System Evaporation vulnerabilities where TypeScript compile-time types are trusted but evaporate at serialization boundaries (JSON.stringify), enabling type confusion attacks.

**Why AI Agents Need This:**
- **Full-stack security:** Detect vulnerabilities that span frontend/backend boundaries
- **Type safety advocacy:** Help developers understand the limits of TypeScript types
- **Schema generation:** Enterprise tier auto-generates runtime validation
- **API contract enforcement:** Ensure frontend and backend agree on data shapes
- **Modern stack coverage:** Essential for TypeScript + Python/Node stacks

---

## Research Queries for Future Development

### Foundational Research
| Topic | Query | Purpose |
|-------|-------|---------|
| Type Soundness | "typescript type soundness runtime validation" | Understand TS limitations |
| Serialization | "serialization boundary security type confusion" | Better detection |
| Schema Validation | "json schema validation performance comparison" | Optimal validation |
| API Contracts | "api contract testing consumer-driven contracts" | Contract enforcement |

### Language-Specific Research
| Topic | Query | Purpose |
|-------|-------|---------|
| TypeScript | "typescript discriminated unions runtime checking" | Better TS patterns |
| Zod/io-ts | "runtime type validation typescript libraries comparison" | Schema generation |
| Python | "pydantic fastapi validation patterns" | Better Python detection |
| GraphQL | "graphql type safety runtime validation" | GraphQL support |

### Advanced Techniques
| Topic | Query | Purpose |
|-------|-------|---------|
| Static Analysis | "cross-language static analysis frontend backend" | Better correlation |
| ML Types | "machine learning type inference cross-boundary" | AI-assisted detection |
| Contract Testing | "contract testing microservices techniques" | Better validation |
| Schema Evolution | "schema evolution backward compatibility checking" | Version handling |

---

## Current Capabilities (v1.0)

### Community Tier
- ✅ Explicit `any` detection - `explicit_any_detection`
- ✅ TypeScript any scanning - `typescript_any_scanning`
- ✅ Basic type checking - `basic_type_check`
- ⚠️ **Limits:** Frontend-only analysis, max 50 files

### Pro Tier
- ✅ All Community features (500 files max)
- ✅ Frontend TypeScript type evaporation - `frontend_backend_correlation`
- ✅ Backend Python unvalidated input - `frontend_backend_correlation`
- ✅ Cross-file endpoint correlation - `frontend_backend_correlation`
- ✅ Implicit `any` from `.json()` detection - `implicit_any_tracing`
- ✅ Network boundary analysis (fetch, axios) - `network_boundary_analysis`
- ✅ Library boundary analysis - `library_boundary_analysis`
- ✅ JSON.parse location detection - `json_parse_tracking`

### Enterprise Tier
- ✅ All Pro features (unlimited files)
- ✅ Zod schema generation for TypeScript - `zod_schema_generation`
- ✅ Pydantic model generation for Python - `pydantic_model_generation`
- ✅ API contract validation - `api_contract_validation`
- ✅ Schema coverage metrics - `schema_coverage_metrics`
- ✅ Automated remediation suggestions - `automated_remediation`
- ✅ Custom type rules - `custom_type_rules`
- ✅ Compliance validation - `compliance_validation`

---

## Return Model: TypeEvaporationResult

```python
class TypeEvaporationResult(BaseModel):
    # Core fields (All Tiers)
    success: bool                                  # Whether scan succeeded
    frontend_issues: list[FrontendIssue]           # TypeScript type issues
    backend_issues: list[BackendIssue]             # Python unvalidated input
    cross_file_issues: list[CrossFileIssue]        # Frontend→Backend correlations
    total_issues: int                              # Total issue count
    risk_level: str                                # "critical" | "high" | "medium" | "low"
    
    # Pro Tier
    implicit_any_locations: list[Location]         # .json() without types
    network_boundaries: list[NetworkBoundary]      # fetch/axios calls
    library_boundaries: list[LibraryBoundary]      # localStorage, postMessage
    json_parse_locations: list[Location]           # JSON.parse without validation
    
    # Enterprise Tier
    generated_zod_schemas: dict[str, str]          # Type → Zod schema
    generated_pydantic_models: dict[str, str]      # Type → Pydantic model
    api_contracts: list[APIContract]               # Extracted contracts
    schema_coverage: SchemaCoverageMetrics         # Validation coverage
    remediation_suggestions: list[Remediation]     # Automated fixes
    
    error: str | None                              # Error message if failed
```

---

## Usage Examples

### Community Tier
```python
result = await type_evaporation_scan(
    frontend_code='''
type Role = 'admin' | 'user';
const role = input.value as Role;  // Unsafe assertion!
fetch('/api/user', {body: JSON.stringify({role})});
''',
    backend_code='''
role = request.get_json()['role']  # No validation!
'''
)
# Returns: cross_file_issues with frontend→backend type evaporation
# Limited to frontend-only for Community
```

### Pro Tier
```python
result = await type_evaporation_scan(
    frontend_file="/src/App.tsx",
    backend_file="/src/api/user.py"
)
# Additional: implicit_any_locations, network_boundaries,
#             library_boundaries, json_parse_locations
# Up to 500 files
```

### Enterprise Tier
```python
result = await type_evaporation_scan(
    frontend_root="/frontend/src",
    backend_root="/backend/src",
    generate_schemas=True
)
# Additional: generated_zod_schemas, generated_pydantic_models,
#             api_contracts, schema_coverage, remediation_suggestions
# Unlimited files
```

---

## Integration Points

### Related Tools
| Tool | Relationship |
|------|--------------|
| `security_scan` | Code-level vulnerabilities |
| `unified_sink_detect` | Sink detection (type evap is a source issue) |
| `cross_file_security_scan` | Multi-file taint analysis |
| `simulate_refactor` | Verify type changes are safe |

### Export Formats
| Format | Status | Use Case |
|--------|--------|----------|
| **JSON** | ✅ v1.0 | Programmatic analysis |
| **Zod schemas** | ✅ v1.0 (Enterprise) | Frontend validation |
| **Pydantic models** | ✅ v1.0 (Enterprise) | Backend validation |
| **OpenAPI spec** | 🔄 v1.2 | API documentation |

---

## Competitive Analysis

| Tool | Strengths | Weaknesses | Our Differentiation |
|------|-----------|------------|---------------------|
| **TypeScript** | Type checking | Runtime blind | Runtime validation gen |
| **Zod** | Great DX | Manual schema writing | Auto-generation |
| **io-ts** | Functional style | Verbose | Simpler output |
| **tRPC** | Full-stack types | tRPC-only | Any stack |
| **Pact** | Contract testing | Setup complexity | Integrated analysis |

---

## Configuration Files

### Tier Capabilities
- **File:** `src/code_scalpel/licensing/features.py` (line 978)
- **Structure:** Defines `capabilities` set and `limits` dict per tier

### Numeric Limits
- **File:** `.code-scalpel/limits.toml` (lines 154-162)
- **Community:** `max_files=50`, frontend-only
- **Pro:** `max_files=500`
- **Enterprise:** Unlimited

### Response Verbosity
- **File:** `.code-scalpel/response_config.json` (line 156)
- **Exclude fields:** `scan_metadata`, `ast_locations_raw`

---

## MCP Request/Response Examples

### MCP Request Format

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "mcp_code-scalpel_type_evaporation_scan",
    "arguments": {
      "frontend_code": "type Role = 'admin' | 'user';\nconst role = input.value as Role;\nfetch('/api/user', {body: JSON.stringify({role})});",
      "backend_code": "role = request.get_json()['role']  # No validation!"
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
    "frontend_issues": [
      {
        "type": "unsafe_type_assertion",
        "line": 2,
        "column": 14,
        "message": "Type assertion 'as Role' does not provide runtime validation",
        "typescript_type": "Role",
        "source": "input.value",
        "severity": "high"
      }
    ],
    "backend_issues": [],
    "cross_file_issues": [],
    "total_issues": 1,
    "risk_level": "high",
    "implicit_any_locations": null,
    "network_boundaries": null,
    "library_boundaries": null,
    "json_parse_locations": null,
    "generated_zod_schemas": null,
    "generated_pydantic_models": null,
    "api_contracts": null,
    "schema_coverage": null,
    "remediation_suggestions": null,
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
    "frontend_issues": [
      {
        "type": "unsafe_type_assertion",
        "line": 2,
        "column": 14,
        "message": "Type assertion 'as Role' does not provide runtime validation",
        "typescript_type": "Role",
        "source": "input.value",
        "severity": "high"
      }
    ],
    "backend_issues": [
      {
        "type": "unvalidated_json_input",
        "line": 1,
        "column": 8,
        "message": "JSON input accessed without validation",
        "field": "role",
        "expected_type": "unknown",
        "severity": "high"
      }
    ],
    "cross_file_issues": [
      {
        "frontend_file": "frontend.ts",
        "backend_file": "backend.py",
        "frontend_line": 3,
        "backend_line": 1,
        "type": "type_evaporation",
        "typescript_type": "Role ('admin' | 'user')",
        "description": "TypeScript union type 'Role' evaporates at JSON.stringify boundary - backend receives unvalidated string",
        "attack_vector": "Attacker can send arbitrary role value like 'superadmin' bypassing frontend type check"
      }
    ],
    "total_issues": 3,
    "risk_level": "critical",
    "implicit_any_locations": [
      {
        "file": "frontend.ts",
        "line": 3,
        "type": "fetch_response",
        "description": "fetch() response .json() returns implicit any"
      }
    ],
    "network_boundaries": [
      {
        "type": "fetch",
        "line": 3,
        "url": "/api/user",
        "method": "POST",
        "data_shape": "{role: string}"
      }
    ],
    "library_boundaries": [],
    "json_parse_locations": [],
    "generated_zod_schemas": null,
    "generated_pydantic_models": null,
    "api_contracts": null,
    "schema_coverage": null,
    "remediation_suggestions": null,
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
    "frontend_issues": [
      {
        "type": "unsafe_type_assertion",
        "line": 2,
        "column": 14,
        "message": "Type assertion 'as Role' does not provide runtime validation"
      }
    ],
    "backend_issues": [
      {
        "type": "unvalidated_json_input",
        "line": 1,
        "column": 8,
        "message": "JSON input accessed without validation"
      }
    ],
    "cross_file_issues": [
      {
        "frontend_file": "frontend.ts",
        "backend_file": "backend.py",
        "type": "type_evaporation",
        "typescript_type": "Role ('admin' | 'user')",
        "description": "TypeScript union type evaporates at serialization boundary"
      }
    ],
    "total_issues": 3,
    "risk_level": "critical",
    "implicit_any_locations": [],
    "network_boundaries": [],
    "library_boundaries": [],
    "json_parse_locations": [],
    "generated_zod_schemas": {
      "Role": "import { z } from 'zod';\n\nexport const RoleSchema = z.enum(['admin', 'user']);\nexport type Role = z.infer<typeof RoleSchema>;\n\n// Usage:\n// const role = RoleSchema.parse(input.value);",
      "UserRequest": "export const UserRequestSchema = z.object({\n  role: RoleSchema\n});"
    },
    "generated_pydantic_models": {
      "Role": "from enum import Enum\nfrom pydantic import BaseModel\n\nclass Role(str, Enum):\n    admin = 'admin'\n    user = 'user'",
      "UserRequest": "class UserRequest(BaseModel):\n    role: Role\n\n# Usage:\n# data = UserRequest(**request.get_json())"
    },
    "api_contracts": [
      {
        "endpoint": "/api/user",
        "method": "POST",
        "request_schema": "UserRequest",
        "typescript_types": ["Role"],
        "python_models": ["Role", "UserRequest"]
      }
    ],
    "schema_coverage": {
      "total_endpoints": 1,
      "validated_endpoints": 0,
      "coverage_percentage": 0.0,
      "unvalidated_fields": ["role"]
    },
    "remediation_suggestions": [
      {
        "file": "frontend.ts",
        "line": 2,
        "suggestion": "Replace type assertion with Zod validation",
        "before": "const role = input.value as Role;",
        "after": "const role = RoleSchema.parse(input.value);"
      },
      {
        "file": "backend.py",
        "line": 1,
        "suggestion": "Use Pydantic model for request validation",
        "before": "role = request.get_json()['role']",
        "after": "data = UserRequest(**request.get_json())\nrole = data.role"
      }
    ],
    "error": null
  },
  "id": 1
}
```

---

## Roadmap

### v1.1 (Q1 2026): Enhanced Detection

#### Pro Tier
- [ ] WebSocket message validation
- [ ] postMessage boundary tracking
- [ ] LocalStorage type evaporation
- [ ] GraphQL type checking

#### Enterprise Tier
- [ ] gRPC contract verification
- [ ] Protobuf schema generation
- [ ] OpenAPI spec validation
- [ ] Automated schema sync

### v1.2 (Q2 2026): Framework Support

#### Pro Tier
- [ ] React query/mutation tracking
- [ ] Next.js server action validation
- [ ] tRPC type safety checking
- [ ] Express middleware analysis

#### Enterprise Tier
- [ ] NestJS decorator analysis
- [ ] FastAPI endpoint validation
- [ ] Django view type checking
- [ ] Custom framework support

### v1.3 (Q3 2026): Advanced Features

#### Pro Tier
- [ ] Runtime type guard generation
- [ ] Automated test generation
- [ ] Type narrowing analysis
- [ ] Flow type support

#### Enterprise Tier
- [ ] Custom validation library support
- [ ] Multi-language contract verification
- [ ] Microservice boundary analysis
- [ ] Event-driven architecture validation

### v1.4 (Q4 2026): Automation & Integration

#### Pro Tier
- [ ] IDE real-time checking
- [ ] Pre-commit validation
- [ ] CI/CD integration

#### Enterprise Tier
- [ ] Automated PR creation for fixes
- [ ] Schema drift monitoring
- [ ] Compliance reporting
- [ ] SLA-based alerts

---

## Known Issues & Limitations

### Current Limitations
- **TypeScript/Python only:** Currently limited to TS frontend + Python backend
- **Complex types:** Very complex union types may not be fully analyzed
- **Third-party libraries:** External validation libraries not recognized

### Planned Fixes
- v1.1: Additional validation library support
- v1.2: Java/Go backend support
- v1.3: Better complex type handling

---

## Success Metrics

### Performance Targets
- **Scan time:** <2s for typical frontend/backend pair
- **Accuracy:** >90% correct type evaporation detection
- **False positive rate:** <10%

### Adoption Metrics
- **Usage:** 20K+ scans per month by Q4 2026
- **Vulnerabilities found:** 5K+ type evaporation issues
- **Schemas generated:** 10K+ validation schemas

---

## Dependencies

### Internal Dependencies
- `code_parsers/typescript_parsers/` - TypeScript parsing
- `code_parsers/python_parser.py` - Python parsing
- `security/analyzers/taint_tracker.py` - Taint analysis

### External Dependencies
- `tree-sitter-typescript` - TypeScript parsing
- `tree-sitter-python` - Python parsing

---

## Breaking Changes

None planned for v1.x series.

**Security Guarantee:**
- Detection format stable
- Schema generation backward compatible

---

**Last Updated:** December 30, 2025  
**Next Review:** March 31, 2026
