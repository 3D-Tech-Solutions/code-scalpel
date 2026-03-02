"""
Compliance PDF Report Builder — Enterprise tier.

[20260227_FEATURE] v2.0.0 - Branded, white-label-ready compliance reports.

Builds a styled HTML document from a CodePolicyResult and an optional
ReportConfig, then attempts to convert it to PDF via weasyprint.  Falls back
to returning the raw HTML (base64-encoded) if weasyprint is unavailable.

Usage
-----
    builder = ComplianceReportBuilder(result, config)
    b64_pdf_or_html = builder.build()

The returned string is always a base64-encoded payload.  Callers can detect
whether it is a real PDF by checking the raw decoded prefix:
    decoded = base64.b64decode(b64)
    is_pdf = decoded[:4] == b"%PDF"
"""

from __future__ import annotations

import base64
import html as html_lib
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import CodePolicyResult, ReportConfig

# ──────────────────────────────────────────────────────────────────────────────
# Brand constants
# ──────────────────────────────────────────────────────────────────────────────
_BRAND_PRIMARY = "#1d4ed8"
_BRAND_DARK = "#0f172a"
_BRAND_ACCENT = "#38bdf8"
_BRAND_SUCCESS = "#16a34a"
_BRAND_WARNING = "#d97706"
_BRAND_ERROR = "#dc2626"
_BRAND_MUTED = "#64748b"

_CLASSIFICATION_COLORS = {
    "CONFIDENTIAL": "#dc2626",
    "INTERNAL": "#d97706",
    "PUBLIC": "#16a34a",
}

# Inline SVG scalpel logo mark (simplified)
_LOGO_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="36" height="36">
  <rect width="48" height="48" rx="8" fill="#1d4ed8"/>
  <path d="M10 38 L24 10 L28 14 L16 38 Z" fill="white" opacity="0.9"/>
  <path d="M24 10 L38 38 L34 38 L24 18 Z" fill="white" opacity="0.6"/>
  <circle cx="24" cy="10" r="3" fill="#38bdf8"/>
