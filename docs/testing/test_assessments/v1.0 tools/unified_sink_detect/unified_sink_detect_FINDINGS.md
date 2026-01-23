# unified_sink_detect Test Implementation Findings

**Tool**: `unified_sink_detect` (v1.0)  
**Assessment Date**: 2025-01-XX  
**Current Test Count**: 81 tests  
**Target Test Count**: 93 tests (v3.3.0)  
**Implementation Status**: ✅ RELEASE-READY (v3.1.0)

---

## Executive Summary

**unified_sink_detect has the BEST tier enforcement testing of all Code Scalpel MCP tools.**

**Key Strengths**:
- ✅ 60+ comprehensive core tests
- ✅ All 4 languages tested (Python, Java, JavaScript, TypeScript)
- ✅ **EXCELLENT tier limit test** with parametrization and JWT validation
- ✅ OWASP mapping thoroughly validated
- ✅ Confidence scoring tested

**What Makes This Special**:
- Only tool with proper tier limit enforcement test
- Tier test can serve as template for other tools
- Already surpasses security_scan (0 tier tests) and symbolic_execute (1 weak tier test)

**Gaps**:
- License fallback edge cases (invalid/expired)
- Pro feature gating tests (5 needed)
- Enterprise feature gating tests (5 needed, can defer)

**Release Recommendation**: **SHIP v3.1.0** with Pro/Enterprise as "Beta"

---

## Test Implementation Guide

### Phase 1: License Fallback Tests (2 tests, 2 hours)

**Goal**: Validate graceful degradation when license is invalid/expired

#### Test 1: Invalid License Fallback

**File**: `tests/mcp/test_tier_boundary_limits.py`  
**Function**: `test_unified_sink_detect_invalid_license_fallback`  
**Estimated Time**: 1 hour

**Requirements**:
- Generate code with 60 sinks (exceeds Community 50 limit)
- Use invalid JWT token (malformed, wrong signature)
- Verify system falls back to Community tier (50 sink limit)
- Verify warning message about license validation failure

**Test Code Template**:
```python
import pytest
from datetime import datetime, timedelta

async def test_unified_sink_detect_invalid_license_fallback(
    tmp_path, hs256_test_secret
):
    """
    Invalid license should enforce Community 50-sink limit
    
    References:
    - features.py line 1050: Community max_sinks=50
    - Tier test template: test_unified_sink_detect_max_sinks_differs_by_tier
    """
    # Generate code with 60 sinks (exceeds Community limit)
    sink_count = 60
    code_lines = [f"eval(user_input_{i})" for i in range(sink_count)]
    code = "\n".join(code_lines)
    
    # Create invalid license JWT (wrong signature)
    invalid_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature"
    
    # Write license file
    license_file = tmp_path / "license.jwt"
    license_file.write_text(invalid_jwt)
    
    # Override environment
    import os
    original_license = os.environ.get("CODE_SCALPEL_LICENSE")
    os.environ["CODE_SCALPEL_LICENSE"] = str(license_file)
    
    try:
        # Call unified_sink_detect
        from code_scalpel.mcp.server import unified_sink_detect
        
        result = await unified_sink_detect(
            code=code,
            language="python"
        )
        
        # Should enforce Community 50-sink limit
        assert result.sink_count == 50, \
            f"Expected 50 sinks (Community limit), got {result.sink_count}"
        
        assert len(result.sinks) == 50, \
            f"Expected 50 sink objects, got {len(result.sinks)}"
        
        # Should include truncation warning
        assert any("truncated" in str(w).lower() for w in result.warnings), \
            "Expected truncation warning for exceeding Community limit"
        
        # Should mention license validation failure
        assert any("license" in str(w).lower() for w in result.warnings), \
            "Expected warning about license validation failure"
    
    finally:
        # Restore environment
        if original_license:
            os.environ["CODE_SCALPEL_LICENSE"] = original_license
        else:
            os.environ.pop("CODE_SCALPEL_LICENSE", None)
```

**Acceptance Criteria**:
- ✅ Test passes with invalid JWT
- ✅ Enforces Community 50-sink limit
- ✅ Returns warning about license failure
- ✅ Does not crash or raise exception

---

#### Test 2: Expired License Fallback

