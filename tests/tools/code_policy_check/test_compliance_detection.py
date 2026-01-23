"""
Compliance detection tests for code_policy_check Enterprise features.

[20260105_TEST] Adds coverage for HIPAA, SOC2, GDPR, PCI-DSS findings and PDF generation.
"""

import pytest

from code_scalpel.mcp.server import code_policy_check


class TestComplianceDetection:
    """Enterprise compliance detection should populate reports per standard."""

    @pytest.mark.asyncio
    async def test_detects_enterprise_compliance_findings(self, tmp_path, enterprise_tier):
        """HIPAA/SOC2/GDPR/PCI rules should appear in compliance_reports."""
        test_file = tmp_path / "compliance_targets.py"
        test_file.write_text("""
import logging
import requests

logger = logging.getLogger(__name__)

@app.get("/records")
def get_records(request):
    logger.info("patient_id=%s", request.args["id"])  # HIPAA001
    email = request.json["email"]  # GDPR001
    requests.post("http://payments.example.com/checkout", data={"card": "4111111111111111"})  # PCI003
    return email
""")

        result = await code_policy_check(
            paths=[str(test_file)],
            compliance_standards=["hipaa", "soc2", "gdpr", "pci_dss"],
        )

        assert result.tier == "enterprise"
        assert getattr(result, "compliance_reports", None), "Enterprise should return compliance reports"

        for standard in ["HIPAA", "SOC2", "GDPR", "PCI_DSS"]:
            report = result.compliance_reports.get(standard)
            assert report, f"Missing compliance report for {standard}"
            # report may be ComplianceReport object or dict depending on transport
            findings = report.findings if hasattr(report, "findings") else report.get("findings")
            score = report.score if hasattr(report, "score") else report.get("score")
            assert findings, f"{standard} report should include findings"
            assert score is not None and score >= 0, f"{standard} report should include a score"

    @pytest.mark.asyncio
    async def test_generate_pdf_report_and_score(self, tmp_path, enterprise_tier):
        """Enterprise generate_report should set pdf_report and compliance_score."""
        test_file = tmp_path / "compliance_pdf.py"
        test_file.write_text("""
import logging

logger = logging.getLogger(__name__)

@app.post("/payments")
def process(card):
    logger.info("card number: %s", card)  # PCI001
    return card
""")

        result = await code_policy_check(
            paths=[str(test_file)],
            compliance_standards=["pci_dss"],
            generate_report=True,
        )

        assert result.tier == "enterprise"
        assert getattr(result, "compliance_score", 0) > 0
        assert getattr(result, "pdf_report", None), "PDF report should be generated for Enterprise"
        assert getattr(result, "audit_trail", []), "Audit trail should be recorded"
