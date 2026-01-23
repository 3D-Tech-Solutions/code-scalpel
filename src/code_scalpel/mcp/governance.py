"""Governance helpers for MCP tool enforcement."""

from __future__ import annotations

import json
import os
import time
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from code_scalpel.mcp.contract import ToolError

# [20251231_FEATURE] Tier-aware invisible governance at MCP boundary.
# Tiers are controlled by Authentication/Licensing; governance must use the
# license-derived tier from `_get_current_tier()` and apply enforcement posture.
_GOVERNANCE_FEATURE_POLICY_INTEGRITY = "policy_integrity"
_GOVERNANCE_FEATURE_RESPONSE_CONFIG = "response_config"
_GOVERNANCE_FEATURE_LIMITS = "limits"
_GOVERNANCE_FEATURE_BUDGET = "budget"
_GOVERNANCE_FEATURE_DEV_GOVERNANCE = "dev_governance"
_GOVERNANCE_FEATURE_PROJECT_STRUCTURE = "project_structure"
_GOVERNANCE_FEATURE_POLICY_EVALUATION = "policy_evaluation"


# [20260119_BUGFIX] Provide auto-init scaffold for .code-scalpel/ when requested.
def auto_init_config_dir(
    *,
    project_root: Path,
    tier: str,
    mode: str = "templates_only",
    target: str = "project",
) -> dict[str, Any] | None:
    """Create .code-scalpel scaffolding if missing.

    Args:
        project_root: Root directory for project-level initialization
        tier: License tier (community, pro, enterprise)
        mode: Initialization mode:
            - "templates_only": Minimal scaffolding (directory only for server startup)
            - "full": Complete CLI-style init with templates, manifest, and .env
        target: Where to create config:
            - "project": In project_root/.code-scalpel/
            - "user": In XDG_CONFIG_HOME/code-scalpel/.code-scalpel/

    Returns:
        Dictionary with initialization results, or None on failure
    """
    from code_scalpel.mcp.paths import scalpel_home_dir

    try:
        if target not in {"project", "user"}:
            target = "project"

        if target == "project":
            base_dir = Path(project_root).resolve()
        else:
            # User target: use XDG_CONFIG_HOME/code-scalpel as base
            xdg_base = scalpel_home_dir()
            base_dir = xdg_base / "code-scalpel"
            base_dir.mkdir(parents=True, exist_ok=True)

        config_dir = base_dir / ".code-scalpel"

        # Check if already exists
        if config_dir.exists():
            return {
                "created": False,
                "path": str(config_dir),
                "mode": mode,
                "tier": tier,
                "target": target,
            }

        # For full mode, delegate to the complete init_config_dir
        if mode == "full":
            from code_scalpel.config.init_config import init_config_dir

            result = init_config_dir(target_dir=str(base_dir), mode="full")
            if result.get("success"):
                return {
                    "created": True,
                    "path": result.get("path", str(config_dir)),
                    "mode": mode,
                    "tier": tier,
                    "target": target,
                    "files_created": result.get("files_created", []),
                }
            # Fall through to minimal init if full init fails
            pass

        # Minimal scaffolding (templates_only mode or fallback)
        config_dir.mkdir(parents=True, exist_ok=True)

        return {
            "created": True,
            "path": str(config_dir),
            "mode": mode,
            "tier": tier,
            "target": target,
        }
    except Exception:
        # Best-effort: do not block server startup if initialization fails.
        return None


# [20251230_FEATURE] Invisible governance enforcement.
# Once an organization defines `.code-scalpel` rulesets, the MCP server should
# enforce them automatically without requiring users to remember to run a tool.
_GOVERNANCE_VERIFY_CACHE: dict[str, Any] = {}