**File**: `tests/mcp/test_tier_boundary_limits.py`  
**Function**: `test_unified_sink_detect_expired_license_fallback`  
**Estimated Time**: 1 hour

**Requirements**:
- Generate Pro-tier JWT with exp in past
- Generate code with 60 sinks
- Verify fallback to Community 50-sink limit
- Verify warning about expired license

**Test Code Template**:
```python
import pytest
from datetime import datetime, timedelta
import jwt

async def test_unified_sink_detect_expired_license_fallback(
    tmp_path, hs256_test_secret, write_hs256_license_jwt
):
    """
    Expired Pro license should fall back to Community 50-sink limit
    
    References:
    - features.py line 1050: Community max_sinks=50
    - License expiration check in license validation
    """
    # Generate code with 60 sinks
    sink_count = 60
    code_lines = [f"eval(user_input_{i})" for i in range(sink_count)]
    code = "\n".join(code_lines)
    
    # Create expired Pro JWT (exp = 1 day ago)
    expired_time = datetime.utcnow() - timedelta(days=1)
    payload = {
        "tier": "pro",
        "exp": int(expired_time.timestamp()),
        "features": {
            "unified_sink_detect": {
                "max_sinks": None,  # Unlimited for Pro
                "advanced_confidence": True
            }
        }
    }
    
    expired_jwt = jwt.encode(payload, hs256_test_secret, algorithm="HS256")
    
    # Write license file
    license_file = tmp_path / "expired_license.jwt"
    write_hs256_license_jwt(license_file, tier="pro", expires_in=-86400)  # -1 day
    
    # Override environment
    import os
    original_license = os.environ.get("CODE_SCALPEL_LICENSE")
    os.environ["CODE_SCALPEL_LICENSE"] = str(license_file)
    
    try:
        from code_scalpel.mcp.server import unified_sink_detect
        
        result = await unified_sink_detect(
            code=code,
            language="python"
        )
        
        # Should enforce Community limit (license expired)
        assert result.sink_count == 50, \
            f"Expected 50 sinks (expired → Community), got {result.sink_count}"
        
        assert len(result.sinks) == 50
        
        # Should warn about expiration
        warnings_str = " ".join(str(w).lower() for w in result.warnings)
        assert "expired" in warnings_str or "license" in warnings_str, \
            "Expected warning about expired license"
    
    finally:
        if original_license:
            os.environ["CODE_SCALPEL_LICENSE"] = original_license
        else:
            os.environ.pop("CODE_SCALPEL_LICENSE", None)
```

**Acceptance Criteria**:
- ✅ Test passes with expired JWT
- ✅ Falls back to Community 50-sink limit
- ✅ Warning mentions expiration
- ✅ No crashes

---

### Phase 2: Pro Feature Tests (5 tests, 5 hours)

**Goal**: Validate Pro tier advanced capabilities

#### Test 3: Advanced Confidence Scoring

**File**: `tests/mcp/test_mcp_unified_sink_pro.py` (NEW FILE)  
**Function**: `test_advanced_confidence_scoring_pro`  
**Estimated Time**: 1 hour

**Requirements**:
- Pro license with `advanced_confidence_scoring` enabled
- Code with multiple sink types (varying risk levels)
- Verify confidence scores differentiate between contexts
- Community tier should use simpler scoring (all 1.0 or coarse-grained)

