# Compliance Reporting

**Version:** v2.5.0 Guardian  
**Status:** Complete  
**Priority:** P1

## Overview

The Compliance Reporting feature provides enterprise-grade audit reports for governance, security reviews, and regulatory compliance. This feature generates comprehensive reports analyzing agent operations, policy violations, overrides, and security posture.

## Features

### Report Generation

Generate compliance reports in three formats:
- **JSON** - Machine-readable format for API integration
- **HTML** - Browser-viewable with charts and tables
- **PDF** - Executive-ready format with professional layout

### Report Contents

Each compliance report includes:

1. **Executive Summary**
   - Total operations count
   - Allowed vs blocked operations
   - Override statistics
   - Tamper attempt detection
   - Most violated policies ranking

2. **Policy Violation Analysis**
   - Total violations count
   - Breakdown by severity (CRITICAL, HIGH, MEDIUM, LOW)
   - Breakdown by policy name
   - Breakdown by operation type
   - Critical violations list

3. **Override Analysis**
   - Override requests and approvals
   - Approval rate calculation
   - Analysis by policy
   - Analysis by reason

4. **Security Posture Assessment**
   - Security score (0-100)
   - Letter grade (A-F)
   - Risk level (LOW, MEDIUM, HIGH, CRITICAL)
   - Identified strengths
   - Identified weaknesses

5. **Actionable Recommendations**
   - Priority-ranked suggestions
   - Category classification
   - Detailed descriptions
   - Recommended actions

## Architecture

### Components

```
governance/
├── __init__.py                    # Module exports
├── audit_log.py                   # Audit log interface (stub)
├── policy_engine.py               # Policy engine interface (stub)
└── compliance_reporter.py         # Main compliance reporter
```

### Data Models

- **ComplianceReport** - Complete report with all sections
- **ReportSummary** - Executive summary statistics
- **ViolationAnalysis** - Detailed policy violation breakdown
- **OverrideAnalysis** - Override request and approval analysis
- **SecurityPosture** - Overall security assessment
- **Recommendation** - Actionable recommendation

### Dependencies

The ComplianceReporter depends on:
- **AuditLog** - Event storage and retrieval (stub implementation)
- **PolicyEngine** - Policy definition and evaluation (stub implementation)

## Usage

### Basic Example

```python
from datetime import datetime, timedelta
from code_scalpel.governance import (
    ComplianceReporter,
    AuditLog,
    PolicyEngine,
)

# Create audit log and policy engine
audit_log = AuditLog()
policy_engine = PolicyEngine()

# Log some events
audit_log.log_event(
    "OPERATION_ALLOWED",
    {"operation": "code_analysis", "file": "main.py"},
)
audit_log.log_event(
    "POLICY_VIOLATION",
    {
        "policy_name": "security_policy",
        "severity": "HIGH",
        "operation_type": "file_edit",
    },
)

# Create reporter
reporter = ComplianceReporter(audit_log, policy_engine)

# Generate report for last 7 days
time_range = (
    datetime.now() - timedelta(days=7),
    datetime.now(),
)

# JSON format
json_report = reporter.generate_report(time_range, format="json")

# HTML format
html_report = reporter.generate_report(time_range, format="html")

# PDF format
pdf_report = reporter.generate_report(time_range, format="pdf")

# Get report object for programmatic access
report = reporter.generate_report(time_range, format="object")
print(f"Security Score: {report.security_posture.score}/100")
print(f"Grade: {report.security_posture.grade}")
```

### Running the Demo

```bash
python examples/compliance_reporting_demo.py
```

This generates sample reports demonstrating all features:
- Creates 75 sample audit events
- Generates reports in all 3 formats
- Displays summary statistics

## Report Formats

### JSON Format

Machine-readable JSON with complete report data:

```json
{
  "generated_at": "2025-12-16T20:29:48.607732",
  "time_range": {
    "start": "2025-12-09T20:29:48.607706",
    "end": "2025-12-16T20:29:48.607706"
  },
  "summary": {
    "total_operations": 50,
    "blocked_operations": 15,
    "allowed_operations": 50,
    "overrides_requested": 5,
    "overrides_approved": 2,
    "tamper_attempts": 3,
    "most_violated_policies": [
      ["security_policy", 5],
      ["quality_policy", 5],
      ["style_policy", 5]
    ]
  },
  "security_posture": {
    "score": 58,
    "grade": "F",
    "risk_level": "HIGH",
    "strengths": [...],
    "weaknesses": [...]
  },
  ...
}
```

### HTML Format

Responsive HTML with:
- Professional styling
- Color-coded severity levels
- Data tables
- Metric cards
- Gradient score displays
- Priority badges

Open in browser for interactive viewing.

### PDF Format

Professional PDF layout with:
- Executive summary tables
- Policy violation breakdown
- Severity analysis tables
- Most violated policies ranking
- Recommendations with priority levels
- Page breaks for readability

## Event Types

The following event types are recognized:

### Operation Events
- `OPERATION_ALLOWED` - Successful operation
- `OPERATION_*` - Any operation (prefix match)

### Policy Events
- `POLICY_VIOLATION` - Policy rule violation
- `OVERRIDE_REQUESTED` - Override request submitted
- `OVERRIDE_APPROVED` - Override request approved
- `OVERRIDE_DENIED` - Override request denied

### Security Events
- `TAMPER_ATTEMPT_DETECTED` - Tamper detection event
- `TAMPER_*` - Any tamper event (substring match)

