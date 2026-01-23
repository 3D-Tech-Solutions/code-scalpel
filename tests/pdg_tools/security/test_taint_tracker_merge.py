# [20260119_TEST] Regression tests for taint tracker merge semantics and sink naming.
from __future__ import annotations

from code_scalpel.security.analyzers.taint_tracker import (
    SecuritySink,
    TaintInfo,
    TaintLevel,
    TaintSource,
    TaintTracker,
    Vulnerability,
)


def test_merge_preserves_cleared_sinks_intersection():
    """Merged taint should keep only sinks cleared by all contributors."""
    tracker = TaintTracker()

    left = TaintInfo(
        source=TaintSource.USER_INPUT,
        level=TaintLevel.HIGH,
        source_location=(1, 0),
        propagation_path=["a"],
        sanitizers_applied={"int"},
        sanitizer_history=["int"],
        cleared_sinks={SecuritySink.SQL_QUERY},
    )
    right = TaintInfo(
        source=TaintSource.USER_INPUT,
        level=TaintLevel.HIGH,
        source_location=(2, 0),
        propagation_path=["b"],
        sanitizers_applied={"int", "shlex.quote"},
        sanitizer_history=["int", "shlex.quote"],
        cleared_sinks={SecuritySink.SQL_QUERY, SecuritySink.SHELL_COMMAND},
    )

    tracker.mark_tainted("a", left)
    tracker.mark_tainted("b", right)
    merged = tracker.propagate_assignment("c", ["a", "b"])

    assert merged is not None
    assert SecuritySink.SQL_QUERY in merged.cleared_sinks
    assert SecuritySink.SHELL_COMMAND not in merged.cleared_sinks
    assert "int" in merged.sanitizer_history


def test_vulnerability_type_labels_new_sinks():
    """New sink types should report descriptive vulnerability names."""
    ldap_vuln = Vulnerability(
        sink_type=SecuritySink.LDAP_INJECTION,
        taint_source=TaintSource.USER_INPUT,
        taint_path=["u"],
    )
    html_vuln = Vulnerability(
        sink_type=SecuritySink.HTML_INJECTION,
        taint_source=TaintSource.USER_INPUT,
        taint_path=["body"],
    )

    assert "LDAP" in ldap_vuln.vulnerability_type
    assert "HTML" in html_vuln.vulnerability_type