**Test Code Template**:
```python
import pytest

async def test_advanced_confidence_scoring_pro(
    tmp_path, hs256_test_secret, write_hs256_license_jwt
):
    """
    Pro tier provides granular confidence scoring
    Community tier uses coarse-grained scoring
    
    References:
    - features.py line 1070: Pro advanced_confidence_scoring capability
    - UNIFIED_SINKS confidence field
    """
    # Code with different risk levels
    code = """
# Direct SQL injection - highest risk
cursor.execute(f"SELECT * FROM users WHERE id={user_id}")

# Parameterized with unknown source - medium risk
query = build_query(user_input)
cursor.execute(query)

# Generic db call - lower confidence
db.query(sql_string)
"""
    
    # Test with Community license (coarse scoring)
    community_license = tmp_path / "community.jwt"
    write_hs256_license_jwt(community_license, tier="community")
    
    import os
    os.environ["CODE_SCALPEL_LICENSE"] = str(community_license)
    
    from code_scalpel.mcp.server import unified_sink_detect
    
    result_community = await unified_sink_detect(
        code=code,
        language="python"
    )
    
    # Community should have coarse-grained confidence (less variation)
    confidences_community = sorted([s.confidence for s in result_community.sinks])
    unique_community = len(set(confidences_community))
    
    # Test with Pro license (fine-grained scoring)
    pro_license = tmp_path / "pro.jwt"
    write_hs256_license_jwt(pro_license, tier="pro")
    os.environ["CODE_SCALPEL_LICENSE"] = str(pro_license)
    
    result_pro = await unified_sink_detect(
        code=code,
        language="python"
    )
    
    # Pro should have fine-grained confidence (more variation)
    confidences_pro = sorted([s.confidence for s in result_pro.sinks])
    unique_pro = len(set(confidences_pro))
    
    # Pro should have more confidence levels
    assert unique_pro >= unique_community, \
        f"Pro should have ≥ confidence levels than Community ({unique_pro} vs {unique_community})"
    
    # Pro should differentiate f-string injection (1.0) from generic call (0.7-0.8)
    assert max(confidences_pro) > min(confidences_pro) + 0.15, \
        "Pro should show >0.15 confidence spread"
```

**Acceptance Criteria**:
- ✅ Pro tier shows more confidence variation than Community
- ✅ Direct injection (f-string) has higher confidence than generic call
- ✅ Confidence spread >0.15 for Pro tier

---

#### Test 4: Context-Aware Detection (Sanitizers)

**File**: `tests/mcp/test_mcp_unified_sink_pro.py`  
**Function**: `test_context_aware_sanitizers_pro`  
**Estimated Time**: 1 hour

**Requirements**:
- Pro license with `context_aware_detection` enabled
- Code with sanitizer functions (e.g., `sanitize_sql`, `escape_html`)
- Verify Pro tier lowers confidence when sanitizer detected
- Community tier ignores context

**Test Code Template**:
```python
async def test_context_aware_sanitizers_pro(
    tmp_path, write_hs256_license_jwt
):
    """
    Pro tier recognizes sanitizers and adjusts confidence
    Community tier treats all sinks equally
    
    References:
    - features.py line 1070: Pro context_aware_detection
    - Sanitizer patterns: sanitize_, escape_, validate_
    """
    code = """
# Sanitized SQL - Pro should lower confidence
safe_query = sanitize_sql(user_input)
cursor.execute(safe_query)

# Direct injection - high confidence
unsafe_query = user_input
cursor.execute(unsafe_query)
"""
    
    # Test with Pro license
    pro_license = tmp_path / "pro.jwt"
    write_hs256_license_jwt(pro_license, tier="pro")
    
    import os
    os.environ["CODE_SCALPEL_LICENSE"] = str(pro_license)
    
    from code_scalpel.mcp.server import unified_sink_detect
    
    result = await unified_sink_detect(
        code=code,
        language="python"
    )
    
    # Should detect both sinks
    assert result.sink_count == 2
    
    sinks = sorted(result.sinks, key=lambda s: s.line)
    sanitized_sink = sinks[0]  # Line with sanitize_sql
    unsafe_sink = sinks[1]     # Line with direct user_input
    
    # Pro should give lower confidence to sanitized sink
    assert sanitized_sink.confidence < unsafe_sink.confidence, \
        f"Sanitized should have lower confidence: {sanitized_sink.confidence} vs {unsafe_sink.confidence}"
    
    # Difference should be meaningful (at least 0.1)
    assert unsafe_sink.confidence - sanitized_sink.confidence >= 0.1, \
        "Confidence difference should be ≥0.1"
```

**Acceptance Criteria**:
- ✅ Detects both sanitized and unsanitized sinks
- ✅ Sanitized sink has lower confidence (≥0.1 difference)
- ✅ Pro tier context-awareness functional

---

#### Test 5: Framework-Specific Sinks

**File**: `tests/mcp/test_mcp_unified_sink_pro.py`  
**Function**: `test_framework_specific_sinks_django`  
**Estimated Time**: 1 hour

**Requirements**:
- Pro license with `framework_specific_sinks` enabled
- Django-specific code (ORM raw queries, extra(), RawSQL)
- Verify Pro detects framework sinks
- Community only detects generic sinks

