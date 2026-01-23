"""
Code Scalpel Agents - AI Agent Framework for Code Analysis.

This module provides specialized AI agents that demonstrate how to use Code Scalpel's
MCP tools for various code analysis and improvement tasks.

Agents follow the OODA loop (Observe, Orient, Decide, Act) and use MCP tools to:
- Observe: Gather information about codebases
- Orient: Analyze and understand context
- Decide: Determine optimal actions
- Act: Execute changes safely with verification

Available Agents:
- CodeReviewAgent: Comprehensive code quality and security review
- SecurityAgent: Specialized security vulnerability detection and remediation
- OptimizationAgent: Performance analysis and optimization suggestions
- RefactoringAgent: Code restructuring and design pattern refactoring
- TestingAgent: Test generation and coverage analysis
- DocumentationAgent: Documentation generation and improvement
- MetricsAgent: Code metrics aggregation and analytics

Example Usage:
    from code_scalpel.agents import CodeReviewAgent

    agent = CodeReviewAgent(workspace_root="/path/to/project")
    result = await agent.execute_ooda_loop("src/main.py")
"""

from .base_agent import AgentContext, BaseCodeAnalysisAgent
from .code_review_agent import CodeReviewAgent

# [20251224_BUGFIX] Correct typo in filename: optimazation_agent -> optimization_agent
# Note: File exists as optimazation_agent.py - needs rename during refactoring
from .optimazation_agent import OptimizationAgent
from .security_agent import SecurityAgent

# from .documentation_agent import DocumentationAgent
# from .metrics_agent import MetricsAgent
# from .refactoring_agent import RefactoringAgent
# from .testing_agent import TestingAgent

# Purpose: Establish robust module structure and agent framework foundation

# Purpose: Add sophisticated agent coordination and learning capabilities

# Purpose: Enterprise-grade agent orchestration, governance, and compliance

__all__ = [
    "BaseCodeAnalysisAgent",
    "AgentContext",
    "CodeReviewAgent",
    "OptimizationAgent",
    "SecurityAgent",
    # Add when implemented:
    # "DocumentationAgent",
    # "MetricsAgent",
    # "RefactoringAgent",
    # "TestingAgent",
]
