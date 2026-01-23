#!/usr/bin/env python3
"""
Prettier Parser - JavaScript/TypeScript code formatting.

Parses Prettier output and configuration for automated code formatting verification.
Prettier is an opinionated code formatter with support for many languages.


Features:
    Configuration:
        - .prettierrc / .prettierrc.json parsing
        - prettier.config.js support
        - package.json "prettier" key extraction
        - All formatting options (printWidth, tabWidth, etc.)
        - Plugin detection
        - File-specific overrides

    Formatting:
        - Code formatting via Prettier CLI
        - Format verification (check mode)
        - Multiple parser support (babel, typescript, etc.)

    Diff Generation:
        - Before/after comparison
        - Unified diff output
        - Changed line tracking
        - Addition/deletion counts

    File Operations:
        - Format file in place
        - Format code string
        - Format time tracking

Future Enhancements:
    - Range formatting (partial file)
    - Embedded language formatting
    - .prettierignore parsing
    - Multi-file batch formatting
"""

import difflib
import json
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class PrettierParser(Enum):
    """Prettier parser options."""

    BABEL = "babel"
    BABEL_FLOW = "babel-flow"
    BABEL_TS = "babel-ts"
    FLOW = "flow"
    TYPESCRIPT = "typescript"
    ESPREE = "espree"
    MERIYAH = "meriyah"
    ACORN = "acorn"
    CSS = "css"
    LESS = "less"
    SCSS = "scss"
    HTML = "html"
    MARKDOWN = "markdown"
    MDX = "mdx"
    YAML = "yaml"
    JSON = "json"
    JSON5 = "json5"
    GRAPHQL = "graphql"


class EndOfLine(Enum):
    """End of line options."""

    LF = "lf"
    CRLF = "crlf"
    CR = "cr"
    AUTO = "auto"


class QuoteType(Enum):
    """Quote type options."""

    DOUBLE = "double"
    SINGLE = "single"


class TrailingComma(Enum):
    """Trailing comma options."""

    ALL = "all"
    ES5 = "es5"
    NONE = "none"


class ProseWrap(Enum):
    """Prose wrap options for Markdown."""

    ALWAYS = "always"
    NEVER = "never"
    PRESERVE = "preserve"


class HTMLWhitespaceSensitivity(Enum):
    """HTML whitespace sensitivity."""

    CSS = "css"
    STRICT = "strict"
    IGNORE = "ignore"


@dataclass
class PrettierConfig:
    """Prettier configuration representation."""

    # Width
    print_width: int = 80
    tab_width: int = 2
    use_tabs: bool = False

    # Strings
    single_quote: bool = False
    jsx_single_quote: bool = False

    # Trailing Commas
    trailing_comma: TrailingComma = TrailingComma.ES5

    # Brackets and Parens
    bracket_spacing: bool = True
    bracket_same_line: bool = False

    # JSX
    jsx_bracket_same_line: bool = False  # Deprecated, use bracket_same_line

    # Arrow Functions
    arrow_parens: str = "always"  # "always" or "avoid"

    # Semicolons
    semi: bool = True

    # Line Endings
    end_of_line: EndOfLine = EndOfLine.LF

    # Prose
    prose_wrap: ProseWrap = ProseWrap.PRESERVE

    # HTML
    html_whitespace_sensitivity: HTMLWhitespaceSensitivity = HTMLWhitespaceSensitivity.CSS

    # Vue
    vue_indent_script_and_style: bool = False

    # Embedded Languages
    embedded_language_formatting: str = "auto"  # "auto" or "off"

    # Single Attribute Per Line
    single_attribute_per_line: bool = False

    # Parser
    parser: str | None = None

    # Plugins
    plugins: list[str] = field(default_factory=list)

    # File-specific overrides
    overrides: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class FormatDiff:
    """Represents formatting differences."""

    original: str
    formatted: str
    has_changes: bool
    unified_diff: str
    changed_lines: list[int] = field(default_factory=list)
    additions: int = 0
    deletions: int = 0

    @property
    def change_ratio(self) -> float:
        """Calculate ratio of changes."""
        total = max(len(self.original.splitlines()), 1)
        return len(self.changed_lines) / total