**Test Code Template**:
```python
async def test_framework_specific_sinks_django(
    tmp_path, write_hs256_license_jwt
):
    """
    Pro tier detects Django-specific sinks
    
    References:
    - features.py line 1070: Pro framework_specific_sinks
    - Django ORM: raw(), extra(), RawSQL()
    """
    code = """
from django.db.models import Q, RawSQL

# Django ORM raw query - framework-specific sink
users = User.objects.raw(f"SELECT * FROM users WHERE name='{name}'")

# Django ORM extra() with WHERE clause - framework-specific
users = User.objects.extra(where=[f"name = '{name}'"])

# Django RawSQL annotation - framework-specific
users = User.objects.annotate(
    custom=RawSQL(f"SELECT COUNT(*) FROM orders WHERE user_id={user_id}", [])
)
"""
    
    # Test with Pro license
    pro_license = tmp_path / "pro.jwt"
    write_hs256_license_jwt(pro_license, tier="pro")
    
    import os
    os.environ["CODE_SCALPEL_LICENSE"] = str(pro_license)
    
    from code_scalpel.mcp.server import unified_sink_detect
    
    result = await unified_sink_detect(
        code=code,
        language="python"
    )
    
    # Should detect Django framework sinks
    assert result.sink_count >= 3, \
        f"Expected ≥3 Django sinks, got {result.sink_count}"
    
    sink_names = [s.name for s in result.sinks]
    
    # Should detect ORM-specific methods
    assert any("raw" in name.lower() for name in sink_names), \
        "Should detect .raw() method"
    
    assert any("extra" in name.lower() or "RawSQL" in name for name in sink_names), \
        "Should detect .extra() or RawSQL"
```

**Acceptance Criteria**:
- ✅ Detects ≥3 Django-specific sinks
- ✅ Identifies `.raw()` method
- ✅ Identifies `.extra()` or `RawSQL`

---

#### Test 6: Custom Sink Definitions

**File**: `tests/mcp/test_mcp_unified_sink_pro.py`  
**Function**: `test_custom_sink_definitions_pro`  
**Estimated Time**: 1 hour

**Requirements**:
- Pro license with `custom_sink_definitions` enabled
- Organization-specific dangerous functions
- Verify custom sinks detected with correct metadata

**Test Code Template**:
```python
async def test_custom_sink_definitions_pro(
    tmp_path, write_hs256_license_jwt
):
    """
    Pro tier allows custom organization-specific sink definitions
    
    References:
    - features.py line 1070: Pro custom_sink_definitions
    - Custom sinks format: {language: {sink_name: {confidence, cwe, category}}}
    """
    code = """
# Organization's internal database wrapper
internal_db.execute_raw_query(user_provided_sql)

# Internal command execution wrapper
internal_shell.run_command(user_command)
"""
    
    # Define custom organization sinks
    custom_sinks = {
        "python": {
            "execute_raw_query": {
                "confidence": 1.0,
                "cwe": "CWE-89",
                "category": "A03:2021",  # SQL Injection
                "description": "Internal raw SQL execution"
            },
            "run_command": {
                "confidence": 1.0,
                "cwe": "CWE-78",
                "category": "A01:2021",  # Command Injection
                "description": "Internal shell command execution"
            }
        }
    }
    
    # Test with Pro license
    pro_license = tmp_path / "pro.jwt"
    write_hs256_license_jwt(pro_license, tier="pro")
    
    import os
    os.environ["CODE_SCALPEL_LICENSE"] = str(pro_license)
    
    from code_scalpel.mcp.server import unified_sink_detect
    
    result = await unified_sink_detect(
        code=code,
        language="python",
        custom_sinks=custom_sinks
    )
    
    # Should detect both custom sinks
    assert result.sink_count == 2, \
        f"Expected 2 custom sinks, got {result.sink_count}"
    
    sink_names = [s.name for s in result.sinks]
    
    assert "execute_raw_query" in sink_names, \
        "Should detect custom execute_raw_query sink"
    
    assert "run_command" in sink_names, \
        "Should detect custom run_command sink"
    
    # Verify CWE mapping
    cwes = [s.cwe for s in result.sinks]
    assert "CWE-89" in cwes, "Should map to CWE-89"
    assert "CWE-78" in cwes, "Should map to CWE-78"
```

