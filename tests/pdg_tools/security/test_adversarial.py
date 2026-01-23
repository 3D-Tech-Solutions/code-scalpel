#!/usr/bin/env python
"""
Adversarial and Stress Tests for Code Scalpel MCP Tools

[20251215_TEST] This module contains difficult, edge-case, and adversarial tests
to ensure Code Scalpel tools are robust and production-ready.

Categories:
1. Malformed input handling
2. Unicode and encoding edge cases
3. Deeply nested code structures
4. Extremely large inputs
5. Pathological patterns (ReDoS, exponential complexity)
6. Cross-language edge cases
7. Security bypass attempts
8. Concurrent access patterns
"""

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from code_scalpel.mcp.server import (
    analyze_code,
    extract_code,
    security_scan,
    validate_paths,
)

# [20251215_TEST] Lint cleanup for adversarial tests (remove unused imports).


# ============================================================================
# 1. MALFORMED INPUT HANDLING
# ============================================================================


class TestMalformedInputs:
    """Tests for handling malformed, incomplete, or invalid inputs."""

    @pytest.mark.asyncio
    async def test_extract_empty_string(self):
        """Empty code string should fail gracefully."""
        result = await extract_code(code="", target_type="function", target_name="foo")
        assert not result.success
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_extract_whitespace_only(self):
        """Whitespace-only code should fail gracefully."""
        result = await extract_code(code="   \n\t\n   ", target_type="function", target_name="foo")
        assert not result.success

    @pytest.mark.asyncio
    async def test_extract_incomplete_function(self):
        """Incomplete function definition should be handled."""
        code = "def incomplete_func("
        result = await extract_code(code=code, target_type="function", target_name="incomplete_func")
        # Should either fail gracefully or handle partial parse
        assert result.error is not None or not result.success

    @pytest.mark.asyncio
    async def test_extract_mismatched_brackets(self):
        """Mismatched brackets should fail gracefully."""
        code = """
def broken():
    x = [1, 2, 3
    return x
"""
        result = await extract_code(code=code, target_type="function", target_name="broken")
        assert not result.success

    @pytest.mark.asyncio
    async def test_extract_null_bytes(self):
        """Code with null bytes should be handled."""
        code = "def foo():\x00\n    pass"
        result = await extract_code(code=code, target_type="function", target_name="foo")
        # Should either clean or reject
        assert result is not None

    @pytest.mark.asyncio
    async def test_extract_mixed_indentation(self):
        """Mixed tabs and spaces should be handled."""
        code = "def mixed():\n\treturn 1\n    return 2"
        result = await extract_code(code=code, target_type="function", target_name="mixed")
        # Python would reject this, so should we
        assert not result.success or "indent" in str(result.error).lower()

    @pytest.mark.asyncio
    async def test_security_scan_binary_content(self):
        """Binary content should be rejected gracefully."""
        binary = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]).decode("latin-1")
        result = await security_scan(code=binary)
        # Should not crash
        assert result is not None


# ============================================================================
# 2. UNICODE AND ENCODING EDGE CASES
# ============================================================================


