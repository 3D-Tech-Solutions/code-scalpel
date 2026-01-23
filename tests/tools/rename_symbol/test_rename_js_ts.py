"""
Tests for JavaScript/TypeScript rename_symbol functionality.

[20251231_TEST] Phase 2: JS/TS rename support for Community tier v1.0.
"""

import os
import tempfile
import unittest

from code_scalpel.surgery.surgical_patcher import PolyglotPatcher


class TestRenameJavaScript(unittest.TestCase):
    """Test rename_symbol for JavaScript files."""

    def test_rename_function_declaration(self):
        """Regular function declaration should be renamed."""
        code = """
function oldFunc() {
    return 42;
}

const result = oldFunc();
"""
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".js") as f:
            f.write(code)
            f.flush()

            patcher = PolyglotPatcher.from_file(f.name)
            result = patcher.rename_symbol("function", "oldFunc", "newFunc")

            self.assertTrue(result.success)
            self.assertIn("function newFunc()", patcher.current_code)
            self.assertIn("newFunc()", patcher.current_code)
            self.assertNotIn("oldFunc", patcher.current_code)

            os.unlink(f.name)

    def test_rename_arrow_function(self):
        """Arrow function should be renamed."""
        code = """
const oldFunc = () => {
    return 42;
};

const result = oldFunc();
"""
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".js") as f:
            f.write(code)
            f.flush()

            patcher = PolyglotPatcher.from_file(f.name)
            result = patcher.rename_symbol("function", "oldFunc", "newFunc")

            self.assertTrue(result.success)
            self.assertIn("const newFunc =", patcher.current_code)
            self.assertIn("newFunc()", patcher.current_code)
            self.assertNotIn("oldFunc", patcher.current_code)

            os.unlink(f.name)

    def test_rename_async_function(self):
        """Async function should be renamed."""
        code = """
async function oldFunc() {
    return await fetch('/api');
}

const data = await oldFunc();
"""
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".js") as f:
            f.write(code)
            f.flush()

            patcher = PolyglotPatcher.from_file(f.name)
            result = patcher.rename_symbol("function", "oldFunc", "newFunc")

            self.assertTrue(result.success)
            self.assertIn("async function newFunc()", patcher.current_code)
            self.assertIn("newFunc()", patcher.current_code)
            self.assertNotIn("oldFunc", patcher.current_code)

            os.unlink(f.name)

    def test_rename_class(self):
        """Class declaration should be renamed."""
        code = """
class OldClass {
    constructor() {
        this.value = 42;
    }
}

const instance = new OldClass();
"""
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".js") as f:
            f.write(code)
            f.flush()

            patcher = PolyglotPatcher.from_file(f.name)
            result = patcher.rename_symbol("class", "OldClass", "NewClass")

            self.assertTrue(result.success)
            self.assertIn("class NewClass", patcher.current_code)
            self.assertIn("new NewClass()", patcher.current_code)
            self.assertNotIn("OldClass", patcher.current_code)

            os.unlink(f.name)

    def test_rename_method(self):
        """Method should be renamed along with this.method calls."""
        code = """
class MyClass {
    oldMethod() {
        return 42;
    }

    otherMethod() {
        return this.oldMethod();
    }
}
"""
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".js") as f:
            f.write(code)
            f.flush()

            patcher = PolyglotPatcher.from_file(f.name)
            result = patcher.rename_symbol("method", "MyClass.oldMethod", "newMethod")

            self.assertTrue(result.success)
            self.assertIn("newMethod()", patcher.current_code)
            self.assertIn("this.newMethod()", patcher.current_code)
            self.assertNotIn("oldMethod", patcher.current_code)

            os.unlink(f.name)


