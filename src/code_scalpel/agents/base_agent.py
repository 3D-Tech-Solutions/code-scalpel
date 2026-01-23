"""
Base agent framework for AI agents using Code Scalpel MCP tools.

This module provides the foundation for building AI agents that leverage Code Scalpel's
surgical code analysis and modification capabilities. Agents follow the OODA loop:
Observe → Orient → Decide → Act.

The base agent provides:
- MCP tool integration
- Context management
- Error handling
- Logging and telemetry
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Any

# Import MCP tools for agent use
from code_scalpel.mcp.tools.context import get_file_context, get_symbol_references
from code_scalpel.mcp.tools.extraction import extract_code, update_symbol
from code_scalpel.mcp.tools.symbolic import simulate_refactor


class AgentContext:
    """Context information for agent operations."""

    def __init__(self):
        self.workspace_root: str | None = None
        self.current_file: str | None = None
        self.recent_operations: list[dict[str, Any]] = []
        self.knowledge_base: dict[str, Any] = {}

        # Purpose: Establish robust context tracking and basic persistence

        # Purpose: Add intelligent context management and learning capabilities

        # Purpose: Enterprise-grade context governance and compliance

    def add_operation(self, operation: str, result: Any, success: bool = True):
        """Record an operation and its result."""
        # [20251215_BUGFIX] Use a monotonic clock even when no asyncio loop is running
        try:
            timestamp = asyncio.get_running_loop().time()
        except RuntimeError:
            timestamp = time.monotonic()

        self.recent_operations.append(
            {
                "operation": operation,
                "result": result,
                "success": success,
                "timestamp": timestamp,
            }
        )

    def get_recent_context(self, limit: int = 5) -> list[dict[str, Any]]:
        """Get recent operations for context."""
        return self.recent_operations[-limit:]


class BaseCodeAnalysisAgent(ABC):
    """
    Base class for AI agents that use Code Scalpel MCP tools.

    Agents should implement the OODA loop:
    1. Observe: Gather information about the codebase
    2. Orient: Analyze and understand the context
    3. Decide: Determine what actions to take
    4. Act: Execute changes safely
    """

    def __init__(self, workspace_root: str | None = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.context = AgentContext()
        self.workspace_root = workspace_root
        self._setup_logging()

    @property
    def workspace_root(self) -> str | None:
        """[20260104_BUGFIX] Keep workspace_root accessible on the agent while syncing context."""
        return self.context.workspace_root

    @workspace_root.setter
    def workspace_root(self, value: str | None) -> None:
        self.context.workspace_root = value

    def _setup_logging(self):
        """Setup logging for the agent."""
        handler = logging.StreamHandler()
        formatter = logging.Formatter(f"%(asctime)s - {self.__class__.__name__} - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    # MCP Tool Integration Methods

    async def observe_file(self, file_path: str) -> dict[str, Any]:
        """Observe a file using get_file_context tool."""
        try:
            result = await get_file_context(file_path)
            self.context.add_operation("observe_file", result, result.success)
            return result.model_dump()
        except Exception as e:
            self.logger.error(f"Failed to observe file {file_path}: {e}")
            self.context.add_operation("observe_file", str(e), False)
            return {"success": False, "error": str(e)}

    async def find_symbol_usage(self, symbol_name: str, project_root: str | None = None) -> dict[str, Any]:
        """Find all usages of a symbol using get_symbol_references tool."""
        try:
            result = await get_symbol_references(symbol_name, project_root)
            self.context.add_operation("find_symbol_usage", result, result.success)
            return result.model_dump()
        except Exception as e:
            self.logger.error(f"Failed to find symbol {symbol_name}: {e}")
            self.context.add_operation("find_symbol_usage", str(e), False)
            return {"success": False, "error": str(e)}

    async def analyze_code_security(self, code: str) -> dict[str, Any]:
        """Analyze code for security issues using security_scan tool."""
        try:
            from code_scalpel.mcp.tools.security import security_scan

            result = await security_scan(code)
            self.context.add_operation("analyze_security", result, True)
            return result.model_dump()
        except Exception as e:
            self.logger.error(f"Failed to analyze security: {e}")
            self.context.add_operation("analyze_security", str(e), False)
            return {"success": False, "error": str(e)}

    async def extract_function(self, file_path: str, function_name: str) -> dict[str, Any]:
        """Extract a specific function using extract_code tool."""
        try:
            result = await extract_code(file_path, "function", function_name)
            self.context.add_operation("extract_function", result, result.success)
            return result.model_dump()
        except Exception as e:
            self.logger.error(f"Failed to extract function {function_name}: {e}")
            self.context.add_operation("extract_function", str(e), False)
            return {"success": False, "error": str(e)}

    async def simulate_code_change(self, original_code: str, new_code: str) -> dict[str, Any]:
        """Simulate a code change to verify safety using simulate_refactor tool."""
        try:
            result = await simulate_refactor(original_code, new_code)
            self.context.add_operation("simulate_change", result, True)
            return result.model_dump()
        except Exception as e:
            self.logger.error(f"Failed to simulate change: {e}")
            self.context.add_operation("simulate_change", str(e), False)
            return {"success": False, "error": str(e)}

    async def apply_safe_change(
        self, file_path: str, target_type: str, target_name: str, new_code: str
    ) -> dict[str, Any]:
        """Apply a safe code change using update_symbol tool."""
        try:
            result = await update_symbol(file_path, target_type, target_name, new_code)
            self.context.add_operation("apply_change", result, result.success)
            return result.model_dump()
        except Exception as e:
            self.logger.error(f"Failed to apply change: {e}")
            self.context.add_operation("apply_change", str(e), False)
            return {"success": False, "error": str(e)}

    # Abstract Methods for Agent Logic

    @abstractmethod
    async def observe(self, target: str) -> dict[str, Any]:
        """Observe the target (file, function, etc.) and gather information."""
        pass

    @abstractmethod
    async def orient(self, observations: dict[str, Any]) -> dict[str, Any]:
        """Analyze observations and build understanding."""
        pass

    @abstractmethod
    async def decide(self, analysis: dict[str, Any]) -> dict[str, Any]:
        """Decide what actions to take based on analysis."""
        pass

    @abstractmethod
    async def act(self, decisions: dict[str, Any]) -> dict[str, Any]:
        """Execute the decided actions safely."""
        pass

    # Main Agent Loop

    async def execute_ooda_loop(self, target: str) -> dict[str, Any]:
        """
        Execute the complete OODA loop for a given target.

        Returns:
            Dict containing the results of each phase and overall success
        """
        # Purpose: Implement robust OODA loop execution with safety guarantees

        # Purpose: Add intelligent loop optimization and advanced capabilities

        # Purpose: Enterprise-grade OODA orchestration and governance
        try:
            self.logger.info(f"Starting OODA loop for target: {target}")

            # Observe
            observations = await self.observe(target)
            if not observations.get("success", False):
                return {
                    "success": False,
                    "phase": "observe",
                    "error": observations.get("error"),
                }

            # Orient
            analysis = await self.orient(observations)
            if not analysis.get("success", False):
                return {
                    "success": False,
                    "phase": "orient",
                    "error": analysis.get("error"),
                }

            # Decide
            decisions = await self.decide(analysis)
            if not decisions.get("success", False):
                return {
                    "success": False,
                    "phase": "decide",
                    "error": decisions.get("error"),
                }

            # Act
            actions = await self.act(decisions)
            success = actions.get("success", False)

            result = {
                "success": success,
                "phases": {
                    "observe": observations,
                    "orient": analysis,
                    "decide": decisions,
                    "act": actions,
                },
                "context": self.context.get_recent_context(),
            }

            self.logger.info(f"OODA loop completed with success: {success}")
            return result

        except Exception as e:
            self.logger.error(f"OODA loop failed: {e}")
            return {"success": False, "error": str(e)}

    # Utility Methods

    def get_context_summary(self) -> dict[str, Any]:
        """Get a summary of the current agent context."""
        return {
            "workspace_root": self.context.workspace_root,
            "current_file": self.context.current_file,
            "recent_operations_count": len(self.context.recent_operations),
            "knowledge_base_keys": list(self.context.knowledge_base.keys()),
        }
