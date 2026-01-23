#!/usr/bin/env python3
"""
ESLint Parser - JavaScript/TypeScript linting integration.

Parses ESLint output (JSON format) for comprehensive code quality analysis.
Supports custom rules, plugins, and configuration parsing.

ESLint is the most widely used JavaScript linter with extensive plugin ecosystem.
Features:
    Output Parsing:
        - ESLint JSON format parsing
        - Rule violation extraction with severity levels
        - Fix suggestions extraction
        - Fixable violation filtering

    Configuration:
        - .eslintrc.json / .eslintrc.yaml parsing
        - Plugin and extends resolution
        - Environment and globals extraction
        - Parser options extraction

    Inline Directives:
        - eslint-disable / eslint-enable parsing
        - eslint-disable-line / eslint-disable-next-line
        - Block directive pairing (start/end lines)
        - Suppression report generation

    Rule Documentation:
        - Automatic docs URL generation for core rules
        - Plugin rule URL mapping (@typescript-eslint, react, etc.)

    Execution:
        - Real-time ESLint execution via subprocess
        - File and code string analysis
        - Configurable ESLint path
"""

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class ESLintSeverity(Enum):
    """ESLint severity levels."""

    OFF = 0
    WARN = 1
    ERROR = 2


class ESLintDirectiveType(Enum):
    """Types of ESLint inline directives."""

    DISABLE = "disable"
    DISABLE_LINE = "disable-line"
    DISABLE_NEXT_LINE = "disable-next-line"
    ENABLE = "enable"
    ENV = "env"
    GLOBAL = "global"
    GLOBALS = "globals"


@dataclass
class ESLintDirective:
    """Represents an ESLint inline directive (comment)."""

    directive_type: ESLintDirectiveType
    line: int
    rules: list[str] = field(default_factory=list)  # Empty means all rules
    description: str | None = None
    end_line: int | None = None  # For block disable


@dataclass
class ESLintViolation:
    """Represents a single ESLint rule violation."""

    rule_id: str
    message: str
    severity: ESLintSeverity
    line: int
    column: int
    end_line: int | None = None
    end_column: int | None = None
    node_type: str | None = None
    fix: dict[str, Any] | None = None  # {range: [start, end], text: "replacement"}
    suggestions: list[dict[str, Any]] = field(default_factory=list)
    docs_url: str | None = None  # Rule documentation URL

    @property
    def is_fixable(self) -> bool:
        """Check if this violation has an auto-fix available."""
        return self.fix is not None or len(self.suggestions) > 0

    def get_docs_url(self) -> str:
        """Get the documentation URL for this rule."""
        if self.docs_url:
            return self.docs_url

        # Generate URL based on rule source
        if "/" in self.rule_id:
            # Plugin rule: plugin/rule-name
            plugin, rule = self.rule_id.split("/", 1)
            plugin_urls = {
                "@typescript-eslint": f"https://typescript-eslint.io/rules/{rule}",
                "react": f"https://github.com/jsx-eslint/eslint-plugin-react/blob/master/docs/rules/{rule}.md",
                "react-hooks": "https://reactjs.org/docs/hooks-rules.html",
                "import": f"https://github.com/import-js/eslint-plugin-import/blob/main/docs/rules/{rule}.md",
                "jsx-a11y": f"https://github.com/jsx-eslint/eslint-plugin-jsx-a11y/blob/main/docs/rules/{rule}.md",
                "node": f"https://github.com/eslint-community/eslint-plugin-n/blob/master/docs/rules/{rule}.md",
                "promise": f"https://github.com/eslint-community/eslint-plugin-promise/blob/main/docs/rules/{rule}.md",
            }
            return plugin_urls.get(plugin, f"https://www.npmjs.com/package/eslint-plugin-{plugin}")
        else:
            # Core ESLint rule
            return f"https://eslint.org/docs/latest/rules/{self.rule_id}"


@dataclass
class ESLintFileResult:
    """ESLint results for a single file."""

    file_path: str
    violations: list[ESLintViolation] = field(default_factory=list)
    directives: list[ESLintDirective] = field(default_factory=list)
    error_count: int = 0
    warning_count: int = 0
    fixable_error_count: int = 0
    fixable_warning_count: int = 0
    source: str | None = None  # Original source if requested

    @property
    def has_errors(self) -> bool:
        """Check if file has any errors."""
        return self.error_count > 0

    @property
    def suppressed_rules(self) -> set[str]:
        """Get set of rules that are disabled via directives."""
        suppressed: set[str] = set()
        for directive in self.directives:
            if directive.directive_type in (
                ESLintDirectiveType.DISABLE,
                ESLintDirectiveType.DISABLE_LINE,
                ESLintDirectiveType.DISABLE_NEXT_LINE,
            ):
                suppressed.update(directive.rules)
        return suppressed