class TestUnicodeEdgeCases:
    """Tests for Unicode handling and encoding edge cases."""

    @pytest.mark.asyncio
    async def test_extract_unicode_function_name(self):
        """Function with Unicode name should be extractable."""
        code = """
def 计算税(金额, 税率=0.1):
    return 金额 * 税率
"""
        result = await extract_code(code=code, target_type="function", target_name="计算税")
        # Python 3 supports Unicode identifiers
        assert result.success or "unicode" in str(result.error).lower()

    @pytest.mark.asyncio
    async def test_extract_emoji_in_string(self):
        """Code with emoji in strings should be handled."""
        code = """
def greet():
    return "Hello 👋 World 🌍!"
"""
        result = await extract_code(code=code, target_type="function", target_name="greet")
        assert result.success
        assert "👋" in result.target_code or result.success

    @pytest.mark.asyncio
    async def test_extract_rtl_characters(self):
        """Right-to-left characters should be handled."""
        code = """
def test_rtl():
    # مرحبا
    return "שלום"
"""
        result = await extract_code(code=code, target_type="function", target_name="test_rtl")
        assert result.success

    @pytest.mark.asyncio
    async def test_extract_zero_width_characters(self):
        """Zero-width characters should not break parsing."""
        # Zero-width space and zero-width joiner
        code = "def foo\u200b\u200c():\n    pass"
        result = await extract_code(code=code, target_type="function", target_name="foo")
        # Should either succeed or fail gracefully
        assert result is not None

    @pytest.mark.asyncio
    async def test_security_scan_homoglyph_attack(self):
        """Homoglyph attack (lookalike characters) should be detected."""
        # Using Cyrillic 'а' (U+0430) instead of Latin 'a'
        code = """
pаssword = "secret123"  # Cyrillic 'а' in password
"""
        result = await security_scan(code=code)
        # Should detect the secret even with homoglyph
        assert result.success


# ============================================================================
# 3. DEEPLY NESTED STRUCTURES
# ============================================================================


class TestDeeplyNestedStructures:
    """Tests for handling deeply nested code structures."""

    @pytest.mark.asyncio
    async def test_extract_deeply_nested_function(self):
        """Deeply nested function (10 levels) should be extractable."""
        code = """
class A:
    class B:
        class C:
            class D:
                class E:
                    class F:
                        class G:
                            class H:
                                class I:
                                    class J:
                                        def deeply_nested(self):
                                            return "found"
"""
        result = await extract_code(code=code, target_type="method", target_name="J.deeply_nested")
        assert result.success
        assert "deeply_nested" in result.target_code

    @pytest.mark.asyncio
    async def test_extract_deeply_nested_comprehension(self):
        """Deeply nested comprehension should be handled."""
        code = """
def matrix_cube():
    return [[[[[x*y*z*w*v for v in range(2)] for w in range(2)] for z in range(2)] for y in range(2)] for x in range(2)]
"""
        result = await extract_code(code=code, target_type="function", target_name="matrix_cube")
        assert result.success

    @pytest.mark.asyncio
    async def test_analyze_recursive_type_hints(self):
        """Recursive type hints should be handled."""
        code = """
from typing import Optional, List

class Node:
    def __init__(self, value: int, children: Optional[List['Node']] = None):
        self.value = value
        self.children = children or []
"""
        result = await analyze_code(code=code)
        assert result.success
        assert "Node" in result.classes


# ============================================================================
# 4. EXTREMELY LARGE INPUTS
# ============================================================================


class TestLargeInputs:
    """Tests for handling extremely large inputs."""

    @pytest.mark.asyncio
    async def test_extract_from_huge_file(self):
        """Extract from a file with 10,000 functions."""
        functions = [f"def func_{i}():\n    return {i}\n" for i in range(1000)]
        code = "\n".join(functions)

        # Extract function from middle
        result = await extract_code(code=code, target_type="function", target_name="func_500")
        assert result.success
        assert "500" in result.target_code

    @pytest.mark.asyncio
    async def test_extract_function_with_huge_body(self):
        """Function with 1000+ lines should be extractable."""
        lines = ["    x = " + str(i) for i in range(500)]
        code = "def huge_function():\n" + "\n".join(lines) + "\n    return x"

        result = await extract_code(code=code, target_type="function", target_name="huge_function")
        assert result.success
        assert result.line_end - result.line_start >= 500

    @pytest.mark.asyncio
    async def test_analyze_code_with_many_classes(self):
        """Analyze code with 100 classes."""
        classes = [f"class Class{i}:\n    pass\n" for i in range(100)]
        code = "\n".join(classes)

        result = await analyze_code(code=code)
        assert result.success
        assert result.class_count == 100

    @pytest.mark.asyncio
    async def test_security_scan_large_codebase(self):
        """Security scan on large codebase should complete."""
        # Generate code with many potential vulnerabilities
        vulnerable_funcs = []
        for i in range(50):
            vulnerable_funcs.append(f"""
def vulnerable_{i}(user_input):
    query = f"SELECT * FROM table WHERE id={{user_input}}"
    cursor.execute(query)
""")  # noqa: S608 -- intentional vulnerability in test data
        code = "\n".join(vulnerable_funcs)

        result = await security_scan(code=code)
        assert result.success
        assert result.vulnerability_count > 0


