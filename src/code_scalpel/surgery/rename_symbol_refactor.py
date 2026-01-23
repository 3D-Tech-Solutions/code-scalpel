"""rename_symbol V1.0 helpers.

This module implements conservative, token-preserving reference/import renames for
Python projects.

Design goals:
- Preserve formatting: edits are applied via tokenize.untokenize.
- Be conservative: only rewrite references when we can infer linkage via imports.
- Avoid strings/comments: tokenizer edits NAME tokens only.

Tier intent (enforced by caller):
- Community: definition-only (no cross-file changes)
- Pro: cross-file reference/import renames with bounded limits
- Enterprise: same as Pro, but no tier limits + audit trail
"""

from __future__ import annotations

import ast
import io
import keyword
import os
import shutil
import tempfile
import time
import tokenize
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from code_scalpel.parsing.unified_parser import ParsingError, parse_python_code

from .audit_trail import AuditEntry, get_audit_trail
from .compliance import check_rename_compliance, format_compliance_error

_SKIP_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".mypy_cache",
    ".pytest_cache",
}


# [20260108_BUGFIX] Python identifier validation to prevent invalid renames
def _is_valid_python_identifier(name: str) -> bool:
    return bool(name) and name.isidentifier() and not keyword.iskeyword(name)


def _relativize(path: Path, root: Path) -> str:
    """Return a root-relative path string when possible to avoid leaking host paths."""
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except Exception:
        return str(path)


@dataclass(frozen=True)
class RenameEdits:
    # Mapping from token (line, col) start position to (old, new)
    token_replacements: dict[tuple[int, int], tuple[str, str]]


@dataclass
class CrossFileRenameResult:
    success: bool
    changed_files: list[str]
    backup_paths: dict[str, str | None]
    warnings: list[str]
    error: str | None = None
    audit_entry: AuditEntry | None = None  # [20260108_FEATURE] Enterprise audit trail


def iter_python_files(project_root: Path, *, max_files: int | None = None) -> Iterable[Path]:
    """Yield Python files under project_root, skipping common virtualenv/build dirs."""
    count = 0
    for root, dirnames, filenames in os.walk(project_root):
        # Mutate dirnames in-place to prune walk
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIR_NAMES and not d.startswith(".")]

        for name in filenames:
            if not name.endswith(".py"):
                continue
            path = Path(root) / name
            yield path
            count += 1
            if max_files is not None and count >= max_files:
                return


def module_name_for_file(project_root: Path, file_path: Path) -> str | None:
    """Best-effort module name for a .py file relative to project_root."""
    try:
        rel = file_path.resolve().relative_to(project_root.resolve())
    except Exception:
        return None

    if rel.suffix != ".py":
        return None

    parts = list(rel.parts)
    if not parts:
        return None

    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1][:-3]  # strip .py

    # Filter empty parts
    parts = [p for p in parts if p]
    if not parts:
        return None
    return ".".join(parts)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_text_atomic(path: Path, new_text: str, *, create_backup: bool) -> str | None:
    backup_path: str | None = None
    if create_backup:
        backup_path = f"{path}.bak"
        shutil.copy2(path, backup_path)

    dir_path = str(path.parent)
    with tempfile.NamedTemporaryFile(mode="w", dir=dir_path, delete=False, suffix=".tmp", encoding="utf-8") as f:
        f.write(new_text)
        tmp_path = f.name

    os.replace(tmp_path, path)
    return backup_path


def _tokenize(code: str) -> list[tokenize.TokenInfo]:
    return list(tokenize.generate_tokens(io.StringIO(code).readline))


def _apply_token_replacements(
    tokens: list[tokenize.TokenInfo],
    replacements: dict[tuple[int, int], tuple[str, str]],
) -> str:
    new_tokens: list[tokenize.TokenInfo] = []
    for tok in tokens:
        repl = replacements.get(tok.start)
        if repl and tok.type == tokenize.NAME and tok.string == repl[0]:
            tok = tokenize.TokenInfo(tok.type, repl[1], tok.start, tok.end, tok.line)
        new_tokens.append(tok)
    return tokenize.untokenize(new_tokens)