## Security Scoring

The security score (0-100) is calculated based on:

1. **Block Rate** (50% weight)
   - Percentage of operations blocked by policies
   - Higher block rate = better security

2. **Override Rate** (50% weight)
   - Percentage of blocked operations that were overridden
   - Lower override rate = better security

Score-to-Grade mapping:
- 90-100: A (Excellent)
- 80-89: B (Good)
- 70-79: C (Acceptable)
- 60-69: D (Needs Improvement)
- 0-59: F (Poor)

Risk-Level mapping:
- 80+: LOW
- 60-79: MEDIUM
- 40-59: HIGH
- 0-39: CRITICAL

## Recommendations

The system automatically generates recommendations based on patterns:

### High Override Rate (>30%)
- **Priority:** MEDIUM
- **Category:** Policy Adjustment
- **Trigger:** Override approval rate exceeds 30% of violations
- **Action:** Review policies for unnecessary restrictions

### Frequently Violated Policy (>10 violations)
- **Priority:** HIGH
- **Category:** Policy Tuning
- **Trigger:** Single policy violated more than 10 times
- **Action:** Review policy definition and agent training

## Testing

Comprehensive test suite with 31 tests:

```bash
# Run all compliance reporter tests
pytest tests/test_compliance_reporter.py -v

# Run with coverage
pytest tests/test_compliance_reporter.py --cov=src/code_scalpel/governance
```

### Test Coverage

- **Overall Coverage:** 97%
- **AuditLog:** 100%
- **PolicyEngine:** 100%
- **ComplianceReporter:** 97%

### Test Categories

1. **AuditLog Tests** (4 tests)
   - Initialization
   - Event logging
   - Time range filtering
   - Event clearing

2. **PolicyEngine Tests** (3 tests)
   - Initialization
   - Policy loading
   - Operation evaluation

3. **ComplianceReporter Tests** (19 tests)
   - Report generation
   - Summary statistics
   - Violation analysis
   - Override analysis
   - Security scoring
   - Recommendation generation
   - Format exports (JSON, HTML, PDF)
   - Edge cases (empty log, high override rates, etc.)

4. **Data Model Tests** (5 tests)
   - All dataclass creation and validation

## Integration

### Future Integration Points

The stub implementations (AuditLog and PolicyEngine) provide interfaces for future integration:

1. **AuditLog Integration**
   - Connect to persistent storage (database, log files)
   - Add event streaming support
   - Implement event retention policies

2. **PolicyEngine Integration**
   - Integrate with OPA/Rego
   - Add policy validation
   - Implement semantic blocking rules

3. **MCP Server Integration**
   - Expose compliance reporting via MCP tools
   - Add real-time compliance monitoring
   - Integrate with existing security scanning

## Performance

Report generation performance (sample data with 75 events):

- **JSON Export:** < 50ms
- **HTML Export:** < 100ms
- **PDF Export:** < 500ms (includes reportlab rendering)

Memory usage: Proportional to number of events in time range.

## Dependencies

### Required
- Python 3.9+
- Standard library (json, datetime, collections, dataclasses)

### Optional
- `reportlab>=4.0.0` - For PDF generation (auto-fallback if not installed)

Install with:
```bash
pip install reportlab
```

## Known Limitations

1. **In-Memory Storage**
   - AuditLog stub stores events in memory only
   - Events are lost when process terminates
   - Full implementation will use persistent storage

2. **Policy Engine Stub**
   - PolicyEngine stub always allows operations
   - Full implementation will enforce real policies
   - Policy evaluation logic not yet implemented

3. **Report Caching**
   - Reports are generated on-demand
   - No caching mechanism for repeated queries
   - Future versions may add caching

## Future Enhancements

Planned for future versions:

1. **Enhanced Analytics**
   - Trend analysis over time
   - Comparative reports (month-over-month)
   - Predictive risk modeling

2. **Customization**
   - Custom report templates
   - Configurable metrics
   - Brand customization (logos, colors)

3. **Export Options**
   - Excel/CSV export
   - Markdown export
   - Email delivery

4. **Real-Time Monitoring**
   - Live compliance dashboard
   - Alerting on critical violations
   - Automated report scheduling

## Troubleshooting

### PDF Generation Fails

**Symptom:** PDF returns error message about missing reportlab

**Solution:**
```bash
pip install reportlab
```

### Empty Reports

**Symptom:** All metrics show zero

**Causes:**
1. No events logged to AuditLog
2. Time range doesn't match event timestamps
3. Events filtered out by time range

**Solution:**
- Verify events are logged: `audit_log.get_events()`
- Check event timestamps match time range
- Expand time range to include more events

### JSON Serialization Errors

**Symptom:** TypeError about datetime not being serializable

**Solution:**
This is handled automatically by the `_render_json()` method. If you're using custom serialization, ensure datetime objects are converted to ISO format strings.

## See Also

- [v2.5.0 Guardian Roadmap](../DEVELOPMENT_ROADMAP.md#v250---guardian-governance--policy)
- [Policy Engine Documentation](policy_engine.md) (future)
- [Audit Log Documentation](audit_log.md) (future)
- [Security Analysis](security_analysis.md)

## Credits

**Feature:** Compliance Reporting  
**Version:** v2.5.0 Guardian  
**Tag:** [20251216_FEATURE]  
**Status:** Complete (P1)