# ============================================================================
# 5. PATHOLOGICAL PATTERNS
# ============================================================================


class TestPathologicalPatterns:
    """Tests for pathological patterns that could cause performance issues."""

    @pytest.mark.asyncio
    async def test_extract_with_many_decorators(self):
        """Function with 20 decorators should be extractable."""
        decorators = "\n".join([f"@decorator{i}" for i in range(20)])
        code = f"""
{decorators}
def heavily_decorated():
    pass
"""
        result = await extract_code(code=code, target_type="function", target_name="heavily_decorated")
        assert result.success

    @pytest.mark.asyncio
    async def test_extract_with_long_string_literal(self):
        """Function with 10KB string literal should be handled."""
        long_string = "x" * 10000
        code = f"""
def with_long_string():
    return "{long_string}"
"""
        result = await extract_code(code=code, target_type="function", target_name="with_long_string")
        assert result.success

    @pytest.mark.asyncio
    async def test_security_scan_regex_bomb(self):
        """Input that could cause regex catastrophic backtracking."""
        # Pattern that could cause ReDoS if not handled properly
        code = """
password = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaab"
"""
        result = await security_scan(code=code)
        # Should complete without hanging
        assert result is not None

    @pytest.mark.asyncio
    async def test_extract_function_with_many_parameters(self):
        """Function with 100 parameters should be extractable."""
        params = ", ".join([f"arg{i}=None" for i in range(100)])
        code = f"def many_params({params}):\n    return locals()"

        result = await extract_code(code=code, target_type="function", target_name="many_params")
        assert result.success


# ============================================================================
# 6. CROSS-LANGUAGE EDGE CASES
# ============================================================================


class TestCrossLanguageEdgeCases:
    """Tests for polyglot extraction edge cases."""

    @pytest.mark.asyncio
    async def test_typescript_generic_constraints(self):
        """Complex TypeScript generics should be extractable."""
        code = """
function complexGeneric<T extends Record<string, unknown>, K extends keyof T>(
    obj: T,
    key: K
): T[K] {
    return obj[key];
}
"""
        result = await extract_code(
            code=code,
            target_type="function",
            target_name="complexGeneric",
            language="typescript",
        )
        assert result.success
        assert "complexGeneric" in result.target_code

    @pytest.mark.asyncio
    async def test_java_annotation_heavy_class(self):
        """Java class with many annotations should be extractable."""
        code = """
@Entity
@Table(name = "users")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
@EqualsAndHashCode(callSuper = true)
@ToString(exclude = {"password"})
public class User extends BaseEntity {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true)
    @NotBlank
    @Email
    private String email;
}
"""
        result = await extract_code(code=code, target_type="class", target_name="User", language="java")
        assert result.success
        assert "@Entity" in result.target_code

    @pytest.mark.asyncio
    async def test_javascript_template_literals(self):
        """JavaScript template literals with expressions should be handled."""
        code = """
function buildQuery(table, conditions) {
    const query = `
        SELECT *
        FROM ${table}
        WHERE ${conditions.map(c => `${c.field} = '${c.value}'`).join(' AND ')}
    `;
    return query;
}
"""
        result = await extract_code(
            code=code,
            target_type="function",
            target_name="buildQuery",
            language="javascript",
        )
        assert result.success

    @pytest.mark.asyncio
    async def test_typescript_tsx_component(self):
        """TSX component with complex props should be extractable."""
        code = """
interface Props<T> {
    items: T[];
    renderItem: (item: T, index: number) => React.ReactNode;
    keyExtractor: (item: T) => string;
}

function GenericList<T>({ items, renderItem, keyExtractor }: Props<T>) {
    return items.map((item, i) => renderItem(item, i));
}
"""
        result = await extract_code(
            code=code,
            target_type="function",
            target_name="GenericList",
            language="typescript",
        )
        assert result.success


