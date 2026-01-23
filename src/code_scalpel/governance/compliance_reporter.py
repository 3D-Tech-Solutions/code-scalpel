"""
Compliance Reporting for Enterprise Governance and Audits.

This module generates comprehensive compliance reports for enterprise
governance, security reviews, and regulatory audits.
"""

# [20251216_FEATURE] v2.5.0 Compliance reporting implementation

import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from code_scalpel.policy_engine import PolicyEngine

# [20251221_REFACTOR] v3.1.0 - Use policy_engine's full audit_log implementation
from code_scalpel.policy_engine.audit_log import AuditLog


@dataclass
class Recommendation:
    """Actionable recommendation for improving security posture."""

    priority: str  # "HIGH", "MEDIUM", "LOW"
    category: str  # e.g., "Policy Tuning", "Policy Adjustment"
    title: str
    description: str
    action: str


@dataclass
class SecurityPosture:
    """Overall security posture assessment."""

    score: int  # 0-100
    grade: str  # A-F
    strengths: list[str]
    weaknesses: list[str]
    risk_level: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"


@dataclass
class OverrideAnalysis:
    """Analysis of policy override requests and approvals."""

    total_requested: int
    total_approved: int
    total_denied: int
    approval_rate: float
    by_policy: dict[str, int]
    by_reason: dict[str, int]


@dataclass
class ViolationAnalysis:
    """Detailed analysis of policy violations."""

    total: int
    by_severity: dict[str, list[dict[str, Any]]]
    by_policy: dict[str, list[dict[str, Any]]]
    by_operation_type: dict[str, list[dict[str, Any]]]
    critical_violations: list[dict[str, Any]]


@dataclass
class ReportSummary:
    """Executive summary statistics for compliance report."""

    total_operations: int
    blocked_operations: int
    allowed_operations: int
    overrides_requested: int
    overrides_approved: int
    tamper_attempts: int
    most_violated_policies: list[tuple[str, int]]


@dataclass
class ComplianceReport:
    """Complete compliance report with all analysis sections."""

    generated_at: datetime
    time_range: tuple[datetime, datetime]
    summary: ReportSummary
    policy_violations: ViolationAnalysis
    override_analysis: OverrideAnalysis
    security_posture: SecurityPosture
    recommendations: list[Recommendation]


