"""
Compliance Mapper - Enterprise Tier Feature.

[20251226_FEATURE] v3.2.9 - Enterprise tier compliance mapping.

This module maps security vulnerabilities to compliance frameworks:
- OWASP Top 10 (2021)
- CWE (Common Weakness Enumeration)
- PCI DSS
- HIPAA
- GDPR
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ComplianceMapper:
    """
    Maps vulnerabilities to compliance frameworks.

    Enterprise tier feature for regulatory compliance tracking.
    """

    # OWASP Top 10 2021 mapping
    OWASP_TOP_10_2021 = {
        "A01:2021": {
            "name": "Broken Access Control",
            "vulnerabilities": ["Path Traversal", "Insecure Direct Object Reference"],
        },
        "A02:2021": {
            "name": "Cryptographic Failures",
            "vulnerabilities": [
                "Weak Cryptography",
                "Hardcoded Secret",
                "Insecure Random",
            ],
        },
        "A03:2021": {
            "name": "Injection",
            "vulnerabilities": [
                "SQL Injection",
                "NoSQL Injection",
                "Command Injection",
                "LDAP Injection",
                "XSS",
                "XXE",
                "SSTI",
                "Code Injection",
            ],
        },
        "A04:2021": {
            "name": "Insecure Design",
            "vulnerabilities": [],  # Architectural issues
        },
        "A05:2021": {
            "name": "Security Misconfiguration",
            "vulnerabilities": ["Weak Cryptography", "Insecure Random"],
        },
        "A06:2021": {
            "name": "Vulnerable and Outdated Components",
            "vulnerabilities": [],  # Handled by scan_dependencies
        },
        "A07:2021": {
            "name": "Identification and Authentication Failures",
            "vulnerabilities": ["Hardcoded Secret", "Weak Cryptography"],
        },
        "A08:2021": {
            "name": "Software and Data Integrity Failures",
            "vulnerabilities": ["Code Injection"],
        },
        "A09:2021": {
            "name": "Security Logging and Monitoring Failures",
            "vulnerabilities": ["Sensitive Data Logging"],
        },
        "A10:2021": {
            "name": "Server-Side Request Forgery (SSRF)",
            "vulnerabilities": [],  # Not yet detected
        },
    }

    # CWE mapping
    CWE_MAPPING = {
        "SQL Injection": "CWE-89",
        "NoSQL Injection": "CWE-943",
        "Command Injection": "CWE-78",
        "Path Traversal": "CWE-22",
        "XSS": "CWE-79",
        "XXE": "CWE-611",
        "SSTI": "CWE-1336",
        "LDAP Injection": "CWE-90",
        "Code Injection": "CWE-94",
        "Hardcoded Secret": "CWE-798",
        "Weak Cryptography": "CWE-327",
        "Insecure Random": "CWE-338",
        "Sensitive Data Logging": "CWE-532",
    }

    # PCI DSS requirements
    PCI_DSS_MAPPING = {
        "Hardcoded Secret": ["Req 8.2", "Req 8.3"],  # Authentication
        "Weak Cryptography": ["Req 4.1", "Req 6.5.3"],  # Cryptography
        "SQL Injection": ["Req 6.5.1"],  # Injection flaws
        "XSS": ["Req 6.5.7"],  # Cross-site scripting
        "Path Traversal": ["Req 6.5.8"],  # Improper access control
        "Sensitive Data Logging": ["Req 3.2", "Req 3.4"],  # Cardholder data
    }

    # HIPAA mapping
    HIPAA_MAPPING = {
        "Hardcoded Secret": ["164.312(a)(2)(i)"],  # Unique User Identification
        "Weak Cryptography": ["164.312(a)(2)(iv)", "164.312(e)(2)(ii)"],  # Encryption
        "Sensitive Data Logging": ["164.308(a)(3)(i)"],  # Workforce Security
        "SQL Injection": ["164.312(a)(1)"],  # Access Control
    }

    # GDPR Articles
    GDPR_MAPPING = {
        "Hardcoded Secret": ["Article 32"],  # Security of processing
        "Weak Cryptography": ["Article 32"],  # Security of processing
        "Sensitive Data Logging": ["Article 32"],  # Security of processing
        "SQL Injection": ["Article 32"],  # Security of processing
        "XSS": ["Article 32"],  # Security of processing
    }

    def __init__(self):
        """Initialize the compliance mapper."""
        pass

    def map_to_owasp_top_10(self, vulnerability_type: str) -> list[str]:
        """
        Map vulnerability to OWASP Top 10 categories.

        Args:
            vulnerability_type: Type of vulnerability

        Returns:
            List of OWASP Top 10 IDs (e.g., ["A03:2021"])
        """
        matches = []

        for owasp_id, data in self.OWASP_TOP_10_2021.items():
            if vulnerability_type in data["vulnerabilities"]:
                matches.append(owasp_id)

        return matches

    def map_to_cwe(self, vulnerability_type: str) -> str | None:
        """
        Map vulnerability to CWE ID.

        Args:
            vulnerability_type: Type of vulnerability

        Returns:
            CWE ID string (e.g., "CWE-89") or None
        """
        return self.CWE_MAPPING.get(vulnerability_type)

    def map_to_pci_dss(self, vulnerability_type: str) -> list[str]:
        """
        Map vulnerability to PCI DSS requirements.

        Args:
            vulnerability_type: Type of vulnerability

        Returns:
            List of PCI DSS requirement IDs
        """
        return self.PCI_DSS_MAPPING.get(vulnerability_type, [])

    def map_to_hipaa(self, vulnerability_type: str) -> list[str]:
        """
        Map vulnerability to HIPAA standards.

        Args:
            vulnerability_type: Type of vulnerability

        Returns:
            List of HIPAA standard references
        """
        return self.HIPAA_MAPPING.get(vulnerability_type, [])

    def map_to_gdpr(self, vulnerability_type: str) -> list[str]:
        """
        Map vulnerability to GDPR articles.

        Args:
            vulnerability_type: Type of vulnerability

        Returns:
            List of GDPR article references
        """
        return self.GDPR_MAPPING.get(vulnerability_type, [])

    def map_all_vulnerabilities(self, vulnerabilities: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Map all vulnerabilities to compliance frameworks.

        Args:
            vulnerabilities: List of vulnerability dicts

        Returns:
            Comprehensive compliance mapping
        """
        owasp_counts = {}
        cwe_list = []
        pci_dss_reqs = set()
        hipaa_refs = set()
        gdpr_articles = set()

        for vuln in vulnerabilities:
            vuln_type = vuln.get("type", "Unknown")

            # OWASP Top 10
            owasp_ids = self.map_to_owasp_top_10(vuln_type)
            for owasp_id in owasp_ids:
                owasp_counts[owasp_id] = owasp_counts.get(owasp_id, 0) + 1

            # CWE
            cwe = self.map_to_cwe(vuln_type)
            if cwe:
                cwe_list.append({"vulnerability": vuln_type, "cwe": cwe})

            # PCI DSS
            pci_reqs = self.map_to_pci_dss(vuln_type)
            pci_dss_reqs.update(pci_reqs)

            # HIPAA
            hipaa = self.map_to_hipaa(vuln_type)
            hipaa_refs.update(hipaa)

            # GDPR
            gdpr = self.map_to_gdpr(vuln_type)
            gdpr_articles.update(gdpr)

        return {
            "OWASP_TOP_10": dict(owasp_counts),
            "CWE": cwe_list,
            "PCI_DSS": sorted(list(pci_dss_reqs)),
            "HIPAA": sorted(list(hipaa_refs)),
            "GDPR": sorted(list(gdpr_articles)),
            "total_vulnerabilities": len(vulnerabilities),
        }

    def generate_compliance_report(self, mapping: dict[str, Any]) -> str:
        """
        Generate a human-readable compliance report.

        Args:
            mapping: Result from map_all_vulnerabilities

        Returns:
            Formatted compliance report
        """
        report_parts = ["Compliance Framework Mapping Report", "=" * 50]

        # OWASP Top 10
        owasp = mapping.get("OWASP_TOP_10", {})
        if owasp:
            report_parts.append("\nOWASP Top 10 2021:")
            for owasp_id, count in sorted(owasp.items()):
                category_name = self.OWASP_TOP_10_2021[owasp_id]["name"]
                report_parts.append(f"  {owasp_id} - {category_name}: {count} finding(s)")

        # PCI DSS
        pci = mapping.get("PCI_DSS", [])
        if pci:
            report_parts.append(f"\nPCI DSS Requirements: {', '.join(pci)}")

        # HIPAA
        hipaa = mapping.get("HIPAA", [])
        if hipaa:
            report_parts.append(f"\nHIPAA Standards: {', '.join(hipaa)}")

        # GDPR
        gdpr = mapping.get("GDPR", [])
        if gdpr:
            report_parts.append(f"\nGDPR Articles: {', '.join(gdpr)}")

        report_parts.append(f"\nTotal Vulnerabilities: {mapping.get('total_vulnerabilities', 0)}")

        return "\n".join(report_parts)
