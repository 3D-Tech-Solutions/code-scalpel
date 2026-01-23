#!/usr/bin/env python3
"""
Babel Parser - Modern JavaScript/JSX parsing with latest ECMAScript support.
Babel is the industry-standard JavaScript compiler that supports the latest
ECMAScript features, JSX, TypeScript, and Flow. This parser leverages Babel
for comprehensive JavaScript analysis.
Features:
    Syntax Detection:
        - ECMAScript version detection (ES5 through ES2024+)
        - Arrow functions, template literals, destructuring
        - Async/await, optional chaining, nullish coalescing
        - Private fields, static blocks, decorators
        - Logical assignment, numeric separators, BigInt

    JSX Analysis:
        - Element detection and prop extraction
        - Component vs HTML element differentiation
        - Spread props detection
        - Self-closing tag detection

    Configuration:
        - .babelrc / babel.config.json parsing
        - Plugin and preset extraction
        - Target browser/environment detection

    Transformation:
        - Code transformation via Babel CLI
        - Source map generation
        - Polyfill requirement detection
"""

import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class ECMAScriptVersion(Enum):
    """ECMAScript versions."""

    ES5 = "es5"
    ES2015 = "es2015"  # ES6
    ES2016 = "es2016"
    ES2017 = "es2017"
    ES2018 = "es2018"
    ES2019 = "es2019"
    ES2020 = "es2020"
    ES2021 = "es2021"
    ES2022 = "es2022"
    ES2023 = "es2023"
    ES2024 = "es2024"
    ESNEXT = "esnext"


class ProposalStage(Enum):
    """TC39 proposal stages."""

    STAGE_0 = 0  # Strawman
    STAGE_1 = 1  # Proposal
    STAGE_2 = 2  # Draft
    STAGE_3 = 3  # Candidate
    STAGE_4 = 4  # Finished


@dataclass
class BabelPlugin:
    """A Babel plugin configuration."""

    name: str
    options: dict[str, Any] = field(default_factory=dict)
    is_official: bool = False  # @babel/* plugin
    proposal_stage: ProposalStage | None = None


@dataclass
class BabelPreset:
    """A Babel preset configuration."""

    name: str
    options: dict[str, Any] = field(default_factory=dict)
    included_plugins: list[str] = field(default_factory=list)


@dataclass
class BabelConfig:
    """Babel configuration."""

    presets: list[BabelPreset] = field(default_factory=list)
    plugins: list[BabelPlugin] = field(default_factory=list)
    targets: dict[str, Any] = field(default_factory=dict)  # Browser/Node targets
    source_type: str = "module"  # "module", "script", "unambiguous"
    assumptions: dict[str, bool] = field(default_factory=dict)
    env: dict[str, Any] = field(default_factory=dict)  # Environment-specific config
    ignore: list[str] = field(default_factory=list)
    only: list[str] = field(default_factory=list)


@dataclass
class SyntaxFeature:
    """A JavaScript syntax feature detected in code."""

    name: str
    line: int
    column: int
    es_version: ECMAScriptVersion
    requires_plugin: str | None = None
    proposal_stage: ProposalStage | None = None
    description: str | None = None


@dataclass
class TransformationResult:
    """Result of Babel transformation."""

    original_code: str
    transformed_code: str
    source_map: dict[str, Any] | None = None
    plugins_used: list[str] = field(default_factory=list)
    helpers_injected: list[str] = field(default_factory=list)
    polyfills_needed: list[str] = field(default_factory=list)
    parse_time_ms: float = 0.0
    transform_time_ms: float = 0.0


@dataclass
class JSXElement:
    """A JSX element in the code."""

    tag_name: str
    line: int
    column: int
    is_self_closing: bool = False
    is_component: bool = False  # PascalCase = component
    props: list[str] = field(default_factory=list)
    spread_props: bool = False
    children_count: int = 0


@dataclass
class ModernJSSyntax:
    """Modern JavaScript syntax usage analysis."""

    arrow_functions: int = 0
    template_literals: int = 0
    destructuring: int = 0
    spread_operator: int = 0
    rest_parameters: int = 0
    default_parameters: int = 0
    async_await: int = 0
    optional_chaining: int = 0
    nullish_coalescing: int = 0
    private_fields: int = 0
    static_blocks: int = 0
    top_level_await: int = 0
    decorators: int = 0
    class_fields: int = 0
    logical_assignment: int = 0  # &&=, ||=, ??=