class ComplianceReporter:
    """Generate compliance reports for governance audits."""

    def __init__(self, audit_log: AuditLog, policy_engine: PolicyEngine):
        """
        Initialize compliance reporter.

        Args:
            audit_log: Audit log containing event history
            policy_engine: Policy engine for validation
        """
        # [20251222_BUGFIX] Keep compatibility with older tests/code paths that
        # expect private attributes, while retaining the public ones.
        self.audit_log = audit_log
        self.policy_engine = policy_engine
        self._audit_log = audit_log
        self._policy_engine = policy_engine

    def _coerce_event_timestamp(self, value: Any) -> datetime:
        """Normalize event timestamps to datetime.

        [20251222_BUGFIX] AuditLog persists timestamps as ISO strings; report
        filtering needs datetimes.
        """
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return datetime.min
        return datetime.min

    def generate_report(
        self,
        time_range: tuple[datetime, datetime],
        format: str = "json",
    ) -> ComplianceReport | str | bytes:
        """
        Generate compliance report for specified time range.

        Args:
            time_range: (start, end) datetime tuple
            format: "pdf", "json", or "html"

        Returns:
            ComplianceReport object, JSON string, HTML string, or PDF bytes
        """
        events = self._load_events(time_range)

        report = ComplianceReport(
            generated_at=datetime.now(),
            time_range=time_range,
            summary=self._generate_summary(events),
            policy_violations=self._analyze_violations(events),
            override_analysis=self._analyze_overrides(events),
            security_posture=self._assess_security_posture(events),
            recommendations=self._generate_recommendations(events),
        )

        if format == "pdf":
            return self._render_pdf(report)
        elif format == "json":
            return self._render_json(report)
        elif format == "html":
            return self._render_html(report)
        else:
            return report

    def _load_events(self, time_range: tuple[datetime, datetime]) -> list[dict[str, Any]]:
        """
        Load events from audit log for the specified time range.

        Args:
            time_range: (start, end) datetime tuple

        Returns:
            List of event dictionaries
        """
        events = self.audit_log.get_events()

        # Filter events within the time range
        start, end = time_range
        filtered: list[dict[str, Any]] = []
        for event in events:
            ts = self._coerce_event_timestamp(event.get("timestamp"))
            if start <= ts <= end:
                # Preserve normalized timestamp for downstream consumers.
                event = dict(event)
                event["timestamp"] = ts
                filtered.append(event)
        return filtered

    def _generate_summary(self, events: list[dict[str, Any]]) -> ReportSummary:
        """
        Generate executive summary statistics.

        Args:
            events: List of audit log events

        Returns:
            ReportSummary with key statistics
        """
        return ReportSummary(
            total_operations=len([e for e in events if e["event_type"].startswith("OPERATION_")]),
            blocked_operations=len([e for e in events if e["event_type"] == "POLICY_VIOLATION"]),
            allowed_operations=len([e for e in events if e["event_type"] == "OPERATION_ALLOWED"]),
            overrides_requested=len([e for e in events if e["event_type"] == "OVERRIDE_REQUESTED"]),
            overrides_approved=len([e for e in events if e["event_type"] == "OVERRIDE_APPROVED"]),
            tamper_attempts=len([e for e in events if "TAMPER" in e["event_type"]]),
            most_violated_policies=self._rank_violated_policies(events),
        )

    def _rank_violated_policies(self, events: list[dict[str, Any]]) -> list[tuple[str, int]]:
        """
        Rank policies by number of violations.

        Args:
            events: List of audit log events

        Returns:
            List of (policy_name, violation_count) tuples, sorted descending
        """
        violations = [e for e in events if e["event_type"] == "POLICY_VIOLATION"]
        policy_counts: dict[str, int] = defaultdict(int)

        for violation in violations:
            policy = violation["details"].get("policy_name", "unknown")
            policy_counts[policy] += 1

        return sorted(policy_counts.items(), key=lambda x: x[1], reverse=True)

    def _analyze_violations(self, events: list[dict[str, Any]]) -> ViolationAnalysis:
        """
        Analyze policy violations in detail.

        Args:
            events: List of audit log events

        Returns:
            ViolationAnalysis with detailed breakdown
        """
        violations = [e for e in events if e["event_type"] == "POLICY_VIOLATION"]

        by_severity: dict[str, list[dict[str, Any]]] = defaultdict(list)
        by_policy: dict[str, list[dict[str, Any]]] = defaultdict(list)
        by_operation_type: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for violation in violations:
            # [20251222_BUGFIX] Some call sites store severity inside details,
            # while AuditLog persists severity at the event level.
            details = violation.get("details", {})
            severity = details.get("severity") or violation.get("severity") or "UNKNOWN"
            policy = violation["details"].get("policy_name", "unknown")
            operation = violation["details"].get("operation_type", "unknown")

            by_severity[severity].append(violation)
            by_policy[policy].append(violation)
            by_operation_type[operation].append(violation)

        return ViolationAnalysis(
            total=len(violations),
            by_severity=dict(by_severity),
            by_policy=dict(by_policy),
            by_operation_type=dict(by_operation_type),
            critical_violations=by_severity.get("CRITICAL", []),
        )

    def _analyze_overrides(self, events: list[dict[str, Any]]) -> OverrideAnalysis:
        """
        Analyze policy override requests and approvals.

        Args:
            events: List of audit log events

        Returns:
            OverrideAnalysis with override statistics
        """
        requested = [e for e in events if e["event_type"] == "OVERRIDE_REQUESTED"]
        approved = [e for e in events if e["event_type"] == "OVERRIDE_APPROVED"]
        denied = [e for e in events if e["event_type"] == "OVERRIDE_DENIED"]

        by_policy: dict[str, int] = defaultdict(int)
        by_reason: dict[str, int] = defaultdict(int)

        for override in requested:
            policy = override["details"].get("policy_name", "unknown")
            reason = override["details"].get("reason", "unspecified")
            by_policy[policy] += 1
            by_reason[reason] += 1

        total_requested = len(requested)
        total_approved = len(approved)
        approval_rate = total_approved / total_requested if total_requested > 0 else 0.0

        return OverrideAnalysis(
            total_requested=total_requested,
            total_approved=total_approved,
            total_denied=len(denied),
            approval_rate=approval_rate,
            by_policy=dict(by_policy),
            by_reason=dict(by_reason),
        )

    def _assess_security_posture(self, events: list[dict[str, Any]]) -> SecurityPosture:
        """
        Assess overall security posture.

        Args:
            events: List of audit log events

        Returns:
            SecurityPosture with score, grade, and assessment
        """
        violations = [e for e in events if e["event_type"] == "POLICY_VIOLATION"]
        overrides = [e for e in events if e["event_type"] == "OVERRIDE_APPROVED"]

        # Calculate security score (0-100)
        total_ops = len([e for e in events if e["event_type"].startswith("OPERATION_")])
        blocked_ops = len(violations)

        if total_ops == 0:
            security_score = 100
        else:
            # Score based on block rate and override frequency
            block_rate = blocked_ops / total_ops
            override_rate = len(overrides) / max(blocked_ops, 1)

            # High block rate = good, high override rate = concerning
            security_score = int((block_rate * 50) + ((1 - override_rate) * 50))

        return SecurityPosture(
            score=security_score,
            grade=self._score_to_grade(security_score),
            strengths=self._identify_strengths(events),
            weaknesses=self._identify_weaknesses(events),
            risk_level=self._assess_risk_level(security_score),
        )

    def _score_to_grade(self, score: int) -> str:
        """
        Convert security score to letter grade.

        Args:
            score: Security score (0-100)

        Returns:
            Letter grade (A-F)
        """
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"

    def _assess_risk_level(self, score: int) -> str:
        """
        Assess risk level based on security score.

        Args:
            score: Security score (0-100)

        Returns:
            Risk level string
        """
        if score >= 80:
            return "LOW"
        elif score >= 60:
            return "MEDIUM"
        elif score >= 40:
            return "HIGH"
        else:
            return "CRITICAL"

    def _identify_strengths(self, events: list[dict[str, Any]]) -> list[str]:
        """
        Identify security strengths from event patterns.

        Args:
            events: List of audit log events

        Returns:
            List of strength descriptions
        """
        strengths = []

        violations = [e for e in events if e["event_type"] == "POLICY_VIOLATION"]
        if violations:
            strengths.append("Active policy enforcement blocking violations")

        tamper_attempts = [e for e in events if "TAMPER" in e["event_type"]]
        if tamper_attempts:
            strengths.append("Tamper detection system operational")

        operations = [e for e in events if e["event_type"].startswith("OPERATION_")]
        if operations:
            strengths.append("Comprehensive audit trail of operations")

        return strengths if strengths else ["No significant strengths identified"]

    def _identify_weaknesses(self, events: list[dict[str, Any]]) -> list[str]:
        """
        Identify security weaknesses from event patterns.

        Args:
            events: List of audit log events

        Returns:
            List of weakness descriptions
        """
        weaknesses = []

        overrides = [e for e in events if e["event_type"] == "OVERRIDE_APPROVED"]
        violations = [e for e in events if e["event_type"] == "POLICY_VIOLATION"]

        if overrides and violations:
            override_rate = len(overrides) / len(violations)
            if override_rate > 0.3:
                weaknesses.append(f"High override rate ({override_rate:.1%}) suggests policies may be too restrictive")

        critical_violations = [e for e in violations if e["details"].get("severity") == "CRITICAL"]
        if critical_violations:
            weaknesses.append(f"{len(critical_violations)} critical violations detected")

        return weaknesses if weaknesses else ["No significant weaknesses identified"]

    def _generate_recommendations(self, events: list[dict[str, Any]]) -> list[Recommendation]:
        """
        Generate actionable recommendations.

        Args:
            events: List of audit log events

        Returns:
            List of Recommendation objects
        """
        recommendations = []

        violations = [e for e in events if e["event_type"] == "POLICY_VIOLATION"]
        overrides = [e for e in events if e["event_type"] == "OVERRIDE_APPROVED"]

        # Frequent violations suggest policy needs tuning
        policy_counts: dict[str, int] = defaultdict(int)
        for v in violations:
            policy = v["details"].get("policy_name")
            if policy:
                policy_counts[policy] += 1

        for policy, count in policy_counts.items():
            if count > 10:  # Threshold for "frequent"
                recommendations.append(
                    Recommendation(
                        priority="HIGH",
                        category="Policy Tuning",
                        title=f"Review frequently violated policy: {policy}",
                        description=f"Policy '{policy}' was violated {count} times. Consider if this policy is too strict or if agent behavior needs adjustment.",
                        action="Review policy definition and agent training",
                    )
                )

        # High override rate suggests policies are too restrictive
        if violations and len(overrides) > len(violations) * 0.3:  # >30% override rate
            recommendations.append(
                Recommendation(
                    priority="MEDIUM",
                    category="Policy Adjustment",
                    title="High override rate detected",
                    description=f"{len(overrides)} overrides for {len(violations)} violations. Policies may be too restrictive.",
                    action="Review policies for unnecessary restrictions",
                )
            )

        return recommendations

    def _render_json(self, report: ComplianceReport) -> str:
        """
        Render report as JSON.

        Args:
            report: ComplianceReport object

        Returns:
            JSON string representation
        """

        def serialize_datetime(obj: Any) -> Any:
            """Recursively serialize datetime objects to ISO format strings."""
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: serialize_datetime(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [serialize_datetime(item) for item in obj]
            return obj

        data = {
            "generated_at": report.generated_at.isoformat(),
            "time_range": {
                "start": report.time_range[0].isoformat(),
                "end": report.time_range[1].isoformat(),
            },
            "summary": asdict(report.summary),
            "violations": asdict(report.policy_violations),
            "overrides": asdict(report.override_analysis),
            "security_posture": asdict(report.security_posture),
            "recommendations": [asdict(r) for r in report.recommendations],
        }

        # Serialize all nested datetime objects
        serialized_data = serialize_datetime(data)

        return json.dumps(serialized_data, indent=2)

    def _render_html(self, report: ComplianceReport) -> str:
        """
        Render report as HTML.

        Args:
            report: ComplianceReport object

        Returns:
            HTML string representation
        """
        # [20251216_FEATURE] HTML report rendering with charts and tables
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Compliance Report - {report.generated_at.strftime('%Y-%m-%d')}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 40px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 8px;
        }}
        h3 {{
            color: #7f8c8d;
        }}
        .meta-info {{
            background-color: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        .score-card {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin: 20px 0;
            text-align: center;
            min-width: 200px;
        }}
        .score-value {{
            font-size: 48px;
            font-weight: bold;
        }}
        .grade {{
            font-size: 36px;
            margin-left: 20px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .metric-card {{
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 5px;
            border-left: 4px solid #3498db;
        }}
        .metric-value {{
            font-size: 32px;
            font-weight: bold;
            color: #2c3e50;
        }}
        .metric-label {{
            color: #7f8c8d;
            margin-top: 5px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #3498db;
            color: white;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .recommendation {{
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 10px 0;
            border-radius: 3px;
        }}
        .priority-HIGH {{
            border-left-color: #dc3545;
        }}
        .priority-MEDIUM {{
            border-left-color: #ffc107;
        }}
        .priority-LOW {{
            border-left-color: #28a745;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: bold;
        }}
        .badge-critical {{
            background-color: #dc3545;
            color: white;
        }}
        .badge-high {{
            background-color: #fd7e14;
            color: white;
        }}
        .badge-medium {{
            background-color: #ffc107;
            color: black;
        }}
        .badge-low {{
            background-color: #28a745;
            color: white;
        }}
        .risk-CRITICAL {{ color: #dc3545; font-weight: bold; }}
        .risk-HIGH {{ color: #fd7e14; font-weight: bold; }}
        .risk-MEDIUM {{ color: #ffc107; font-weight: bold; }}
        .risk-LOW {{ color: #28a745; font-weight: bold; }}
        ul {{
            list-style-type: none;
            padding-left: 0;
        }}
        li {{
            padding: 8px 0;
            border-bottom: 1px solid #ecf0f1;
        }}
        li:before {{
            content: "✓ ";
            color: #27ae60;
            font-weight: bold;
            margin-right: 8px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Compliance Report</h1>

        <div class="meta-info">
            <strong>Generated:</strong> {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}<br>
            <strong>Period:</strong> {report.time_range[0].strftime('%Y-%m-%d')} to {report.time_range[1].strftime('%Y-%m-%d')}
        </div>

        <h2>Security Posture</h2>
        <div class="score-card">
            <div>
                <span class="score-value">{report.security_posture.score}</span>
                <span class="grade">{report.security_posture.grade}</span>
            </div>
            <div style="margin-top: 10px;">
                Risk Level: <span class="risk-{report.security_posture.risk_level}">{report.security_posture.risk_level}</span>
            </div>
        </div>

        <h2>Executive Summary</h2>
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value">{report.summary.total_operations}</div>
                <div class="metric-label">Total Operations</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{report.summary.allowed_operations}</div>
                <div class="metric-label">Allowed Operations</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{report.summary.blocked_operations}</div>
                <div class="metric-label">Blocked Operations</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{report.summary.overrides_approved}</div>
                <div class="metric-label">Overrides Approved</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{report.summary.tamper_attempts}</div>
                <div class="metric-label">Tamper Attempts</div>
            </div>
        </div>

        <h2>Policy Violations</h2>
        <p><strong>Total Violations:</strong> {report.policy_violations.total}</p>

        <h3>By Severity</h3>
        <table>
            <tr>
                <th>Severity</th>
                <th>Count</th>
            </tr>
"""

        for severity, violations in report.policy_violations.by_severity.items():
            badge_class = f"badge-{severity.lower()}"
            html += f"""
            <tr>
                <td><span class="badge {badge_class}">{severity}</span></td>
                <td>{len(violations)}</td>
            </tr>
"""

        html += """
        </table>

        <h3>Most Violated Policies</h3>
        <table>
            <tr>
                <th>Policy</th>
                <th>Violations</th>
            </tr>
"""

        for policy, count in report.summary.most_violated_policies[:10]:
            html += f"""
            <tr>
                <td>{policy}</td>
                <td>{count}</td>
            </tr>
"""

        html += f"""
        </table>

        <h2>Override Analysis</h2>
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value">{report.override_analysis.total_requested}</div>
                <div class="metric-label">Overrides Requested</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{report.override_analysis.total_approved}</div>
                <div class="metric-label">Overrides Approved</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{report.override_analysis.approval_rate:.1%}</div>
                <div class="metric-label">Approval Rate</div>
            </div>
        </div>

        <h2>Security Assessment</h2>

        <h3>Strengths</h3>
        <ul>
"""

        for strength in report.security_posture.strengths:
            html += f"            <li>{strength}</li>\n"

        html += """
        </ul>

        <h3>Weaknesses</h3>
        <ul>
"""

        for weakness in report.security_posture.weaknesses:
            html += f"            <li>{weakness}</li>\n"

        html += """
        </ul>

        <h2>Recommendations</h2>
"""

        for rec in report.recommendations:
            html += f"""
        <div class="recommendation priority-{rec.priority}">
            <h3>{rec.title} <span class="badge badge-{rec.priority.lower()}">{rec.priority}</span></h3>
            <p><strong>Category:</strong> {rec.category}</p>
            <p>{rec.description}</p>
            <p><strong>Recommended Action:</strong> {rec.action}</p>
        </div>
"""

        html += """
    </div>
</body>
</html>
"""
        return html

    def _render_pdf(self, report: ComplianceReport) -> bytes:
        """
        Render report as PDF.

        Args:
            report: ComplianceReport object

        Returns:
            PDF bytes
        """
        # [20251216_FEATURE] PDF report rendering with charts and tables
        try:
            from io import BytesIO

            from reportlab.lib import colors  # type: ignore[import-not-found]
            from reportlab.lib.enums import TA_CENTER  # type: ignore[import-not-found]
            from reportlab.lib.pagesizes import letter  # type: ignore[import-not-found]
            from reportlab.lib.styles import (  # type: ignore[import-not-found]
                ParagraphStyle,
                getSampleStyleSheet,
            )
            from reportlab.lib.units import inch  # type: ignore[import-not-found]
            from reportlab.platypus import (  # type: ignore[import-not-found]
                PageBreak,
                Paragraph,
                SimpleDocTemplate,
                Spacer,
                Table,
                TableStyle,
            )
        except ImportError:
            # Fallback if reportlab is not installed
            return b"PDF generation requires reportlab package. Install with: pip install reportlab"

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()

        # Title
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=24,
            textColor=colors.HexColor("#2c3e50"),
            spaceAfter=30,
            alignment=TA_CENTER,
        )
        story.append(Paragraph("Compliance Report", title_style))
        story.append(Spacer(1, 12))

        # Meta information
        meta_text = f"""
        <b>Generated:</b> {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}<br/>
        <b>Period:</b> {report.time_range[0].strftime('%Y-%m-%d')} to {report.time_range[1].strftime('%Y-%m-%d')}
        """
        story.append(Paragraph(meta_text, styles["Normal"]))
        story.append(Spacer(1, 20))

        # Security Posture
        story.append(Paragraph("Security Posture", styles["Heading2"]))
        posture_data = [
            ["Security Score", str(report.security_posture.score)],
            ["Grade", report.security_posture.grade],
            ["Risk Level", report.security_posture.risk_level],
        ]
        posture_table = Table(posture_data, colWidths=[3 * inch, 3 * inch])
        posture_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.lightgrey),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        story.append(posture_table)
        story.append(Spacer(1, 20))

        # Executive Summary
        story.append(Paragraph("Executive Summary", styles["Heading2"]))
        summary_data = [
            ["Metric", "Count"],
            ["Total Operations", str(report.summary.total_operations)],
            ["Allowed Operations", str(report.summary.allowed_operations)],
            ["Blocked Operations", str(report.summary.blocked_operations)],
            ["Overrides Requested", str(report.summary.overrides_requested)],
            ["Overrides Approved", str(report.summary.overrides_approved)],
            ["Tamper Attempts", str(report.summary.tamper_attempts)],
        ]
        summary_table = Table(summary_data, colWidths=[3 * inch, 3 * inch])
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        story.append(summary_table)
        story.append(Spacer(1, 20))

        # Policy Violations
        story.append(Paragraph("Policy Violations", styles["Heading2"]))
        story.append(
            Paragraph(
                f"<b>Total Violations:</b> {report.policy_violations.total}",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 12))

        if report.policy_violations.by_severity:
            story.append(Paragraph("By Severity", styles["Heading3"]))
            severity_data = [["Severity", "Count"]]
            for severity, violations in report.policy_violations.by_severity.items():
                severity_data.append([severity, str(len(violations))])

            severity_table = Table(severity_data, colWidths=[3 * inch, 3 * inch])
            severity_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]
                )
            )
            story.append(severity_table)
            story.append(Spacer(1, 20))

        # Most Violated Policies
        if report.summary.most_violated_policies:
            story.append(Paragraph("Most Violated Policies", styles["Heading3"]))
            policy_data = [["Policy", "Violations"]]
            for policy, count in report.summary.most_violated_policies[:10]:
                policy_data.append([policy, str(count)])

            policy_table = Table(policy_data, colWidths=[4 * inch, 2 * inch])
            policy_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]
                )
            )
            story.append(policy_table)
            story.append(Spacer(1, 20))

        # Page break before recommendations
        story.append(PageBreak())

        # Recommendations
        story.append(Paragraph("Recommendations", styles["Heading2"]))
        for rec in report.recommendations:
            rec_text = f"""
            <b>{rec.title}</b> [Priority: {rec.priority}]<br/>
            <b>Category:</b> {rec.category}<br/>
            {rec.description}<br/>
            <b>Recommended Action:</b> {rec.action}
            """
            story.append(Paragraph(rec_text, styles["Normal"]))
            story.append(Spacer(1, 12))

        # Build PDF
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()

        return pdf_bytes