</svg>
"""

_SEVERITY_BADGE = {
    "critical": f'<span style="background:{_BRAND_ERROR};color:#fff;padding:2px 7px;border-radius:10px;font-size:11px;font-weight:700">CRITICAL</span>',
    "error": '<span style="background:#f97316;color:#fff;padding:2px 7px;border-radius:10px;font-size:11px;font-weight:700">ERROR</span>',
    "warning": f'<span style="background:{_BRAND_WARNING};color:#fff;padding:2px 7px;border-radius:10px;font-size:11px;font-weight:700">WARNING</span>',
    "info": f'<span style="background:{_BRAND_MUTED};color:#fff;padding:2px 7px;border-radius:10px;font-size:11px;font-weight:700">INFO</span>',
}

_STATUS_BADGE = {
    "compliant": f'<span style="background:{_BRAND_SUCCESS};color:#fff;padding:3px 10px;border-radius:10px;font-size:12px;font-weight:700">COMPLIANT</span>',
    "partial": f'<span style="background:{_BRAND_WARNING};color:#fff;padding:3px 10px;border-radius:10px;font-size:12px;font-weight:700">PARTIAL</span>',
    "non_compliant": f'<span style="background:{_BRAND_ERROR};color:#fff;padding:3px 10px;border-radius:10px;font-size:12px;font-weight:700">NON-COMPLIANT</span>',
}


# ──────────────────────────────────────────────────────────────────────────────
# Builder
# ──────────────────────────────────────────────────────────────────────────────
class ComplianceReportBuilder:
    """
    Builds a professionally branded compliance PDF report.

    Parameters
    ----------
    result : CodePolicyResult
        The full result from CodePolicyChecker.check_files().
    config : ReportConfig | None
        Optional branding / org metadata.  Uses sensible defaults if None.
    """

    def __init__(
        self,
        result: "CodePolicyResult",
        config: "ReportConfig | None" = None,
    ) -> None:
        from .models import ReportConfig as _RC

        self._result = result
        self._cfg = config if config is not None else _RC()
        self._now = datetime.now()
        self._title = (
            self._cfg.report_title
            or f"{self._cfg.project_name} — Compliance Audit Report"
        )

    # ── Public entry point ────────────────────────────────────────────────────

    def build(self) -> str:
        """
        Assemble the report and return a base64-encoded PDF (or HTML fallback).
        """
        html_content = self._assemble_html()
        try:
            import weasyprint  # type: ignore[import]

            pdf_bytes: bytes = weasyprint.HTML(string=html_content).write_pdf()
            return base64.b64encode(pdf_bytes).decode()
        except Exception:
            pass
        return base64.b64encode(html_content.encode("utf-8")).decode()

    # ── HTML assembly ─────────────────────────────────────────────────────────

    def _assemble_html(self) -> str:
        parts: list[str] = []
        parts.append(self._html_head())
        parts.append("<body>")

        # Cover page
        parts.append(self._cover_page())

        # Executive summary
        parts.append(self._exec_summary_page())

        # Per-standard detail pages
        for standard, report in self._result.compliance_reports.items():
            parts.append(self._standard_detail_page(standard, report))

        # Remediation roadmap (critical + error only)
        parts.append(self._remediation_page())

        # Certificate pages
        for cert in self._result.certifications:
            parts.append(self._certificate_page(cert))

        # Metadata / signature page
        parts.append(self._metadata_page())

        parts.append("</body></html>")
        return "\n".join(parts)

    # ── <head> ────────────────────────────────────────────────────────────────

    def _html_head(self) -> str:
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<title>{html_lib.escape(self._title)}</title>
<style>
{self._css()}
</style>
</head>"""

    # ── CSS ───────────────────────────────────────────────────────────────────

    def _css(self) -> str:
        clf_color = _CLASSIFICATION_COLORS.get(
            self._cfg.classification.upper(), _BRAND_ERROR
        )
        return f"""
/* ── Reset & base ──────────────────────────────────────────────────── */
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
html {{ font-size: 13px; }}
body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: {_BRAND_DARK};
       background: #fff; line-height: 1.55; }}

/* ── @page for weasyprint ───────────────────────────────────────────── */
@page {{
    size: A4;
    margin: 0;
}}
@page :first {{
    margin: 0;
}}

/* ── Page wrapper ───────────────────────────────────────────────────── */
.page {{
    width: 210mm;
    min-height: 297mm;
    page-break-after: always;
    overflow: hidden;
    position: relative;
}}

/* ── Classification banner ──────────────────────────────────────────── */
.clf-banner {{
    background: {clf_color};
    color: #fff;
    text-align: center;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2px;
    padding: 4px 0;
}}

/* ── Page header chrome ─────────────────────────────────────────────── */
.page-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 20px;
    border-bottom: 2px solid {_BRAND_PRIMARY};
    background: #f8fafc;
}}
.page-header .brand {{
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 11px;
    font-weight: 700;
    color: {_BRAND_PRIMARY};
    text-transform: uppercase;
    letter-spacing: 1px;
}}
.page-header .doc-title {{
    font-size: 11px;
    color: {_BRAND_MUTED};
    max-width: 280px;
    text-align: right;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}

/* ── Page footer chrome ─────────────────────────────────────────────── */
.page-footer {{
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    background: #f8fafc;
    border-top: 1px solid #e2e8f0;
    padding: 6px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 10px;
    color: {_BRAND_MUTED};
}}

/* ── Body area ──────────────────────────────────────────────────────── */
.page-body {{
    padding: 18px 22px 60px;
}}

/* ── Cover page ─────────────────────────────────────────────────────── */
.cover {{
    min-height: 297mm;
    background: linear-gradient(160deg, {_BRAND_DARK} 0%, #1e3a5f 60%, {_BRAND_PRIMARY} 100%);
    display: flex;
    flex-direction: column;
    color: #fff;
    position: relative;
    overflow: hidden;
}}
.cover-deco {{
    position: absolute;
    top: -80px; right: -80px;
    width: 320px; height: 320px;
    border-radius: 50%;
    background: rgba(56,189,248,0.08);
}}
.cover-deco2 {{
    position: absolute;
    bottom: -60px; left: -60px;
    width: 240px; height: 240px;
    border-radius: 50%;
    background: rgba(255,255,255,0.04);
}}
.cover-top {{
    padding: 28px 32px 0;
    display: flex;
    align-items: center;
    gap: 12px;
}}
.cover-top .cs-wordmark {{
    font-size: 15px;
    font-weight: 800;
    letter-spacing: 0.5px;
    color: #fff;
}}
.cover-top .cs-wordmark span {{
    color: {_BRAND_ACCENT};
}}
.cover-main {{
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 0 32px;
    gap: 14px;
}}
.cover-tag {{
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 3px;
    color: {_BRAND_ACCENT};
    font-weight: 600;
}}
.cover-title {{
    font-size: 26px;
    font-weight: 800;
    line-height: 1.25;
    color: #fff;
    max-width: 500px;
}}
.cover-org {{
    font-size: 14px;
    color: rgba(255,255,255,0.75);
    font-weight: 500;
}}
.cover-meta-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px 20px;
    margin-top: 10px;
}}
.cover-meta-item {{
    font-size: 11px;
    color: rgba(255,255,255,0.6);
}}
.cover-meta-item strong {{
    display: block;
    color: rgba(255,255,255,0.9);
    font-weight: 600;
    font-size: 12px;
}}
.cover-score-row {{
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
    margin-top: 16px;
}}
.cover-score-card {{
    background: rgba(255,255,255,0.1);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 10px;
    padding: 12px 18px;
    min-width: 110px;
    backdrop-filter: blur(4px);
}}
.cover-score-card .score-label {{
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: rgba(255,255,255,0.6);
}}
.cover-score-card .score-value {{
    font-size: 28px;
    font-weight: 800;
    color: #fff;
    line-height: 1.1;
}}
.cover-score-card .score-sub {{
    font-size: 10px;
    color: rgba(255,255,255,0.5);
}}
.cover-bottom {{
    padding: 18px 32px;
    border-top: 1px solid rgba(255,255,255,0.12);
    display: flex;
    align-items: center;
    justify-content: space-between;
}}
.cover-clf {{
    background: {clf_color};
    color: #fff;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2px;
    padding: 4px 12px;
    border-radius: 4px;
}}
.cover-bottom-right {{
    font-size: 10px;
    color: rgba(255,255,255,0.5);
    text-align: right;
}}

/* ── Section headings ───────────────────────────────────────────────── */
.section-heading {{
    font-size: 17px;
    font-weight: 800;
    color: {_BRAND_PRIMARY};
    border-bottom: 2px solid {_BRAND_PRIMARY};
    padding-bottom: 6px;
    margin-bottom: 14px;
}}
.sub-heading {{
    font-size: 13px;
    font-weight: 700;
    color: {_BRAND_DARK};
    margin: 14px 0 6px;
}}

/* ── KPI grid ───────────────────────────────────────────────────────── */
.kpi-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
    margin-bottom: 16px;
}}
.kpi-card {{
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 10px 14px;
    text-align: center;
}}
.kpi-card .kpi-value {{
    font-size: 22px;
    font-weight: 800;
    color: {_BRAND_PRIMARY};
}}
.kpi-card .kpi-label {{
    font-size: 10px;
    color: {_BRAND_MUTED};
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-top: 2px;
}}

/* ── Tables ─────────────────────────────────────────────────────────── */
table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    margin-bottom: 14px;
}}
th {{
    background: {_BRAND_DARK};
    color: #fff;
    padding: 8px 10px;
    text-align: left;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.4px;
}}
td {{
    padding: 7px 10px;
    border-bottom: 1px solid #e2e8f0;
    vertical-align: top;
}}
tr:nth-child(even) td {{
    background: #f8fafc;
}}
tr:hover td {{
    background: #eff6ff;
}}

/* ── Code snippet ───────────────────────────────────────────────────── */
.code-snip {{
    background: #1e293b;
    color: #e2e8f0;
    font-family: 'Courier New', monospace;
    font-size: 11px;
    padding: 8px 12px;
    border-radius: 6px;
    margin: 4px 0 6px;
    white-space: pre-wrap;
    word-break: break-all;
}}

/* ── Score dial ─────────────────────────────────────────────────────── */
.score-dial-wrap {{
    display: flex;
    align-items: center;
    gap: 20px;
    margin-bottom: 16px;
}}
.score-dial {{
    width: 80px; height: 80px;
    border-radius: 50%;
    border: 8px solid #e2e8f0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    font-weight: 800;
    flex-shrink: 0;
}}
.score-dial.good {{ border-color: {_BRAND_SUCCESS}; color: {_BRAND_SUCCESS}; }}
.score-dial.warn {{ border-color: {_BRAND_WARNING}; color: {_BRAND_WARNING}; }}
.score-dial.bad  {{ border-color: {_BRAND_ERROR};   color: {_BRAND_ERROR};   }}

/* ── Remediation ────────────────────────────────────────────────────── */
.finding-card {{
    background: #fff8f8;
    border-left: 4px solid {_BRAND_ERROR};
    border-radius: 4px;
    padding: 10px 14px;
    margin-bottom: 10px;
}}
.finding-card.warning {{
    background: #fffbeb;
    border-left-color: {_BRAND_WARNING};
}}
.finding-card .fc-head {{
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 4px;
}}
.finding-card .fc-rule {{
    font-weight: 700;
    font-size: 12px;
    color: {_BRAND_DARK};
}}
.finding-card .fc-file {{
    font-size: 11px;
    color: {_BRAND_MUTED};
    font-family: 'Courier New', monospace;
}}
.finding-card .fc-msg {{
    font-size: 12px;
    color: #374151;
    margin-bottom: 4px;
}}
.finding-card .fc-fix {{
    font-size: 11px;
    color: {_BRAND_SUCCESS};
    font-style: italic;
}}

/* ── Recommendations ────────────────────────────────────────────────── */
.rec-list {{
    list-style: none;
    padding: 0;
}}
.rec-list li {{
    padding: 5px 0 5px 20px;
    position: relative;
    font-size: 12px;
    color: #374151;
    border-bottom: 1px solid #f1f5f9;
}}
.rec-list li::before {{
    content: "→";
    position: absolute;
    left: 0;
    color: {_BRAND_PRIMARY};
    font-weight: 700;
}}

/* ── Certificate ────────────────────────────────────────────────────── */
.cert-page {{
    min-height: 297mm;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: #fff;
    padding: 40px;
    page-break-after: always;
}}
.cert-box {{
    border: 3px solid {_BRAND_PRIMARY};
    border-radius: 16px;
    padding: 40px 50px;
    max-width: 500px;
    width: 100%;
    position: relative;
    text-align: center;
    box-shadow: 0 0 0 8px rgba(29,78,216,0.08);
}}
.cert-corner {{
    position: absolute;
    width: 40px; height: 40px;
    border-color: {_BRAND_ACCENT};
    border-style: solid;
}}
.cert-corner.tl {{ top: 10px; left: 10px; border-width: 3px 0 0 3px; }}
.cert-corner.tr {{ top: 10px; right: 10px; border-width: 3px 3px 0 0; }}
.cert-corner.bl {{ bottom: 10px; left: 10px; border-width: 0 0 3px 3px; }}
.cert-corner.br {{ bottom: 10px; right: 10px; border-width: 0 3px 3px 0; }}
.cert-issued {{
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 3px;
    color: {_BRAND_MUTED};
    margin-bottom: 8px;
}}
.cert-standard {{
    font-size: 28px;
    font-weight: 800;
    color: {_BRAND_PRIMARY};
    margin-bottom: 6px;
}}
.cert-subtitle {{
    font-size: 14px;
    color: {_BRAND_MUTED};
    margin-bottom: 20px;
}}
.cert-org {{
    font-size: 18px;
    font-weight: 700;
    color: {_BRAND_DARK};
    border-top: 1px solid #e2e8f0;
    border-bottom: 1px solid #e2e8f0;
    padding: 10px 0;
    margin-bottom: 16px;
}}
.cert-detail {{
    font-size: 11px;
    color: {_BRAND_MUTED};
    line-height: 1.8;
}}
.cert-id {{
    font-family: 'Courier New', monospace;
    font-size: 10px;
    color: {_BRAND_MUTED};
    margin-top: 16px;
    background: #f8fafc;
    padding: 4px 8px;
    border-radius: 4px;
    display: inline-block;
}}
.cert-score-badge {{
    display: inline-block;
    background: {_BRAND_SUCCESS};
    color: #fff;
    font-size: 13px;
    font-weight: 700;
    padding: 4px 14px;
    border-radius: 20px;
    margin-bottom: 14px;
}}

/* ── Status / info boxes ─────────────────────────────────────────────── */
.info-box {{
    background: #eff6ff;
    border-left: 4px solid {_BRAND_PRIMARY};
    border-radius: 4px;
    padding: 10px 14px;
    font-size: 12px;
    color: #1e3a5f;
    margin-bottom: 12px;
}}

/* ── Metadata table ─────────────────────────────────────────────────── */
.meta-table td:first-child {{
    width: 35%;
    font-weight: 600;
    color: {_BRAND_MUTED};
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.3px;
}}

/* ── Utilities ──────────────────────────────────────────────────────── */
.text-muted {{ color: {_BRAND_MUTED}; }}
.text-sm {{ font-size: 11px; }}
.mb-0 {{ margin-bottom: 0; }}
.mt-8 {{ margin-top: 8px; }}
.mt-14 {{ margin-top: 14px; }}
.gap-fill {{ flex: 1; }}
"""

    # ── Cover page ────────────────────────────────────────────────────────────

    def _cover_page(self) -> str:
        cfg = self._cfg
        result = self._result

        # Score card data
        overall = result.compliance_score
        n_standards = len(result.compliance_reports)
        n_certs = len(result.certifications)
        n_critical = sum(
            1
            for v in result.violations
            if getattr(v.severity, "value", v.severity) == "critical"
        )

        def _score_color(s: float) -> str:
            if s >= 90:
                return _BRAND_SUCCESS
            if s >= 70:
                return _BRAND_WARNING
            return _BRAND_ERROR

        score_cards_html = f"""
<div class="cover-score-row">
  <div class="cover-score-card">
    <div class="score-label">Overall Score</div>
    <div class="score-value" style="color:{_score_color(overall)}">{overall:.0f}</div>
    <div class="score-sub">out of 100</div>
  </div>
  <div class="cover-score-card">
    <div class="score-label">Standards</div>
    <div class="score-value">{n_standards}</div>
    <div class="score-sub">audited</div>
  </div>
  <div class="cover-score-card">
    <div class="score-label">Certifications</div>
    <div class="score-value">{n_certs}</div>
    <div class="score-sub">issued</div>
  </div>
  <div class="cover-score-card">
    <div class="score-label">Critical Issues</div>
    <div class="score-value" style="color:{_BRAND_ERROR if n_critical else _BRAND_SUCCESS}">{n_critical}</div>
    <div class="score-sub">found</div>
  </div>
</div>
"""

        # Optional org logo
        logo_html = ""
        if cfg.logo_b64:
            logo_html = f'<img src="{html_lib.escape(cfg.logo_b64)}" style="height:40px;object-fit:contain;margin-left:auto;margin-right:10px;" alt="org logo"/>'

        meta_items = []
        if cfg.project_description:
            meta_items.append(("Project", cfg.project_description))
        if cfg.audit_period:
            meta_items.append(("Audit Period", cfg.audit_period))
        if cfg.department:
            meta_items.append(("Department", cfg.department))
        if cfg.prepared_by:
            meta_items.append(("Prepared By", cfg.prepared_by))
        meta_html = ""
        if meta_items:
            items_html = "".join(
                f'<div class="cover-meta-item"><strong>{html_lib.escape(k)}</strong>{html_lib.escape(v)}</div>'
                for k, v in meta_items
            )
            meta_html = f'<div class="cover-meta-grid">{items_html}</div>'

        return f"""
<div class="page cover">
  <div class="cover-deco"></div>
  <div class="cover-deco2"></div>

  <div class="cover-top">
    {_LOGO_SVG}
    <div class="cs-wordmark">Code <span>Scalpel</span></div>
    {logo_html}
  </div>

  <div class="cover-main">
    <div class="cover-tag">Compliance Audit Report</div>
    <div class="cover-title">{html_lib.escape(self._title)}</div>
    <div class="cover-org">{html_lib.escape(cfg.organization_name)}</div>
    {meta_html}
    {score_cards_html}
  </div>

  <div class="cover-bottom">
    <div class="cover-clf">{html_lib.escape(cfg.classification)}</div>
    <div class="cover-bottom-right">
      Generated: {self._now.strftime('%Y-%m-%d %H:%M UTC')}<br/>
      Version: {html_lib.escape(cfg.version)} &nbsp;|&nbsp; Code Scalpel Enterprise
    </div>
  </div>
</div>"""

    # ── Executive summary page ────────────────────────────────────────────────

    def _exec_summary_page(self) -> str:
        result = self._result
        cfg = self._cfg
        overall = result.compliance_score

        # Score dial class
        dial_cls = "good" if overall >= 90 else ("warn" if overall >= 70 else "bad")

        # Severity breakdown
        from collections import Counter

        sev_counts: Counter[str] = Counter()
        for v in result.violations:
            sev_counts[getattr(v.severity, "value", v.severity)] += 1
        # Also pull from compliance_reports findings
        for rpt in result.compliance_reports.values():
            for f in rpt.findings:
                sev = f.get("severity", "warning")
                sev_counts[sev] += 1

        kpi_html = f"""
<div class="kpi-grid">
  <div class="kpi-card">
    <div class="kpi-value">{result.files_checked}</div>
    <div class="kpi-label">Files Scanned</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-value" style="color:{_BRAND_ERROR}">{sev_counts.get('critical', 0)}</div>
    <div class="kpi-label">Critical</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-value" style="color:#f97316">{sev_counts.get('error', 0)}</div>
    <div class="kpi-label">Errors</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-value" style="color:{_BRAND_WARNING}">{sev_counts.get('warning', 0)}</div>
    <div class="kpi-label">Warnings</div>
  </div>
</div>"""

        # Standards summary table
        std_rows = ""
        for std, rpt in result.compliance_reports.items():
            badge = _STATUS_BADGE.get(rpt.status, rpt.status)
            n_findings = len(rpt.findings)
            score_color = (
                _BRAND_SUCCESS
                if rpt.score >= 90
                else (_BRAND_WARNING if rpt.score >= 70 else _BRAND_ERROR)
            )
            std_rows += f"""
<tr>
  <td><strong>{html_lib.escape(std)}</strong></td>
  <td>{badge}</td>
  <td style="color:{score_color};font-weight:700">{rpt.score:.1f}/100</td>
  <td>{n_findings}</td>
</tr>"""

        std_table = f"""
<table>
  <thead><tr>
    <th>Standard</th><th>Status</th><th>Score</th><th>Findings</th>
  </tr></thead>
  <tbody>{std_rows}</tbody>
</table>"""

        # Certifications issued
        cert_html = ""
        if result.certifications:
            cert_rows = "".join(
                f"<tr><td><strong>{html_lib.escape(c.standard)}</strong></td>"
                f"<td>{html_lib.escape(c.certificate_id)}</td>"
                f'<td>{c.issued_date.strftime("%Y-%m-%d")}</td>'
                f'<td>{c.valid_until.strftime("%Y-%m-%d")}</td></tr>'
                for c in result.certifications
            )
            cert_html = f"""
<div class="sub-heading">Certifications Issued</div>
<table>
  <thead><tr><th>Standard</th><th>Certificate ID</th><th>Issued</th><th>Valid Until</th></tr></thead>
  <tbody>{cert_rows}</tbody>
</table>"""

        proj_desc_html = ""
        if cfg.project_description:
            proj_desc_html = f'<div class="info-box">{html_lib.escape(cfg.project_description)}</div>'

        body = f"""
<div class="section-heading">Executive Summary</div>
{proj_desc_html}
<div class="score-dial-wrap">
  <div class="score-dial {dial_cls}">{overall:.0f}</div>
  <div>
    <div style="font-size:15px;font-weight:700;color:{_BRAND_DARK}">Overall Compliance Score</div>
    <div class="text-muted text-sm">{len(result.compliance_reports)} standard(s) audited &nbsp;·&nbsp; {result.files_checked} file(s) scanned</div>
    <div class="text-muted text-sm">Scan date: {self._now.strftime('%Y-%m-%d')}</div>
  </div>
</div>
{kpi_html}
<div class="sub-heading">Standards Summary</div>
{std_table}
{cert_html}"""

        return self._wrap_content_page("Executive Summary", body)

    # ── Standard detail page ──────────────────────────────────────────────────

    def _standard_detail_page(self, standard: str, report: "object") -> str:
        from .models import ComplianceReport

        if not isinstance(report, ComplianceReport):
            return ""

        badge = _STATUS_BADGE.get(report.status, report.status)
        score_color = (
            _BRAND_SUCCESS
            if report.score >= 90
            else (_BRAND_WARNING if report.score >= 70 else _BRAND_ERROR)
        )

        # Sort findings: critical → error → warning → info
        _sev_order = {"critical": 0, "error": 1, "warning": 2, "info": 3}
        sorted_findings = sorted(
            report.findings,
            key=lambda f: _sev_order.get(f.get("severity", "warning"), 2),
        )

        rows = ""
        for f in sorted_findings:
            sev = f.get("severity", "warning")
            badge_sev = _SEVERITY_BADGE.get(sev, sev)
            rule_id = html_lib.escape(f.get("rule_id", f.get("pattern_id", "")))
            msg = html_lib.escape(f.get("message", f.get("description", "")))
            file_ref = html_lib.escape(f.get("file", ""))
            line_ref = f.get("line", "")
            snip = f.get("code_snippet") or f.get("matched_text") or ""
            snip_html = (
                f'<div class="code-snip">{html_lib.escape(snip[:200])}</div>'
                if snip
                else ""
            )
            rows += f"""
<tr>
  <td>{badge_sev}</td>
  <td><code style="font-size:11px">{rule_id}</code></td>
  <td>{msg}{snip_html}</td>
  <td style="font-size:11px;font-family:'Courier New',monospace">{file_ref}:{line_ref}</td>
</tr>"""

        findings_table = f"""
<table>
  <thead><tr>
    <th style="width:90px">Severity</th>
    <th style="width:90px">Rule ID</th>
    <th>Message</th>
    <th style="width:160px">Location</th>
  </tr></thead>
  <tbody>{rows if rows else '<tr><td colspan="4" style="text-align:center;color:#16a34a;font-weight:600">No findings — fully compliant</td></tr>'}</tbody>
</table>"""

        rec_items = "".join(
            f"<li>{html_lib.escape(r)}</li>" for r in (report.recommendations or [])
        )
        rec_html = (
            f"""
<div class="sub-heading">Recommendations</div>
<ul class="rec-list">{rec_items}</ul>"""
            if rec_items
            else ""
        )

        body = f"""
<div class="section-heading">{html_lib.escape(standard)} — Compliance Details</div>
<div style="display:flex;align-items:center;gap:12px;margin-bottom:14px">
  {badge}
  <span style="font-size:18px;font-weight:800;color:{score_color}">{report.score:.1f}<span style="font-size:12px;color:{_BRAND_MUTED}">/100</span></span>
  <span class="text-muted text-sm">{len(report.findings)} finding(s)</span>
  <span class="text-muted text-sm">Scanned: {report.timestamp.strftime('%Y-%m-%d')}</span>
</div>
<div class="sub-heading">Findings</div>
{findings_table}
{rec_html}"""

        return self._wrap_content_page(f"{standard} Details", body)

    # ── Remediation roadmap ───────────────────────────────────────────────────

    def _remediation_page(self) -> str:
        # Collect all critical + error findings across standards
        critical_findings: list[dict] = []
        error_findings: list[dict] = []

        for std, rpt in self._result.compliance_reports.items():
            for f in rpt.findings:
                sev = f.get("severity", "warning")
                tagged = dict(f, _standard=std)
                if sev == "critical":
                    critical_findings.append(tagged)
                elif sev == "error":
                    error_findings.append(tagged)

        if not critical_findings and not error_findings:
            body = f"""
<div class="section-heading">Remediation Roadmap</div>
<div class="info-box" style="background:#f0fdf4;border-color:{_BRAND_SUCCESS};color:#166534">
  No critical or error-level findings. The codebase is in excellent compliance health.
</div>"""
            return self._wrap_content_page("Remediation Roadmap", body)

        def _card(f: dict, cls: str) -> str:
            sev = f.get("severity", "warning")
            badge_sev = _SEVERITY_BADGE.get(sev, sev)
            rule_id = html_lib.escape(f.get("rule_id", f.get("pattern_id", "")))
            msg = html_lib.escape(f.get("message", f.get("description", "")))
            fix = html_lib.escape(
                f.get("suggestion", f.get("recommendation", "")) or ""
            )
            file_ref = html_lib.escape(f.get("file", ""))
            line_ref = f.get("line", "")
            std = html_lib.escape(f.get("_standard", ""))
            snip = f.get("code_snippet") or f.get("matched_text") or ""
            snip_html = (
                f'<div class="code-snip">{html_lib.escape(snip[:300])}</div>'
                if snip
                else ""
            )
            fix_html = f'<div class="fc-fix">Suggested fix: {fix}</div>' if fix else ""
            return f"""
<div class="finding-card {cls}">
  <div class="fc-head">
    {badge_sev}
    <span class="fc-rule">{rule_id}</span>
    <span class="text-muted text-sm">[{std}]</span>
  </div>
  <div class="fc-file">{file_ref} line {line_ref}</div>
  <div class="fc-msg">{msg}</div>
  {snip_html}
  {fix_html}
</div>"""

        critical_html = ""
        if critical_findings:
            cards = "".join(_card(f, "") for f in critical_findings)
            critical_html = f"""
<div class="sub-heading" style="color:{_BRAND_ERROR}">Critical — Remediate Immediately</div>
{cards}"""

        error_html = ""
        if error_findings:
            cards = "".join(_card(f, "warning") for f in error_findings)
            error_html = f"""
<div class="sub-heading" style="color:#f97316">Errors — Remediate Before Next Release</div>
{cards}"""

        body = f"""
<div class="section-heading">Remediation Roadmap</div>
<div class="info-box">
  This section lists only <strong>critical</strong> and <strong>error</strong>-severity findings
  that require the most urgent attention. Address critical issues immediately.
</div>
{critical_html}
{error_html}"""

        return self._wrap_content_page("Remediation Roadmap", body)

    # ── Certificate page ──────────────────────────────────────────────────────

    def _certificate_page(self, cert: "object") -> str:
        from .models import Certification

        if not isinstance(cert, Certification):
            return ""

        rpt = self._result.compliance_reports.get(cert.standard)
        score = rpt.score if rpt else 100.0

        return f"""
<div class="page cert-page">
  <div class="cert-box">
    <div class="cert-corner tl"></div>
    <div class="cert-corner tr"></div>
    <div class="cert-corner bl"></div>
    <div class="cert-corner br"></div>

    <div style="margin-bottom:10px">{_LOGO_SVG}</div>
    <div class="cert-issued">This certifies that</div>
    <div class="cert-org">{html_lib.escape(self._cfg.organization_name)}</div>
    <div class="cert-subtitle">has demonstrated compliance with</div>
    <div class="cert-standard">{html_lib.escape(cert.standard)}</div>
    <div class="cert-score-badge">Score: {score:.0f}/100</div>
    <div class="cert-detail">
      Issued by: {html_lib.escape(cert.issuer)}<br/>
      Issue Date: {cert.issued_date.strftime('%B %d, %Y')}<br/>
      Valid Until: {cert.valid_until.strftime('%B %d, %Y')}<br/>
      Project: {html_lib.escape(self._cfg.project_name)}
    </div>
    <div class="cert-id">Certificate ID: {html_lib.escape(cert.certificate_id)}</div>
  </div>
</div>"""

    # ── Metadata page ─────────────────────────────────────────────────────────

    def _metadata_page(self) -> str:
        cfg = self._cfg
        result = self._result

        rows: list[tuple[str, str]] = [
            ("Report Title", self._title),
            ("Organization", cfg.organization_name),
            ("Project", cfg.project_name),
            ("Classification", cfg.classification),
            ("Report Version", cfg.version),
            ("Generated", self._now.strftime("%Y-%m-%d %H:%M UTC")),
            ("Files Scanned", str(result.files_checked)),
            ("Rules Applied", str(result.rules_applied)),
            ("Compliance Score", f"{result.compliance_score:.1f}/100"),
            ("Standards Audited", ", ".join(result.compliance_reports.keys()) or "—"),
            ("Certifications Issued", str(len(result.certifications))),
        ]
        if cfg.contact_name:
            rows.append(("Contact", cfg.contact_name))
        if cfg.contact_email:
            rows.append(("Contact Email", cfg.contact_email))
        if cfg.department:
            rows.append(("Department", cfg.department))
        if cfg.prepared_by:
            rows.append(("Prepared By", cfg.prepared_by))
        if cfg.audit_period:
            rows.append(("Audit Period", cfg.audit_period))

        rows_html = "".join(
            f"<tr><td>{html_lib.escape(k)}</td><td>{html_lib.escape(v)}</td></tr>"
            for k, v in rows
        )

        footer_extra = ""
        if cfg.custom_footer:
            footer_extra = f'<div class="info-box mt-14">{html_lib.escape(cfg.custom_footer)}</div>'

        body = f"""
<div class="section-heading">Report Metadata</div>
<table class="meta-table">
  <tbody>{rows_html}</tbody>
</table>
{footer_extra}
<div class="info-box mt-14" style="font-size:11px;color:{_BRAND_MUTED}">
  <strong>Disclaimer:</strong> This report was generated automatically by Code Scalpel
  using static analysis. It reflects the state of the codebase at the time of the scan
  and does not constitute a formal legal compliance certification. Consult qualified
  compliance professionals for regulatory guidance.
</div>"""

        return self._wrap_content_page("Report Metadata", body)

    # ── Shared page chrome ────────────────────────────────────────────────────

    def _wrap_content_page(self, section_title: str, body_html: str) -> str:
        cfg = self._cfg

        footer_text = (
            f"{html_lib.escape(cfg.organization_name)} &nbsp;·&nbsp; "
            f"{html_lib.escape(self._title)} &nbsp;·&nbsp; "
            f"{html_lib.escape(cfg.classification)}"
        )
        if cfg.custom_footer:
            footer_text += f" &nbsp;·&nbsp; {html_lib.escape(cfg.custom_footer)}"

        return f"""
<div class="page">
  <div class="clf-banner">{html_lib.escape(cfg.classification)}</div>
  <div class="page-header">
    <div class="brand">
      {_LOGO_SVG}
      Code Scalpel
    </div>
    <div class="doc-title">{html_lib.escape(section_title)} — {html_lib.escape(cfg.project_name)}</div>
  </div>
  <div class="page-body">
    {body_html}
  </div>
  <div class="page-footer">
    <span>{footer_text}</span>
    <span>Generated {self._now.strftime('%Y-%m-%d')}</span>
  </div>
</div>"""
