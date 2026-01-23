"""
Code Scalpel Autonomy Integrations - Framework-specific integrations.

[20251217_FEATURE] Framework integrations for LangGraph, CrewAI, and AutoGen.
"""

from .autogen import create_scalpel_autogen_agents
from .crewai import create_scalpel_fix_crew
from .langgraph import ScalpelState, create_scalpel_fix_graph

__all__ = [
    "create_scalpel_fix_graph",
    "ScalpelState",
    "create_scalpel_fix_crew",
    "create_scalpel_autogen_agents",
]