def _collect_import_context(
    tree: ast.AST,
    *,
    target_module: str,
    old_short: str,
    target_type: str,
    target_name: str,
) -> tuple[
    # from-import info: (local_name, should_rename_local_uses, has_asname)
    list[tuple[str, bool, bool]],
    # module alias names for `import target_module as alias`
    list[str],
    # local class names imported for method renames (OldClass or alias)
    list[str],
]:
    from_imports: list[tuple[str, bool, bool]] = []
    module_aliases: list[str] = []
    imported_class_locals: list[str] = []

    method_class: str | None = None
    method_old: str | None = None
    if target_type == "method":
        if "." in target_name:
            method_class, method_old = target_name.split(".", 1)

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module != target_module:
                continue
            for alias in node.names:
                local = alias.asname or alias.name

                if target_type in {"function", "class"} and alias.name == old_short:
                    # If imported without alias, local uses should be renamed.
                    from_imports.append((local, alias.asname is None, alias.asname is not None))

                if target_type == "method" and method_class and alias.name == method_class:
                    imported_class_locals.append(local)

        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name != target_module:
                    continue
                module_aliases.append(alias.asname or alias.name.split(".")[-1])

    return from_imports, module_aliases, imported_class_locals


def _collect_reference_edits(
    code: str,
    *,
    target_module: str,
    target_type: str,
    target_name: str,
    new_name: str,
) -> RenameEdits:
    """Collect token edits for a single file.

    Conservative rules:
    - Only rename local `Name(old)` when the file has `from target_module import old`.
    - Only rename `module_alias.old` when the file has `import target_module [as module_alias]`.
    - Method rename only rewrites `ClassName.old_method` and `module_alias.ClassName.old_method` patterns.

    Import statement rewriting is also applied when the module matches.
    """
    try:
        tree, _report = parse_python_code(code, filename="<rename>")
    except ParsingError:
        return RenameEdits(token_replacements={})

    tokens = _tokenize(code)

    if target_type == "method":
        if "." not in target_name:
            return RenameEdits(token_replacements={})
        class_name, old_short = target_name.split(".", 1)
        new_short = new_name
    else:
        old_short = target_name
        new_short = new_name
        class_name = None

    from_imports, module_aliases, imported_class_locals = _collect_import_context(
        tree,
        target_module=target_module,
        old_short=old_short,
        target_type=target_type,
        target_name=target_name,
    )

    instance_vars: set[str] = set()
    if target_type == "method" and class_name:
        instance_vars = _collect_instance_names_for_class(
            tree=tree,
            class_name=class_name,
            module_aliases=module_aliases,
            imported_class_locals=imported_class_locals,
        )

    replacements: dict[tuple[int, int], tuple[str, str]] = {}
    replacements.update(
        _rewrite_from_imports(
            tree=tree,
            tokens=tokens,
            target_module=target_module,
            target_type=target_type,
            class_name=class_name,
            old_short=old_short,
            new_short=new_short,
        )
    )
    replacements.update(
        _rewrite_local_names(
            tree=tree,
            target_type=target_type,
            from_imports=from_imports,
            old_short=old_short,
            new_short=new_short,
        )
    )
    replacements.update(
        _rewrite_module_attribute_calls(
            tree=tree,
            target_type=target_type,
            module_aliases=module_aliases,
            old_short=old_short,
            new_short=new_short,
        )
    )
    replacements.update(
        _rewrite_method_calls(
            tree=tree,
            target_type=target_type,
            class_name=class_name,
            old_short=old_short,
            new_short=new_short,
            module_aliases=module_aliases,
            imported_class_locals=imported_class_locals,
            instance_vars=instance_vars,
        )
    )

    return RenameEdits(token_replacements=replacements)


def _rewrite_from_imports(
    *,
    tree: ast.AST,
    tokens: list[tokenize.TokenInfo],
    target_module: str,
    target_type: str,
    class_name: str | None,
    old_short: str,
    new_short: str,
) -> dict[tuple[int, int], tuple[str, str]]:
    """Rewrite symbols in `from target_module import ...` statements."""
    replacements: dict[tuple[int, int], tuple[str, str]] = {}

    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != target_module:
            continue

        desired: dict[str, str] = {}
        if target_type in {"function", "class"}:
            for alias in node.names:
                if alias.name == old_short:
                    desired[alias.name] = new_short
        elif target_type == "method" and class_name:
            for alias in node.names:
                if alias.name == class_name:
                    desired = {}

        if not desired:
            continue

        start_line = getattr(node, "lineno", None)
        end_line = getattr(node, "end_lineno", start_line)
        if not start_line:
            continue

        seen_import_kw = False
        for tok in tokens:
            if tok.start[0] < start_line or (end_line and tok.start[0] > end_line):
                continue
            if tok.type != tokenize.NAME:
                continue
            if tok.string == "import":
                seen_import_kw = True
                continue
            if not seen_import_kw:
                continue
            replacement = desired.get(tok.string)
            if replacement:
                replacements[tok.start] = (tok.string, replacement)

    return replacements


