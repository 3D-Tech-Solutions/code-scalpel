# [20251230_REFACTOR] MCP-first: keep integrations importable without optional deps.
# This module lazily imports agent/web integrations only when accessed.


from __future__ import annotations

from typing import TYPE_CHECKING, Any

# [20251230_REFACTOR] MCP-first: keep integrations importable without optional deps.
# This module lazily imports agent/web integrations only when accessed.


if TYPE_CHECKING:
    # Agent integrations
    from .autogen import AnalysisResult, AutogenCodeAnalysisAgent, AutogenScalpel
    from .crewai import CrewAIScalpel, RefactorResult

    # Legacy REST API server (Flask)
    from .rest_api_server import MCPServerConfig, create_app
    from .rest_api_server import run_server as run_rest_server

__all__ = [
    # Autogen integration
    "AutogenScalpel",
    "AutogenCodeAnalysisAgent",  # Backward compatibility alias
    "AnalysisResult",
    # CrewAI integration
    "CrewAIScalpel",
    "RefactorResult",
    # REST API Server (legacy, not MCP-compliant)
    "create_app",
    "run_rest_server",
    "MCPServerConfig",
]


def __getattr__(name: str) -> Any:
    """Lazy attribute loading for optional integrations (PEP 562)."""
    if name in {"AutogenScalpel", "AutogenCodeAnalysisAgent", "AnalysisResult"}:
        try:
            from .autogen import (
                AnalysisResult,
                AutogenCodeAnalysisAgent,
                AutogenScalpel,
            )
        except ImportError as e:  # pragma: no cover
            raise ImportError(
                "AutoGen integration requires optional dependencies. "
                'Install with: pip install "code-scalpel[agents]"'
            ) from e
        return {
            "AutogenScalpel": AutogenScalpel,
            "AutogenCodeAnalysisAgent": AutogenCodeAnalysisAgent,
            "AnalysisResult": AnalysisResult,
        }[name]

    if name in {"CrewAIScalpel", "RefactorResult"}:
        try:
            from .crewai import CrewAIScalpel, RefactorResult
        except ImportError as e:  # pragma: no cover
            raise ImportError(
                "CrewAI integration requires optional dependencies. " 'Install with: pip install "code-scalpel[agents]"'
            ) from e
        return {"CrewAIScalpel": CrewAIScalpel, "RefactorResult": RefactorResult}[name]

    if name in {"MCPServerConfig", "create_app", "run_rest_server"}:
        try:
            from .rest_api_server import MCPServerConfig, create_app
            from .rest_api_server import run_server as run_rest_server
        except ImportError as e:  # pragma: no cover
            raise ImportError(
                "The legacy REST API server requires Flask. " 'Install with: pip install "code-scalpel[web]"'
            ) from e
        return {
            "MCPServerConfig": MCPServerConfig,
            "create_app": create_app,
            "run_rest_server": run_rest_server,
        }[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
