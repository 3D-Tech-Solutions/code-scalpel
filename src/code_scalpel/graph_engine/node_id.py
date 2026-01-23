"""
Universal Node ID System - Standardized AST node identification across languages.

[20251216_FEATURE] v2.1.0 - Universal node ID format for cross-language graphs

This module implements a standardized format for identifying code elements
across Python, Java, TypeScript, and JavaScript. The format is:

    language::module::type::name[:method]

Examples:
    "python::app.handlers::class::RequestHandler"
    "java::com.example.api::controller::UserController:getUser"
    "typescript::src/api/client::function::fetchUsers"
    "javascript::utils/helpers::function::formatDate"

The universal ID enables the graph engine to:
- Reference any code element uniformly
- Build cross-language dependency graphs
- Track taint flow across module boundaries
- Detect HTTP links between frontend and backend
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


# [20251216_FEATURE] Node types for universal identification
class NodeType(Enum):
    """Type of code element."""

    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    FIELD = "field"
    PROPERTY = "property"
    VARIABLE = "variable"
    INTERFACE = "interface"
    ENDPOINT = "endpoint"  # HTTP endpoint
    CLIENT = "client"  # HTTP client call
    CONTROLLER = "controller"  # Java/TypeScript controller
    MODULE = "module"
    PACKAGE = "package"


# [20251216_FEATURE] Universal node ID data structure
@dataclass
class UniversalNodeID:
    """
    Universal identifier for a code element across any language.

    Attributes:
        language: Programming language (python, java, typescript, javascript)
        module: Module/package path (e.g., "app.handlers", "com.example.api")
        node_type: Type of code element (function, class, method, etc.)
        name: Name of the element
        method: Optional method name (for class methods)
        line: Optional line number
        file: Optional file path
    """

    language: str
    module: str
    node_type: NodeType
    name: str
    method: str | None = None
    line: int | None = None
    file: str | None = None

    def __str__(self) -> str:
        """Format as universal ID string."""
        parts = [self.language, self.module, self.node_type.value, self.name]
        id_str = "::".join(parts)
        if self.method:
            id_str += f":{self.method}"
        return id_str

    def to_short_id(self) -> str:
        """Short ID without module for display."""
        if self.method:
            return f"{self.language}::{self.name}:{self.method}"
        return f"{self.language}::{self.name}"

    def to_dict(self) -> dict[str, str | int]:
        """
        Convert to dictionary for JSON serialization.

        [20251220_BUGFIX] Fixed return type annotation to accept both str and int values.
        The dict contains string fields (id, language, module, type, name, method, file)
        and optional integer field (line).
        """
        result: dict[str, str | int] = {
            "id": str(self),
            "language": self.language,
            "module": self.module,
            "type": self.node_type.value,
            "name": self.name,
        }
        if self.method:
            result["method"] = self.method
        if self.line is not None:
            result["line"] = self.line
        if self.file:
            result["file"] = self.file
        return result

    @staticmethod
    def from_dict(data: dict) -> UniversalNodeID:
        """Create from dictionary."""
        return UniversalNodeID(  # type: ignore[call-arg]
            language=data["language"],
            module=data["module"],
            node_type=NodeType(data["type"]),
            name=data["name"],
            method=data.get("method"),
            line=data.get("line"),
            file=data.get("file"),
        )


# [20251216_FEATURE] Parser for universal node IDs
def parse_node_id(id_string: str) -> UniversalNodeID:
    """
    Parse a universal node ID string into components.

    Args:
        id_string: ID in format "language::module::type::name[:method]"

    Returns:
        UniversalNodeID object

    Raises:
        ValueError: If format is invalid

    Examples:
        >>> parse_node_id("python::app.handlers::class::RequestHandler")
        UniversalNodeID(language='python', module='app.handlers', ...)

        >>> parse_node_id("java::com.example::controller::UserController:getUser")
        UniversalNodeID(language='java', ..., method='getUser')
    """
    # Split by :: for main components
    parts = id_string.split("::")
    if len(parts) != 4:
        raise ValueError(f"Invalid node ID format: {id_string}. " f"Expected: language::module::type::name[:method]")

    language, module, type_str, name_part = parts

    # Check for method suffix (after :)
    method = None
    if ":" in name_part:
        name, method = name_part.split(":", 1)
    else:
        name = name_part

    try:
        node_type = NodeType(type_str)
    except ValueError:
        raise ValueError(f"Invalid node type: {type_str}")

    return UniversalNodeID(  # type: ignore[call-arg]
        language=language,
        module=module,
        node_type=node_type,
        name=name,
        method=method,
    )


# [20251216_FEATURE] Factory function for creating node IDs
def create_node_id(
    language: str,
    module: str,
    node_type: str | NodeType,
    name: str,
    method: str | None = None,
    line: int | None = None,
    file: str | None = None,
) -> UniversalNodeID:
    """
    Create a universal node ID.

    Args:
        language: Programming language
        module: Module/package path
        node_type: Type of node (as string or NodeType enum)
        name: Name of the element
        method: Optional method name
        line: Optional line number
        file: Optional file path

    Returns:
        UniversalNodeID object

    Examples:
        >>> create_node_id("python", "app.handlers", "class", "RequestHandler")
        >>> create_node_id(
        ...     "java", "com.example", NodeType.METHOD, "UserController", "getUser"
        ... )
    """
    if isinstance(node_type, str):
        node_type = NodeType(node_type)

    return UniversalNodeID(  # type: ignore[call-arg]
        language=language,
        module=module,
        node_type=node_type,
        name=name,
        method=method,
        line=line,
        file=file,
    )