def _rewrite_local_names(
    *,
    tree: ast.AST,
    target_type: str,
    from_imports: list[tuple[str, bool, bool]],
    old_short: str,
    new_short: str,
) -> dict[tuple[int, int], tuple[str, str]]:
    """Rename local `Name` nodes when imported directly without alias."""
    if target_type not in {"function", "class"}:
        return {}

    rename_local_names = {
        local for (local, should_rename, _has_as) in from_imports if should_rename and local == old_short
    }
    if not rename_local_names:
        return {}

    replacements: dict[tuple[int, int], tuple[str, str]] = {}

    def _collect_params(node: ast.AST) -> set[str]:
        params: set[str] = set()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            args = getattr(node, "args", None)
            if args:
                for arg in (
                    getattr(args, "posonlyargs", []) + getattr(args, "args", []) + getattr(args, "kwonlyargs", [])
                ):
                    if arg and getattr(arg, "arg", None):
                        params.add(arg.arg)
                if getattr(args, "vararg", None) and getattr(args.vararg, "arg", None):
                    params.add(args.vararg.arg)
                if getattr(args, "kwarg", None) and getattr(args.kwarg, "arg", None):
                    params.add(args.kwarg.arg)
        return params

    def _scope_flags(node: ast.AST) -> tuple[set[str], set[str]]:
        globals_declared: set[str] = set()
        nonlocals_declared: set[str] = set()
        for child in getattr(node, "body", []) or []:
            if isinstance(child, ast.Global):
                globals_declared.update(child.names)
            if isinstance(child, ast.Nonlocal):
                nonlocals_declared.update(child.names)
        return globals_declared, nonlocals_declared

    def walk(node: ast.AST, shadowed: bool) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            params = _collect_params(node)
            globals_declared, nonlocals_declared = _scope_flags(node)
            # [20260108_BUGFIX] Avoid renaming when symbol is shadowed by parameters unless global/nonlocal restores outer binding
            has_param_shadow = (
                old_short in params and old_short not in globals_declared and old_short not in nonlocals_declared
            )
            new_shadowed = shadowed or has_param_shadow
            for child in ast.iter_child_nodes(node):
                walk(child, new_shadowed)
            return

        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id == old_short and not shadowed:
            if hasattr(node, "lineno") and hasattr(node, "col_offset"):
                replacements[(node.lineno, node.col_offset)] = (old_short, new_short)

        for child in ast.iter_child_nodes(node):
            walk(child, shadowed)

    walk(tree, shadowed=False)
    return replacements


