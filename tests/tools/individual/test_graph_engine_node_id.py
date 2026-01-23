"""
Tests for universal node ID system.

[20251216_FEATURE] v2.1.0 - Test universal node IDs across languages
"""

import pytest

from code_scalpel.graph_engine.node_id import (
    NodeType,
    UniversalNodeID,
    create_node_id,
    parse_node_id,
)


class TestUniversalNodeID:
    """Tests for UniversalNodeID class."""

    def test_create_python_function(self):
        """Test creating a Python function node ID."""
        node_id = UniversalNodeID(
            language="python",
            module="app.handlers",
            node_type=NodeType.FUNCTION,
            name="process_request",
        )

        assert str(node_id) == "python::app.handlers::function::process_request"
        assert node_id.language == "python"
        assert node_id.module == "app.handlers"
        assert node_id.node_type == NodeType.FUNCTION
        assert node_id.name == "process_request"
        assert node_id.method is None

    def test_create_java_method(self):
        """Test creating a Java method node ID."""
        node_id = UniversalNodeID(
            language="java",
            module="com.example.api",
            node_type=NodeType.METHOD,
            name="UserController",
            method="getUser",
        )

        assert str(node_id) == "java::com.example.api::method::UserController:getUser"
        assert node_id.method == "getUser"

    def test_create_typescript_function(self):
        """Test creating a TypeScript function node ID."""
        node_id = UniversalNodeID(
            language="typescript",
            module="src/api/client",
            node_type=NodeType.FUNCTION,
            name="fetchUsers",
        )

        assert str(node_id) == "typescript::src/api/client::function::fetchUsers"

    def test_to_short_id(self):
        """Test short ID generation."""
        node_id = UniversalNodeID(
            language="python",
            module="app.handlers",
            node_type=NodeType.CLASS,
            name="RequestHandler",
        )

        assert node_id.to_short_id() == "python::RequestHandler"

    def test_to_short_id_with_method(self):
        """Test short ID with method."""
        node_id = UniversalNodeID(
            language="java",
            module="com.example",
            node_type=NodeType.METHOD,
            name="UserController",
            method="getUser",
        )

        assert node_id.to_short_id() == "java::UserController:getUser"

    def test_to_dict(self):
        """Test dictionary serialization."""
        node_id = UniversalNodeID(
            language="python",
            module="app.handlers",
            node_type=NodeType.CLASS,
            name="RequestHandler",
            line=10,
            file="app/handlers.py",
        )

        d = node_id.to_dict()
        assert d["id"] == "python::app.handlers::class::RequestHandler"
        assert d["language"] == "python"
        assert d["module"] == "app.handlers"
        assert d["type"] == "class"
        assert d["name"] == "RequestHandler"
        assert d["line"] == 10
        assert d["file"] == "app/handlers.py"

    def test_from_dict(self):
        """Test dictionary deserialization."""
        data = {
            "id": "python::app.handlers::class::RequestHandler",
            "language": "python",
            "module": "app.handlers",
            "type": "class",
            "name": "RequestHandler",
            "line": 10,
        }

        node_id = UniversalNodeID.from_dict(data)
        assert node_id.language == "python"
        assert node_id.module == "app.handlers"
        assert node_id.node_type == NodeType.CLASS
        assert node_id.name == "RequestHandler"
        assert node_id.line == 10


class TestParseNodeID:
    """Tests for parse_node_id function."""

    def test_parse_python_class(self):
        """Test parsing a Python class ID."""
        node_id = parse_node_id("python::app.handlers::class::RequestHandler")

        assert node_id.language == "python"
        assert node_id.module == "app.handlers"
        assert node_id.node_type == NodeType.CLASS
        assert node_id.name == "RequestHandler"
        assert node_id.method is None

    def test_parse_java_method(self):
        """Test parsing a Java method ID."""
        node_id = parse_node_id("java::com.example.api::controller::UserController:getUser")

        assert node_id.language == "java"
        assert node_id.module == "com.example.api"
        assert node_id.node_type == NodeType.CONTROLLER
        assert node_id.name == "UserController"
        assert node_id.method == "getUser"

    def test_parse_typescript_function(self):
        """Test parsing a TypeScript function ID."""
        node_id = parse_node_id("typescript::src/api/client::function::fetchUsers")

        assert node_id.language == "typescript"
        assert node_id.module == "src/api/client"
        assert node_id.node_type == NodeType.FUNCTION
        assert node_id.name == "fetchUsers"

    def test_parse_invalid_format_too_few_parts(self):
        """Test parsing with too few parts."""
        with pytest.raises(ValueError, match="Invalid node ID format"):
            parse_node_id("python::app.handlers::class")

    def test_parse_invalid_format_too_many_colons(self):
        """Test parsing handles extra colons correctly."""
        # Should parse correctly - method part can contain colons
        node_id = parse_node_id("python::app.handlers::class::RequestHandler")
        assert node_id.name == "RequestHandler"

    def test_parse_invalid_node_type(self):
        """Test parsing with invalid node type."""
        with pytest.raises(ValueError, match="Invalid node type"):
            parse_node_id("python::app.handlers::invalid_type::Handler")


class TestCreateNodeID:
    """Tests for create_node_id factory function."""

    def test_create_with_string_type(self):
        """Test creating with string node type."""
        node_id = create_node_id(
            language="python",
            module="app.handlers",
            node_type="function",
            name="process_request",
        )

        assert node_id.node_type == NodeType.FUNCTION
        assert str(node_id) == "python::app.handlers::function::process_request"

    def test_create_with_enum_type(self):
        """Test creating with NodeType enum."""
        node_id = create_node_id(
            language="java",
            module="com.example",
            node_type=NodeType.CLASS,
            name="UserService",
        )

        assert node_id.node_type == NodeType.CLASS

    def test_create_with_method(self):
        """Test creating with method name."""
        node_id = create_node_id(
            language="java",
            module="com.example",
            node_type="method",
            name="UserController",
            method="getUser",
        )

        assert node_id.method == "getUser"
        assert str(node_id) == "java::com.example::method::UserController:getUser"

    def test_create_with_line_and_file(self):
        """Test creating with line number and file path."""
        node_id = create_node_id(
            language="python",
            module="app.handlers",
            node_type="class",
            name="Handler",
            line=42,
            file="app/handlers.py",
        )

        assert node_id.line == 42
        assert node_id.file == "app/handlers.py"


class TestNodeTypeEnum:
    """Tests for NodeType enum."""

    def test_all_types_available(self):
        """Test all expected node types are defined."""
        expected_types = [
            "function",
            "class",
            "method",
            "field",
            "property",
            "variable",
            "interface",
            "endpoint",
            "client",
            "module",
            "package",
        ]

        for type_name in expected_types:
            node_type = NodeType(type_name)
            assert node_type.value == type_name

    def test_endpoint_and_client_types(self):
        """Test HTTP-specific node types."""
        endpoint = NodeType.ENDPOINT
        client = NodeType.CLIENT

        assert endpoint.value == "endpoint"
        assert client.value == "client"
