"""
Tests for v2.0.0 MCP Tool Polyglot Integration.

[20251214_TEST] v2.0.0 - Test extract_code MCP tool with JavaScript, TypeScript, and Java.
"""

import pytest


@pytest.fixture
def java_file(tmp_path):
    """Create a temporary Java file for testing."""
    code = """
public class Calculator {
    private int result;

    public int add(int a, int b) {
        return a + b;
    }

    public int multiply(int x, int y) {
        return x * y;
    }
}
"""
    file_path = tmp_path / "Calculator.java"
    file_path.write_text(code)
    return str(file_path)


@pytest.fixture
def js_file(tmp_path):
    """Create a temporary JavaScript file for testing."""
    code = """
function add(a, b) {
    return a + b;
}

const multiply = (x, y) => x * y;

class Calculator {
    constructor() {
        this.result = 0;
    }

    subtract(a, b) {
        return a - b;
    }
}
"""
    file_path = tmp_path / "calculator.js"
    file_path.write_text(code)
    return str(file_path)


@pytest.fixture
def ts_file(tmp_path):
    """Create a temporary TypeScript file for testing."""
    code = """
interface User {
    name: string;
    age: number;
}

function greet(user: User): string {
    return `Hello ${user.name}`;
}

class UserService {
    private users: User[] = [];

    addUser(user: User): void {
        this.users.push(user);
    }
}
"""
    file_path = tmp_path / "user.ts"
    file_path.write_text(code)
    return str(file_path)


class TestMCPExtractJava:
    """Test MCP extract_code tool with Java files."""

    @pytest.mark.asyncio
    async def test_extract_java_class_from_file(self, java_file):
        from code_scalpel.mcp.server import extract_code

        result = await extract_code(
            target_type="class",
            target_name="Calculator",
            file_path=java_file,
        )

        assert result.success
        assert "public class Calculator" in result.target_code

    @pytest.mark.asyncio
    async def test_extract_java_method_from_file(self, java_file):
        from code_scalpel.mcp.server import extract_code

        result = await extract_code(
            target_type="method",
            target_name="Calculator.add",
            file_path=java_file,
        )

        assert result.success
        assert "public int add" in result.target_code

    @pytest.mark.asyncio
    async def test_extract_java_with_explicit_language(self, java_file):
        from code_scalpel.mcp.server import extract_code

        result = await extract_code(
            target_type="class",
            target_name="Calculator",
            file_path=java_file,
            language="java",
        )

        assert result.success


class TestMCPExtractJavaScript:
    """Test MCP extract_code tool with JavaScript files."""

    @pytest.mark.asyncio
    async def test_extract_js_function_from_file(self, js_file):
        from code_scalpel.mcp.server import extract_code

        result = await extract_code(
            target_type="function",
            target_name="add",
            file_path=js_file,
        )

        assert result.success
        assert "function add" in result.target_code

    @pytest.mark.asyncio
    async def test_extract_js_class_from_file(self, js_file):
        from code_scalpel.mcp.server import extract_code

        result = await extract_code(
            target_type="class",
            target_name="Calculator",
            file_path=js_file,
        )

        assert result.success
        assert "class Calculator" in result.target_code

    @pytest.mark.asyncio
    async def test_extract_js_with_explicit_language(self, js_file):
        from code_scalpel.mcp.server import extract_code

        result = await extract_code(
            target_type="function",
            target_name="add",
            file_path=js_file,
            language="javascript",
        )

        assert result.success


class TestMCPExtractTypeScript:
    """Test MCP extract_code tool with TypeScript files."""

    @pytest.mark.asyncio
    async def test_extract_ts_function_from_file(self, ts_file):
        from code_scalpel.mcp.server import extract_code

        result = await extract_code(
            target_type="function",
            target_name="greet",
            file_path=ts_file,
        )

        assert result.success
        assert "function greet" in result.target_code

    @pytest.mark.asyncio
    async def test_extract_ts_class_from_file(self, ts_file):
        from code_scalpel.mcp.server import extract_code

        result = await extract_code(
            target_type="class",
            target_name="UserService",
            file_path=ts_file,
        )

        assert result.success
        assert "class UserService" in result.target_code

    @pytest.mark.asyncio
    async def test_extract_ts_with_explicit_language(self, ts_file):
        from code_scalpel.mcp.server import extract_code

        result = await extract_code(
            target_type="function",
            target_name="greet",
            file_path=ts_file,
            language="typescript",
        )

        assert result.success


class TestMCPExtractFromCode:
    """Test MCP extract_code tool with inline code."""

    @pytest.mark.asyncio
    async def test_extract_java_from_code(self):
        from code_scalpel.mcp.server import extract_code

        java_code = """
public class Test {
    public void hello() {
        System.out.println("Hello");
    }
}
"""
        result = await extract_code(
            target_type="class",
            target_name="Test",
            code=java_code,
            language="java",
        )

        assert result.success
        assert "public class Test" in result.target_code

    @pytest.mark.asyncio
    async def test_extract_js_from_code(self):
        from code_scalpel.mcp.server import extract_code

        js_code = """
function hello() {
    console.log("Hello");
}
"""
        result = await extract_code(
            target_type="function",
            target_name="hello",
            code=js_code,
            language="javascript",
        )

        assert result.success
        assert "function hello" in result.target_code


class TestMCPExtractErrors:
    """Test error handling in polyglot extraction."""

    @pytest.mark.asyncio
    async def test_extract_nonexistent_java_class(self, java_file):
        from code_scalpel.mcp.server import extract_code

        result = await extract_code(
            target_type="class",
            target_name="NonExistent",
            file_path=java_file,
        )

        assert not result.success
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_extract_nonexistent_js_function(self, js_file):
        from code_scalpel.mcp.server import extract_code

        result = await extract_code(
            target_type="function",
            target_name="notexists",
            file_path=js_file,
        )

        assert not result.success
        assert "not found" in result.error.lower()