def _rewrite_module_attribute_calls(
    *,
    tree: ast.AST,
    target_type: str,
    module_aliases: list[str],
    old_short: str,
    new_short: str,
) -> dict[tuple[int, int], tuple[str, str]]:
    """Rename `module_alias.old_short` attribute references."""
    if target_type not in {"function", "class"}:
        return {}

    replacements: dict[tuple[int, int], tuple[str, str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute):
            continue
        if node.attr != old_short:
            continue
        if isinstance(node.value, ast.Name) and node.value.id in module_aliases:
            if (
                hasattr(node, "end_lineno")
                and hasattr(node, "end_col_offset")
                and node.end_lineno is not None
                and node.end_col_offset is not None
            ):
                start = (node.end_lineno, node.end_col_offset - len(old_short))
                replacements[start] = (old_short, new_short)
    return replacements


def _rewrite_method_calls(
    *,
    tree: ast.AST,
    target_type: str,
    class_name: str | None,
    old_short: str,
    new_short: str,
    module_aliases: list[str],
    imported_class_locals: list[str],
    instance_vars: set[str],
) -> dict[tuple[int, int], tuple[str, str]]:
    """Rename ClassName.old_method and module_alias.ClassName.old_method patterns."""
    if target_type != "method" or not class_name:
        return {}

    replacements: dict[tuple[int, int], tuple[str, str]] = {}
    old_method = old_short
    new_method = new_short

    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute):
            continue
        if node.attr != old_method:
            continue

        if isinstance(node.value, ast.Name) and node.value.id in imported_class_locals:
            if (
                hasattr(node, "end_lineno")
                and hasattr(node, "end_col_offset")
                and node.end_lineno is not None
                and node.end_col_offset is not None
            ):
                start = (node.end_lineno, node.end_col_offset - len(old_method))
                replacements[start] = (old_method, new_method)
            continue

        if isinstance(node.value, ast.Attribute) and node.value.attr == class_name:
            inner = node.value
            if isinstance(inner.value, ast.Name) and inner.value.id in module_aliases:
                if (
                    hasattr(node, "end_lineno")
                    and hasattr(node, "end_col_offset")
                    and node.end_lineno is not None
                    and node.end_col_offset is not None
                ):
                    start = (node.end_lineno, node.end_col_offset - len(old_method))
                    replacements[start] = (old_method, new_method)

        # [20260108_BUGFIX] Rename method calls on local instances (e.g., obj.old_method())
        if isinstance(node.value, ast.Name) and node.value.id in instance_vars:
            if (
                hasattr(node, "end_lineno")
                and hasattr(node, "end_col_offset")
                and node.end_lineno is not None
                and node.end_col_offset is not None
            ):
                start = (node.end_lineno, node.end_col_offset - len(old_method))
                replacements[start] = (old_method, new_method)

    return replacements


def _collect_instance_names_for_class(
    *,
    tree: ast.AST,
    class_name: str,
    module_aliases: list[str],
    imported_class_locals: list[str],
) -> set[str]:
    """Collect local variable names bound to instances of the target class."""
    instances: set[str] = set()

    def is_target_constructor(call: ast.Call) -> bool:
        func = call.func
        if isinstance(func, ast.Name) and func.id in imported_class_locals:
            return True
        if (
            isinstance(func, ast.Attribute)
            and func.attr == class_name
            and isinstance(func.value, ast.Name)
            and func.value.id in module_aliases
        ):
            return True
        return False

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            value = node.value
            if isinstance(value, ast.Call) and is_target_constructor(value):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        instances.add(target.id)
        if isinstance(node, ast.AnnAssign):
            value = getattr(node, "value", None)
            if isinstance(value, ast.Call) and is_target_constructor(value):
                target = getattr(node, "target", None)
                if isinstance(target, ast.Name):
                    instances.add(target.id)

    return instances