def _emit_governance_audit_event(policy_dir: Path, event: dict[str, Any]) -> None:
    """Emit a structured audit event.

    Events are appended to `.code-scalpel/audit.jsonl`.

    [20251231_FEATURE] Audit logging for governance preflight decisions.
    """
    # Default: on when governance is active; can be disabled.
    if not _parse_bool_env("SCALPEL_GOVERNANCE_AUDIT", default=True):
        return

    try:
        audit_path = policy_dir / "audit.jsonl"
        payload = dict(event)
        payload.setdefault("ts", time.time())
        payload.setdefault("iso_utc", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        with audit_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            f.write("\n")
    except Exception:
        # Best-effort only: governance enforcement must not fail due to audit IO.
        return


def _parse_bool_env(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    v = val.strip().lower()
    if v in {"1", "true", "yes", "on"}:
        return True
    if v in {"0", "false", "no", "off"}:
        return False
    return default


def _get_governance_enforcement(tier: str) -> str:
    """Resolve enforcement posture.

    Supports:
    - SCALPEL_GOVERNANCE_ENFORCEMENT=off|warn|block
    - Legacy SCALPEL_GOVERNANCE_MODE=enforce|warn|off

    Note: For Pro/Enterprise, WARN requires explicit break-glass.
    """

    # Prefer the explicit new name.
    raw = os.environ.get("SCALPEL_GOVERNANCE_ENFORCEMENT")
    if raw is None:
        legacy = os.environ.get("SCALPEL_GOVERNANCE_MODE")
        if legacy is not None:
            legacy_norm = legacy.strip().lower()
            if legacy_norm in {"enforce", "block"}:
                raw = "block"
            elif legacy_norm == "warn":
                raw = "warn"
            else:
                raw = "off"

    enforcement = (raw or "off").strip().lower()
    if enforcement not in {"off", "warn", "block"}:
        enforcement = "off"

    # [20251231_FEATURE] Pro/Enterprise must remain fail-closed unless
    # break-glass is explicitly enabled.
    if enforcement == "warn" and tier in {"pro", "enterprise"}:
        if not _parse_bool_env("SCALPEL_GOVERNANCE_BREAK_GLASS", default=False):
            return "block"

    return enforcement


def _default_governance_features_for_tier(tier: str) -> set[str]:
    if tier == "community":
        return {_GOVERNANCE_FEATURE_RESPONSE_CONFIG, _GOVERNANCE_FEATURE_LIMITS}
    return {
        _GOVERNANCE_FEATURE_POLICY_INTEGRITY,
        _GOVERNANCE_FEATURE_RESPONSE_CONFIG,
        _GOVERNANCE_FEATURE_LIMITS,
        # [20251231_FEATURE] Pro/Enterprise: enforce write budgets when enabled.
        _GOVERNANCE_FEATURE_BUDGET,
    }


def _is_budgeted_write_tool(tool_id: str) -> bool:
    # [20251231_FEATURE] Budget enforcement is applied only to tools that can
    # mutate the filesystem.
    return tool_id in {"update_symbol", "rename_symbol"}


def _diff_added_removed_lines(old_code: str, new_code: str) -> tuple[list[str], list[str]]:
    """Compute added/removed lines for budget accounting.

    [20251231_FEATURE] Used by governance budget preflight.
    """
    import difflib

    added: list[str] = []
    removed: list[str] = []
    for line in difflib.ndiff(old_code.splitlines(), new_code.splitlines()):
        if line.startswith("+ "):
            added.append(line[2:])
        elif line.startswith("- "):
            removed.append(line[2:])
    return added, removed


def _evaluate_change_budget_for_write_tool(
    *,
    tool_id: str,
    tier: str,
    arguments: dict[str, Any],
    policy_dir: Path,
) -> tuple[bool, dict[str, Any] | None]:
    """Evaluate change budgets for write tools without mutating the filesystem.

    Returns:
        (allowed, details)
    """
    try:
        from code_scalpel.governance.change_budget import (
            ChangeBudget,
            FileChange,
            Operation,
            load_budget_config,
        )
        from code_scalpel.mcp.path_resolver import resolve_path
        from code_scalpel.surgery.surgical_patcher import UnifiedPatcher
    except Exception as e:
        return True, {"skipped": True, "reason": f"Budget preflight unavailable: {e}"}

    def _simulate_cross_file_rename(
        *,
        project_root: Path,
        target_file: Path,
        target_type: str,
        target_name: str,
        new_name: str,
        max_files_searched: int | None,
        max_files_updated: int | None,
    ) -> list[tuple[Path, str, str]]:
        """Simulate cross-file rename edits without writing.

        [20251231_FEATURE] Budget preflight accounts for cross-file edits.
        """
        try:
            from code_scalpel.surgery.rename_symbol_refactor import (
                _apply_token_replacements,
                _collect_reference_edits,
                _read_text,
                _tokenize,
                iter_python_files,
                module_name_for_file,
            )
        except Exception:
            return []

        target_module = module_name_for_file(project_root, target_file)
        if not target_module:
            return []

        updates: list[tuple[Path, str, str]] = []
        updated = 0
        for py_file in iter_python_files(project_root, max_files=max_files_searched):
            if py_file.resolve() == target_file.resolve():
                continue

            try:
                code = _read_text(py_file)
            except Exception:
                continue

            edits = _collect_reference_edits(
                code,
                target_module=target_module,
                target_type=target_type,
                target_name=target_name,
                new_name=new_name,
            )
            if not getattr(edits, "token_replacements", None):
                continue

            new_code = _apply_token_replacements(_tokenize(code), edits.token_replacements)
            if new_code == code:
                continue

            if max_files_updated is not None and updated >= max_files_updated:
                break

            updates.append((py_file, code, new_code))
            updated += 1

        return updates

    raw_file_path = str(arguments.get("file_path") or "")
    if not raw_file_path:
        # Tool will fail input validation anyway.
        return True, {"skipped": True, "reason": "Missing file_path"}

    server = import_module("code_scalpel.mcp.server")

    try:
        resolved = resolve_path(raw_file_path, str(server.PROJECT_ROOT))
        resolved_path = Path(resolved)
    except Exception as e:
        # Tool will likely fail later; do not block here.
        return True, {"skipped": True, "reason": f"Path resolve failed: {e}"}

    budget_config = load_budget_config(str(policy_dir / "agent_limits.yaml"))
    default_budget = budget_config if isinstance(budget_config, dict) else {}
    budget = ChangeBudget(default_budget)

    try:
        # [20260103_BUGFIX] Use UnifiedPatcher for automatic language detection
        patcher = UnifiedPatcher.from_file(str(resolved_path))
    except Exception as e:
        return True, {"skipped": True, "reason": f"Cannot load file for budget: {e}"}

    original_source = patcher.original_code

    changes: list[FileChange] = []

    try:
        if tool_id == "rename_symbol":
            target_type = str(arguments.get("target_type") or "")
            target_name = str(arguments.get("target_name") or "")
            new_name = str(arguments.get("new_name") or "")
            if not (target_type and target_name and new_name):
                return True, {"skipped": True, "reason": "Missing rename arguments"}
            patch_result = patcher.rename_symbol(target_type, target_name, new_name)

        elif tool_id == "update_symbol":
            target_type = str(arguments.get("target_type") or "")
            target_name = str(arguments.get("target_name") or "")
            op = str(arguments.get("operation") or "replace").strip().lower()
            if op == "rename":
                new_name = str(arguments.get("new_name") or "")
                if not (target_type and target_name and new_name):
                    return True, {"skipped": True, "reason": "Missing rename arguments"}
                patch_result = patcher.rename_symbol(target_type, target_name, new_name)
            else:
                new_code = arguments.get("new_code")
                if not (target_type and target_name and new_code):
                    return True, {
                        "skipped": True,
                        "reason": "Missing replace arguments",
                    }

                if target_type == "function":
                    patch_result = patcher.update_function(target_name, str(new_code))
                    if not patch_result.success and "not found" in (patch_result.error or "").lower():
                        insert_fn = getattr(patcher, "insert_function", None)
                        if callable(insert_fn):
                            patch_result = insert_fn(str(new_code))
                elif target_type == "class":
                    patch_result = patcher.update_class(target_name, str(new_code))
                    if not patch_result.success and "not found" in (patch_result.error or "").lower():
                        insert_cls = getattr(patcher, "insert_class", None)
                        if callable(insert_cls):
                            patch_result = insert_cls(str(new_code))
                elif target_type == "method":
                    if "." not in target_name:
                        return True, {
                            "skipped": True,
                            "reason": "Invalid method target_name",
                        }
                    class_name, method_name = target_name.rsplit(".", 1)
                    patch_result = patcher.update_method(class_name, method_name, str(new_code))
                    if (
                        not patch_result.success
                        and "not found" in (patch_result.error or "").lower()
                        and "class" not in (patch_result.error or "").lower()
                    ):
                        insert_method = getattr(patcher, "insert_method", None)
                        if callable(insert_method):
                            patch_result = insert_method(class_name, str(new_code))
                else:
                    return True, {
                        "skipped": True,
                        "reason": f"Unknown target_type: {target_type}",
                    }
        else:
            return True, {"skipped": True, "reason": "Not a budgeted write tool"}
    except Exception as e:
        return True, {"skipped": True, "reason": f"Patch simulation failed: {e}"}

    if not getattr(patch_result, "success", False):
        # Don't block on budget when the tool itself would fail.
        return True, {"skipped": True, "reason": "Patch simulation did not succeed"}

    new_source = patcher.current_code
    added, removed = _diff_added_removed_lines(original_source, new_source)
    changes.append(
        FileChange(
            file_path=str(resolved_path),
            added_lines=added,
            removed_lines=removed,
            original_code=original_source,
            modified_code=new_source,
        )
    )

    # If this is a rename operation at Pro/Enterprise, include the cross-file
    # rename edits that the tool would apply (bounded by its configured limits).
    is_rename_op = tool_id == "rename_symbol" or (
        tool_id == "update_symbol" and str(arguments.get("operation") or "").strip().lower() == "rename"
    )
    if is_rename_op and tier in {"pro", "enterprise"}:
        try:
            from code_scalpel.licensing.config_loader import (
                get_cached_limits,
                get_tool_limits,
                merge_limits,
            )
            from code_scalpel.licensing.features import get_tool_capabilities

            caps = get_tool_capabilities("rename_symbol", tier)
            default_limits = (caps or {}).get("limits", {})
            config = get_cached_limits()
            overrides = get_tool_limits("rename_symbol", tier, config=config)
            limits = merge_limits(default_limits, overrides)

            max_files_searched = limits.get("max_files_searched")
            max_files_updated = limits.get("max_files_updated")

            if not ((max_files_searched == 0) and (max_files_updated == 0)):
                project_root = Path(server.PROJECT_ROOT)
                target_type = str(arguments.get("target_type") or "")
                target_name = str(arguments.get("target_name") or "")
                new_name = str(arguments.get("new_name") or "")
                for p, old, new in _simulate_cross_file_rename(
                    project_root=project_root,
                    target_file=Path(resolved_path),
                    target_type=target_type,
                    target_name=target_name,
                    new_name=new_name,
                    max_files_searched=max_files_searched,
                    max_files_updated=max_files_updated,
                ):
                    a2, r2 = _diff_added_removed_lines(old, new)
                    changes.append(
                        FileChange(
                            file_path=str(p),
                            added_lines=a2,
                            removed_lines=r2,
                            original_code=old,
                            modified_code=new,
                        )
                    )
        except Exception:
            # Best-effort only; if we can't simulate cross-file updates, budget
            # enforcement still applies to the primary file.
            pass

    op_desc = f"{tool_id}:{arguments.get('target_type')}:{arguments.get('target_name')}"
    operation_obj = Operation(changes=changes, description=op_desc)
    decision = budget.validate_operation(operation_obj)

    if getattr(decision, "allowed", True):
        return True, {"allowed": True, "reason": getattr(decision, "reason", "")}

    violations = []
    for v in getattr(decision, "violations", []) or []:
        violations.append(
            {
                "rule": getattr(v, "rule", None),
                "severity": getattr(v, "severity", None),
                "message": getattr(v, "message", None),
                "limit": getattr(v, "limit", None),
                "actual": getattr(v, "actual", None),
                "file": getattr(v, "file", None),
            }
        )

    return False, {
        "allowed": False,
        "reason": getattr(decision, "reason", "Budget constraints violated"),
        "violations": violations,
    }


def _supported_governance_features_for_tier(tier: str) -> set[str]:
    if tier == "community":
        return {_GOVERNANCE_FEATURE_RESPONSE_CONFIG, _GOVERNANCE_FEATURE_LIMITS}
    # Pro/Enterprise: feature set is broader, but some items may remain
    # tool-dependent until fully wired.
    return {
        _GOVERNANCE_FEATURE_POLICY_INTEGRITY,
        _GOVERNANCE_FEATURE_RESPONSE_CONFIG,
        _GOVERNANCE_FEATURE_LIMITS,
        _GOVERNANCE_FEATURE_BUDGET,
        _GOVERNANCE_FEATURE_DEV_GOVERNANCE,
        _GOVERNANCE_FEATURE_PROJECT_STRUCTURE,
        _GOVERNANCE_FEATURE_POLICY_EVALUATION,
    }


def _parse_governance_features_env() -> set[str] | None:
    raw = os.environ.get("SCALPEL_GOVERNANCE_FEATURES")
    if raw is None:
        return None
    parts = [p.strip().lower() for p in raw.split(",")]
    features = {p for p in parts if p}
    return features


def _compute_effective_governance_features(tier: str) -> tuple[set[str], list[str]]:
    requested = _parse_governance_features_env()
    effective = requested if requested is not None else _default_governance_features_for_tier(tier)

    supported = _supported_governance_features_for_tier(tier)
    unsupported = sorted(effective - supported)
    effective = set(effective & supported)

    enforcement = _get_governance_enforcement(tier)
    warnings: list[str] = []
    if unsupported and enforcement == "warn":
        for feat in unsupported:
            warnings.append(f"Governance WARN: feature '{feat}' is unavailable at tier '{tier}' (ignored).")

    return effective, warnings


def _policy_state_fingerprint(policy_dir: Path) -> str:
    """Create a cheap fingerprint for policy inputs to support caching."""
    try:
        # Only include files relevant to integrity verification.
        candidates: list[Path] = []
        manifest = policy_dir / "policy.manifest.json"
        if manifest.exists():
            candidates.append(manifest)

        for ext in ("*.yaml", "*.yml", "*.json"):
            candidates.extend(policy_dir.glob(ext))

        max_mtime = 0.0
        total_size = 0
        for p in candidates:
            st = p.stat()
            max_mtime = max(max_mtime, st.st_mtime)
            total_size += st.st_size

        return f"files={len(candidates)};mtime={max_mtime:.6f};size={total_size}"
    except Exception:
        # If we cannot stat, disable caching by returning a changing key.
        return f"nocache:{time.time()}"


def _governance_enforcement_for_tier(tier: str) -> str:
    """Deprecated shim: use _get_governance_enforcement().

    [20251231_REFACTOR] Consolidate enforcement resolution.
    """
    return _get_governance_enforcement(tier)


def _maybe_enforce_governance_before_tool(
    *,
    tool_id: str,
    tier: str,
    arguments: dict[str, Any] | None = None,
) -> tuple[ToolError | None, list[str]]:
    """Apply tier-aware governance preflight.

    This is invoked by the envelope wrapper before executing any tool.

    Returns:
        (error, warnings)
    """

    from code_scalpel.mcp.contract import ToolError

    # The integrity tool must remain callable for debugging.
    if tool_id == "verify_policy_integrity":
        return None, []

    enforcement = _get_governance_enforcement(tier)
    if enforcement == "off":
        return None, []

    effective_features, warnings = _compute_effective_governance_features(tier)

    # [20251231_FEATURE] Optional optimization: apply governance preflight only
    # to write-capable tools (keeps Community/Pro read tools low overhead).
    write_tools_only = _parse_bool_env("SCALPEL_GOVERNANCE_WRITE_TOOLS_ONLY", default=False)

    server = import_module("code_scalpel.mcp.server")
    policy_dir = server._resolve_policy_dir()
    if policy_dir is None:
        # If org mandates governance but no policies present, fail closed.
        required = (os.environ.get("SCALPEL_GOVERNANCE_REQUIRED") or "").strip().lower()
        if required in {"1", "true", "yes", "on"}:
            return (
                ToolError(
                    error="Governance required but no .code-scalpel directory found",
                    error_code="forbidden",
                    error_details={"expected": ".code-scalpel", "tier": tier},
                ),
                warnings,
            )
        return None, warnings

    is_write_tool = _is_budgeted_write_tool(tool_id)
    if write_tools_only and not is_write_tool:
        return None, warnings

    base_audit: dict[str, Any] = {
        # [20251231_FEATURE] Common fields for governance audit events.
        "tool_id": tool_id,
        "tier": tier,
        "enforcement": enforcement,
        "features": sorted(effective_features),
    }

    # [20251231_FEATURE] Highest-level governance: policy integrity preflight.
    if _GOVERNANCE_FEATURE_POLICY_INTEGRITY in effective_features and tier in {
        "pro",
        "enterprise",
    }:
        manifest_source = (os.environ.get("SCALPEL_POLICY_MANIFEST_SOURCE") or "file").strip().lower()
        if manifest_source not in {"file", "git", "env"}:
            manifest_source = "file"

        fingerprint = _policy_state_fingerprint(policy_dir)
        cache_key = f"tier={tier};dir={policy_dir};source={manifest_source};{fingerprint}"
        cached = _GOVERNANCE_VERIFY_CACHE.get(cache_key)
        if cached is not None:
            verified = cached
        else:
            verified = server._verify_policy_integrity_sync(
                policy_dir=str(policy_dir),
                manifest_source=manifest_source,
                tier=tier,
            )
            if len(_GOVERNANCE_VERIFY_CACHE) > 25:
                _GOVERNANCE_VERIFY_CACHE.clear()
            _GOVERNANCE_VERIFY_CACHE[cache_key] = verified

        _emit_governance_audit_event(
            policy_dir,
            {
                **base_audit,
                "check": "policy_integrity",
                "manifest_source": manifest_source,
                "cached": cached is not None,
                "verified": bool(getattr(verified, "success", False)),
            },
        )

        if not getattr(verified, "success", False):
            err = getattr(verified, "error", None) or "Policy integrity verification failed"
            if enforcement == "warn":
                warnings.append("Governance WARN: policy integrity check failed; proceeding due to break-glass.")
                _emit_governance_audit_event(
                    policy_dir,
                    {
                        **base_audit,
                        "check": "policy_integrity",
                        "decision": "allow_warn",
                        "reason": str(err),
                    },
                )
                return None, warnings

            _emit_governance_audit_event(
                policy_dir,
                {
                    **base_audit,
                    "check": "policy_integrity",
                    "decision": "deny",
                    "reason": str(err),
                },
            )

            return (
                ToolError(
                    error=f"Governance policy integrity check failed: {err}",
                    error_code="forbidden",
                    error_details={
                        "policy_dir": str(policy_dir),
                        "manifest_source": manifest_source,
                        "tier": tier,
                    },
                ),
                warnings,
            )

    # [20251231_FEATURE] Change budget enforcement for write tools.
    if (
        _GOVERNANCE_FEATURE_BUDGET in effective_features
        and tier in {"pro", "enterprise"}
        and arguments is not None
        and _is_budgeted_write_tool(tool_id)
    ):
        allowed, details = _evaluate_change_budget_for_write_tool(
            tool_id=tool_id,
            tier=tier,
            arguments=arguments,
            policy_dir=policy_dir,
        )
        if not allowed:
            if enforcement == "warn":
                warnings.append("Governance WARN: change budget exceeded; proceeding due to break-glass.")
                _emit_governance_audit_event(
                    policy_dir,
                    {
                        **base_audit,
                        "check": "budget",
                        "decision": "allow_warn",
                        "details": details or {},
                    },
                )
                return None, warnings

            _emit_governance_audit_event(
                policy_dir,
                {
                    **base_audit,
                    "check": "budget",
                    "decision": "deny",
                    "details": details or {},
                },
            )
            return (
                ToolError(
                    error="Governance blocked tool execution (change budget exceeded).",
                    error_code="forbidden",
                    error_details=details or {"tier": tier, "tool_id": tool_id},
                ),
                warnings,
            )

        _emit_governance_audit_event(
            policy_dir,
            {
                **base_audit,
                "check": "budget",
                "decision": "allow",
                "details": details or {},
            },
        )

    # [20251231_FEATURE] Policy evaluation preflight for write tools.
    if (
        _GOVERNANCE_FEATURE_POLICY_EVALUATION in effective_features
        and tier in {"pro", "enterprise"}
        and arguments is not None
        and _is_budgeted_write_tool(tool_id)
    ):
        policy_path = policy_dir / "policy.yaml"
        if not policy_path.exists():
            if enforcement == "warn":
                warnings.append(
                    "Governance WARN: policy.yaml missing for policy evaluation; proceeding due to break-glass."
                )
                _emit_governance_audit_event(
                    policy_dir,
                    {
                        **base_audit,
                        "check": "policy_evaluation",
                        "decision": "allow_warn",
                        "reason": f"missing policy.yaml at {policy_path}",
                    },
                )
                return None, warnings

            _emit_governance_audit_event(
                policy_dir,
                {
                    **base_audit,
                    "check": "policy_evaluation",
                    "decision": "deny",
                    "reason": f"missing policy.yaml at {policy_path}",
                },
            )
            return (
                ToolError(
                    error="Governance blocked tool execution (policy.yaml missing for policy evaluation).",
                    error_code="forbidden",
                    error_details={
                        "policy_path": str(policy_path),
                        "tier": tier,
                        "tool_id": tool_id,
                    },
                ),
                warnings,
            )

        from code_scalpel.policy_engine import PolicyEngine as OpaPolicyEngine
        from code_scalpel.policy_engine.policy_engine import (
            Operation as PolicyOperation,
        )
        from code_scalpel.policy_engine.policy_engine import (
            PolicyError as OpaPolicyError,
        )

        try:
            file_path = str(arguments.get("file_path") or "")
            # Provide the most relevant code view we have pre-mutation.
            code_blob = ""
            if tool_id == "update_symbol":
                new_code = arguments.get("new_code")
                if isinstance(new_code, str):
                    code_blob = new_code

            language = Path(file_path).suffix.lstrip(".") if file_path else ""
            affected_files = [Path(file_path)] if file_path else []

            engine = OpaPolicyEngine(str(policy_path))
            op = PolicyOperation(
                type="code_edit",
                code=code_blob,
                language=language,
                file_path=file_path,
                affected_files=affected_files,
                metadata={
                    "tool": tool_id,
                    "target_type": arguments.get("target_type"),
                    "target_name": arguments.get("target_name"),
                    "new_name": arguments.get("new_name"),
                },
            )
            decision = engine.evaluate(op)
        except OpaPolicyError as exc:
            _emit_governance_audit_event(
                policy_dir,
                {
                    **base_audit,
                    "check": "policy_evaluation",
                    "decision": "deny",
                    "reason": f"PolicyError: {exc}",
                },
            )
            return (
                ToolError(
                    error="Governance blocked tool execution (policy evaluation failed).",
                    error_code="forbidden",
                    error_details={
                        "tier": tier,
                        "tool_id": tool_id,
                        "reason": str(exc),
                    },
                ),
                warnings,
            )
        except Exception as exc:
            _emit_governance_audit_event(
                policy_dir,
                {
                    **base_audit,
                    "check": "policy_evaluation",
                    "decision": "deny",
                    "reason": f"error: {type(exc).__name__}",
                },
            )
            return (
                ToolError(
                    error="Governance blocked tool execution (policy evaluation failed).",
                    error_code="forbidden",
                    error_details={
                        "tier": tier,
                        "tool_id": tool_id,
                        "reason": f"{type(exc).__name__}",
                    },
                ),
                warnings,
            )

        if not getattr(decision, "allowed", False):
            if enforcement == "warn":
                warnings.append("Governance WARN: policy evaluation denied; proceeding due to break-glass.")
                _emit_governance_audit_event(
                    policy_dir,
                    {
                        **base_audit,
                        "check": "policy_evaluation",
                        "decision": "allow_warn",
                        "reason": getattr(decision, "reason", ""),
                        "violated_policies": getattr(decision, "violated_policies", []),
                    },
                )
                return None, warnings

            _emit_governance_audit_event(
                policy_dir,
                {
                    **base_audit,
                    "check": "policy_evaluation",
                    "decision": "deny",
                    "reason": getattr(decision, "reason", ""),
                    "violated_policies": getattr(decision, "violated_policies", []),
                },
            )
            return (
                ToolError(
                    error="Governance blocked tool execution (policy evaluation denied).",
                    error_code="forbidden",
                    error_details={
                        "tier": tier,
                        "tool_id": tool_id,
                        "reason": getattr(decision, "reason", None),
                        "violated_policies": getattr(decision, "violated_policies", []),
                    },
                ),
                warnings,
            )

        _emit_governance_audit_event(
            policy_dir,
            {
                **base_audit,
                "check": "policy_evaluation",
                "decision": "allow",
                "reason": getattr(decision, "reason", ""),
            },
        )

    return None, warnings


__all__ = [
    "_GOVERNANCE_FEATURE_POLICY_INTEGRITY",
    "_GOVERNANCE_FEATURE_RESPONSE_CONFIG",
    "_GOVERNANCE_FEATURE_LIMITS",
    "_GOVERNANCE_FEATURE_BUDGET",
    "_GOVERNANCE_FEATURE_DEV_GOVERNANCE",
    "_GOVERNANCE_FEATURE_PROJECT_STRUCTURE",
    "_GOVERNANCE_FEATURE_POLICY_EVALUATION",
    "_GOVERNANCE_VERIFY_CACHE",
    "_emit_governance_audit_event",
    "_parse_bool_env",
    "_get_governance_enforcement",
    "_default_governance_features_for_tier",
    "_is_budgeted_write_tool",
    "_diff_added_removed_lines",
    "_evaluate_change_budget_for_write_tool",
    "_supported_governance_features_for_tier",
    "_parse_governance_features_env",
    "_compute_effective_governance_features",
    "_policy_state_fingerprint",
    "_governance_enforcement_for_tier",
    "_maybe_enforce_governance_before_tool",
]