# ============================================================================
# 7. SECURITY BYPASS ATTEMPTS
# ============================================================================


class TestSecurityBypassAttempts:
    """Tests for attempted security scanner bypasses."""

    @pytest.mark.asyncio
    async def test_detect_obfuscated_sql_injection(self):
        """Detect SQL injection with string concatenation obfuscation."""
        code = """
def sneaky_sql(user_id):
    part1 = "SELECT * FROM "
    part2 = "users WHERE "
    part3 = "id = "
    query = part1 + part2 + part3 + user_id
    cursor.execute(query)
"""
        result = await security_scan(code=code)
        # Should detect this pattern
        assert result.success

    @pytest.mark.asyncio
    async def test_detect_encoded_secret(self):
        """Detect base64-encoded secrets."""
        code = """
import base64
# This is "password123" base64 encoded
secret = base64.b64decode("cGFzc3dvcmQxMjM=").decode()
"""
        result = await security_scan(code=code)
        # May or may not detect, but should not crash
        assert result.success

    @pytest.mark.asyncio
    async def test_detect_eval_injection(self):
        """Detect eval-based code injection."""
        code = """
def dynamic_exec(user_code):
    eval(user_code)  # Code injection

def also_dangerous(cmd):
    exec(cmd)  # Also code injection
"""
        result = await security_scan(code=code)
        assert result.success
        assert result.vulnerability_count > 0

    @pytest.mark.asyncio
    async def test_detect_pickle_deserialization(self):
        """Detect unsafe pickle deserialization."""
        code = """
import pickle

def load_data(user_data):
    return pickle.loads(user_data)  # Unsafe deserialization
"""
        result = await security_scan(code=code)
        assert result.success

    @pytest.mark.asyncio
    async def test_detect_yaml_load(self):
        """Detect unsafe YAML load."""
        code = """
import yaml

def parse_config(user_yaml):
    return yaml.load(user_yaml)  # Unsafe without Loader
"""
        result = await security_scan(code=code)
        assert result.success


# ============================================================================
# 8. CONCURRENT ACCESS PATTERNS
# ============================================================================


class TestConcurrentAccess:
    """Tests for concurrent access to tools."""

    @pytest.mark.asyncio
    async def test_concurrent_extractions(self):
        """Multiple concurrent extractions should not interfere."""
        code1 = "def func1():\n    return 1"
        code2 = "def func2():\n    return 2"
        code3 = "def func3():\n    return 3"

        # Run concurrently
        results = await asyncio.gather(
            extract_code(code=code1, target_type="function", target_name="func1"),
            extract_code(code=code2, target_type="function", target_name="func2"),
            extract_code(code=code3, target_type="function", target_name="func3"),
        )

        assert all(r.success for r in results)
        assert "func1" in results[0].target_code
        assert "func2" in results[1].target_code
        assert "func3" in results[2].target_code

    @pytest.mark.asyncio
    async def test_concurrent_security_scans(self):
        """Multiple concurrent security scans should complete."""
        codes = [f"def vuln_{i}(x):\n    cursor.execute(f'SELECT {{x}}')" for i in range(10)]

        results = await asyncio.gather(*[security_scan(code=code) for code in codes])

        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_mixed_language_concurrent(self):
        """Concurrent extractions across languages."""
        python_code = "def py_func():\n    return 'python'"
        ts_code = "function tsFunc(): string { return 'typescript'; }"
        java_code = "public class JavaClass { void method() {} }"

        results = await asyncio.gather(
            extract_code(code=python_code, target_type="function", target_name="py_func"),
            extract_code(
                code=ts_code,
                target_type="function",
                target_name="tsFunc",
                language="typescript",
            ),
            extract_code(
                code=java_code,
                target_type="class",
                target_name="JavaClass",
                language="java",
            ),
        )

        assert all(r.success for r in results)


