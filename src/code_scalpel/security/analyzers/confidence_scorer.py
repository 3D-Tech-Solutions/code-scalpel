"""
Confidence Scorer - Pro Tier Feature.

[20251226_FEATURE] v3.2.9 - Pro tier confidence scoring for vulnerabilities.

This module assigns confidence scores to detected vulnerabilities based on:
- Data flow analysis depth
- Source/sink confidence
- Sanitizer presence
- Control flow complexity
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ConfidenceScorer:
    """
    Scores vulnerability confidence based on analysis quality.

    Pro tier feature that provides confidence metrics for security findings.
    """

    def __init__(self):
        """Initialize the confidence scorer."""
        pass

    def score_vulnerability(
        self,
        vuln_type: str,
        has_taint_flow: bool,
        taint_path_length: int = 0,
        has_sanitizer: bool = False,
        control_flow_complexity: int = 1,
    ) -> float:
        """
        Calculate confidence score for a vulnerability.

        Args:
            vuln_type: Type of vulnerability (SQL Injection, XSS, etc.)
            has_taint_flow: Whether taint flow analysis was performed
            taint_path_length: Number of steps in taint flow (0 = direct)
            has_sanitizer: Whether a sanitizer was detected
            control_flow_complexity: Cyclomatic complexity of the path

        Returns:
            Confidence score 0.0-1.0
        """
        base_confidence = self._get_base_confidence(vuln_type)

        # Adjust for data flow analysis
        if has_taint_flow:
            # Direct taint flow = higher confidence
            if taint_path_length == 0:
                base_confidence *= 1.1
            elif taint_path_length <= 3:
                base_confidence *= 1.0
            else:
                # Long taint paths reduce confidence
                base_confidence *= max(0.7, 1.0 - (taint_path_length * 0.05))

        # Sanitizer presence reduces confidence
        if has_sanitizer:
            base_confidence *= 0.5

        # Complex control flow reduces confidence
        if control_flow_complexity > 5:
            base_confidence *= 0.9

        # Clamp to 0.0-1.0
        return min(1.0, max(0.0, base_confidence))

    def _get_base_confidence(self, vuln_type: str) -> float:
        """Get base confidence for vulnerability type."""
        # Different vulnerability types have different detection reliability
        base_scores = {
            "SQL Injection": 0.9,  # High confidence - well-defined patterns
            "NoSQL Injection": 0.85,
            "Command Injection": 0.9,
            "Path Traversal": 0.85,
            "XSS": 0.8,  # Medium-high - many sanitizer options
            "XXE": 0.95,  # Very high - clear XML parsing patterns
            "SSTI": 0.85,
            "LDAP Injection": 0.8,
            "Hardcoded Secret": 0.95,  # Very high - clear patterns
            "Weak Cryptography": 0.9,
            "Code Injection": 0.85,
        }
        return base_scores.get(vuln_type, 0.7)  # Default 0.7

    def score_all_vulnerabilities(
        self,
        vulnerabilities: list[dict[str, Any]],
        taint_flows: list[dict[str, Any]],
        sanitizers: list[Any],
    ) -> dict[str, float]:
        """
        Score all detected vulnerabilities.

        Args:
            vulnerabilities: List of vulnerability dicts
            taint_flows: List of taint flow paths
            sanitizers: List of detected sanitizers

        Returns:
            Dict mapping vulnerability ID/line to confidence score
        """
        scores = {}

        for vuln in vulnerabilities:
            vuln_type = vuln.get("type", "Unknown")
            vuln_line = vuln.get("line", 0)
            vuln_id = f"{vuln_type}_{vuln_line}"

            # Check if this vulnerability has taint flow
            has_taint_flow = False
            taint_path_length = 0
            for flow in taint_flows:
                # Check if this taint flow ends at the vulnerability line
                if isinstance(flow, dict):
                    sink_line = flow.get("sink_line", 0)
                    if abs(sink_line - vuln_line) <= 2:  # Within 2 lines
                        has_taint_flow = True
                        taint_path_length = len(flow.get("path", []))
                        break

            # Check if there's a sanitizer near this vulnerability
            has_sanitizer = False
            for sanitizer in sanitizers:
                if hasattr(sanitizer, "line"):
                    if abs(sanitizer.line - vuln_line) <= 5:  # Within 5 lines
                        has_sanitizer = True
                        break

            # Calculate score
            score = self.score_vulnerability(
                vuln_type=vuln_type,
                has_taint_flow=has_taint_flow,
                taint_path_length=taint_path_length,
                has_sanitizer=has_sanitizer,
                control_flow_complexity=1,  # Could be enhanced with CFG analysis
            )

            scores[vuln_id] = score

        return scores

    def categorize_confidence(self, score: float) -> str:
        """
        Categorize confidence score into human-readable level.

        Args:
            score: Confidence score 0.0-1.0

        Returns:
            "high", "medium", or "low"
        """
        if score >= 0.8:
            return "high"
        elif score >= 0.6:
            return "medium"
        else:
            return "low"

    def generate_confidence_report(
        self, vulnerabilities: list[dict[str, Any]], scores: dict[str, float]
    ) -> dict[str, Any]:
        """
        Generate a comprehensive confidence report.

        Args:
            vulnerabilities: List of vulnerabilities
            scores: Confidence scores by vulnerability ID

        Returns:
            Report dict with statistics and breakdown
        """
        if not vulnerabilities or not scores:
            return {
                "average_confidence": 0.0,
                "high_confidence_count": 0,
                "medium_confidence_count": 0,
                "low_confidence_count": 0,
                "total_scored": 0,
            }

        high_count = sum(1 for s in scores.values() if s >= 0.8)
        medium_count = sum(1 for s in scores.values() if 0.6 <= s < 0.8)
        low_count = sum(1 for s in scores.values() if s < 0.6)

        avg_confidence = sum(scores.values()) / len(scores) if scores else 0.0

        return {
            "average_confidence": round(avg_confidence, 2),
            "high_confidence_count": high_count,
            "medium_confidence_count": medium_count,
            "low_confidence_count": low_count,
            "total_scored": len(scores),
            "details": f"{high_count} high, {medium_count} medium, {low_count} low confidence findings",
        }
