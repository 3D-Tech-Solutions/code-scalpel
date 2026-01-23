"""Policy loading and composition for code_policy_check.

Goals (v1.0 doc parity):
- Organization-specific policies via repo-local config
- Policy templates library
- Policy inheritance and composition via `extends`

This module intentionally uses only the standard library (JSON).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .templates import get_policy_template

DEFAULT_POLICY_FILENAMES = (
    "code_policy_check.json",
    "code_policy_check.policy.json",
)


def find_policy_file(start_dir: str | Path | None = None) -> Path | None:
    base = Path(start_dir or ".").resolve()
    # Search: start_dir/.code-scalpel/<name>
    candidate_dir = base / ".code-scalpel"
    for name in DEFAULT_POLICY_FILENAMES:
        candidate = candidate_dir / name
        if candidate.is_file():
            return candidate
    return None


def load_policy_file(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Policy file must contain a JSON object")
    return data


def compute_policy_hash(policy: dict[str, Any]) -> str:
    # Stable hash for audit/logging.
    blob = json.dumps(policy, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _merge_lists_unique(base: list[Any], extra: list[Any]) -> list[Any]:
    seen = set()
    out: list[Any] = []
    for item in base + extra:
        key = json.dumps(item, sort_keys=True, default=str) if isinstance(item, (dict, list)) else str(item)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def merge_policies(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Merge two policy dicts.

    - dict values merge recursively
    - list values concatenate uniquely
    - scalars override
    """
    result: dict[str, Any] = dict(base)
    for key, value in override.items():
        if key == "extends":
            # extends is handled by resolution; keep it for transparency
            if key in result and isinstance(result[key], list) and isinstance(value, list):
                result[key] = _merge_lists_unique(result[key], value)
            else:
                result[key] = value
            continue

        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_policies(result[key], value)
        elif key in result and isinstance(result[key], list) and isinstance(value, list):
            result[key] = _merge_lists_unique(result[key], value)
        else:
            result[key] = value
    return result


def resolve_policy(
    policy: dict[str, Any],
    policy_dir: Path,
    *,
    _seen: set[str] | None = None,
) -> dict[str, Any]:
    """Resolve a policy with inheritance via `extends`.

    `extends` entries support:
    - template:<name>
    - relative/absolute file paths to JSON policies
    """
    seen = _seen or set()

    extends = policy.get("extends")
    if not extends:
        return dict(policy)

    if not isinstance(extends, list):
        raise ValueError("policy.extends must be a list")

    composed: dict[str, Any] = {}

    for ext in extends:
        if not isinstance(ext, str):
            continue

        if ext.startswith("template:"):
            template_name = ext.split(":", 1)[1].strip()
            template = get_policy_template(template_name)
            if template is None:
                raise ValueError(f"Unknown policy template: {template_name}")
            # Templates themselves can extend others
            resolved_template = resolve_policy(template, policy_dir, _seen=seen)
            composed = merge_policies(composed, resolved_template)
            continue

        # Treat as path
        ext_path = Path(ext)
        if not ext_path.is_absolute():
            ext_path = (policy_dir / ext_path).resolve()

        fingerprint = str(ext_path)
        if fingerprint in seen:
            raise ValueError(f"Cycle detected in policy extends: {fingerprint}")
        seen.add(fingerprint)

        ext_policy = load_policy_file(ext_path)
        resolved_ext = resolve_policy(ext_policy, ext_path.parent, _seen=seen)
        composed = merge_policies(composed, resolved_ext)

    # Finally overlay the concrete policy on top
    composed = merge_policies(composed, {k: v for k, v in policy.items() if k != "extends"})
    return composed


def load_effective_policy(
    start_dir: str | Path | None = None,
) -> tuple[dict[str, Any] | None, Path | None, str | None]:
    """Load policy if present and return (policy, policy_path, policy_hash)."""
    policy_path = find_policy_file(start_dir)
    if not policy_path:
        return None, None, None

    raw = load_policy_file(policy_path)
    resolved = resolve_policy(raw, policy_path.parent)
    return resolved, policy_path, compute_policy_hash(resolved)