class TestRenameTypeScript(unittest.TestCase):
    """Test rename_symbol for TypeScript files."""

    def test_rename_typed_function(self):
        """TypeScript function with type annotations should be renamed."""
        code = """
function oldFunc(x: number): number {
    return x * 2;
}

const result: number = oldFunc(21);
"""
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".ts") as f:
            f.write(code)
            f.flush()

            patcher = PolyglotPatcher.from_file(f.name)
            result = patcher.rename_symbol("function", "oldFunc", "newFunc")

            self.assertTrue(result.success)
            self.assertIn("function newFunc(x: number)", patcher.current_code)
            self.assertIn("newFunc(21)", patcher.current_code)
            self.assertNotIn("oldFunc", patcher.current_code)

            os.unlink(f.name)

    def test_rename_interface(self):
        """TypeScript interface should be renamed."""
        code = """
interface OldInterface {
    name: string;
    age: number;
}

function process(data: OldInterface): void {
    console.log(data.name);
}
"""
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".ts") as f:
            f.write(code)
            f.flush()

            patcher = PolyglotPatcher.from_file(f.name)
            result = patcher.rename_symbol("class", "OldInterface", "NewInterface")

            self.assertTrue(result.success)
            self.assertIn("interface NewInterface", patcher.current_code)
            self.assertIn("data: NewInterface", patcher.current_code)
            self.assertNotIn("OldInterface", patcher.current_code)

            os.unlink(f.name)

    def test_rename_class_with_generics(self):
        """TypeScript class with generics should be renamed."""
        code = """
class OldClass<T> {
    private value: T;

    constructor(value: T) {
        this.value = value;
    }
}

const instance = new OldClass<string>("hello");
"""
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".ts") as f:
            f.write(code)
            f.flush()

            patcher = PolyglotPatcher.from_file(f.name)
            result = patcher.rename_symbol("class", "OldClass", "NewClass")

            self.assertTrue(result.success)
            self.assertIn("class NewClass<T>", patcher.current_code)
            self.assertIn("new NewClass<string>", patcher.current_code)
            self.assertNotIn("OldClass", patcher.current_code)

            os.unlink(f.name)

    def test_rename_preserves_imports(self):
        """Import statements should NOT be modified (cross-file concern)."""
        code = """
import { oldFunc } from './utils';

function oldFunc() {
    return 42;
}

const result = oldFunc();
"""
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".ts") as f:
            f.write(code)
            f.flush()

            patcher = PolyglotPatcher.from_file(f.name)
            result = patcher.rename_symbol("function", "oldFunc", "newFunc")

            self.assertTrue(result.success)
            # Definition and local call should be renamed
            self.assertIn("function newFunc()", patcher.current_code)
            self.assertIn("result = newFunc()", patcher.current_code)
            # Import statement should be preserved (cross-file concern)
            self.assertIn("import { oldFunc }", patcher.current_code)

            os.unlink(f.name)


class TestRenameJSX(unittest.TestCase):
    """Test rename_symbol for JSX/TSX React files."""

    def test_rename_react_component(self):
        """React component function should be renamed."""
        code = """
function OldComponent({ name }) {
    return <div>Hello {name}</div>;
}

export default function App() {
    return <OldComponent name="World" />;
}
"""
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".jsx") as f:
            f.write(code)
            f.flush()

            patcher = PolyglotPatcher.from_file(f.name)
            result = patcher.rename_symbol("function", "OldComponent", "NewComponent")

            self.assertTrue(result.success)
            self.assertIn("function NewComponent(", patcher.current_code)
            # JSX usage should also be renamed
            self.assertIn("<NewComponent", patcher.current_code)
            self.assertNotIn("OldComponent", patcher.current_code)

            os.unlink(f.name)


class TestRenameErrorHandling(unittest.TestCase):
    """Test error handling for JS/TS rename."""

    def test_rename_nonexistent_function(self):
        """Renaming nonexistent function should fail gracefully."""
        code = """
function existingFunc() {
    return 42;
}
"""
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".js") as f:
            f.write(code)
            f.flush()

            patcher = PolyglotPatcher.from_file(f.name)
            result = patcher.rename_symbol("function", "nonExistent", "newName")

            self.assertFalse(result.success)
            self.assertIn("not found", result.error)

            os.unlink(f.name)

    def test_rename_method_without_class(self):
        """Method name without class qualifier should fail."""
        code = """
class MyClass {
    myMethod() {
        return 42;
    }
}
"""
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".js") as f:
            f.write(code)
            f.flush()

            patcher = PolyglotPatcher.from_file(f.name)
            result = patcher.rename_symbol("method", "myMethod", "newMethod")

            self.assertFalse(result.success)
            self.assertIn("qualified", result.error.lower())

            os.unlink(f.name)

    def test_js_reserved_word_rejected(self):
        """Renaming to JS reserved word should be rejected."""
        code = """
function oldFunc() {
    return 1;
}
"""
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".js") as f:
            f.write(code)
            f.flush()

            patcher = PolyglotPatcher.from_file(f.name)
            result = patcher.rename_symbol("function", "oldFunc", "class")

            self.assertFalse(result.success)
            self.assertIn("reserved", result.error.lower())

            os.unlink(f.name)

    def test_ts_reserved_word_rejected(self):
        """Renaming to TS reserved word should be rejected."""
        code = """
function oldFunc(): number {
    return 1;
}
"""
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".ts") as f:
            f.write(code)
            f.flush()

            patcher = PolyglotPatcher.from_file(f.name)
            result = patcher.rename_symbol("function", "oldFunc", "let")

            self.assertFalse(result.success)
            self.assertIn("reserved", result.error.lower())

            os.unlink(f.name)


if __name__ == "__main__":
    unittest.main()