def rename_references_across_project(
    *,
    project_root: Path,
    target_file: Path,
    target_type: str,
    target_name: str,
    new_name: str,
    create_backup: bool,
    max_files_searched: int | None,
    max_files_updated: int | None,
    tier: str | None = None,  # [20260108_FEATURE] Tier for audit trail
    enable_audit: bool = False,  # [20260108_FEATURE] Enable Enterprise audit trail
    enable_compliance: bool = False,  # [20260108_FEATURE] Enable Enterprise compliance checking
) -> CrossFileRenameResult:
    """Rename references/imports across a project for Pro/Enterprise tiers.

    Args:
        project_root: Root directory of the project
        target_file: File containing the definition
        target_type: Type of symbol ("function", "class", "method")
        target_name: Original symbol name
        new_name: New symbol name
        create_backup: Whether to create backup files
        max_files_searched: Maximum files to search (None = unlimited)
        max_files_updated: Maximum files to update (None = unlimited)
        tier: License tier ("community", "pro", "enterprise")
        enable_audit: Enable audit trail logging (Enterprise only)
        enable_compliance: Enable compliance checking (Enterprise only)

    Returns:
        CrossFileRenameResult with audit_entry if enabled
    """
    warnings: list[str] = []
    session_id = str(uuid.uuid4())
    start_time = time.time()

    # Initialize audit trail if enabled
    audit_trail = get_audit_trail() if enable_audit else None
    audit_entry = None

    # [20260108_FEATURE] Run compliance check if enabled
    if enable_compliance:
        compliance_result = check_rename_compliance(
            target_file=str(target_file),
            target_type=target_type,
            target_name=target_name,
            new_name=new_name,
            project_root=project_root,
        )

        if not compliance_result.allowed:
            error_msg = format_compliance_error(compliance_result)

            # Log compliance failure in audit
            if audit_trail:
                audit_entry = audit_trail.create_entry(
                    operation="rename_symbol_cross_file",
                    session_id=session_id,
                    target_file=str(target_file),
                    target_type=target_type,
                    target_name=target_name,
                    new_name=new_name,
                    tier=tier,
                    success=False,
                    error=error_msg,
                    duration_ms=(time.time() - start_time) * 1000,
                    metadata={"compliance_violations": compliance_result.violations},
                )
                audit_trail.log(audit_entry)

            return CrossFileRenameResult(
                success=False,
                changed_files=[],
                backup_paths={},
                warnings=warnings + [error_msg],
                error=error_msg,
                audit_entry=audit_entry,
            )

    # [20260108_BUGFIX] Reject invalid Python identifiers early
    if not _is_valid_python_identifier(new_name):
        error_msg = f"Invalid Python identifier: {new_name}"

        # Log audit entry for failed operation
        if audit_trail:
            audit_entry = audit_trail.create_entry(
                operation="rename_symbol_cross_file",
                session_id=session_id,
                target_file=str(target_file),
                target_type=target_type,
                target_name=target_name,
                new_name=new_name,
                tier=tier,
                success=False,
                error=error_msg,
                duration_ms=(time.time() - start_time) * 1000,
            )
            audit_trail.log(audit_entry)

        return CrossFileRenameResult(
            success=False,
            changed_files=[],
            backup_paths={},
            warnings=warnings + [error_msg],
            error=error_msg,
            audit_entry=audit_entry,
        )

    target_module = module_name_for_file(project_root, target_file)
    if not target_module:
        error_msg = "Could not determine target module name for cross-file rename."

        # Log audit entry for failed operation
        if audit_trail:
            audit_entry = audit_trail.create_entry(
                operation="rename_symbol_cross_file",
                session_id=session_id,
                target_file=str(target_file),
                target_type=target_type,
                target_name=target_name,
                new_name=new_name,
                tier=tier,
                success=False,
                error=error_msg,
                duration_ms=(time.time() - start_time) * 1000,
            )
            audit_trail.log(audit_entry)

        return CrossFileRenameResult(
            success=False,
            changed_files=[],
            backup_paths={},
            warnings=warnings,
            error=error_msg,
            audit_entry=audit_entry,
        )

    changed_files: list[str] = []
    backup_paths: dict[str, str | None] = {}

    searched = 0
    updated = 0

    for py_file in iter_python_files(project_root, max_files=max_files_searched):
        searched += 1
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

        if not edits.token_replacements:
            continue

        new_code = _apply_token_replacements(_tokenize(code), edits.token_replacements)
        if new_code == code:
            continue

        if max_files_updated is not None and updated >= max_files_updated:
            warnings.append(
                f"Reached max_files_updated={max_files_updated}; additional reference updates were skipped."
            )
            break

        try:
            backup_path = _write_text_atomic(py_file, new_code, create_backup=create_backup)
            rel_path = _relativize(py_file, project_root)
            changed_files.append(rel_path)
            backup_paths[rel_path] = backup_path
            updated += 1
        except Exception as e:
            rel_path = _relativize(py_file, project_root)
            warnings.append(f"Failed to update {rel_path}: {e}")

    if max_files_searched is not None and searched >= max_files_searched:
        warnings.append(f"Search truncated at max_files_searched={max_files_searched}.")

    # [20260108_FEATURE] Log audit entry for successful operation
    if audit_trail:
        audit_entry = audit_trail.create_entry(
            operation="rename_symbol_cross_file",
            session_id=session_id,
            target_file=str(target_file),
            target_type=target_type,
            target_name=target_name,
            new_name=new_name,
            tier=tier,
            success=True,
            changed_files=changed_files,
            warnings=warnings,
            duration_ms=(time.time() - start_time) * 1000,
            metadata={
                "files_searched": searched,
                "files_updated": updated,
                "max_files_searched": max_files_searched,
                "max_files_updated": max_files_updated,
            },
        )
        audit_trail.log(audit_entry)

    return CrossFileRenameResult(
        success=True,
        changed_files=changed_files,
        backup_paths=backup_paths,
        warnings=warnings,
        error=None,
        audit_entry=audit_entry,
    )
