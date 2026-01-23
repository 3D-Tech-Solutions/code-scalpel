"""
Code Policy Check - Main Analyzer.

[20251226_FEATURE] v3.4.0 - Main code policy checking engine.

This module provides the CodePolicyChecker class that orchestrates:
- Style guide checking (PEP8, ESLint)
- Pattern-based analysis
- Best practice detection
- Compliance auditing
- Report generation
"""

from __future__ import annotations

import ast
import base64
import hashlib
import json
import logging
import os
import re
import subprocess
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .models import (
    AuditEntry,
    BestPracticeViolation,
    Certification,
    CodePolicyResult,
    ComplianceReport,
    CustomRule,
    PatternMatch,
    PolicyViolation,
    SecurityWarning,
    ViolationSeverity,
)
from .patterns import (
    ASYNC_PATTERNS,
    BEST_PRACTICE_PATTERNS,
    SECURITY_PATTERNS,
    PatternDefinition,
    get_compliance_patterns,
    get_patterns_for_tier,
)
from .policy_loader import load_effective_policy

logger = logging.getLogger(__name__)


class CodePolicyChecker:
    """
    Main code policy checking engine.

    [20251226_FEATURE] Tier-based policy checking with style, patterns, and compliance.

    Attributes:
        tier: Current tier level (community, pro, enterprise)
        custom_rules: List of custom rules (Pro tier)
        compliance_standards: List of compliance standards to check (Enterprise tier)
    """

    def __init__(
        self,
        tier: str = "community",
        custom_rules: list[CustomRule] | None = None,
        compliance_standards: list[str] | None = None,
        policy_path: str | None = None,
    ):
        """
        Initialize the checker.

        Args:
            tier: Tier level (community, pro, enterprise)
            custom_rules: Custom rules to apply (Pro tier)
            compliance_standards: Compliance standards to audit (Enterprise tier)
        """
        self.tier = tier.lower()
        self.custom_rules = custom_rules or []
        self.compliance_standards = compliance_standards or []

        # Organization policies + templates (best-effort)
        policy, discovered_path, policy_hash = load_effective_policy()
        if policy_path:
            # Allow explicit override (relative to CWD)
            explicit = Path(policy_path).expanduser().resolve()
            if explicit.is_file():
                from .policy_loader import (
                    compute_policy_hash,
                    load_policy_file,
                    resolve_policy,
                )

                raw = load_policy_file(explicit)
                policy = resolve_policy(raw, explicit.parent)
                discovered_path = explicit
                policy_hash = compute_policy_hash(policy)

        self.policy: dict[str, Any] | None = policy
        self.policy_file: str | None = str(discovered_path) if discovered_path else None
        self.policy_hash: str | None = policy_hash

        include_ext = None
        exclude_dirs = None
        complexity = None
        eslint = None
        if isinstance(policy, dict):
            include_ext = policy.get("include_extensions")
            exclude_dirs = policy.get("exclude_dirs")
            complexity = policy.get("complexity")
            eslint = policy.get("eslint")

        # Defaults matching v1.0 doc claims
        self.include_extensions: list[str] = (
            [str(x) for x in include_ext] if isinstance(include_ext, list) and include_ext else [".py", ".js", ".jsx"]
        )
        self.exclude_dirs: tuple[str, ...] = (
            tuple(str(x) for x in exclude_dirs)
            if isinstance(exclude_dirs, list) and exclude_dirs
            else (
                "__pycache__",
                ".venv",
                "venv",
                "node_modules",
                ".git",
            )
        )
        self.complexity_thresholds: dict[str, int] = {}
        if isinstance(complexity, dict):
            for k, v in complexity.items():
                if isinstance(k, str) and isinstance(v, int):
                    self.complexity_thresholds[k.lower()] = v
        if "python" not in self.complexity_thresholds:
            self.complexity_thresholds["python"] = 15
        if "javascript" not in self.complexity_thresholds:
            self.complexity_thresholds["javascript"] = 20

        self.eslint_config: dict[str, Any] = eslint if isinstance(eslint, dict) else {}

        # Organization-specific custom rules (Pro/Enterprise) from policy config
        if self.tier in ("pro", "enterprise") and isinstance(policy, dict):
            policy_custom_rules = policy.get("custom_rules")
            if isinstance(policy_custom_rules, list) and policy_custom_rules:
                by_name = {r.name: r for r in self.custom_rules}
                for r in policy_custom_rules:
                    if not isinstance(r, dict):
                        continue
                    name = r.get("name")
                    pattern = r.get("pattern")
                    if not isinstance(name, str) or not isinstance(pattern, str):
                        continue
                    if name in by_name:
                        continue
                    severity_raw = r.get("severity")
                    try:
                        severity = (
                            ViolationSeverity(str(severity_raw).lower())
                            if severity_raw is not None
                            else ViolationSeverity.WARNING
                        )
                    except Exception:
                        severity = ViolationSeverity.WARNING

                    by_name[name] = CustomRule(
                        name=name,
                        description=str(r.get("description") or ""),
                        pattern=pattern,
                        pattern_type=str(r.get("pattern_type") or "regex"),
                        severity=severity,
                        message_template=str(r.get("message_template") or "Matched pattern: {pattern_name}"),
                        enabled=bool(r.get("enabled", True)),
                    )

                self.custom_rules = list(by_name.values())

        # Get patterns for this tier
        self.patterns = get_patterns_for_tier(self.tier)

        # Track audit entries (Enterprise tier)
        self._audit_entries: list[AuditEntry] = []

    def check_files(
        self,
        paths: list[str],
        rules: list[str] | None = None,
        generate_report: bool = False,
    ) -> CodePolicyResult:
        """
        Check files for policy violations.

        [20251226_FEATURE] Main entry point for policy checking.

        Args:
            paths: List of file paths or directories to check
            rules: Optional list of rule IDs to apply (None = all rules)
            generate_report: Whether to generate PDF report (Enterprise tier)

        Returns:
            CodePolicyResult with all findings
        """
        datetime.now()

        # Collect all files to check
        files_to_check = self._collect_files(paths)

        # Apply tier limits
        max_files = self._get_tier_limit("max_files")
        if max_files and len(files_to_check) > max_files:
            files_to_check = files_to_check[:max_files]

        # Initialize result
        violations: list[PolicyViolation] = []
        best_practices: list[BestPracticeViolation] = []
        pattern_matches: list[PatternMatch] = []
        security_warnings: list[SecurityWarning] = []
        custom_results: dict[str, list[dict[str, Any]]] = {}

        rules_applied = 0

        # Check each file
        for file_path in files_to_check:
            try:
                file_violations, file_rules = self._check_file(file_path, rules)
                violations.extend(file_violations)
                rules_applied += file_rules

                # Pro tier: additional checks
                if self.tier in ("pro", "enterprise"):
                    bp_violations = self._check_best_practices(file_path)
                    best_practices.extend(bp_violations)

                    async_violations = self._check_async_patterns(file_path)
                    best_practices.extend(async_violations)

                    sec_warnings = self._check_security_patterns(file_path)
                    security_warnings.extend(sec_warnings)

                    # Custom rules
                    for rule in self.custom_rules:
                        matches = self._apply_custom_rule(file_path, rule)
                        if matches:
                            if rule.name not in custom_results:
                                custom_results[rule.name] = []
                            custom_results[rule.name].extend(matches)

            except Exception as e:
                logger.warning(f"Error checking {file_path}: {e}")

        # Determine success (no errors or critical violations)
        critical_count = sum(1 for v in violations if v.severity == ViolationSeverity.CRITICAL)
        success = critical_count == 0

        # Build summary
        summary = self._build_summary(
            len(files_to_check),
            len(violations),
            critical_count,
            len(best_practices),
            len(security_warnings),
        )

        # Initialize result
        result = CodePolicyResult(
            success=success,
            files_checked=len(files_to_check),
            rules_applied=rules_applied,
            summary=summary,
            violations=violations,
            tier=self.tier,
        )

        # Add Pro tier fields
        if self.tier in ("pro", "enterprise"):
            result.best_practices_violations = best_practices
            result.pattern_matches = pattern_matches
            result.security_warnings = security_warnings
            result.custom_rule_results = custom_results

        # Enterprise tier: compliance and audit
        if self.tier == "enterprise":
            compliance_reports = self._run_compliance_audit(files_to_check)
            result.compliance_reports = compliance_reports

            # Calculate compliance score
            if compliance_reports:
                scores = [r.score for r in compliance_reports.values()]
                result.compliance_score = sum(scores) / len(scores)

            # Add audit entry
            audit_entry = AuditEntry(
                timestamp=datetime.now(),
                action="code_policy_check",
                user=os.environ.get("USER", os.environ.get("USERNAME")),
                files_checked=files_to_check,
                rules_applied=rules_applied,
                violations_found=len(violations),
                compliance_standards=list(compliance_reports.keys()),
                metadata={
                    "policy_file": self.policy_file,
                    "policy_hash": self.policy_hash,
                    "policy_extends": (self.policy.get("extends") if isinstance(self.policy, dict) else None),
                },
            )
            result.audit_trail = [audit_entry]

            # [20251229_FEATURE] Persist audit log
            self._save_audit_entry(audit_entry)

            # Generate PDF report if requested
            if generate_report:
                pdf_content = self._generate_pdf_report(result)
                result.pdf_report = pdf_content

                # Generate certifications for passing standards
                result.certifications = self._generate_certifications(compliance_reports)

        return result

    def _collect_files(self, paths: list[str]) -> list[str]:
        """Collect source files from paths."""
        files: list[str] = []

        for path in paths:
            path_obj = Path(path)
            if path_obj.is_file():
                if path_obj.suffix in self.include_extensions:
                    files.append(str(path_obj.absolute()))
            elif path_obj.is_dir():
                for ext in self.include_extensions:
                    pattern = f"*{ext}" if ext.startswith(".") else ext
                    for src_file in path_obj.rglob(pattern):
                        if any(part in src_file.parts for part in self.exclude_dirs):
                            continue
                        files.append(str(src_file.absolute()))

        return files

    def _get_tier_limit(self, limit_name: str) -> int | None:
        """Get tier-specific limit."""
        limits = {
            "community": {"max_files": 100, "max_rules": 50},
            "pro": {"max_files": None, "max_rules": 200},
            "enterprise": {"max_files": None, "max_rules": None},
        }
        return limits.get(self.tier, {}).get(limit_name)

    def _check_file(self, file_path: str, rules: list[str] | None) -> tuple[list[PolicyViolation], int]:
        """
        Check a single file for violations.

        [20251226_FEATURE] Core file checking logic.
        """
        violations: list[PolicyViolation] = []
        rules_checked = 0

        max_rules = self._get_tier_limit("max_rules")

        def _can_check_more() -> bool:
            return max_rules is None or rules_checked < max_rules

        suffix = Path(file_path).suffix.lower()

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            if suffix == ".py":
                # Parse AST for pattern matching
                try:
                    tree = ast.parse(content)
                except SyntaxError as e:
                    violations.append(
                        PolicyViolation(
                            file=file_path,
                            line=e.lineno or 1,
                            column=e.offset or 0,
                            rule_id="SYNTAX",
                            message=f"Syntax error: {e.msg}",
                            severity=ViolationSeverity.ERROR,
                            category="syntax",
                        )
                    )
                    return violations, 0

                # Check PEP8 style (Community tier)
                if _can_check_more() and (not rules or "PEP8" in rules):
                    pep8_violations = self._check_pep8(file_path)
                    violations.extend(pep8_violations)
                    rules_checked += 1

                # Simple complexity thresholds
                if _can_check_more() and (not rules or "CPLX001" in rules):
                    violations.extend(self._check_complexity_python(file_path, tree))
                    rules_checked += 1

                # Check patterns
                for pattern in self.patterns:
                    if not _can_check_more():
                        break
                    if rules and pattern.id not in rules:
                        continue

                    rules_checked += 1

                    if pattern.regex_pattern:
                        regex_violations = self._check_regex_pattern(file_path, content, pattern)
                        violations.extend(regex_violations)

                    if pattern.ast_node_types:
                        ast_violations = self._check_ast_pattern(file_path, tree, pattern)
                        violations.extend(ast_violations)

            elif suffix in (".js", ".jsx", ".ts", ".tsx"):
                # JavaScript/TypeScript: ESLint (best-effort) + simple complexity thresholds.
                if _can_check_more():
                    eslint_violations = self._check_eslint(file_path)
                    # Optional rule filtering
                    if rules:
                        eslint_violations = [v for v in eslint_violations if v.rule_id in rules]
                    violations.extend(eslint_violations)
                    rules_checked += 1

                if _can_check_more() and (not rules or "CPLX001" in rules):
                    violations.extend(self._check_complexity_javascript(file_path, content))
                    rules_checked += 1

        except Exception as e:
            logger.warning(f"Error checking {file_path}: {e}")

        return violations, rules_checked

    def _check_pep8(self, file_path: str) -> list[PolicyViolation]:
        """
        Run PEP8/pycodestyle checks.

        [20251226_FEATURE] Community tier style checking.
        """
        violations: list[PolicyViolation] = []

        try:
            # Try using pycodestyle
            result = subprocess.run(
                ["python", "-m", "pycodestyle", "--max-line-length=100", file_path],
                capture_output=True,
                text=True,
                timeout=30,
            )

            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                # Parse pycodestyle output: "file.py:10:5: E501 line too long"
                match = re.match(r"(.+):(\d+):(\d+):\s*([A-Z]\d+)\s+(.+)", line)
                if match:
                    violations.append(
                        PolicyViolation(
                            file=match.group(1),
                            line=int(match.group(2)),
                            column=int(match.group(3)),
                            rule_id=match.group(4),
                            message=match.group(5),
                            severity=(
                                ViolationSeverity.WARNING if match.group(4).startswith("W") else ViolationSeverity.ERROR
                            ),
                            category="style",
                        )
                    )

        except subprocess.TimeoutExpired:
            logger.warning(f"PEP8 check timed out for {file_path}")
        except FileNotFoundError:
            # pycodestyle not installed - skip
            pass
        except Exception as e:
            logger.warning(f"PEP8 check failed for {file_path}: {e}")

        return violations

    def _check_eslint(self, file_path: str) -> list[PolicyViolation]:
        """Run ESLint checks for JS/TS (best-effort)."""
        violations: list[PolicyViolation] = []

        eslint_enabled = self.eslint_config.get("enabled")
        if eslint_enabled is False:
            return violations

        eslint_bin = self.eslint_config.get("bin") or "eslint"
        eslint_args = self.eslint_config.get("args")
        if not isinstance(eslint_args, list):
            eslint_args = ["-f", "json"]

        # Ensure JSON output
        if "-f" not in eslint_args and "--format" not in eslint_args:
            eslint_args = list(eslint_args) + ["-f", "json"]

        eslint_cmd = [str(eslint_bin)] + [str(a) for a in eslint_args] + [file_path]

        def _run(cmd: list[str]) -> subprocess.CompletedProcess[str] | None:
            try:
                return subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
            except FileNotFoundError:
                return None
            except subprocess.TimeoutExpired:
                violations.append(
                    PolicyViolation(
                        file=file_path,
                        line=1,
                        column=0,
                        rule_id="ESLINT_TIMEOUT",
                        message="ESLint check timed out",
                        severity=ViolationSeverity.WARNING,
                        category="style",
                    )
                )
                return None

        result = _run(eslint_cmd)
        if result is None:
            # Try npx fallback (no network assumed; uses local node_modules)
            result = _run(["npx", "eslint"] + [str(a) for a in eslint_args] + [file_path])

        if result is None:
            # ESLint not available; record informational marker for transparency.
            violations.append(
                PolicyViolation(
                    file=file_path,
                    line=1,
                    column=0,
                    rule_id="ESLINT_MISSING",
                    message="ESLint not available; skipped JS/TS style checks",
                    severity=ViolationSeverity.INFO,
                    category="style",
                )
            )
            return violations

        stdout = (result.stdout or "").strip()
        if not stdout:
            return violations

        try:
            parsed = json.loads(stdout)
        except Exception:
            # ESLint output not parseable; keep a single marker
            violations.append(
                PolicyViolation(
                    file=file_path,
                    line=1,
                    column=0,
                    rule_id="ESLINT_PARSE",
                    message="Failed to parse ESLint JSON output",
                    severity=ViolationSeverity.INFO,
                    category="style",
                )
            )
            return violations

        if not isinstance(parsed, list):
            return violations

        for file_report in parsed:
            if not isinstance(file_report, dict):
                continue
            messages = file_report.get("messages")
            if not isinstance(messages, list):
                continue
            for msg in messages:
                if not isinstance(msg, dict):
                    continue
                line = int(msg.get("line") or 1)
                col = int(msg.get("column") or 0)
                rule_id = msg.get("ruleId") or "ESLINT"
                message = msg.get("message") or "ESLint issue"
                severity_num = msg.get("severity")
                severity = ViolationSeverity.ERROR if severity_num == 2 else ViolationSeverity.WARNING
                violations.append(
                    PolicyViolation(
                        file=file_path,
                        line=line,
                        column=col,
                        rule_id=str(rule_id),
                        message=str(message),
                        severity=severity,
                        category="style",
                    )
                )

        return violations

    def _check_complexity_python(self, file_path: str, tree: ast.AST) -> list[PolicyViolation]:
        """Simple cyclomatic-ish complexity threshold check for Python."""
        threshold = self.complexity_thresholds.get("python")
        if not isinstance(threshold, int) or threshold <= 0:
            return []

        complexity = 1
        for node in ast.walk(tree):
            if isinstance(
                node,
                (
                    ast.If,
                    ast.For,
                    ast.While,
                    ast.Try,
                    ast.With,
                    ast.AsyncWith,
                    ast.AsyncFor,
                    ast.ExceptHandler,
                ),
            ):
                complexity += 1
            elif isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
                # Count boolean chaining as additional branches
                complexity += max(0, len(node.values) - 1)

        if complexity <= threshold:
            return []

        return [
            PolicyViolation(
                file=file_path,
                line=1,
                column=0,
                rule_id="CPLX001",
                message=f"Complexity {complexity} exceeds threshold {threshold}",
                severity=ViolationSeverity.WARNING,
                category="complexity",
                suggestion="Refactor to reduce branching or split into smaller functions",
            )
        ]

    def _check_complexity_javascript(self, file_path: str, content: str) -> list[PolicyViolation]:
        """Simple keyword-based complexity threshold check for JavaScript/TypeScript."""
        threshold = self.complexity_thresholds.get("javascript")
        if not isinstance(threshold, int) or threshold <= 0:
            return []

        # Heuristic: count common branching/looping tokens.
        tokens = re.findall(r"\b(if|else\s+if|for|while|case|catch)\b|\?|&&|\|\|", content)
        complexity = 1 + len(tokens)
        if complexity <= threshold:
            return []

        return [
            PolicyViolation(
                file=file_path,
                line=1,
                column=0,
                rule_id="CPLX001",
                message=f"Complexity {complexity} exceeds threshold {threshold}",
                severity=ViolationSeverity.WARNING,
                category="complexity",
                suggestion="Refactor to reduce branching or split into smaller functions",
            )
        ]

    def _check_regex_pattern(self, file_path: str, content: str, pattern: PatternDefinition) -> list[PolicyViolation]:
        """Check content against regex pattern."""
        violations: list[PolicyViolation] = []

        if not pattern.regex_pattern:
            return violations

        try:
            regex = re.compile(pattern.regex_pattern, re.MULTILINE | re.IGNORECASE)

            for match in regex.finditer(content):
                # Calculate line number
                line_num = content[: match.start()].count("\n") + 1
                col = match.start() - content.rfind("\n", 0, match.start())

                violations.append(
                    PolicyViolation(
                        file=file_path,
                        line=line_num,
                        column=col,
                        rule_id=pattern.id,
                        message=pattern.description,
                        severity=pattern.severity,
                        category=pattern.category.value,
                        code_snippet=match.group(0)[:100],
                        suggestion=pattern.suggestion,
                    )
                )

        except re.error as e:
            logger.warning(f"Invalid regex pattern {pattern.id}: {e}")

        return violations

    def _check_ast_pattern(self, file_path: str, tree: ast.AST, pattern: PatternDefinition) -> list[PolicyViolation]:
        """Check AST against pattern."""
        violations: list[PolicyViolation] = []

        if not pattern.ast_node_types:
            return violations

        for node in ast.walk(tree):
            if isinstance(node, pattern.ast_node_types):
                # Apply validator if present
                if pattern.ast_validator:
                    try:
                        if not pattern.ast_validator(node):
                            continue
                    except Exception:
                        continue

                violations.append(
                    PolicyViolation(
                        file=file_path,
                        line=getattr(node, "lineno", 1),
                        column=getattr(node, "col_offset", 0),
                        rule_id=pattern.id,
                        message=pattern.description,
                        severity=pattern.severity,
                        category=pattern.category.value,
                        suggestion=pattern.suggestion,
                    )
                )

        return violations

    def _check_best_practices(self, file_path: str) -> list[BestPracticeViolation]:
        """
        Check for best practice violations (Pro tier).

        [20251226_FEATURE] Pro tier best practice analysis.
        """
        violations: list[BestPracticeViolation] = []

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)

            for pattern in BEST_PRACTICE_PATTERNS:
                if pattern.regex_pattern:
                    for match in re.finditer(pattern.regex_pattern, content, re.MULTILINE):
                        line_num = content[: match.start()].count("\n") + 1
                        violations.append(
                            BestPracticeViolation(
                                file=file_path,
                                line=line_num,
                                pattern_id=pattern.id,
                                description=pattern.description,
                                severity=pattern.severity,
                                category="best_practice",
                                recommendation=pattern.suggestion,
                            )
                        )

                if pattern.ast_node_types:
                    for node in ast.walk(tree):
                        if isinstance(node, pattern.ast_node_types):
                            if pattern.ast_validator:
                                try:
                                    if not pattern.ast_validator(node):
                                        continue
                                except Exception:
                                    continue

                            violations.append(
                                BestPracticeViolation(
                                    file=file_path,
                                    line=getattr(node, "lineno", 1),
                                    pattern_id=pattern.id,
                                    description=pattern.description,
                                    severity=pattern.severity,
                                    category="best_practice",
                                    recommendation=pattern.suggestion,
                                )
                            )

        except Exception as e:
            logger.warning(f"Best practice check failed for {file_path}: {e}")

        return violations

    def _check_security_patterns(self, file_path: str) -> list[SecurityWarning]:
        """
        Check for security issues (Pro tier).

        [20251226_FEATURE] Pro tier security pattern detection.
        """
        warnings: list[SecurityWarning] = []

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)

            for pattern in SECURITY_PATTERNS:
                if pattern.regex_pattern:
                    for match in re.finditer(pattern.regex_pattern, content, re.MULTILINE | re.IGNORECASE):
                        line_num = content[: match.start()].count("\n") + 1
                        warnings.append(
                            SecurityWarning(
                                file=file_path,
                                line=line_num,
                                warning_type=pattern.name,
                                description=pattern.description,
                                severity=pattern.severity,
                                cwe_id=pattern.cwe_id,
                                remediation=pattern.suggestion,
                            )
                        )

                if pattern.ast_node_types:
                    for node in ast.walk(tree):
                        if isinstance(node, pattern.ast_node_types):
                            if pattern.ast_validator:
                                try:
                                    if not pattern.ast_validator(node):
                                        continue
                                except Exception:
                                    continue

                            warnings.append(
                                SecurityWarning(
                                    file=file_path,
                                    line=getattr(node, "lineno", 1),
                                    warning_type=pattern.name,
                                    description=pattern.description,
                                    severity=pattern.severity,
                                    cwe_id=pattern.cwe_id,
                                    remediation=pattern.suggestion,
                                )
                            )

        except Exception as e:
            logger.warning(f"Security check failed for {file_path}: {e}")

        return warnings

    def _check_async_patterns(self, file_path: str) -> list[BestPracticeViolation]:
        """
        Check for async/await anti-patterns (Pro tier).

        [20251226_FEATURE] Pro tier async pattern analysis.
        """
        violations: list[BestPracticeViolation] = []

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Only check files that use async
            if "async " not in content and "await " not in content:
                return violations

            ast.parse(content)

            for pattern in ASYNC_PATTERNS:
                if pattern.regex_pattern:
                    for match in re.finditer(pattern.regex_pattern, content, re.MULTILINE):
                        line_num = content[: match.start()].count("\n") + 1
                        violations.append(
                            BestPracticeViolation(
                                file=file_path,
                                line=line_num,
                                pattern_id=pattern.id,
                                description=pattern.description,
                                severity=pattern.severity,
                                category="async",
                                recommendation=pattern.suggestion,
                            )
                        )

        except Exception as e:
            logger.warning(f"Async pattern check failed for {file_path}: {e}")

        return violations

    def _apply_custom_rule(self, file_path: str, rule: CustomRule) -> list[dict[str, Any]]:
        """
        Apply a custom rule to a file (Pro tier).

        [20251226_FEATURE] Pro tier custom rule engine.
        """
        matches: list[dict[str, Any]] = []

        if not rule.enabled:
            return matches

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            if rule.pattern_type == "regex":
                regex = re.compile(rule.pattern, re.MULTILINE)
                for match in regex.finditer(content):
                    line_num = content[: match.start()].count("\n") + 1
                    matches.append(
                        {
                            "file": file_path,
                            "line": line_num,
                            "match": match.group(0)[:100],
                            "message": rule.message_template.format(
                                pattern_name=rule.name,
                                match=match.group(0)[:50],
                            ),
                            "severity": rule.severity.value,
                        }
                    )

        except Exception as e:
            logger.warning(f"Custom rule {rule.name} failed for {file_path}: {e}")

        return matches

    def _run_compliance_audit(self, files: list[str]) -> dict[str, ComplianceReport]:
        """
        Run compliance audits (Enterprise tier).

        [20251226_FEATURE] Enterprise tier compliance checking.
        """
        reports: dict[str, ComplianceReport] = {}

        standards_to_check = self.compliance_standards or [
            "hipaa",
            "soc2",
            "gdpr",
            "pci_dss",
        ]

        for standard in standards_to_check:
            patterns = get_compliance_patterns([standard])
            findings: list[dict[str, Any]] = []

            for file_path in files:
                try:
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()

                    for pattern in patterns:
                        if pattern.regex_pattern:
                            for match in re.finditer(
                                pattern.regex_pattern,
                                content,
                                re.MULTILINE | re.IGNORECASE,
                            ):
                                line_num = content[: match.start()].count("\n") + 1
                                findings.append(
                                    {
                                        "file": file_path,
                                        "line": line_num,
                                        "rule_id": pattern.id,
                                        "description": pattern.description,
                                        "severity": pattern.severity.value,
                                        "cwe_id": pattern.cwe_id,
                                    }
                                )

                except Exception as e:
                    logger.warning(f"Compliance check failed for {file_path}: {e}")

            # Calculate compliance score
            if len(files) > 0:
                # Score based on critical findings per file
                critical_findings = sum(1 for f in findings if f.get("severity") in ("critical", "error"))
                score = max(0, 100 - (critical_findings / len(files)) * 20)
            else:
                score = 100.0

            # Determine status
            if score >= 90:
                status = "compliant"
            elif score >= 70:
                status = "partial"
            else:
                status = "non_compliant"

            # Generate recommendations
            recommendations = list(
                set(
                    pattern.suggestion
                    for pattern in patterns
                    if pattern.suggestion and any(f.get("rule_id") == pattern.id for f in findings)
                )
            )

            reports[standard.upper()] = ComplianceReport(
                standard=standard.upper(),
                status=status,
                score=score,
                findings=findings,
                recommendations=recommendations,
            )

        return reports

    def _generate_pdf_report(self, result: CodePolicyResult) -> str:
        """
        Generate PDF compliance report (Enterprise tier).

        [20251226_FEATURE] Enterprise tier PDF generation.

        Returns base64-encoded PDF content.
        """
        # Simple HTML-based PDF (requires weasyprint or similar)
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Code Policy Compliance Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                h1 {{ color: #333; }}
                .summary {{ background: #f5f5f5; padding: 20px; margin: 20px 0; }}
                .score {{ font-size: 48px; font-weight: bold; color: {'green' if result.compliance_score >= 90 else 'orange' if result.compliance_score >= 70 else 'red'}; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #4CAF50; color: white; }}
                .critical {{ color: red; font-weight: bold; }}
                .warning {{ color: orange; }}
            </style>
        </head>
        <body>
            <h1>Code Policy Compliance Report</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

            <div class="summary">
                <h2>Executive Summary</h2>
                <p class="score">{result.compliance_score:.1f}%</p>
                <p>Files Checked: {result.files_checked}</p>
                <p>Rules Applied: {result.rules_applied}</p>
                <p>Violations Found: {len(result.violations)}</p>
            </div>

            <h2>Compliance Status by Standard</h2>
            <table>
                <tr>
                    <th>Standard</th>
                    <th>Status</th>
                    <th>Score</th>
                    <th>Findings</th>
                </tr>
        """

        for standard, report in result.compliance_reports.items():
            html_content += f"""
                <tr>
                    <td>{standard}</td>
                    <td>{report.status.upper()}</td>
                    <td>{report.score:.1f}%</td>
                    <td>{len(report.findings)}</td>
                </tr>
            """

        html_content += """
            </table>

            <h2>Critical Findings</h2>
        """

        critical = [v for v in result.violations if v.severity == ViolationSeverity.CRITICAL]

        if critical:
            html_content += "<ul>"
            for v in critical[:20]:  # Limit to 20
                html_content += f"<li class='critical'>{v.file}:{v.line} - {v.message}</li>"
            html_content += "</ul>"
        else:
            html_content += "<p>No critical findings.</p>"

        html_content += """
            <div style="margin-top: 50px; border-top: 1px solid #ccc; padding-top: 20px;">
                <p><em>This report was generated by Code Scalpel Enterprise.</em></p>
            </div>
        </body>
        </html>
        """

        # For now, return base64-encoded HTML
        # In production, use weasyprint to convert to PDF
        return base64.b64encode(html_content.encode()).decode()

    def _generate_certifications(self, reports: dict[str, ComplianceReport]) -> list[Certification]:
        """
        Generate certifications for passing standards (Enterprise tier).

        [20251226_FEATURE] Enterprise tier certification generation.
        """
        certifications: list[Certification] = []

        for standard, report in reports.items():
            if report.status == "compliant":
                cert_id = (
                    hashlib.sha256(f"{standard}:{datetime.now().isoformat()}:{uuid.uuid4()}".encode())
                    .hexdigest()[:16]
                    .upper()
                )

                certifications.append(
                    Certification(
                        standard=standard,
                        issued_date=datetime.now(),
                        valid_until=datetime.now() + timedelta(days=90),
                        certificate_id=f"CS-{standard}-{cert_id}",
                        issuer="Code Scalpel Enterprise",
                        status="valid",
                    )
                )

        return certifications

    def _build_summary(
        self,
        files_checked: int,
        violations: int,
        critical: int,
        best_practices: int,
        security: int,
    ) -> str:
        """Build human-readable summary."""
        parts = [f"Checked {files_checked} files"]

        if violations == 0:
            parts.append("no policy violations found")
        else:
            parts.append(f"found {violations} policy violations")
            if critical > 0:
                parts.append(f"({critical} critical)")

        if self.tier in ("pro", "enterprise"):
            if best_practices > 0:
                parts.append(f"{best_practices} best practice issues")
            if security > 0:
                parts.append(f"{security} security warnings")

        return "; ".join(parts) + "."

    def _save_audit_entry(self, entry: AuditEntry) -> None:
        """
        Save audit entry to persistent storage.

        [20251229_FEATURE] Persist audit logs to .code-scalpel/audit.jsonl
        """
        try:
            # Determine audit log path
            audit_dir = Path(".code-scalpel")
            if not audit_dir.exists():
                audit_dir.mkdir(parents=True, exist_ok=True)

            audit_file = audit_dir / "audit.jsonl"

            # Convert entry to dict
            entry_dict = {
                "timestamp": entry.timestamp.isoformat(),
                "action": entry.action,
                "user": entry.user,
                "files_checked": entry.files_checked,
                "rules_applied": entry.rules_applied,
                "violations_found": entry.violations_found,
                "compliance_standards": entry.compliance_standards,
                "metadata": entry.metadata,
            }

            # Append to file
            with open(audit_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry_dict) + "\n")

        except Exception as e:
            logger.warning(f"Failed to save audit entry: {e}")