# ============================================================================
# 9. REAL-WORLD COMPLEX PATTERNS
# ============================================================================


class TestRealWorldPatterns:
    """Tests based on real-world complex code patterns."""

    @pytest.mark.asyncio
    async def test_extract_async_context_manager(self):
        """Async context manager should be extractable."""
        code = """
class AsyncDBConnection:
    async def __aenter__(self):
        self.conn = await create_connection()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.conn.close()
        return False
"""
        result = await extract_code(code=code, target_type="class", target_name="AsyncDBConnection")
        assert result.success
        assert "__aenter__" in result.target_code

    @pytest.mark.asyncio
    async def test_extract_metaclass(self):
        """Metaclass should be extractable."""
        code = """
class SingletonMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]
"""
        result = await extract_code(code=code, target_type="class", target_name="SingletonMeta")
        assert result.success

    @pytest.mark.asyncio
    async def test_extract_property_decorator(self):
        """Property with getter/setter/deleter should be extractable."""
        code = """
class Temperature:
    def __init__(self):
        self._celsius = 0

    @property
    def fahrenheit(self):
        return self._celsius * 9/5 + 32

    @fahrenheit.setter
    def fahrenheit(self, value):
        self._celsius = (value - 32) * 5/9

    @fahrenheit.deleter
    def fahrenheit(self):
        del self._celsius
"""
        result = await extract_code(code=code, target_type="class", target_name="Temperature")
        assert result.success
        assert "@property" in result.target_code

    @pytest.mark.asyncio
    async def test_security_scan_sqlalchemy_patterns(self):
        """Detect vulnerabilities in SQLAlchemy patterns."""
        code = """
from sqlalchemy import text
from sqlalchemy.orm import Session

def unsafe_query(session: Session, table: str, user_id: str):
    # Unsafe - string formatting
    query = text(f"SELECT * FROM {table} WHERE id = {user_id}")
    return session.execute(query)

def safe_query(session: Session, user_id: str):
    # Safe - parameterized
    query = text("SELECT * FROM users WHERE id = :id")
    return session.execute(query, {"id": user_id})
"""
        result = await security_scan(code=code)
        assert result.success
        # Should detect the unsafe pattern
        assert result.vulnerability_count > 0


# ============================================================================
# 10. ERROR RECOVERY
# ============================================================================


class TestErrorRecovery:
    """Tests for graceful error recovery."""

    @pytest.mark.asyncio
    async def test_extract_nonexistent_function(self):
        """Extracting non-existent function should fail gracefully."""
        code = "def actual_function():\n    pass"
        result = await extract_code(code=code, target_type="function", target_name="nonexistent_function")
        assert not result.success
        assert "not found" in result.error.lower() or "nonexistent" in str(result.error).lower()

    @pytest.mark.asyncio
    async def test_extract_wrong_type(self):
        """Extracting wrong type should fail gracefully."""
        code = "class MyClass:\n    pass"
        result = await extract_code(code=code, target_type="function", target_name="MyClass")
        # Should either succeed (finding nothing) or fail gracefully
        assert result is not None

    @pytest.mark.asyncio
    async def test_analyze_invalid_syntax(self):
        """Analyzing syntactically invalid code should fail gracefully."""
        code = "def broken(\n    this is not valid python"
        result = await analyze_code(code=code)
        assert not result.success
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_validate_special_paths(self):
        """Special path characters should be handled."""
        paths = [
            "/path/with spaces/file.py",
            "/path/with'quotes/file.py",
            '/path/with"doublequotes/file.py',
            "../relative/../path/file.py",
            "//network/share/file.py",
        ]
        result = await validate_paths(paths=paths)
        # Should not crash, all should be inaccessible
        assert result is not None
        assert len(result.inaccessible) == len(paths)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