**Acceptance Criteria**:
- ✅ Detects custom organization sinks
- ✅ Maps to correct CWE identifiers
- ✅ Custom confidence/category applied

---

#### Test 7: Sink Coverage Analysis

**File**: `tests/mcp/test_mcp_unified_sink_pro.py`  
**Function**: `test_sink_coverage_analysis_pro`  
**Estimated Time**: 1 hour

**Requirements**:
- Pro license with `sink_coverage_analysis` enabled
- Code with multiple vulnerability types
- Verify coverage report includes all OWASP categories

**Test Code Template**:
```python
async def test_sink_coverage_analysis_pro(
    tmp_path, write_hs256_license_jwt
):
    """
    Pro tier provides comprehensive sink coverage analysis
    
    References:
    - features.py line 1070: Pro sink_coverage_analysis
    - Coverage: total_patterns, by_language, by_category
    """
    code = """
# SQL Injection - A03:2021
cursor.execute(f"SELECT * FROM users WHERE id={user_id}")

# XSS - A03:2021 (Injection)
innerHTML = user_data

# Command Injection - A03:2021
os.system(f"ping {host}")

# Path Traversal - A01:2021 (Broken Access Control)
open(user_filename, 'r')
"""
    
    # Test with Pro license
    pro_license = tmp_path / "pro.jwt"
    write_hs256_license_jwt(pro_license, tier="pro")
    
    import os
    os.environ["CODE_SCALPEL_LICENSE"] = str(pro_license)
    
    from code_scalpel.mcp.server import unified_sink_detect
    
    result = await unified_sink_detect(
        code=code,
        language="python"
    )
    
    # Should provide coverage report
    assert hasattr(result, "coverage"), "Pro should provide coverage report"
    
    coverage = result.coverage
    
    # Should have total pattern count
    assert coverage.total_patterns > 0, "Should count total sink patterns"
    
    # Should categorize by OWASP Top 10
    assert hasattr(coverage, "by_category"), "Should provide by_category breakdown"
    
    categories = coverage.by_category
    assert "A03:2021" in categories, "Should detect injection sinks (A03:2021)"
    assert "A01:2021" in categories, "Should detect access control issues (A01:2021)"
    
    # Should report by language
    assert hasattr(coverage, "by_language"), "Should provide by_language breakdown"
    assert "python" in coverage.by_language, "Should report Python coverage"
```

**Acceptance Criteria**:
- ✅ Provides `coverage` field in result
- ✅ Reports `total_patterns` count
- ✅ Breaks down by OWASP category
- ✅ Breaks down by language

---

### Phase 3: Enterprise Features (5 tests, 5 hours)

**Deferred to v3.3.0** - Smaller customer base, lower priority

#### Test 8: Organization-Specific Rules (1 hour)
- Custom rule sets per organization
- Rule inheritance and overrides
- Rule versioning

#### Test 9: Sink Risk Scoring (1 hour)
- Business impact weighting
- Contextual risk factors
- Risk score calculation

#### Test 10: Compliance Mapping (1 hour)
- OWASP Top 10 2021 mapping
- CWE classification
- PCI-DSS requirements
- HIPAA compliance

#### Test 11: Historical Tracking (1 hour)
- Sink trend analysis over time
- Regression detection
- Improvement metrics

#### Test 12: Automated Remediation (1 hour)
- Fix suggestions
- Code patch generation
- Validation of fixes

---

## Template: Using Existing Tier Test as Reference

**Best-in-class example**: `test_unified_sink_detect_max_sinks_differs_by_tier`

**Location**: `tests/mcp/test_tier_boundary_limits.py` lines 350-420