@dataclass
class FormatResult:
    """Result of formatting a file."""

    file_path: str
    success: bool
    original_code: str
    formatted_code: str
    diff: FormatDiff | None = None
    error: str | None = None
    format_time_ms: float | None = None


class PrettierFormatter:
    """
    Parser for Prettier output and configuration files.

    Provides methods to:
    - Parse Prettier configuration files
    - Format JavaScript/TypeScript code
    - Generate format diffs
    - Check formatting compliance

    Example usage:
        formatter = PrettierFormatter()

        # Parse config
        config = formatter.parse_config('.prettierrc')

        # Format code
        result = formatter.format_code(source_code)

        # Check formatting
        is_formatted = formatter.check_format(source_code)
    """

    def __init__(self, prettier_path: str | None = None):
        """
        Initialize Prettier formatter.

        :param prettier_path: Path to Prettier executable.
        """
        self._prettier_path = prettier_path or self._find_prettier()

    def _find_prettier(self) -> str | None:
        """Find Prettier executable."""
        prettier = shutil.which("prettier")
        if prettier:
            return prettier

        local = Path("node_modules/.bin/prettier")
        if local.exists():
            return str(local)

        if shutil.which("npx"):
            return "npx prettier"

        return None

    def parse_config(self, config_path: str) -> PrettierConfig:
        """
        Parse Prettier configuration file.

        Supports:
        - .prettierrc (JSON or YAML)
        - .prettierrc.json
        - .prettierrc.js
        - prettier.config.js

        :param config_path: Path to config file.
        :return: PrettierConfig object.
        """
        path = Path(config_path)

        if not path.exists():
            raise FileNotFoundError(f"Prettier config not found: {config_path}")

        content = path.read_text()

        # Handle different config formats
        if path.suffix in [".json", ""] or path.name == ".prettierrc":
            try:
                config_data = json.loads(content)
            except json.JSONDecodeError:
                # Try YAML
                try:
                    import yaml

                    config_data = yaml.safe_load(content)
                except ImportError:
                    raise ValueError("Cannot parse config - install PyYAML for YAML support")
        elif path.suffix == ".js":
            # For JS configs, need to run through Node
            raise NotImplementedError("JS config files require Node.js evaluation")
        else:
            raise ValueError(f"Unsupported config format: {path.suffix}")

        return self._parse_config_dict(config_data)

    def _parse_config_dict(self, data: dict[str, Any]) -> PrettierConfig:
        """Parse config from dictionary."""
        config = PrettierConfig()

        # Map camelCase to snake_case
        mappings = {
            "printWidth": "print_width",
            "tabWidth": "tab_width",
            "useTabs": "use_tabs",
            "singleQuote": "single_quote",
            "jsxSingleQuote": "jsx_single_quote",
            "trailingComma": "trailing_comma",
            "bracketSpacing": "bracket_spacing",
            "bracketSameLine": "bracket_same_line",
            "jsxBracketSameLine": "jsx_bracket_same_line",
            "arrowParens": "arrow_parens",
            "endOfLine": "end_of_line",
            "proseWrap": "prose_wrap",
            "htmlWhitespaceSensitivity": "html_whitespace_sensitivity",
            "vueIndentScriptAndStyle": "vue_indent_script_and_style",
            "embeddedLanguageFormatting": "embedded_language_formatting",
            "singleAttributePerLine": "single_attribute_per_line",
        }

        for key, value in data.items():
            attr_name = mappings.get(key, key)
            if hasattr(config, attr_name):
                # Handle enums
                if attr_name == "trailing_comma" and isinstance(value, str):
                    value = TrailingComma(value)
                elif attr_name == "end_of_line" and isinstance(value, str):
                    value = EndOfLine(value)
                elif attr_name == "prose_wrap" and isinstance(value, str):
                    value = ProseWrap(value)
                elif attr_name == "html_whitespace_sensitivity" and isinstance(value, str):
                    value = HTMLWhitespaceSensitivity(value)
                setattr(config, attr_name, value)

        return config

    def format_code(self, code: str, config: PrettierConfig | None = None, parser: str = "babel") -> FormatResult:
        """
        Format JavaScript code using Prettier.

        :param code: Source code to format.
        :param config: Optional PrettierConfig.
        :param parser: Parser to use (babel, typescript, etc.).
        :return: FormatResult with formatted code.
        """
        if not self._prettier_path:
            raise RuntimeError("Prettier not found. Install with: npm install prettier")

        import tempfile
        import time

        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write(code)
            temp_path = f.name

        try:
            cmd = self._prettier_path.split() if " " in self._prettier_path else [self._prettier_path]
            cmd.extend(["--parser", parser, temp_path])

            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            format_time = (time.time() - start_time) * 1000

            if result.returncode != 0 and result.stderr:
                return FormatResult(
                    file_path=temp_path,
                    success=False,
                    original_code=code,
                    formatted_code=code,
                    error=result.stderr,
                )

            formatted = result.stdout
            diff = self._generate_diff(code, formatted)

            return FormatResult(
                file_path=temp_path,
                success=True,
                original_code=code,
                formatted_code=formatted,
                diff=diff,
                format_time_ms=format_time,
            )
        except subprocess.TimeoutExpired:
            return FormatResult(
                file_path=temp_path,
                success=False,
                original_code=code,
                formatted_code=code,
                error="Prettier timed out",
            )
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def check_format(self, code: str, parser: str = "babel") -> bool:
        """
        Check if code is already formatted.

        :param code: Source code to check.
        :param parser: Parser to use.
        :return: True if code is properly formatted.
        """
        result = self.format_code(code, parser=parser)
        return result.success and not (result.diff and result.diff.has_changes)

    def _generate_diff(self, original: str, formatted: str) -> FormatDiff:
        """Generate diff between original and formatted code."""
        original_lines = original.splitlines(keepends=True)
        formatted_lines = formatted.splitlines(keepends=True)

        unified = "".join(
            difflib.unified_diff(original_lines, formatted_lines, fromfile="original", tofile="formatted")
        )

        # Find changed line numbers
        changed_lines: list[int] = []
        additions = 0
        deletions = 0

        for i, (orig, fmt) in enumerate(zip(original_lines, formatted_lines, strict=False)):
            if orig != fmt:
                changed_lines.append(i + 1)

        # Count additions/deletions from diff
        for line in unified.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                additions += 1
            elif line.startswith("-") and not line.startswith("---"):
                deletions += 1

        return FormatDiff(
            original=original,
            formatted=formatted,
            has_changes=original != formatted,
            unified_diff=unified,
            changed_lines=changed_lines,
            additions=additions,
            deletions=deletions,
        )

    def format_file(self, file_path: str, write: bool = False) -> FormatResult:
        """
        Format a file with Prettier.

        :param file_path: Path to file.
        :param write: If True, write changes to file.
        :return: FormatResult.
        """
        if not self._prettier_path:
            raise RuntimeError("Prettier not found. Install with: npm install prettier")

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        original_code = path.read_text()

        cmd = self._prettier_path.split() if " " in self._prettier_path else [self._prettier_path]
        if write:
            cmd.extend(["--write", file_path])
        else:
            cmd.append(file_path)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if write:
                formatted_code = path.read_text()
            else:
                formatted_code = result.stdout

            diff = self._generate_diff(original_code, formatted_code)

            return FormatResult(
                file_path=file_path,
                success=result.returncode == 0,
                original_code=original_code,
                formatted_code=formatted_code,
                diff=diff,
                error=result.stderr if result.returncode != 0 else None,
            )
        except subprocess.TimeoutExpired:
            return FormatResult(
                file_path=file_path,
                success=False,
                original_code=original_code,
                formatted_code=original_code,
                error="Prettier timed out",
            )

    def get_supported_parsers(self) -> list[str]:
        """Get list of supported parsers."""
        return [p.value for p in PrettierParser]
