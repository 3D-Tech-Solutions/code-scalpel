"""rust-analyzer Parser — parse rust-analyzer LSP diagnostic output.

[20260305_FEATURE] Enterprise-tool pattern: execute raises NotImplementedError
with setup instructions; parse methods fully implemented.

rust-analyzer communicates via the Language Server Protocol (LSP).
Diagnostics are sent as ``textDocument/publishDiagnostics`` notifications.
JSON structure:
    {
      "method": "textDocument/publishDiagnostics",
      "params": {
        "uri": "file:///path/to/file.rs",
        "diagnostics": [
          {
            "range": {"start": {"line": 0, "character": 0}, "end": {...}},
            "severity": 1,  // 1=Error, 2=Warning, 3=Information, 4=Hint
            "code": "E0001",
            "message": "...",
            "source": "rust-analyzer"
          }
        ]
      }
    }
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# LSP severity mapping
_SEVERITY_MAP = {1: "error", 2: "warning", 3: "information", 4: "hint"}


@dataclass
class RustAnalyzerDiagnostic:
    """Single rust-analyzer LSP diagnostic.

    [20260305_FEATURE] Represents one LSP publishDiagnostics entry.
    """

    severity: str  # "error", "warning", "information", "hint"
    message: str
    code: Optional[str]
    file_uri: Optional[str]
    line: int  # 1-based
    column: int  # 1-based
    source: str = "rust-analyzer"

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "message": self.message,
            "code": self.code,
            "file_uri": self.file_uri,
            "line": self.line,
            "column": self.column,
            "source": self.source,
        }


class RustAnalyzerParser:
    """Parser for rust-analyzer LSP diagnostic output.

    [20260305_FEATURE] Enterprise-tool pattern.

    **Enterprise setup required:**
    rust-analyzer is a Language Server Protocol (LSP) server.
    To use it:
    1. Install rust-analyzer: ``rustup component add rust-analyzer``
       or download from https://github.com/rust-lang/rust-analyzer/releases
    2. Start as an LSP daemon: ``rust-analyzer``
    3. Send LSP ``initialize`` + ``workspace/didOpen`` requests
    4. Collect ``textDocument/publishDiagnostics`` notifications
    5. Feed JSON notification payloads to ``parse_lsp_notification()``

    For IDE integration, rust-analyzer is typically embedded in editors
    (VS Code rust-analyzer extension, IntelliJ Rust, etc.).

    Execute::
        parser = RustAnalyzerParser()
        # execute raises NotImplementedError with setup instructions
        try:
            parser.execute_rust_analyzer([Path("src/")])
        except NotImplementedError as e:
            print(e)

    Parse raw LSP output (once you have it)::
        diags = parser.parse_lsp_notification(lsp_json_payload)
    """

    TOOL_NAME = "rust-analyzer"
    DISPLAY_NAME = "rust-analyzer"

    # ---------------------------------------------------------------------------
    # Execution (enterprise — not directly executable)
    # ---------------------------------------------------------------------------

    def execute_rust_analyzer(self, paths, **kwargs):
        """Run rust-analyzer.

        This method raises NotImplementedError because rust-analyzer operates
        as an LSP daemon and requires IDE/editor integration.

        Raises:
            NotImplementedError: Always — use LSP integration instead.
        """
        raise NotImplementedError(
            "rust-analyzer requires LSP integration to produce diagnostics.\n"
            "\n"
            "Setup instructions:\n"
            "  1. Install: rustup component add rust-analyzer\n"
            "     Or download from: https://github.com/rust-lang/rust-analyzer/releases\n"
            "  2. Start the LSP daemon: rust-analyzer\n"
            "  3. Send LSP initialize + textDocument/didOpen requests\n"
            "  4. Collect textDocument/publishDiagnostics notifications\n"
            "  5. Parse them with RustAnalyzerParser.parse_lsp_notification()\n"
            "\n"
            "For CI use, consider cargo check or cargo clippy instead.\n"
            "These provide compiler diagnostics in JSON format without LSP setup:\n"
            "  cargo check --message-format json\n"
            "  cargo clippy --message-format json"
        )

    # ---------------------------------------------------------------------------
    # Parsing
    # ---------------------------------------------------------------------------

    def parse_lsp_notification(
        self, notification: Dict[str, Any]
    ) -> List[RustAnalyzerDiagnostic]:
        """Parse a single ``textDocument/publishDiagnostics`` LSP notification.

        Args:
            notification: Parsed JSON dict from the LSP server.

        Returns:
            List of RustAnalyzerDiagnostic objects.
        """
        findings: List[RustAnalyzerDiagnostic] = []
        if notification.get("method") != "textDocument/publishDiagnostics":
            return findings
        params = notification.get("params", {})
        uri = params.get("uri", "")
        for diag in params.get("diagnostics", []):
            finding = self._parse_diagnostic(diag, file_uri=uri)
            if finding:
                findings.append(finding)
        return findings

    def parse_output(self, output: str) -> List[RustAnalyzerDiagnostic]:
        """Parse newline-delimited LSP notifications from a text stream.

        Args:
            output: Newline-delimited JSON LSP messages.

        Returns:
            List of RustAnalyzerDiagnostic objects.
        """
        findings: List[RustAnalyzerDiagnostic] = []
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            findings.extend(self.parse_lsp_notification(obj))
        return findings

    def parse_diagnostics_array(
        self, diagnostics: List[Dict[str, Any]], file_uri: str = ""
    ) -> List[RustAnalyzerDiagnostic]:
        """Parse a raw ``diagnostics`` array (without the LSP wrapper).

        Args:
            diagnostics: List of LSP Diagnostic objects.
            file_uri: The URI of the file these diagnostics belong to.

        Returns:
            List of RustAnalyzerDiagnostic objects.
        """
        findings: List[RustAnalyzerDiagnostic] = []
        for diag in diagnostics:
            finding = self._parse_diagnostic(diag, file_uri=file_uri)
            if finding:
                findings.append(finding)
        return findings

    def _parse_diagnostic(
        self, diag: Dict[str, Any], file_uri: str = ""
    ) -> Optional[RustAnalyzerDiagnostic]:
        """Parse a single LSP Diagnostic object."""
        severity_int = diag.get("severity", 1)
        severity = _SEVERITY_MAP.get(severity_int, "error")
        message = diag.get("message", "")
        if not message:
            return None
        code = diag.get("code")
        if isinstance(code, dict):
            code = code.get("value") or code.get("code")
        source = diag.get("source", "rust-analyzer")

        # Extract range (0-based LSP → 1-based for parity with other parsers)
        range_obj = diag.get("range", {})
        start = range_obj.get("start", {})
        line = start.get("line", 0) + 1
        column = start.get("character", 0) + 1

        return RustAnalyzerDiagnostic(
            severity=severity,
            message=message,
            code=str(code) if code else None,
            file_uri=file_uri or None,
            line=line,
            column=column,
            source=source,
        )