**Why it's excellent**:
```python
@pytest.mark.parametrize("requested_sinks", [60, 120])
async def test_unified_sink_detect_max_sinks_differs_by_tier(
    tmp_path, requested_sinks, hs256_test_secret, write_hs256_license_jwt
):
    # ✅ Parametrized for multiple scenarios
    # ✅ Tests Community limit (50)
    # ✅ Tests Pro unlimited
    # ✅ Uses real JWT generation
    # ✅ Clear assertions with context
    # ✅ Proper cleanup (license file management)
    
    code = "\n".join(["eval(user_input)"] * requested_sinks)
    
    # Community test
    community_license = tmp_path / "community.jwt"
    write_hs256_license_jwt(community_license, tier="community")
    
    result = await unified_sink_detect(code=code, language="python")
    
    assert result.sink_count == 50
    assert len(result.sinks) == 50
    
    # Pro test
    pro_license = tmp_path / "pro.jwt"
    write_hs256_license_jwt(pro_license, tier="pro")
    
    result_pro = await unified_sink_detect(code=code, language="python")
    
    assert result_pro.sink_count == requested_sinks
    assert len(result_pro.sinks) == requested_sinks
```

**Reusable patterns**:
- `write_hs256_license_jwt(file, tier=...)` for license generation
- `@pytest.mark.parametrize` for multiple scenarios
- Clear Community vs Pro comparisons
- License file cleanup via `tmp_path`

---

## Implementation Checklist

### Phase 1: License Fallback (v3.2.0)
- [ ] Test 1: Invalid license fallback (1 hour)
- [ ] Test 2: Expired license fallback (1 hour)
- [ ] Run tests: `pytest tests/mcp/test_tier_boundary_limits.py -k "unified_sink" -v`
- [ ] Verify coverage: `pytest --cov=code_scalpel.mcp.server --cov-report=term-missing`

### Phase 2: Pro Features (v3.2.0)
- [ ] Create `tests/mcp/test_mcp_unified_sink_pro.py`
- [ ] Test 3: Advanced confidence scoring (1 hour)
- [ ] Test 4: Context-aware sanitizers (1 hour)
- [ ] Test 5: Framework-specific sinks (1 hour)
- [ ] Test 6: Custom sink definitions (1 hour)
- [ ] Test 7: Sink coverage analysis (1 hour)
- [ ] Run Pro tests: `pytest tests/mcp/test_mcp_unified_sink_pro.py -v`

### Phase 3: Enterprise Features (v3.3.0+)
- [ ] Create `tests/mcp/test_mcp_unified_sink_enterprise.py`
- [ ] Test 8: Organization rules (1 hour)
- [ ] Test 9: Risk scoring (1 hour)
- [ ] Test 10: Compliance mapping (1 hour)
- [ ] Test 11: Historical tracking (1 hour)
- [ ] Test 12: Automated remediation (1 hour)

### Quality Gates
- [ ] All tests pass
- [ ] Coverage ≥90% combined (statement + branch)
- [ ] No regressions in existing 81 tests
- [ ] Tier enforcement validated for all new features
- [ ] Documentation updated (release notes, tier matrix)

---

## Success Metrics

**v3.2.0 Target** (Phase 1+2):
- Total tests: 88 (81 current + 7 new)
- License fallback: 100% validated
- Pro features: 100% validated
- Time investment: 12 hours

**v3.3.0 Target** (Phase 3):
- Total tests: 93 (88 + 5 Enterprise)
- Enterprise features: 100% validated
- Time investment: +5 hours

**Quality Metrics**:
- Test pass rate: 100%
- Coverage: ≥90% combined
- Tier test quality: Gold standard (template for other tools)
- Documentation: Complete tier matrix in release notes

---

## Notes for Developers

**Reuse existing patterns**:
- License generation: `write_hs256_license_jwt(file, tier, expires_in=3600)`
- Environment management: Use fixtures, restore in `finally` block
- Parametrization: Test multiple tiers/scenarios with `@pytest.mark.parametrize`

**Avoid common pitfalls**:
- Don't forget to restore `CODE_SCALPEL_LICENSE` env var
- Use `tmp_path` for license files (auto-cleanup)
- Test both positive (feature works) and negative (fallback) cases

**Best practices**:
- Follow existing tier test structure (test_tier_boundary_limits.py)
- Use descriptive assertion messages with context
- Include docstring with feature reference (features.py line number)
- Add `# [YYYYMMDD_FEATURE]` tag to new tests

**Questions?** See:
- Existing tier test: `tests/mcp/test_tier_boundary_limits.py` line 350
- Features config: `src/code_scalpel/features.py` line 1043
- License utils: `tests/fixtures/license_helpers.py`