@dataclass
class ESLintConfig:
    """ESLint configuration representation."""

    extends: list[str] = field(default_factory=list)
    plugins: list[str] = field(default_factory=list)
    rules: dict[str, Any] = field(default_factory=dict)
    env: dict[str, bool] = field(default_factory=dict)
    globals: dict[str, str] = field(default_factory=dict)
    parser: str | None = None
    parser_options: dict[str, Any] = field(default_factory=dict)
    settings: dict[str, Any] = field(default_factory=dict)
    ignore_patterns: list[str] = field(default_factory=list)


class ESLintParser:
    """
    Parser for ESLint output and configuration files.

    Provides methods to:
    - Parse ESLint JSON output into structured results
    - Parse ESLint configuration files
    - Execute ESLint on source code
    - Extract fixable violations

    Example usage:
        parser = ESLintParser()

        # Parse existing ESLint JSON output
        results = parser.parse_output(json_string)

        # Run ESLint on code
        results = parser.analyze_code(source_code)

        # Parse config file
        config = parser.parse_config('.eslintrc.json')
    """

    def __init__(self, eslint_path: str | None = None):
        """
        Initialize ESLint parser.

        :param eslint_path: Path to ESLint executable. If None, uses 'npx eslint'.
        """
        self._eslint_path = eslint_path or self._find_eslint()

    def _find_eslint(self) -> str | None:
        """Find ESLint executable in PATH or node_modules."""
        # Check if eslint is in PATH
        eslint = shutil.which("eslint")
        if eslint:
            return eslint

        # Check local node_modules
        local_eslint = Path("node_modules/.bin/eslint")
        if local_eslint.exists():
            return str(local_eslint)

        # Fall back to npx
        if shutil.which("npx"):
            return "npx eslint"

        return None

    def parse_output(self, json_output: str) -> list[ESLintFileResult]:
        """
        Parse ESLint JSON format output.

        :param json_output: ESLint output in JSON format (--format=json).
        :return: List of ESLintFileResult for each file.
        """
        try:
            data = json.loads(json_output)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid ESLint JSON output: {e}")

        results: list[ESLintFileResult] = []

        for file_data in data:
            violations: list[ESLintViolation] = []

            for msg in file_data.get("messages", []):
                severity = ESLintSeverity(msg.get("severity", 1))

                violation = ESLintViolation(
                    rule_id=msg.get("ruleId", "unknown"),
                    message=msg.get("message", ""),
                    severity=severity,
                    line=msg.get("line", 0),
                    column=msg.get("column", 0),
                    end_line=msg.get("endLine"),
                    end_column=msg.get("endColumn"),
                    node_type=msg.get("nodeType"),
                    fix=msg.get("fix"),
                    suggestions=msg.get("suggestions", []),
                )
                violations.append(violation)

            result = ESLintFileResult(
                file_path=file_data.get("filePath", ""),
                violations=violations,
                error_count=file_data.get("errorCount", 0),
                warning_count=file_data.get("warningCount", 0),
                fixable_error_count=file_data.get("fixableErrorCount", 0),
                fixable_warning_count=file_data.get("fixableWarningCount", 0),
                source=file_data.get("source"),
            )
            results.append(result)

        return results

    def parse_config(self, config_path: str) -> ESLintConfig:
        """
        Parse ESLint configuration file.

        :param config_path: Path to .eslintrc.json, .eslintrc.js, etc.
        :return: ESLintConfig object.
        """
        path = Path(config_path)

        if not path.exists():
            raise FileNotFoundError(f"ESLint config not found: {config_path}")

        config_data: dict[str, Any] = {}

        if path.suffix == ".json" or path.name == ".eslintrc":
            with open(path) as f:
                config_data = json.load(f)
        elif path.suffix in (".js", ".cjs", ".mjs"):
            # For JS configs, we'd need to execute them - simplified here
            raise NotImplementedError("JavaScript ESLint configs require Node.js execution")
        elif path.suffix in (".yaml", ".yml"):
            try:
                import yaml

                with open(path) as f:
                    config_data = yaml.safe_load(f)
            except ImportError:
                raise ImportError("PyYAML required for YAML config parsing")

        # Build extends list safely
        extends_raw = config_data.get("extends", [])
        if isinstance(extends_raw, list):
            extends_list: list[str] = [str(e) for e in extends_raw if e is not None]
        elif extends_raw:
            extends_list = [str(extends_raw)]
        else:
            extends_list = []

        return ESLintConfig(
            extends=extends_list,
            plugins=config_data.get("plugins", []),
            rules=config_data.get("rules", {}),
            env=config_data.get("env", {}),
            globals=config_data.get("globals", {}),
            parser=config_data.get("parser"),
            parser_options=config_data.get("parserOptions", {}),
            settings=config_data.get("settings", {}),
            ignore_patterns=config_data.get("ignorePatterns", []),
        )

    def analyze_file(self, file_path: str, config_path: str | None = None) -> ESLintFileResult:
        """
        Run ESLint on a file and return results.

        :param file_path: Path to JavaScript/TypeScript file.
        :param config_path: Optional path to ESLint config.
        :return: ESLintFileResult with violations.
        """
        if not self._eslint_path:
            raise RuntimeError("ESLint not found. Install with: npm install eslint")

        cmd = [self._eslint_path, "--format=json", file_path]
        if config_path:
            cmd.extend(["--config", config_path])

        # Handle 'npx eslint' as a single command
        if " " in self._eslint_path:
            cmd = self._eslint_path.split() + ["--format=json", file_path]
            if config_path:
                cmd.extend(["--config", config_path])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )
            # ESLint returns non-zero on lint errors, but still outputs JSON
            output = result.stdout or result.stderr
            results = self.parse_output(output)
            return results[0] if results else ESLintFileResult(file_path=file_path)
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"ESLint timed out analyzing {file_path}")
        except subprocess.SubprocessError as e:
            raise RuntimeError(f"ESLint execution failed: {e}")

    def analyze_code(
        self,
        code: str,
        filename: str = "input.js",
        config_path: str | None = None,
        parse_directives: bool = True,
    ) -> ESLintFileResult:
        """
        Run ESLint on source code string.

        :param code: JavaScript/TypeScript source code.
        :param filename: Virtual filename for the code.
        :param config_path: Optional path to ESLint config.
        :param parse_directives: Whether to parse inline directives.
        :return: ESLintFileResult with violations.
        """
        if not self._eslint_path:
            raise RuntimeError("ESLint not found. Install with: npm install eslint")

        cmd = [
            self._eslint_path,
            "--format=json",
            "--stdin",
            "--stdin-filename",
            filename,
        ]
        if config_path:
            cmd.extend(["--config", config_path])

        if " " in self._eslint_path:
            cmd = self._eslint_path.split() + [
                "--format=json",
                "--stdin",
                "--stdin-filename",
                filename,
            ]
            if config_path:
                cmd.extend(["--config", config_path])

        try:
            result = subprocess.run(
                cmd,
                input=code,
                capture_output=True,
                text=True,
                timeout=60,
            )
            output = result.stdout or result.stderr
            results = self.parse_output(output)
            file_result = results[0] if results else ESLintFileResult(file_path=filename)

            # Parse inline directives if requested
            if parse_directives:
                file_result.directives = self.parse_directives(code)

            return file_result
        except subprocess.TimeoutExpired:
            raise TimeoutError("ESLint timed out analyzing code")
        except subprocess.SubprocessError as e:
            raise RuntimeError(f"ESLint execution failed: {e}")

    def parse_directives(self, code: str) -> list[ESLintDirective]:
        """
        Parse ESLint inline directives from source code.

        Supports:
        - eslint-disable
        - eslint-disable-line
        - eslint-disable-next-line
        - eslint-enable
        - eslint-env
        - global / globals

        :param code: JavaScript/TypeScript source code.
        :return: List of ESLintDirective objects.
        """
        directives: list[ESLintDirective] = []
        lines = code.split("\n")

        # Patterns for different directive types
        patterns = {
            ESLintDirectiveType.DISABLE: re.compile(r"/\*\s*eslint-disable\s*(?:(?!eslint-enable)\s+([^*]+))?\s*\*/"),
            ESLintDirectiveType.DISABLE_LINE: re.compile(r"//\s*eslint-disable-line\s*(.*)$"),
            ESLintDirectiveType.DISABLE_NEXT_LINE: re.compile(r"//\s*eslint-disable-next-line\s*(.*)$"),
            ESLintDirectiveType.ENABLE: re.compile(r"/\*\s*eslint-enable\s*([^*]*)\s*\*/"),
            ESLintDirectiveType.ENV: re.compile(r"/\*\s*eslint-env\s+([^*]+)\s*\*/"),
            ESLintDirectiveType.GLOBAL: re.compile(r"/\*\s*globals?\s+([^*]+)\s*\*/"),
        }

        # Also match single-line disable/enable
        single_line_disable = re.compile(r"//\s*eslint-disable\s*(.*)$")

        for i, line in enumerate(lines, 1):
            # Check block comments
            for dtype, pattern in patterns.items():
                match = pattern.search(line)
                if match:
                    rules_str = match.group(1) if match.lastindex else ""
                    rules = self._parse_rule_list(rules_str)

                    # Extract description (text after --)
                    description = None
                    if "--" in rules_str:
                        _, description = rules_str.split("--", 1)
                        description = description.strip()

                    directives.append(
                        ESLintDirective(
                            directive_type=dtype,
                            line=i,
                            rules=rules,
                            description=description,
                        )
                    )

            # Single-line disable comment
            match = single_line_disable.search(line)
            if match and "eslint-disable-line" not in line and "eslint-disable-next-line" not in line:
                rules_str = match.group(1) if match.lastindex else ""
                rules = self._parse_rule_list(rules_str)
                directives.append(
                    ESLintDirective(
                        directive_type=ESLintDirectiveType.DISABLE_LINE,
                        line=i,
                        rules=rules,
                    )
                )

        # Find block disable/enable pairs
        self._pair_block_directives(directives)

        return directives

    def _parse_rule_list(self, rules_str: str) -> list[str]:
        """Parse comma-separated rule list from directive."""
        if not rules_str:
            return []

        # Remove description part
        if "--" in rules_str:
            rules_str = rules_str.split("--")[0]

        # Split and clean
        rules = []
        for rule in rules_str.split(","):
            rule = rule.strip()
            # Remove any trailing comments or whitespace
            if rule and not rule.startswith("--"):
                # Handle rules with options like "rule: 'option'"
                rule_name = rule.split(":")[0].strip()
                if rule_name:
                    rules.append(rule_name)

        return rules

    def _pair_block_directives(self, directives: list[ESLintDirective]) -> None:
        """Find matching enable for disable directives to set end_line."""
        disable_stack: list[ESLintDirective] = []

        for directive in directives:
            if directive.directive_type == ESLintDirectiveType.DISABLE:
                disable_stack.append(directive)
            elif directive.directive_type == ESLintDirectiveType.ENABLE:
                # Find matching disable
                for i in range(len(disable_stack) - 1, -1, -1):
                    disable = disable_stack[i]
                    # Match if rules overlap or enable has no rules (enables all)
                    if not directive.rules or not disable.rules:
                        disable.end_line = directive.line
                        disable_stack.pop(i)
                        break
                    elif set(disable.rules) & set(directive.rules):
                        disable.end_line = directive.line
                        disable_stack.pop(i)
                        break

    def get_rule_docs_urls(self, result: ESLintFileResult) -> dict[str, str]:
        """
        Get documentation URLs for all rules with violations.

        :param result: ESLintFileResult to extract URLs from.
        :return: Dictionary mapping rule IDs to documentation URLs.
        """
        return {v.rule_id: v.get_docs_url() for v in result.violations}

    def get_fixable_violations(self, result: ESLintFileResult) -> list[ESLintViolation]:
        """
        Get all fixable violations from a result.

        :param result: ESLintFileResult to filter.
        :return: List of fixable violations.
        """
        return [v for v in result.violations if v.is_fixable]

    def get_errors(self, result: ESLintFileResult) -> list[ESLintViolation]:
        """
        Get only error-severity violations.

        :param result: ESLintFileResult to filter.
        :return: List of error violations.
        """
        return [v for v in result.violations if v.severity == ESLintSeverity.ERROR]

    def get_warnings(self, result: ESLintFileResult) -> list[ESLintViolation]:
        """
        Get only warning-severity violations.

        :param result: ESLintFileResult to filter.
        :return: List of warning violations.
        """
        return [v for v in result.violations if v.severity == ESLintSeverity.WARN]

    def group_by_rule(self, result: ESLintFileResult) -> dict[str, list[ESLintViolation]]:
        """
        Group violations by rule ID.

        :param result: ESLintFileResult to group.
        :return: Dictionary mapping rule IDs to their violations.
        """
        grouped: dict[str, list[ESLintViolation]] = {}
        for violation in result.violations:
            if violation.rule_id not in grouped:
                grouped[violation.rule_id] = []
            grouped[violation.rule_id].append(violation)
        return grouped

    def get_suppression_report(self, result: ESLintFileResult) -> dict[str, Any]:
        """
        Generate a report of suppressed rules via inline directives.

        :param result: ESLintFileResult to analyze.
        :return: Report with suppressed rules and directive usage.
        """
        report: dict[str, Any] = {
            "total_directives": len(result.directives),
            "suppressed_rules": list(result.suppressed_rules),
            "disable_all_count": sum(
                1
                for d in result.directives
                if d.directive_type
                in (
                    ESLintDirectiveType.DISABLE,
                    ESLintDirectiveType.DISABLE_LINE,
                    ESLintDirectiveType.DISABLE_NEXT_LINE,
                )
                and not d.rules
            ),
            "directives_by_type": {},
            "rules_suppression_count": {},
        }

        # Count by type
        for directive in result.directives:
            dtype = directive.directive_type.value
            report["directives_by_type"][dtype] = report["directives_by_type"].get(dtype, 0) + 1

            # Count per-rule suppressions
            for rule in directive.rules:
                report["rules_suppression_count"][rule] = report["rules_suppression_count"].get(rule, 0) + 1

        return report
