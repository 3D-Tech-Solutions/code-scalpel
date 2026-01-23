from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from code_scalpel.governance.compliance_reporter import ComplianceReporter


class _DummyAuditLog:
    """Minimal audit log stub for testing."""

    def __init__(self, events: list[dict[str, Any]]):
        self._events = events

    def get_events(self, time_range: tuple[datetime, datetime] | None = None) -> list[dict[str, Any]]:  # noqa: ARG002
        return self._events


class _DummyPolicyEngine:
    """Placeholder policy engine; not used by ComplianceReporter."""

    pass


def _sample_events() -> list[dict[str, Any]]:
    """Construct diverse events to exercise report generation paths."""
    events: list[dict[str, Any]] = [
        {"event_type": "OPERATION_ALLOWED", "details": {"policy_name": "ALLOW"}},
        {
            "event_type": "POLICY_VIOLATION",
            "details": {
                "policy_name": "CRIT",
                "severity": "CRITICAL",
                "operation_type": "code_edit",
            },
        },
    ]

    # Frequent violations to trigger recommendations
    for _ in range(12):
        events.append(
            {
                "event_type": "POLICY_VIOLATION",
                "details": {
                    "policy_name": "FREQUENT",
                    "severity": "HIGH",
                    "operation_type": "file_write",
                },
            }
        )

    events.extend(
        [
            {
                "event_type": "OVERRIDE_REQUESTED",
                "details": {"policy_name": "FREQUENT", "reason": "business"},
            },
            {
                "event_type": "OVERRIDE_APPROVED",
                "details": {"policy_name": "FREQUENT", "reason": "business"},
            },
            {
                "event_type": "OVERRIDE_DENIED",
                "details": {"policy_name": "FREQUENT", "reason": "risk"},
            },
            {"event_type": "OPERATION_ALLOWED", "details": {"policy_name": "ALLOW"}},
            {"event_type": "TAMPER_DETECTED", "details": {}},
        ]
    )

    return events


def _build_reporter() -> ComplianceReporter:
    events = _sample_events()
    audit_log = _DummyAuditLog(events)
    policy_engine = _DummyPolicyEngine()
    return ComplianceReporter(audit_log, policy_engine)


def _install_fake_reportlab(monkeypatch) -> None:
    import sys
    import types

    fake_reportlab = types.ModuleType("reportlab")
    fake_reportlab.lib = types.ModuleType("reportlab.lib")
    fake_reportlab.lib.pagesizes = types.ModuleType("reportlab.lib.pagesizes")
    fake_reportlab.lib.pagesizes.letter = "LETTER"

    fake_reportlab.lib.units = types.ModuleType("reportlab.lib.units")
    fake_reportlab.lib.units.inch = 1

    fake_reportlab.lib.enums = types.ModuleType("reportlab.lib.enums")
    fake_reportlab.lib.enums.TA_CENTER = 1

    fake_reportlab.lib.colors = types.ModuleType("reportlab.lib.colors")
    fake_reportlab.lib.colors.HexColor = lambda value: value
    fake_reportlab.lib.colors.lightgrey = "lightgrey"
    fake_reportlab.lib.colors.black = "black"
    fake_reportlab.lib.colors.grey = "grey"
    fake_reportlab.lib.colors.whitesmoke = "whitesmoke"
    fake_reportlab.lib.colors.beige = "beige"

    def _get_stylesheet():
        return {
            "Heading1": {},
            "Heading2": {},
            "Heading3": {},
            "Normal": {},
        }

    def _paragraph_style(
        name,
        parent=None,
        fontSize=None,
        textColor=None,
        spaceAfter=None,
        alignment=None,
    ):  # noqa: ARG001,E501
        return {
            "name": name,
            "parent": parent,
            "fontSize": fontSize,
            "textColor": textColor,
            "spaceAfter": spaceAfter,
            "alignment": alignment,
        }

    fake_reportlab.lib.styles = types.ModuleType("reportlab.lib.styles")
    fake_reportlab.lib.styles.getSampleStyleSheet = _get_stylesheet
    fake_reportlab.lib.styles.ParagraphStyle = _paragraph_style

    fake_reportlab.platypus = types.ModuleType("reportlab.platypus")

    class _SimpleDocTemplate:
        def __init__(self, buffer, pagesize=None):  # noqa: ARG002
            self.buffer = buffer

        def build(self, story):  # noqa: ARG002
            self.buffer.write(b"pdf")

    class _Paragraph:
        def __init__(self, text, style):  # noqa: ARG002
            self.text = text

    class _Spacer:
        def __init__(self, width, height):  # noqa: ARG002
            self.width = width
            self.height = height

    class _Table:
        def __init__(self, data, colWidths=None):  # noqa: ARG002
            self.data = data
            self.colWidths = colWidths

        def setStyle(self, style):  # noqa: ARG002
            self.style = style

    class _TableStyle:
        def __init__(self, data):  # noqa: ARG002
            self.data = data

    class _PageBreak:  # pragma: no cover - simple placeholder
        pass

    fake_reportlab.platypus.SimpleDocTemplate = _SimpleDocTemplate
    fake_reportlab.platypus.Paragraph = _Paragraph
    fake_reportlab.platypus.Spacer = _Spacer
    fake_reportlab.platypus.Table = _Table
    fake_reportlab.platypus.TableStyle = _TableStyle
    fake_reportlab.platypus.PageBreak = _PageBreak

    monkeypatch.setitem(sys.modules, "reportlab", fake_reportlab)
    monkeypatch.setitem(sys.modules, "reportlab.lib", fake_reportlab.lib)
    monkeypatch.setitem(sys.modules, "reportlab.lib.pagesizes", fake_reportlab.lib.pagesizes)
    monkeypatch.setitem(sys.modules, "reportlab.lib.units", fake_reportlab.lib.units)
    monkeypatch.setitem(sys.modules, "reportlab.lib.styles", fake_reportlab.lib.styles)
    monkeypatch.setitem(sys.modules, "reportlab.lib.colors", fake_reportlab.lib.colors)
    monkeypatch.setitem(sys.modules, "reportlab.lib.enums", fake_reportlab.lib.enums)
    monkeypatch.setitem(sys.modules, "reportlab.platypus", fake_reportlab.platypus)


# [20251216_TEST] Ensure JSON and HTML rendering paths execute without errors


def test_generate_report_json_and_html() -> None:
    reporter = _build_reporter()
    time_range = (datetime.now() - timedelta(days=1), datetime.now())

    json_report = reporter.generate_report(time_range, format="json")
    assert '"violations"' in json_report

    html_report = reporter.generate_report(time_range, format="html")
    assert "<html" in html_report and "Compliance Report" in html_report


# [20251216_TEST] Exercise PDF rendering through stubbed reportlab


def test_generate_report_pdf_bytes(monkeypatch) -> None:
    _install_fake_reportlab(monkeypatch)

    reporter = _build_reporter()
    time_range = (datetime.now() - timedelta(days=1), datetime.now())

    pdf_result = reporter.generate_report(time_range, format="pdf")
    assert isinstance(pdf_result, (bytes, bytearray))
    assert pdf_result.startswith(b"pdf")