@dataclass
class BabelAnalysis:
    """Complete Babel analysis results."""

    config: BabelConfig | None = None
    syntax_features: list[SyntaxFeature] = field(default_factory=list)
    jsx_elements: list[JSXElement] = field(default_factory=list)
    modern_syntax: ModernJSSyntax | None = None
    min_es_version: ECMAScriptVersion = ECMAScriptVersion.ES5
    transformation: TransformationResult | None = None
    errors: list[str] = field(default_factory=list)


class BabelParser:
    """
    Parser using Babel for modern JavaScript analysis.

    Babel provides comprehensive support for:
    - Latest ECMAScript features
    - JSX transformation
    - TypeScript and Flow
    - Syntax proposals (Stage 0-4)
    - Custom plugins and presets

    Example usage:
        parser = BabelParser()

        # Analyze modern JS features
        analysis = parser.analyze(code)

        # Transform to ES5
        result = parser.transform(code, target=ECMAScriptVersion.ES5)

        # Parse config
        config = parser.parse_config('.babelrc')
    """

    # Syntax patterns for feature detection
    _PATTERNS = {
        "arrow_function": (re.compile(r"=>"), ECMAScriptVersion.ES2015),
        "template_literal": (re.compile(r"`[^`]*`"), ECMAScriptVersion.ES2015),
        "destructuring_array": (
            re.compile(r"(?:const|let|var)\s*\[[^\]]+\]\s*="),
            ECMAScriptVersion.ES2015,
        ),
        "destructuring_object": (
            re.compile(r"(?:const|let|var)\s*\{[^}]+\}\s*="),
            ECMAScriptVersion.ES2015,
        ),
        "spread_operator": (re.compile(r"\.\.\.(?!\.)"), ECMAScriptVersion.ES2015),
        "rest_parameter": (
            re.compile(r"\(\s*[^)]*\.\.\.\w+\s*\)"),
            ECMAScriptVersion.ES2015,
        ),
        "default_parameter": (
            re.compile(r"\([^)]*\w+\s*=[^)]+\)"),
            ECMAScriptVersion.ES2015,
        ),
        "async_function": (
            re.compile(r"\basync\s+(?:function|\()"),
            ECMAScriptVersion.ES2017,
        ),
        "await_expression": (re.compile(r"\bawait\s+"), ECMAScriptVersion.ES2017),
        "optional_chaining": (
            re.compile(r"\?\.\s*(?:\w|\[|\()"),
            ECMAScriptVersion.ES2020,
        ),
        "nullish_coalescing": (re.compile(r"\?\?(?!\?)"), ECMAScriptVersion.ES2020),
        "private_field": (re.compile(r"#\w+"), ECMAScriptVersion.ES2022),
        "static_block": (re.compile(r"static\s*\{"), ECMAScriptVersion.ES2022),
        "top_level_await": (
            re.compile(r"^await\s+", re.MULTILINE),
            ECMAScriptVersion.ES2022,
        ),
        "decorator": (re.compile(r"@\w+(?:\([^)]*\))?"), ECMAScriptVersion.ESNEXT),
        "class_field": (
            re.compile(r"class\s+\w+[^{]*\{[^}]*\n\s*\w+\s*="),
            ECMAScriptVersion.ES2022,
        ),
        "logical_assignment": (
            re.compile(r"(?:\?\?|&&|\|\|)="),
            ECMAScriptVersion.ES2021,
        ),
        "numeric_separator": (re.compile(r"\d_\d"), ECMAScriptVersion.ES2021),
        "bigint": (re.compile(r"\d+n\b"), ECMAScriptVersion.ES2020),
        "dynamic_import": (re.compile(r"\bimport\s*\("), ECMAScriptVersion.ES2020),
        "for_await_of": (re.compile(r"for\s+await\s*\("), ECMAScriptVersion.ES2018),
        "object_rest_spread": (
            re.compile(r"\{[^}]*\.\.\.[^}]*\}"),
            ECMAScriptVersion.ES2018,
        ),
        "promise_finally": (re.compile(r"\.finally\s*\("), ECMAScriptVersion.ES2018),
        "array_includes": (re.compile(r"\.includes\s*\("), ECMAScriptVersion.ES2016),
        "exponentiation": (re.compile(r"\*\*"), ECMAScriptVersion.ES2016),
    }

    def __init__(self, babel_path: str | None = None):
        """
        Initialize Babel parser.

        :param babel_path: Path to Babel CLI (@babel/cli).
        """
        self._babel_path = babel_path or self._find_babel()

    def _find_babel(self) -> str | None:
        """Find Babel CLI."""
        babel = shutil.which("babel")
        if babel:
            return babel

        local = Path("node_modules/.bin/babel")
        if local.exists():
            return str(local)

        if shutil.which("npx"):
            return "npx babel"

        return None

    def analyze(self, code: str, filename: str = "input.js") -> BabelAnalysis:
        """
        Analyze JavaScript code for modern syntax features.

        :param code: JavaScript source code.
        :param filename: Virtual filename.
        :return: BabelAnalysis with detected features.
        """
        analysis = BabelAnalysis()

        # Detect syntax features
        analysis.syntax_features = self._detect_syntax_features(code)

        # Analyze JSX
        analysis.jsx_elements = self._detect_jsx_elements(code)

        # Count modern syntax usage
        analysis.modern_syntax = self._count_modern_syntax(code)

        # Determine minimum ES version needed
        analysis.min_es_version = self._determine_min_es_version(analysis.syntax_features)

        return analysis

    def analyze_file(self, file_path: str) -> BabelAnalysis:
        """
        Analyze a JavaScript file.

        :param file_path: Path to JavaScript file.
        :return: BabelAnalysis.
        """
        path = Path(file_path)
        code = path.read_text(encoding="utf-8")
        return self.analyze(code, path.name)

    def _detect_syntax_features(self, code: str) -> list[SyntaxFeature]:
        """Detect modern syntax features in code."""
        features: list[SyntaxFeature] = []

        for name, (pattern, es_version) in self._PATTERNS.items():
            for match in pattern.finditer(code):
                line = code[: match.start()].count("\n") + 1
                column = match.start() - code.rfind("\n", 0, match.start()) - 1

                feature = SyntaxFeature(
                    name=name,
                    line=line,
                    column=column,
                    es_version=es_version,
                )

                # Add proposal stage for experimental features
                if es_version == ECMAScriptVersion.ESNEXT:
                    if "decorator" in name:
                        feature.proposal_stage = ProposalStage.STAGE_3
                        feature.requires_plugin = "@babel/plugin-proposal-decorators"

                features.append(feature)

        return features

    def _detect_jsx_elements(self, code: str) -> list[JSXElement]:
        """Detect JSX elements in code."""
        elements: list[JSXElement] = []

        # Simple JSX detection pattern
        jsx_pattern = re.compile(r"<(\w+)([^>]*?)(/?)>")

        for match in jsx_pattern.finditer(code):
            tag_name = match.group(1)
            attributes = match.group(2)
            is_self_closing = bool(match.group(3))

            # Skip HTML-like tags in strings
            before = code[: match.start()]
            if before.count('"') % 2 == 1 or before.count("'") % 2 == 1:
                continue
            if before.count("`") % 2 == 1:
                continue

            line = code[: match.start()].count("\n") + 1
            column = match.start() - code.rfind("\n", 0, match.start()) - 1

            # Extract props
            props: list[str] = []
            spread_props = False
            for prop_match in re.finditer(r"(\w+)(?:=|\s|$)|(\{\.\.\.)", attributes):
                if prop_match.group(2):
                    spread_props = True
                elif prop_match.group(1):
                    props.append(prop_match.group(1))

            elements.append(
                JSXElement(
                    tag_name=tag_name,
                    line=line,
                    column=column,
                    is_self_closing=is_self_closing,
                    is_component=tag_name[0].isupper(),
                    props=props,
                    spread_props=spread_props,
                )
            )

        return elements

    def _count_modern_syntax(self, code: str) -> ModernJSSyntax:
        """Count usage of modern JavaScript syntax features."""
        return ModernJSSyntax(
            arrow_functions=len(re.findall(r"=>", code)),
            template_literals=len(re.findall(r"`[^`]*`", code)),
            destructuring=len(re.findall(r"(?:const|let|var)\s*[\[{]", code)),
            spread_operator=len(re.findall(r"\.\.\.(?!\.)", code)),
            rest_parameters=len(re.findall(r"\(\s*[^)]*\.\.\.\w+", code)),
            default_parameters=len(re.findall(r"\(\s*\w+\s*=", code)),
            async_await=len(re.findall(r"\b(?:async|await)\b", code)),
            optional_chaining=len(re.findall(r"\?\.", code)),
            nullish_coalescing=len(re.findall(r"\?\?(?!\?)", code)),
            private_fields=len(re.findall(r"#\w+", code)),
            static_blocks=len(re.findall(r"static\s*\{", code)),
            decorators=len(re.findall(r"@\w+", code)),
            class_fields=len(re.findall(r"(?:public|private|protected)?\s*\w+\s*=", code)),
            logical_assignment=len(re.findall(r"(?:\?\?|&&|\|\|)=", code)),
        )

    def _determine_min_es_version(self, features: list[SyntaxFeature]) -> ECMAScriptVersion:
        """Determine minimum ECMAScript version needed for the features."""
        if not features:
            return ECMAScriptVersion.ES5

        versions = [f.es_version for f in features]

        # Order versions by release year
        version_order = [
            ECMAScriptVersion.ES5,
            ECMAScriptVersion.ES2015,
            ECMAScriptVersion.ES2016,
            ECMAScriptVersion.ES2017,
            ECMAScriptVersion.ES2018,
            ECMAScriptVersion.ES2019,
            ECMAScriptVersion.ES2020,
            ECMAScriptVersion.ES2021,
            ECMAScriptVersion.ES2022,
            ECMAScriptVersion.ES2023,
            ECMAScriptVersion.ES2024,
            ECMAScriptVersion.ESNEXT,
        ]

        max_idx = max(version_order.index(v) for v in versions)
        return version_order[max_idx]

    def parse_config(self, config_path: str) -> BabelConfig:
        """
        Parse a Babel configuration file.

        Supports:
        - .babelrc (JSON)
        - .babelrc.json
        - babel.config.json
        - package.json (babel key)

        :param config_path: Path to config file.
        :return: BabelConfig object.
        """
        path = Path(config_path)

        if not path.exists():
            raise FileNotFoundError(f"Babel config not found: {config_path}")

        if path.name == "package.json":
            with open(path) as f:
                pkg = json.load(f)
                config_data = pkg.get("babel", {})
        elif path.suffix == ".json" or path.name.startswith(".babelrc"):
            with open(path) as f:
                config_data = json.load(f)
        else:
            raise ValueError(f"Unsupported config format: {path.suffix}")

        return self._parse_config_data(config_data)

    def _parse_config_data(self, data: dict[str, Any]) -> BabelConfig:
        """Parse config from dictionary."""
        config = BabelConfig()

        # Parse presets
        for preset in data.get("presets", []):
            if isinstance(preset, str):
                config.presets.append(BabelPreset(name=preset))
            elif isinstance(preset, list) and len(preset) >= 1:
                config.presets.append(
                    BabelPreset(
                        name=preset[0],
                        options=preset[1] if len(preset) > 1 else {},
                    )
                )

        # Parse plugins
        for plugin in data.get("plugins", []):
            if isinstance(plugin, str):
                config.plugins.append(
                    BabelPlugin(
                        name=plugin,
                        is_official=plugin.startswith("@babel/"),
                    )
                )
            elif isinstance(plugin, list) and len(plugin) >= 1:
                config.plugins.append(
                    BabelPlugin(
                        name=plugin[0],
                        options=plugin[1] if len(plugin) > 1 else {},
                        is_official=plugin[0].startswith("@babel/"),
                    )
                )

        # Other config options
        config.targets = data.get("targets", {})
        config.source_type = data.get("sourceType", "module")
        config.assumptions = data.get("assumptions", {})
        config.env = data.get("env", {})
        config.ignore = data.get("ignore", [])
        config.only = data.get("only", [])

        return config

    def transform(
        self,
        code: str,
        target: ECMAScriptVersion = ECMAScriptVersion.ES5,
        presets: list[str] | None = None,
        plugins: list[str] | None = None,
    ) -> TransformationResult:
        """
        Transform JavaScript code using Babel.

        :param code: JavaScript source code.
        :param target: Target ECMAScript version.
        :param presets: Additional presets to use.
        :param plugins: Additional plugins to use.
        :return: TransformationResult with transformed code.
        """
        if not self._babel_path:
            raise RuntimeError("Babel CLI not found. Install with: npm install @babel/cli @babel/core")

        import time

        # Write code to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write(code)
            temp_path = f.name

        try:
            cmd = self._babel_path.split() if " " in self._babel_path else [self._babel_path]
            cmd.extend(["--source-maps", "inline"])

            # Add presets
            if presets:
                for preset in presets:
                    cmd.extend(["--presets", preset])
            else:
                # Default: use preset-env with targets
                cmd.extend(["--presets", "@babel/preset-env"])

            # Add plugins
            if plugins:
                for plugin in plugins:
                    cmd.extend(["--plugins", plugin])

            cmd.append(temp_path)

            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            transform_time = (time.time() - start_time) * 1000

            if result.returncode != 0:
                return TransformationResult(
                    original_code=code,
                    transformed_code=code,
                )

            transformed = result.stdout

            # Extract source map if present
            source_map = None
            if "//# sourceMappingURL=data:" in transformed:
                # Extract inline source map
                import base64

                match = re.search(r"//# sourceMappingURL=data:[^;]+;base64,([^\s]+)", transformed)
                if match:
                    try:
                        map_data = base64.b64decode(match.group(1))
                        source_map = json.loads(map_data)
                    except Exception:
                        pass
                    # Remove source map from output
                    transformed = re.sub(r"\n?//# sourceMappingURL=[^\n]+", "", transformed)

            return TransformationResult(
                original_code=code,
                transformed_code=transformed,
                source_map=source_map,
                transform_time_ms=transform_time,
            )
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def transform_file(
        self,
        file_path: str,
        output_path: str | None = None,
        target: ECMAScriptVersion = ECMAScriptVersion.ES5,
    ) -> TransformationResult:
        """
        Transform a JavaScript file.

        :param file_path: Path to input file.
        :param output_path: Path to output file (optional).
        :param target: Target ECMAScript version.
        :return: TransformationResult.
        """
        path = Path(file_path)
        code = path.read_text(encoding="utf-8")

        result = self.transform(code, target)

        if output_path and result.transformed_code:
            Path(output_path).write_text(result.transformed_code)

        return result

    def get_required_polyfills(self, code: str) -> list[str]:
        """
        Determine polyfills needed for the code.

        :param code: JavaScript source code.
        :return: List of required polyfill names.
        """
        polyfills: list[str] = []

        # Common polyfill patterns
        polyfill_patterns = [
            (r"Promise\b", "promise"),
            (r"\.includes\s*\(", "array.prototype.includes"),
            (r"Object\.entries\b", "object.entries"),
            (r"Object\.values\b", "object.values"),
            (r"Object\.fromEntries\b", "object.fromentries"),
            (r"Array\.from\b", "array.from"),
            (r"\.flat\s*\(", "array.prototype.flat"),
            (r"\.flatMap\s*\(", "array.prototype.flatmap"),
            (r"Symbol\b", "symbol"),
            (r"Map\b", "map"),
            (r"Set\b", "set"),
            (r"WeakMap\b", "weakmap"),
            (r"WeakSet\b", "weakset"),
            (r"fetch\b", "fetch"),
            (r"URL\b", "url"),
            (r"URLSearchParams\b", "urlsearchparams"),
            (r"\.padStart\s*\(", "string.prototype.padstart"),
            (r"\.padEnd\s*\(", "string.prototype.padend"),
            (r"\.trimStart\s*\(", "string.prototype.trimstart"),
            (r"\.trimEnd\s*\(", "string.prototype.trimend"),
            (r"globalThis\b", "globalthis"),
            (r"\.at\s*\(", "array.prototype.at"),
            (r"\.replaceAll\s*\(", "string.prototype.replaceall"),
            (r"structuredClone\b", "structuredclone"),
        ]

        for pattern, polyfill in polyfill_patterns:
            if re.search(pattern, code):
                polyfills.append(polyfill)

        return sorted(set(polyfills))
