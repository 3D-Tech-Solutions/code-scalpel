"""
Frontend Input Tracker - TypeScript/JavaScript DOM Input Detection.

[20251220_FEATURE] v3.0.4 - Ninja Warrior Stage 3

This module detects user input sources in frontend TypeScript/JavaScript code:
- Vanilla JS: document.getElementById, querySelector, .value, event.target
- React: useState hooks with onChange handlers, form state
- Vue: v-model bindings, ref(), reactive()
- Angular: ngModel, FormControl, FormGroup

Security Concerns:
==================

1. DOM XSS: User input flows directly to innerHTML/document.write
   - input.value → element.innerHTML = userInput

2. Unsafe State: Tainted data stored in component state
   - const [query, setQuery] = useState(e.target.value) → dangerouslySetInnerHTML

3. URL/Storage Injection: Reading from URL or storage without validation
   - location.search → API call → DOM manipulation

Supported Frameworks:
- Vanilla JavaScript/TypeScript
- React (hooks and class components)
- Vue 2/3 (Options API and Composition API)
- Angular (Reactive Forms and Template-driven)
- Svelte (bind: directives)

Usage:
    tracker = FrontendInputTracker()

    # Analyze a TypeScript/React file
    result = tracker.analyze_file(source_code, "Component.tsx", "react")

    # Get all detected input sources
    for source in result.input_sources:
        print(f"Input at line {source.line}: {source.pattern}")

    # Get DOM XSS risks (input → dangerous sink)
    for flow in result.dangerous_flows:
        print(f"RISK: {flow.source_pattern} → {flow.sink_pattern}")
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any


class FrontendFramework(Enum):
    """Supported frontend frameworks."""

    VANILLA = "vanilla"  # Plain JS/TS
    REACT = "react"  # React (hooks or class)
    VUE = "vue"  # Vue 2/3
    ANGULAR = "angular"  # Angular
    SVELTE = "svelte"  # Svelte
    UNKNOWN = "unknown"


class InputSourceType(Enum):
    """Types of frontend input sources."""

    # DOM element access
    DOM_ELEMENT = auto()  # document.getElementById, querySelector
    ELEMENT_VALUE = auto()  # .value property
    EVENT_TARGET = auto()  # event.target.value, e.target.value

    # URL/Location
    URL_PARAM = auto()  # URLSearchParams, location.search
    URL_HASH = auto()  # location.hash
    URL_PATH = auto()  # location.pathname

    # Storage
    LOCAL_STORAGE = auto()  # localStorage.getItem
    SESSION_STORAGE = auto()  # sessionStorage.getItem

    # React specific
    REACT_STATE = auto()  # useState setter
    REACT_REF = auto()  # useRef
    REACT_FORM = auto()  # form event handlers

    # Vue specific
    VUE_V_MODEL = auto()  # v-model binding
    VUE_REF = auto()  # ref(), reactive()
    VUE_COMPUTED = auto()  # computed with input

    # Angular specific
    ANGULAR_NG_MODEL = auto()  # ngModel
    ANGULAR_FORM = auto()  # FormControl, FormGroup
    ANGULAR_INPUT = auto()  # @Input() decorator

    # Other
    POST_MESSAGE = auto()  # window.postMessage
    FILE_INPUT = auto()  # File input
    UNKNOWN = auto()


class DangerousSinkType(Enum):
    """Types of dangerous sinks for frontend code."""

    INNER_HTML = auto()  # innerHTML, outerHTML
    DOCUMENT_WRITE = auto()  # document.write, writeln
    DANGEROUSLY_SET = auto()  # React dangerouslySetInnerHTML
    V_HTML = auto()  # Vue v-html directive
    INNER_HTML_BINDING = auto()  # Angular [innerHTML]
    EVAL = auto()  # eval, Function constructor
    SCRIPT_SRC = auto()  # script.src assignment
    HREF = auto()  # a.href with javascript:
    LOCATION = auto()  # location.href, location.assign
    OPEN = auto()  # window.open
    FETCH_URL = auto()  # fetch/axios with user URL
    DOM_MANIPULATION = auto()  # insertAdjacentHTML, outerHTML


@dataclass
class InputSource:
    """Detected frontend input source."""

    source_type: InputSourceType
    pattern: str  # The matched pattern
    variable_name: str | None = None  # Variable storing the input
    line: int = 0
    column: int = 0
    file_path: str = ""
    framework: FrontendFramework = FrontendFramework.VANILLA
    is_validated: bool = False  # Whether validation was detected
    validation_function: str | None = None

    @property
    def risk_level(self) -> str:
        """Determine risk level based on source type."""
        high_risk = {
            InputSourceType.EVENT_TARGET,
            InputSourceType.ELEMENT_VALUE,
            InputSourceType.URL_PARAM,
            InputSourceType.URL_HASH,
            InputSourceType.POST_MESSAGE,
        }
        return "HIGH" if self.source_type in high_risk else "MEDIUM"


@dataclass
class DangerousSink:
    """Detected dangerous sink."""

    sink_type: DangerousSinkType
    pattern: str
    line: int = 0
    column: int = 0
    file_path: str = ""
    cwe: str = "CWE-79"  # XSS by default

    @property
    def description(self) -> str:
        """Human-readable description."""
        descriptions = {
            DangerousSinkType.INNER_HTML: "innerHTML allows arbitrary HTML injection",
            DangerousSinkType.DOCUMENT_WRITE: "document.write can inject arbitrary scripts",
            DangerousSinkType.DANGEROUSLY_SET: "dangerouslySetInnerHTML bypasses React's XSS protection",
            DangerousSinkType.V_HTML: "v-html renders raw HTML without sanitization",
            DangerousSinkType.EVAL: "eval executes arbitrary JavaScript code",
            DangerousSinkType.LOCATION: "location assignment can lead to open redirect",
        }
        return descriptions.get(self.sink_type, "Potentially dangerous operation")


@dataclass
class DataFlow:
    """Represents data flow from input source to sink."""

    source: InputSource
    sink: DangerousSink
    intermediate_variables: list[str] = field(default_factory=list)
    is_sanitized: bool = False
    sanitizer: str | None = None

    @property
    def risk_level(self) -> str:
        """Determine risk based on flow characteristics."""
        if self.is_sanitized:
            return "LOW"
        return "CRITICAL" if self.source.risk_level == "HIGH" else "HIGH"

    @property
    def description(self) -> str:
        """Human-readable flow description."""
        flow_str = " → ".join([self.source.pattern] + self.intermediate_variables + [self.sink.pattern])
        return f"[{self.risk_level}] {flow_str}"


@dataclass
class FrontendAnalysisResult:
    """Result of frontend input analysis."""

    file_path: str = ""
    framework: FrontendFramework = FrontendFramework.UNKNOWN
    input_sources: list[InputSource] = field(default_factory=list)
    dangerous_sinks: list[DangerousSink] = field(default_factory=list)
    data_flows: list[DataFlow] = field(default_factory=list)
    state_variables: dict[str, InputSource] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    @property
    def dangerous_flows(self) -> list[DataFlow]:
        """Get only dangerous (unsanitized) flows."""
        return [f for f in self.data_flows if not f.is_sanitized]

    @property
    def has_risks(self) -> bool:
        """Check if any XSS risks were detected."""
        return len(self.dangerous_flows) > 0

    @property
    def risk_count(self) -> dict[str, int]:
        """Count risks by level."""
        counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for flow in self.data_flows:
            counts[flow.risk_level] += 1
        return counts

    def summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            f"Frontend Analysis: {self.file_path}",
            f"Framework: {self.framework.value}",
            f"Input Sources: {len(self.input_sources)}",
            f"Dangerous Sinks: {len(self.dangerous_sinks)}",
            f"Data Flows: {len(self.data_flows)} ({len(self.dangerous_flows)} unsafe)",
        ]

        if self.dangerous_flows:
            lines.append("\n⚠️  DANGEROUS FLOWS:")
            for flow in self.dangerous_flows:
                lines.append(f"  - {flow.description}")

        return "\n".join(lines)


# =============================================================================
# Pattern Definitions
# =============================================================================

# Vanilla JS/TS input patterns
VANILLA_INPUT_PATTERNS = [
    # DOM element access
    (
        r'document\.getElementById\s*\(\s*["\']([^"\']+)["\']\s*\)',
        InputSourceType.DOM_ELEMENT,
    ),
    (
        r'document\.querySelector\s*\(\s*["\']([^"\']+)["\']\s*\)',
        InputSourceType.DOM_ELEMENT,
    ),
    (
        r'document\.querySelectorAll\s*\(\s*["\']([^"\']+)["\']\s*\)',
        InputSourceType.DOM_ELEMENT,
    ),
    (
        r'document\.getElementsByClassName\s*\(\s*["\']([^"\']+)["\']\s*\)',
        InputSourceType.DOM_ELEMENT,
    ),
    (
        r'document\.getElementsByName\s*\(\s*["\']([^"\']+)["\']\s*\)',
        InputSourceType.DOM_ELEMENT,
    ),
    # Element value access
    (r"(\w+)\.value\b", InputSourceType.ELEMENT_VALUE),
    (r"(\w+)\.textContent\b", InputSourceType.ELEMENT_VALUE),
    (r"(\w+)\.innerText\b", InputSourceType.ELEMENT_VALUE),
    # Event target
    (r"(?:e|event|evt)\.target\.value", InputSourceType.EVENT_TARGET),
    (r"(?:e|event|evt)\.currentTarget\.value", InputSourceType.EVENT_TARGET),
    # URL/Location
    (r"location\.search\b", InputSourceType.URL_PARAM),
    (r"location\.hash\b", InputSourceType.URL_HASH),
    (r"location\.pathname\b", InputSourceType.URL_PATH),
    (r"window\.location\.search\b", InputSourceType.URL_PARAM),
    (r"new\s+URLSearchParams\s*\(", InputSourceType.URL_PARAM),
    (r"URLSearchParams\.get\s*\(", InputSourceType.URL_PARAM),
    # Storage
    (r"localStorage\.getItem\s*\(", InputSourceType.LOCAL_STORAGE),
    (r"sessionStorage\.getItem\s*\(", InputSourceType.SESSION_STORAGE),
    # postMessage
    (r"(?:e|event)\.data\b", InputSourceType.POST_MESSAGE),
    (r'addEventListener\s*\(\s*["\']message["\']\s*,', InputSourceType.POST_MESSAGE),
    # File input
    (r"(\w+)\.files\b", InputSourceType.FILE_INPUT),
    (r"FileReader\.(?:result|readAsText|readAsDataURL)", InputSourceType.FILE_INPUT),
]

# React-specific patterns
REACT_INPUT_PATTERNS = [
    # useState with event handler
    (r'useState\s*<[^>]*>\s*\(\s*["\']', InputSourceType.REACT_STATE),
    (r'useState\s*\(\s*["\']', InputSourceType.REACT_STATE),
    (r"set(\w+)\s*\(\s*(?:e|event|evt)\.target\.value", InputSourceType.REACT_STATE),
    (
        r"set(\w+)\s*\(\s*(?:e|event|evt)\.currentTarget\.value",
        InputSourceType.REACT_STATE,
    ),
    # useRef for DOM access
    (r"useRef\s*<[^>]*>\s*\(", InputSourceType.REACT_REF),
    (r"(\w+)Ref\.current\.value", InputSourceType.REACT_REF),
    # Form handlers
    (r"onChange\s*=\s*\{?\s*\(?(?:e|event|evt)\)?", InputSourceType.REACT_FORM),
    (r"onInput\s*=\s*\{?\s*\(?(?:e|event|evt)\)?", InputSourceType.REACT_FORM),
    (r"onSubmit\s*=", InputSourceType.REACT_FORM),
    # Controlled input pattern
    (r"value\s*=\s*\{\s*(\w+)\s*\}", InputSourceType.REACT_STATE),
]

# Vue-specific patterns
VUE_INPUT_PATTERNS = [
    # v-model
    (r'v-model\s*=\s*["\']([^"\']+)["\']', InputSourceType.VUE_V_MODEL),
    (r"v-model:(\w+)\s*=", InputSourceType.VUE_V_MODEL),
    # Composition API
    (r"ref\s*<[^>]*>\s*\(", InputSourceType.VUE_REF),
    (r'ref\s*\(\s*["\']', InputSourceType.VUE_REF),
    (r"reactive\s*\(\s*\{", InputSourceType.VUE_REF),
    # computed with user input
    (r"computed\s*\(\s*\(\s*\)\s*=>", InputSourceType.VUE_COMPUTED),
    # Event handlers
    (r'@input\s*=\s*["\']([^"\']+)["\']', InputSourceType.VUE_V_MODEL),
    (r'@change\s*=\s*["\']([^"\']+)["\']', InputSourceType.VUE_V_MODEL),
]

# Angular-specific patterns
ANGULAR_INPUT_PATTERNS = [
    # ngModel
    (r'\[\(ngModel\)\]\s*=\s*["\']([^"\']+)["\']', InputSourceType.ANGULAR_NG_MODEL),
    (r'\[ngModel\]\s*=\s*["\']([^"\']+)["\']', InputSourceType.ANGULAR_NG_MODEL),
    # Reactive Forms
    (r"new\s+FormControl\s*\(", InputSourceType.ANGULAR_FORM),
    (r"new\s+FormGroup\s*\(", InputSourceType.ANGULAR_FORM),
    (r"FormBuilder\.control\s*\(", InputSourceType.ANGULAR_FORM),
    (r"\.valueChanges\b", InputSourceType.ANGULAR_FORM),
    # @Input decorator
    (r"@Input\s*\(\s*\)", InputSourceType.ANGULAR_INPUT),
    # Event binding
    (r'\(input\)\s*=\s*["\']([^"\']+)["\']', InputSourceType.ANGULAR_FORM),
    (r'\(change\)\s*=\s*["\']([^"\']+)["\']', InputSourceType.ANGULAR_FORM),
]

# Dangerous sink patterns (all frameworks)
DANGEROUS_SINK_PATTERNS = [
    # innerHTML
    (r"\.innerHTML\s*=", DangerousSinkType.INNER_HTML, "CWE-79"),
    (r"\.outerHTML\s*=", DangerousSinkType.INNER_HTML, "CWE-79"),
    (r"insertAdjacentHTML\s*\(", DangerousSinkType.DOM_MANIPULATION, "CWE-79"),
    # document.write
    (r"document\.write\s*\(", DangerousSinkType.DOCUMENT_WRITE, "CWE-79"),
    (r"document\.writeln\s*\(", DangerousSinkType.DOCUMENT_WRITE, "CWE-79"),
    # React dangerouslySetInnerHTML
    (r"dangerouslySetInnerHTML\s*=", DangerousSinkType.DANGEROUSLY_SET, "CWE-79"),
    (r"dangerouslySetInnerHTML:\s*\{", DangerousSinkType.DANGEROUSLY_SET, "CWE-79"),
    # Vue v-html
    (r"v-html\s*=", DangerousSinkType.V_HTML, "CWE-79"),
    # Angular innerHTML binding
    (r"\[innerHTML\]\s*=", DangerousSinkType.INNER_HTML_BINDING, "CWE-79"),
    # eval and Function
    (r"\beval\s*\(", DangerousSinkType.EVAL, "CWE-94"),
    (r"new\s+Function\s*\(", DangerousSinkType.EVAL, "CWE-94"),
    (r'setTimeout\s*\(\s*["\']', DangerousSinkType.EVAL, "CWE-94"),
    (r'setInterval\s*\(\s*["\']', DangerousSinkType.EVAL, "CWE-94"),
    # Location/Redirect
    (r"location\.href\s*=", DangerousSinkType.LOCATION, "CWE-601"),
    (r"location\.assign\s*\(", DangerousSinkType.LOCATION, "CWE-601"),
    (r"location\.replace\s*\(", DangerousSinkType.LOCATION, "CWE-601"),
    (r"window\.open\s*\(", DangerousSinkType.OPEN, "CWE-601"),
    # Script src
    (r"\.src\s*=", DangerousSinkType.SCRIPT_SRC, "CWE-79"),
]

# Known sanitizer patterns
SANITIZER_PATTERNS = [
    r"DOMPurify\.sanitize\s*\(",
    r"sanitize\s*\(",
    r"escapeHtml\s*\(",
    r"escape\s*\(",
    r"encodeURIComponent\s*\(",
    r"textContent\s*=",  # Safe alternative to innerHTML
    r"innerText\s*=",  # Safe alternative to innerHTML
    r"createTextNode\s*\(",
    r"sanitize-html",
    r"xss-filters",
    r"validator\.escape",
]


class FrontendInputTracker:
    """
    Tracks user input sources in frontend TypeScript/JavaScript code.

    [20251220_FEATURE] v3.0.4 - Ninja Warrior Stage 3

    Detects:
    1. DOM input sources (element.value, event.target.value)
    2. Framework-specific patterns (React useState, Vue v-model, Angular ngModel)
    3. URL/storage input sources
    4. Data flow to dangerous sinks (innerHTML, document.write, etc.)
    """

    def __init__(self):
        """Initialize the frontend input tracker."""
        self.known_tainted_vars: set[str] = set()

    def analyze_file(
        self,
        source_code: str,
        file_path: str = "",
        framework: str | None = None,
    ) -> FrontendAnalysisResult:
        """
        Analyze frontend code for input sources and dangerous sinks.

        Args:
            source_code: The source code to analyze
            file_path: Path to the file (for reporting)
            framework: Optional framework hint ("react", "vue", "angular", "vanilla")

        Returns:
            FrontendAnalysisResult with detected patterns
        """
        result = FrontendAnalysisResult(file_path=file_path)

        # Detect framework if not specified
        if framework:
            result.framework = self._parse_framework(framework)
        else:
            result.framework = self._detect_framework(source_code)

        # Detect input sources
        self._detect_input_sources(source_code, result)

        # Detect dangerous sinks
        self._detect_dangerous_sinks(source_code, result)

        # Track state variables
        self._track_state_variables(source_code, result)

        # Analyze data flows
        self._analyze_data_flows(source_code, result)

        return result

    def _parse_framework(self, framework: str) -> FrontendFramework:
        """Parse framework string to enum."""
        framework_map = {
            "react": FrontendFramework.REACT,
            "vue": FrontendFramework.VUE,
            "angular": FrontendFramework.ANGULAR,
            "svelte": FrontendFramework.SVELTE,
            "vanilla": FrontendFramework.VANILLA,
        }
        return framework_map.get(framework.lower(), FrontendFramework.UNKNOWN)

    def _detect_framework(self, source_code: str) -> FrontendFramework:
        """Auto-detect frontend framework from code patterns."""
        # React indicators
        if any(
            pattern in source_code
            for pattern in [
                "import React",
                "from 'react'",
                'from "react"',
                "useState",
                "useEffect",
                "useRef",
                "React.Component",
                "ReactDOM",
            ]
        ):
            return FrontendFramework.REACT

        # Vue indicators
        if any(
            pattern in source_code
            for pattern in [
                "import Vue",
                "from 'vue'",
                'from "vue"',
                "defineComponent",
                "v-model",
                "v-html",
                "v-bind",
                "@vue/composition-api",
                "createApp",
            ]
        ):
            return FrontendFramework.VUE

        # Angular indicators
        if any(
            pattern in source_code
            for pattern in [
                "@angular/core",
                "@Component",
                "@Injectable",
                "ngModel",
                "FormControl",
                "FormGroup",
                "NgModule",
                "@Input()",
                "@Output()",
            ]
        ):
            return FrontendFramework.ANGULAR

        # Svelte indicators
        if (
            any(
                pattern in source_code
                for pattern in [
                    "svelte",
                    "<script>",
                    "bind:",
                    "export let",
                    "on:click",
                ]
            )
            and ".svelte" in source_code
        ):
            return FrontendFramework.SVELTE

        return FrontendFramework.VANILLA

    def _detect_input_sources(
        self,
        source_code: str,
        result: FrontendAnalysisResult,
    ) -> None:
        """Detect all input sources in the code."""
        lines = source_code.split("\n")

        # Always check vanilla patterns
        self._apply_patterns(
            source_code,
            lines,
            VANILLA_INPUT_PATTERNS,
            result,
            FrontendFramework.VANILLA,
        )

        # Framework-specific patterns
        if result.framework == FrontendFramework.REACT:
            self._apply_patterns(
                source_code,
                lines,
                REACT_INPUT_PATTERNS,
                result,
                FrontendFramework.REACT,
            )
        elif result.framework == FrontendFramework.VUE:
            self._apply_patterns(source_code, lines, VUE_INPUT_PATTERNS, result, FrontendFramework.VUE)
        elif result.framework == FrontendFramework.ANGULAR:
            self._apply_patterns(
                source_code,
                lines,
                ANGULAR_INPUT_PATTERNS,
                result,
                FrontendFramework.ANGULAR,
            )

    def _apply_patterns(
        self,
        source_code: str,
        lines: list[str],
        patterns: list[tuple],
        result: FrontendAnalysisResult,
        framework: FrontendFramework,
    ) -> None:
        """Apply pattern list to source code."""
        for pattern_tuple in patterns:
            pattern, source_type = pattern_tuple[0], pattern_tuple[1]

            for match in re.finditer(pattern, source_code, re.MULTILINE):
                # Calculate line number
                line_num = source_code[: match.start()].count("\n") + 1

                # Extract variable name if captured
                var_name = match.group(1) if match.groups() else None

                source = InputSource(
                    source_type=source_type,
                    pattern=match.group(0),
                    variable_name=var_name,
                    line=line_num,
                    column=match.start() - source_code.rfind("\n", 0, match.start()),
                    file_path=result.file_path,
                    framework=framework,
                )

                # Check for validation near this source
                context_start = max(0, match.start() - 200)
                context_end = min(len(source_code), match.end() + 200)
                context = source_code[context_start:context_end]

                for sanitizer in SANITIZER_PATTERNS:
                    if re.search(sanitizer, context):
                        source.is_validated = True
                        source.validation_function = sanitizer
                        break

                result.input_sources.append(source)

                # Track variable as tainted
                if var_name:
                    self.known_tainted_vars.add(var_name)

    def _detect_dangerous_sinks(
        self,
        source_code: str,
        result: FrontendAnalysisResult,
    ) -> None:
        """Detect dangerous sinks in the code."""
        for pattern, sink_type, cwe in DANGEROUS_SINK_PATTERNS:
            for match in re.finditer(pattern, source_code, re.MULTILINE):
                line_num = source_code[: match.start()].count("\n") + 1

                sink = DangerousSink(
                    sink_type=sink_type,
                    pattern=match.group(0).strip(),
                    line=line_num,
                    column=match.start() - source_code.rfind("\n", 0, match.start()),
                    file_path=result.file_path,
                    cwe=cwe,
                )
                result.dangerous_sinks.append(sink)

    def _track_state_variables(
        self,
        source_code: str,
        result: FrontendAnalysisResult,
    ) -> None:
        """Track which state variables are assigned from input."""
        # React useState pattern: const [value, setValue] = useState(...)
        # Look for setValue(e.target.value) pattern
        state_pattern = re.compile(r"const\s+\[(\w+),\s*set(\w+)\]\s*=\s*useState", re.MULTILINE)

        for match in state_pattern.finditer(source_code):
            var_name = match.group(1)
            setter_name = f"set{match.group(2)}"

            # Check if setter is called with event target value
            setter_pattern = rf"{setter_name}\s*\(\s*(?:e|event|evt)\.(?:target|currentTarget)\.value"
            if re.search(setter_pattern, source_code):
                line_num = source_code[: match.start()].count("\n") + 1
                source = InputSource(
                    source_type=InputSourceType.REACT_STATE,
                    pattern=f"{var_name} (via {setter_name})",
                    variable_name=var_name,
                    line=line_num,
                    file_path=result.file_path,
                    framework=FrontendFramework.REACT,
                )
                result.state_variables[var_name] = source
                self.known_tainted_vars.add(var_name)

    def _analyze_data_flows(
        self,
        source_code: str,
        result: FrontendAnalysisResult,
    ) -> None:
        """Analyze data flow from inputs to sinks."""
        lines = source_code.split("\n")

        # For each dangerous sink, check if any tainted variable flows to it
        for sink in result.dangerous_sinks:
            # Get the line containing the sink
            if 0 < sink.line <= len(lines):
                sink_line = lines[sink.line - 1]

                # Check context around sink (10 lines before)
                start_line = max(0, sink.line - 10)
                context = "\n".join(lines[start_line : sink.line])

                # Check if any input source or tainted var flows to this sink
                for source in result.input_sources:
                    # Direct flow: source on same line as sink
                    if source.line == sink.line:
                        flow = DataFlow(
                            source=source,
                            sink=sink,
                        )
                        self._check_sanitization(context, flow)
                        result.data_flows.append(flow)

                    # Indirect flow via variable
                    elif source.variable_name:
                        if source.variable_name in sink_line or source.variable_name in context:
                            flow = DataFlow(
                                source=source,
                                sink=sink,
                                intermediate_variables=[source.variable_name],
                            )
                            self._check_sanitization(context, flow)
                            result.data_flows.append(flow)

                # Check state variables
                for var_name, source in result.state_variables.items():
                    if var_name in sink_line:
                        flow = DataFlow(
                            source=source,
                            sink=sink,
                            intermediate_variables=[var_name],
                        )
                        self._check_sanitization(context, flow)
                        result.data_flows.append(flow)

    def _check_sanitization(self, context: str, flow: DataFlow) -> None:
        """Check if flow is sanitized."""
        for sanitizer in SANITIZER_PATTERNS:
            if re.search(sanitizer, context):
                flow.is_sanitized = True
                flow.sanitizer = sanitizer
                break

    def get_security_findings(
        self,
        result: FrontendAnalysisResult,
    ) -> list[dict[str, Any]]:
        """
        Generate security findings from analysis result.

        Returns findings compatible with Code Scalpel's reporting.
        """
        findings = []

        for flow in result.dangerous_flows:
            findings.append(
                {
                    "type": "FRONTEND_XSS_RISK",
                    "severity": flow.risk_level,
                    "cwe": flow.sink.cwe,
                    "message": f"User input flows to dangerous sink: {flow.sink.pattern}",
                    "file": result.file_path,
                    "line": flow.sink.line,
                    "source_line": flow.source.line,
                    "source_pattern": flow.source.pattern,
                    "sink_pattern": flow.sink.pattern,
                    "framework": result.framework.value,
                    "recommendation": self._get_recommendation(flow),
                }
            )

        # Informational: unvalidated inputs
        for source in result.input_sources:
            if not source.is_validated:
                findings.append(
                    {
                        "type": "FRONTEND_INPUT_SOURCE",
                        "severity": "INFO",
                        "cwe": "CWE-20",
                        "message": f"User input source detected: {source.pattern}",
                        "file": result.file_path,
                        "line": source.line,
                        "framework": result.framework.value,
                        "recommendation": "Validate and sanitize user input before use.",
                    }
                )

        return findings

    def _get_recommendation(self, flow: DataFlow) -> str:
        """Get recommendation based on sink type."""
        recommendations = {
            DangerousSinkType.INNER_HTML: (
                "Use textContent instead of innerHTML, or sanitize with DOMPurify: "
                "element.innerHTML = DOMPurify.sanitize(userInput)"
            ),
            DangerousSinkType.DANGEROUSLY_SET: (
                "Avoid dangerouslySetInnerHTML with user input. If necessary, "
                "sanitize first: dangerouslySetInnerHTML={{__html: DOMPurify.sanitize(input)}}"
            ),
            DangerousSinkType.V_HTML: (
                "Avoid v-html with user input. Use {{ interpolation }} for text, "
                "or sanitize with DOMPurify before using v-html"
            ),
            DangerousSinkType.DOCUMENT_WRITE: (
                "Avoid document.write entirely. Use DOM manipulation methods "
                "like createElement and appendChild instead"
            ),
            DangerousSinkType.EVAL: (
                "Never use eval with user input. Use JSON.parse for data, "
                "or refactor to avoid dynamic code execution"
            ),
            DangerousSinkType.LOCATION: (
                "Validate URLs before redirect. Use allowlist of permitted domains " "and validate with URL constructor"
            ),
        }
        return recommendations.get(
            flow.sink.sink_type,
            "Validate and sanitize user input before passing to this operation",
        )


# =============================================================================
# Convenience Functions
# =============================================================================


def analyze_frontend_file(
    file_path: str,
    framework: str | None = None,
) -> FrontendAnalysisResult:
    """
    Analyze a frontend file for input sources and XSS risks.

    Args:
        file_path: Path to the file to analyze
        framework: Optional framework hint

    Returns:
        FrontendAnalysisResult with findings
    """
    path = Path(file_path)

    if not path.exists():
        result = FrontendAnalysisResult(file_path=file_path)
        result.errors.append(f"File not found: {file_path}")
        return result

    source_code = path.read_text(encoding="utf-8")

    tracker = FrontendInputTracker()
    return tracker.analyze_file(source_code, file_path, framework)


def analyze_frontend_codebase(
    directory: str,
    framework: str | None = None,
) -> list[FrontendAnalysisResult]:
    """
    Analyze a frontend codebase for input sources and XSS risks.

    Args:
        directory: Root directory to scan
        framework: Optional framework hint

    Returns:
        List of FrontendAnalysisResult for each file with findings
    """
    extensions = [".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte"]
    results = []
    root = Path(directory)

    tracker = FrontendInputTracker()

    for ext in extensions:
        for file_path in root.rglob(f"*{ext}"):
            # Skip node_modules and build directories
            if any(part in file_path.parts for part in ["node_modules", "dist", "build", ".next", ".nuxt"]):
                continue

            try:
                source_code = file_path.read_text(encoding="utf-8")
                result = tracker.analyze_file(source_code, str(file_path), framework)

                # Only include files with findings
                if result.input_sources or result.dangerous_sinks:
                    results.append(result)

            except Exception as e:
                result = FrontendAnalysisResult(file_path=str(file_path))
                result.errors.append(str(e))
                results.append(result)

    return results


def get_xss_risks(results: list[FrontendAnalysisResult]) -> list[DataFlow]:
    """
    Get all XSS risks from multiple analysis results.

    Args:
        results: List of analysis results

    Returns:
        List of dangerous data flows across all files
    """
    all_flows = []
    for result in results:
        all_flows.extend(result.dangerous_flows)
    return all_flows


# [20251225_FEATURE] Export public API for type checkers
__all__ = [
    "FrontendInputTracker",
    "FrontendAnalysisResult",
    "FrontendFramework",
    "InputSource",
    "InputSourceType",
    "DangerousSink",
    "DangerousSinkType",
    "DataFlow",
    "analyze_frontend_file",
    "analyze_frontend_codebase",
    "get_xss_risks",
]
