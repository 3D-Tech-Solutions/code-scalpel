"""Audit log compatibility shim for governance module.

[20251222_BUGFIX] Some tests and legacy imports expect AuditLog to be available
as code_scalpel.governance.audit_log.AuditLog. The implementation lives in
code_scalpel.policy_engine.audit_log.
"""

from code_scalpel.policy_engine.audit_log import AuditLog

__all__ = ["AuditLog"]
