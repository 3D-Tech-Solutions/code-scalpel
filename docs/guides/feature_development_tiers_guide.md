# Feature Development Tiers Guide

> [20251226_DOCS] Comprehensive guide for implementing tier-based features in Code Scalpel MCP tools

**Version:** 1.0.0  
**Last Updated:** December 26, 2025  
**Based On:** Implementation of `code_policy_check` and `verify_policy_integrity` tools

---

## Executive Summary

This guide provides a structured approach for implementing new MCP tools or enhancing existing tools with the three-tier licensing structure (Community, Pro, Enterprise). It captures lessons learned and best practices from the successful implementation of tiered tools.

**Key Principle:** The tier system should provide progressive value while ensuring Community tier users have access to genuinely useful functionality.

---

## Table of Contents

1. [Understanding the Tier System](#1-understanding-the-tier-system)
2. [Planning a Tiered Feature](#2-planning-a-tiered-feature)
3. [Implementation Architecture](#3-implementation-architecture)
4. [Limits Configuration](#4-limits-configuration)
5. [Testing Strategy](#5-testing-strategy)
6. [Documentation Requirements](#6-documentation-requirements)
7. [Checklist Templates](#7-checklist-templates)
8. [Common Patterns and Anti-Patterns](#8-common-patterns-and-anti-patterns)
9. [Reference: Current Tool Inventory](#9-reference-current-tool-inventory)

---

## 1. Understanding the Tier System

### Tier Philosophy

| Tier | Target User | Value Proposition |
|------|-------------|-------------------|
| **Community** | Solo developers, hobbyists, OSS projects | Essential functionality for individual productivity |
| **Pro** | Small teams (1-20 developers) | Team collaboration, advanced analysis, custom rules |
| **Enterprise** | Large organizations (20+ developers) | Compliance, audit trails, unlimited scale, governance |

### Tier Progression Principles

1. **Community Must Be Useful**: Never cripple Community tier to drive upgrades
2. **Pro Adds Power**: More depth, customization, advanced features
3. **Enterprise Adds Scale & Compliance**: Unlimited resources, audit trails, regulatory features

### Standard Limit Categories

```
Community → Pro → Enterprise Progression:

FILES/RESOURCES:     10-100   →   500-1000   →   Unlimited
DEPTH/RECURSION:     1-3      →   5-10       →   Unlimited  
RULES/PATTERNS:      50       →   200        →   Unlimited
FEATURES:            Basic    →   Advanced   →   Full + Compliance
```

---

## 2. Planning a Tiered Feature

### Step 1: Define Core Functionality

Ask: "What is the minimum useful implementation?"

**Example (code_policy_check):**
- Core: Check code against patterns and report violations
- Essential output: file, line, rule_id, message, severity

### Step 2: Map Features to Tiers

Create a capability matrix before coding:

```markdown
| Feature | Community | Pro | Enterprise |
|---------|-----------|-----|------------|
| Basic pattern detection | ✅ | ✅ | ✅ |
| PEP8/style checking | ✅ | ✅ | ✅ |
| Security patterns | ❌ | ✅ | ✅ |
| Custom rules | ❌ | ✅ | ✅ |
| Compliance auditing | ❌ | ❌ | ✅ |
| PDF reports | ❌ | ❌ | ✅ |
| Audit trail | ❌ | ❌ | ✅ |
```

### Step 3: Define Limits

Reference `.code-scalpel/limits.toml` for consistency:

```toml
[community.your_tool]
max_files = 100
max_rules = 50
feature_x = false

[pro.your_tool]
max_files = 1000
max_rules = 200
feature_x = true

[enterprise.your_tool]
# Unlimited - omit limits
feature_x = true
```

### Step 4: Define Result Model Progression

**Community Result:**
```python
class ToolResult:
    success: bool
    files_checked: int
    basic_findings: list[Finding]
    summary: str
    tier: str
```

**Pro Result (adds):**
```python
    advanced_findings: list[AdvancedFinding]
    custom_rule_results: dict[str, list[dict]]
    security_warnings: list[SecurityWarning]
```

**Enterprise Result (adds):**
```python
    compliance_reports: dict[str, ComplianceReport]
    audit_trail: list[AuditEntry]
    pdf_report: str | None  # Base64 encoded
    certifications: list[Certification]
```

---

## 3. Implementation Architecture

### Directory Structure

```
src/code_scalpel/
├── policy_engine/           # Or appropriate parent module
│   └── your_tool/
│       ├── __init__.py      # Public exports
│       ├── models.py        # Data classes and result models
│       ├── patterns.py      # Pattern definitions (if applicable)
│       └── analyzer.py      # Main engine class
├── licensing/
│   └── features.py          # Capability definitions (update this)
└── mcp/
    └── server.py            # MCP tool handler (update this)
```

### Model Design Pattern

```python
# models.py
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class Finding:
    """Base finding - available in all tiers."""
    file: str
    line: int
    rule_id: str
    message: str
    severity: Severity
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "line": self.line,
            "rule_id": self.rule_id,
            "message": self.message,
            "severity": self.severity.value,
        }

@dataclass
class ProFinding(Finding):
    """Extended finding - Pro tier and above."""
    category: str = ""
    recommendation: str = ""
    
@dataclass
class ComplianceReport:
    """Compliance report - Enterprise only."""
    standard: str
    status: str  # "compliant", "partial", "non_compliant"
    score: float
    findings: list[dict] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ToolResult:
    """Main result with tier-aware serialization."""
    success: bool
    files_checked: int
    findings: list[Finding] = field(default_factory=list)
    summary: str = ""
    tier: str = "community"
    
    # Pro fields (None/empty in Community)
    advanced_findings: list[ProFinding] = field(default_factory=list)
    custom_results: dict[str, list] = field(default_factory=dict)
    
    # Enterprise fields (None/empty in Pro/Community)
    compliance_reports: dict[str, ComplianceReport] = field(default_factory=dict)
    audit_trail: list[dict] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize with tier-appropriate fields only."""
        result = {
            "success": self.success,
            "files_checked": self.files_checked,
            "findings": [f.to_dict() for f in self.findings],
            "summary": self.summary,
            "tier": self.tier,
        }
        
        if self.tier in ("pro", "enterprise"):
            result["advanced_findings"] = [f.to_dict() for f in self.advanced_findings]
            result["custom_results"] = self.custom_results
        
        if self.tier == "enterprise":
            result["compliance_reports"] = {
                k: v.to_dict() if hasattr(v, 'to_dict') else v
                for k, v in self.compliance_reports.items()
            }
            result["audit_trail"] = self.audit_trail
        
        return result
```

### Analyzer Pattern

```python
# analyzer.py
import logging
from pathlib import Path
from .models import ToolResult, Finding, ProFinding, ComplianceReport
from .patterns import get_patterns_for_tier

logger = logging.getLogger(__name__)

class ToolAnalyzer:
    """Main analyzer with tier-aware processing."""
    
    def __init__(
        self,
        tier: str = "community",
        custom_rules: list | None = None,
        compliance_standards: list[str] | None = None,
    ):
        self.tier = tier
        self.custom_rules = custom_rules or []
        self.compliance_standards = compliance_standards or []
        self.patterns = get_patterns_for_tier(tier)
        
        # Tier-specific limits from config
        self._max_files = self._get_tier_limit("max_files")
        self._max_rules = self._get_tier_limit("max_rules")
    
    def _get_tier_limit(self, limit_name: str) -> int | None:
        """Get tier-specific limit (None = unlimited)."""
        limits = {
            "community": {"max_files": 100, "max_rules": 50},
            "pro": {"max_files": 1000, "max_rules": 200},
            "enterprise": {"max_files": None, "max_rules": None},
        }
        return limits.get(self.tier, {}).get(limit_name)
    
    def analyze(self, paths: list[str], **options) -> ToolResult:
        """Main entry point - routes to tier-appropriate processing."""
        
        # Collect and limit files
        files = self._collect_files(paths)
        if self._max_files and len(files) > self._max_files:
            files = files[:self._max_files]
        
        # Core processing (all tiers)
        findings = self._run_basic_analysis(files)
        
        result = ToolResult(
            success=True,
            files_checked=len(files),
            findings=findings,
            tier=self.tier,
        )
        
        # Pro tier additions
        if self.tier in ("pro", "enterprise"):
            result.advanced_findings = self._run_advanced_analysis(files)
            result.custom_results = self._apply_custom_rules(files)
        
        # Enterprise tier additions
        if self.tier == "enterprise":
            result.compliance_reports = self._run_compliance_audit(files)
            result.audit_trail = self._create_audit_entry(files, result)
        
        result.summary = self._build_summary(result)
        return result
    
    def _run_basic_analysis(self, files: list[str]) -> list[Finding]:
        """Community tier analysis - always runs."""
        # Implementation
        pass
    
    def _run_advanced_analysis(self, files: list[str]) -> list[ProFinding]:
        """Pro tier analysis - security, best practices, etc."""
        # Implementation
        pass
    
    def _apply_custom_rules(self, files: list[str]) -> dict[str, list]:
        """Pro tier custom rules."""
        # Implementation
        pass
    
    def _run_compliance_audit(self, files: list[str]) -> dict[str, ComplianceReport]:
        """Enterprise tier compliance checking."""
        # Implementation
        pass
    
    def _create_audit_entry(self, files: list[str], result: ToolResult) -> list[dict]:
        """Enterprise tier audit trail."""
        # Implementation
        pass
```

### MCP Server Integration

```python
# In server.py

from pydantic import BaseModel, Field
from typing import Optional

class YourToolResult(BaseModel):
    """MCP response model for your_tool."""
    success: bool
    files_checked: int
    findings: list[dict]
    summary: str
    tier: str
    
    # Pro tier fields (optional)
    advanced_findings: Optional[list[dict]] = None
    custom_results: Optional[dict] = None
    
    # Enterprise tier fields (optional)
    compliance_reports: Optional[dict] = None
    audit_trail: Optional[list[dict]] = None
    error: Optional[str] = None

def _your_tool_sync(
    paths: list[str],
    rules: list[str] | None = None,
    compliance_standards: list[str] | None = None,
    tier: str = "community",
) -> dict:
    """Synchronous wrapper for your_tool."""
    from code_scalpel.your_module import YourAnalyzer
    
    analyzer = YourAnalyzer(
        tier=tier,
        compliance_standards=compliance_standards,
    )
    
    result = analyzer.analyze(paths, rules=rules)
    return result.to_dict()

@mcp.tool()
async def your_tool(
    paths: list[str],
    rules: list[str] | None = None,
    compliance_standards: list[str] | None = None,
) -> YourToolResult:
    """
    Your tool description.
    
    [20251226_FEATURE] Tier-aware tool implementation.
    
    Args:
        paths: List of file paths to analyze
        rules: Optional list of rule IDs to apply
        compliance_standards: Enterprise-only compliance standards
    
    Returns:
        YourToolResult with tier-appropriate fields
    
    Tier Capabilities:
        Community: Basic analysis, limited files
        Pro: + Advanced analysis, custom rules
        Enterprise: + Compliance auditing, audit trail
    """
    import os
    
    tier = os.environ.get("CODE_SCALPEL_TIER", "community").lower()
    
    # Tier downgrade warnings
    if compliance_standards and tier != "enterprise":
        compliance_standards = None  # Ignore in non-enterprise
    
    result = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: _your_tool_sync(paths, rules, compliance_standards, tier),
    )
    
    return YourToolResult(**result)
```

### Features.py Integration

```python
# In licensing/features.py

# Add to TOOL_CAPABILITIES dictionary:
"your_tool": {
    "community": {
        "capabilities": {
            "basic_analysis",
            "pattern_detection",
        },
        "limits": {
            "max_files": 100,
            "max_rules": 50,
        },
    },
    "pro": {
        "capabilities": {
            "basic_analysis",
            "pattern_detection",
            "advanced_analysis",
            "custom_rules",
            "security_patterns",
        },
        "limits": {
            "max_files": 1000,
            "max_rules": 200,
        },
    },
    "enterprise": {
        "capabilities": {
            "basic_analysis",
            "pattern_detection",
            "advanced_analysis",
            "custom_rules",
            "security_patterns",
            "compliance_auditing",
            "audit_trail",
            "certifications",
        },
        "limits": {},  # No limits
    },
},
```

---

## 4. Limits Configuration

### limits.toml Structure

Location: `.code-scalpel/limits.toml`

```toml
# Standard limit structure for a tool
[community.your_tool]
max_files = 100
max_rules = 50
feature_name = false

[pro.your_tool]
max_files = 1000
max_rules = 200
feature_name = true

[enterprise.your_tool]
# Omit limits for unlimited
# Or explicitly set to very high values
feature_name = true
```

### Limit Types

| Type | Community | Pro | Enterprise | Notes |
|------|-----------|-----|------------|-------|
| **File Count** | 100 | 1000 | Unlimited | Files to process |
| **Depth** | 1-3 | 5-10 | Unlimited | Recursion/traversal depth |
| **Rules** | 50 | 200 | Unlimited | Number of rules/patterns |
| **Size** | 1MB | 10MB | 100MB+ | File size limits |
| **Boolean** | false | true | true | Feature flags |

### Loading Limits in Code

```python
import tomllib
from pathlib import Path

def load_tier_limits(tool_name: str, tier: str) -> dict:
    """Load limits from limits.toml."""
    config_paths = [
        Path(".code-scalpel/limits.toml"),
        Path.home() / ".code-scalpel/limits.toml",
        Path("/etc/code-scalpel/limits.toml"),
    ]
    
    for path in config_paths:
        if path.exists():
            with open(path, "rb") as f:
                config = tomllib.load(f)
                return config.get(f"{tier}.{tool_name}", {})
    
    return {}  # Use hardcoded defaults
```

---

## 5. Testing Strategy

### Test File Structure

```
tests/
└── test_your_tool_tiers.py
```

### Test Categories

```python
"""
Tests for your_tool - Tier-based functionality.

[20251226_TEST] Comprehensive tier testing template.
"""

import pytest

class TestCommunityTier:
    """Community tier tests - basic functionality and limits."""
    
    def test_basic_functionality(self):
        """Core functionality works in Community tier."""
        pass
    
    def test_file_limit_enforced(self):
        """File limit is enforced at 100."""
        pass
    
    def test_no_pro_features(self):
        """Pro features not available/empty in Community."""
        pass
    
    def test_no_enterprise_features(self):
        """Enterprise features not available/empty in Community."""
        pass
    
    def test_result_serialization(self):
        """Result dict excludes Pro/Enterprise fields."""
        pass

class TestProTier:
    """Pro tier tests - advanced features."""
    
    def test_includes_community_features(self):
        """All Community features work in Pro."""
        pass
    
    def test_advanced_analysis(self):
        """Pro-specific features work."""
        pass
    
    def test_custom_rules(self):
        """Custom rules are applied."""
        pass
    
    def test_higher_limits(self):
        """Pro limits (1000 files) work."""
        pass
    
    def test_no_enterprise_features(self):
        """Enterprise features not in Pro."""
        pass

class TestEnterpriseTier:
    """Enterprise tier tests - compliance and audit."""
    
    def test_includes_all_features(self):
        """All Pro and Community features work."""
        pass
    
    def test_compliance_auditing(self):
        """Compliance reports generated."""
        pass
    
    def test_audit_trail(self):
        """Audit entries created."""
        pass
    
    def test_no_limits(self):
        """No file/rule limits enforced."""
        pass
    
    def test_pdf_generation(self):
        """PDF reports generated when requested."""
        pass
    
    def test_certifications(self):
        """Certifications generated for passing standards."""
        pass

class TestEdgeCases:
    """Edge cases and error handling."""
    
    def test_empty_input(self):
        """Handles empty file list."""
        pass
    
    def test_nonexistent_files(self):
        """Handles missing files gracefully."""
        pass
    
    def test_syntax_errors(self):
        """Handles malformed files."""
        pass
    
    def test_encoding_errors(self):
        """Handles encoding issues."""
        pass

class TestMCPIntegration:
    """MCP tool integration tests."""
    
    @pytest.mark.asyncio
    async def test_mcp_community_tier(self):
        """MCP tool works with community tier."""
        pass
    
    @pytest.mark.asyncio
    async def test_mcp_pro_tier(self):
        """MCP tool works with pro tier."""
        pass
    
    @pytest.mark.asyncio
    async def test_mcp_enterprise_tier(self):
        """MCP tool works with enterprise tier."""
        pass
    
    @pytest.mark.asyncio
    async def test_tier_downgrade_warning(self):
        """Enterprise features ignored in lower tiers."""
        pass
```

### Test Count Target

| Tier | Minimum Tests |
|------|---------------|
| Community | 5-7 |
| Pro | 5-7 |
| Enterprise | 5-7 |
| Edge Cases | 5-7 |
| MCP Integration | 3-5 |
| **Total** | **25-35** |

---

## 6. Documentation Requirements

### Required Documentation

1. **Roadmap Document** (before implementation)
   - Location: `docs/status/{tool_name}_tier_roadmap.md`
   - Content: Capability matrix, effort estimates, phases
   
2. **Release Notes Entry**
   - Location: `docs/release_notes/RELEASE_NOTES_vX.Y.Z.md`
   - Content: Feature description, usage examples
   
3. **Tier Reference Update**
   - Location: `docs/reference/mcp_tools_by_tier.md`
   - Content: Tool capabilities per tier

### Documentation Template

```markdown
# {tool_name} Tool - Tier Implementation

**Status:** Community ✅ | Pro ✅ | Enterprise ✅
**Version:** vX.Y.Z
**Date:** YYYY-MM-DD

## Capability Matrix

| Feature | Community | Pro | Enterprise |
|---------|-----------|-----|------------|
| Feature A | ✅ | ✅ | ✅ |
| Feature B | ❌ | ✅ | ✅ |
| Feature C | ❌ | ❌ | ✅ |

## Usage Examples

### Community Tier
```python
result = tool.analyze(files, tier="community")
```

### Pro Tier
```python
result = tool.analyze(files, tier="pro", custom_rules=[...])
```

### Enterprise Tier
```python
result = tool.analyze(files, tier="enterprise", compliance=["hipaa"])
```

## Test Results

- Community: X/X tests passing
- Pro: X/X tests passing
- Enterprise: X/X tests passing
- Total: XX/XX tests passing
```

---

## 7. Checklist Templates

### New Tool Development Checklist

```markdown
## New Tool: {tool_name}

### Phase 1: Planning
- [ ] Define core functionality
- [ ] Create capability matrix
- [ ] Define limits per tier
- [ ] Create roadmap document

### Phase 2: Implementation
- [ ] Create module structure
- [ ] Implement models.py
- [ ] Implement patterns.py (if applicable)
- [ ] Implement analyzer.py
- [ ] Update features.py
- [ ] Update limits.toml
- [ ] Add MCP handler to server.py
- [ ] Add to tool registration sets

### Phase 3: Testing
- [ ] Create test file
- [ ] Community tier tests (5+ passing)
- [ ] Pro tier tests (5+ passing)
- [ ] Enterprise tier tests (5+ passing)
- [ ] Edge case tests (5+ passing)
- [ ] MCP integration tests (3+ passing)
- [ ] All tests passing

### Phase 4: Documentation
- [ ] Update roadmap document with completed status
- [ ] Add release notes entry
- [ ] Update tier reference docs

### Phase 5: Verification
- [ ] Run full test suite (no regressions)
- [ ] Run linting/formatting
- [ ] Run type checking
- [ ] Manual testing of all tiers
```

### Existing Tool Enhancement Checklist

```markdown
## Tool Enhancement: {tool_name}

### Assessment
- [ ] Current tier support documented
- [ ] Gaps identified
- [ ] Enhancement scope defined

### Implementation
- [ ] Update models for new tier fields
- [ ] Add tier-specific logic
- [ ] Update MCP handler
- [ ] Update features.py
- [ ] Update limits.toml

### Testing
- [ ] Add tests for new features
- [ ] Verify existing tests pass
- [ ] Add tier enforcement tests

### Documentation
- [ ] Update tool documentation
- [ ] Add release notes entry
```

---

## 8. Common Patterns and Anti-Patterns

### ✅ DO: Progressive Enhancement

```python
# Good: Build on previous tier
if tier in ("pro", "enterprise"):
    result.advanced = self._advanced_analysis()

if tier == "enterprise":
    result.compliance = self._compliance_audit()
```

### ❌ DON'T: Duplicate Code

```python
# Bad: Copy-paste between tiers
if tier == "community":
    result = self._analyze_community()
elif tier == "pro":
    result = self._analyze_pro()  # Duplicates community logic
elif tier == "enterprise":
    result = self._analyze_enterprise()  # Duplicates pro logic
```

### ✅ DO: Graceful Degradation

```python
# Good: Silently ignore unavailable features
if compliance_standards and tier != "enterprise":
    logger.debug("Compliance standards ignored in %s tier", tier)
    compliance_standards = None
```

### ❌ DON'T: Hard Failures

```python
# Bad: Crash on tier mismatch
if compliance_standards and tier != "enterprise":
    raise ValueError("Compliance requires Enterprise tier")
```

### ✅ DO: Tier-Aware Serialization

```python
# Good: Only include tier-relevant fields
def to_dict(self) -> dict:
    result = {"basic": self.basic, "tier": self.tier}
    
    if self.tier in ("pro", "enterprise"):
        result["advanced"] = self.advanced
    
    return result
```

### ❌ DON'T: Leak Higher-Tier Fields

```python
# Bad: All fields visible regardless of tier
def to_dict(self) -> dict:
    return {
        "basic": self.basic,
        "advanced": self.advanced,  # Visible in Community
        "compliance": self.compliance,  # Visible in Community
    }
```

### ✅ DO: Document Tier Requirements

```python
@mcp.tool()
async def your_tool(...) -> Result:
    """
    Tool description.
    
    Tier Capabilities:
        Community: Basic analysis
        Pro: + Custom rules, advanced analysis
        Enterprise: + Compliance, audit trail
    """
```

---

## 9. Reference: Current Tool Inventory

### Tool Tier Availability (21 Tools)

| Tool | Community | Pro | Enterprise | Notes |
|------|-----------|-----|------------|-------|
| `analyze_code` | ✅ | ✅ | ✅ | |
| `extract_code` | ✅ | ✅ | ✅ | |
| `update_symbol` | ✅ | ✅ | ✅ | |
| `get_project_map` | ✅ | ✅ | ✅ | |
| `get_file_context` | ✅ | ✅ | ✅ | |
| `get_symbol_references` | ✅ | ✅ | ✅ | |
| `security_scan` | ✅ | ✅ | ✅ | |
| `unified_sink_detect` | ✅ | ✅ | ✅ | |
| `scan_dependencies` | ✅ | ✅ | ✅ | |
| `validate_paths` | ✅ | ✅ | ✅ | |
| `code_policy_check` | ✅ | ✅ | ✅ | NEW in v1.0.0 |
| `crawl_project` | ❌ | ✅ | ✅ | |
| `get_call_graph` | ❌ | ✅ | ✅ | |
| `get_graph_neighborhood` | ❌ | ✅ | ✅ | |
| `symbolic_execute` | ❌ | ✅ | ✅ | |
| `simulate_refactor` | ❌ | ✅ | ✅ | |
| `generate_unit_tests` | ❌ | ✅ | ✅ | |
| `type_evaporation_scan` | ❌ | ✅ | ✅ | |
| `verify_policy_integrity` | ❌ | ❌ | ✅ | Enterprise-only |
| `cross_file_security_scan` | ❌ | ❌ | ✅ | Enterprise-only |
| `get_cross_file_dependencies` | ❌ | ❌ | ✅ | Enterprise-only |

### limits.toml Quick Reference

```toml
# Standard limit patterns:

# Community: Conservative limits
[community.tool_name]
max_files = 100
max_depth = 3
feature_x = false

# Pro: Generous limits
[pro.tool_name]
max_files = 1000
max_depth = 10
feature_x = true

# Enterprise: Unlimited (omit or set high)
[enterprise.tool_name]
feature_x = true
# Omit max_* for unlimited
```

---

## Appendix A: Quick Start Template

Copy this template to start a new tiered tool:

```bash
# Create module structure
mkdir -p src/code_scalpel/your_module/your_tool
touch src/code_scalpel/your_module/your_tool/__init__.py
touch src/code_scalpel/your_module/your_tool/models.py
touch src/code_scalpel/your_module/your_tool/analyzer.py

# Create test file
touch tests/test_your_tool_tiers.py

# Create roadmap document
touch docs/status/your_tool_tier_roadmap.md
```

---

## Appendix B: Related Documents

- [limits.toml](.code-scalpel/limits.toml) - Tier limits configuration
- [features.py](src/code_scalpel/licensing/features.py) - Capability definitions
- [TIER_CONFIGURATION.md](docs/TIER_CONFIGURATION.md) - Tier system overview
- [release_checklist_template.md](docs/release_notes/release_checklist_template.md) - Release process

---

**Document Version:** 1.0.0  
**Created:** December 26, 2025  
**Author:** Code Scalpel Team
