import os
import tempfile
import unittest

from code_scalpel.surgery.surgical_patcher import SurgicalPatcher


class TestRename(unittest.TestCase):
    def setUp(self):
        self.test_file = tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".py")
        self.test_file.write("""
def old_func():
    pass

class OldClass:
    def old_method(self):
        pass

async def old_async_func():
    pass
""")
        self.test_file.close()
        self.patcher = SurgicalPatcher.from_file(self.test_file.name)

    def tearDown(self):
        os.unlink(self.test_file.name)

    def test_rename_function(self):
        result = self.patcher.rename_symbol("function", "old_func", "new_func")
        self.assertTrue(result.success)
        self.assertIn("def new_func():", self.patcher.current_code)
        self.assertNotIn("def old_func():", self.patcher.current_code)

    def test_rename_class(self):
        result = self.patcher.rename_symbol("class", "OldClass", "NewClass")
        self.assertTrue(result.success)
        self.assertIn("class NewClass:", self.patcher.current_code)
        self.assertNotIn("class OldClass:", self.patcher.current_code)

    def test_rename_method(self):
        result = self.patcher.rename_symbol("method", "OldClass.old_method", "new_method")
        self.assertTrue(result.success)
        self.assertIn("def new_method(self):", self.patcher.current_code)
        self.assertNotIn("def old_method(self):", self.patcher.current_code)

    def test_rename_async_function(self):
        result = self.patcher.rename_symbol("function", "old_async_func", "new_async_func")
        self.assertTrue(result.success)
        self.assertIn("async def new_async_func():", self.patcher.current_code)
        self.assertNotIn("async def old_async_func():", self.patcher.current_code)


# [20251231_TEST] Tests for same-file reference updates (Community tier v1.0)
class TestRenameSameFileReferences(unittest.TestCase):
    """Test that rename_symbol updates references within the same file."""

    def test_rename_function_with_calls(self):
        """Function calls should be updated when function is renamed."""
        code = """
def old_func():
    return 42

result = old_func()
x = old_func
"""
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".py") as f:
            f.write(code)
            f.flush()

            patcher = SurgicalPatcher.from_file(f.name)
            result = patcher.rename_symbol("function", "old_func", "new_func")

            self.assertTrue(result.success)
            self.assertIn("def new_func():", patcher.current_code)
            self.assertIn("result = new_func()", patcher.current_code)
            self.assertIn("x = new_func", patcher.current_code)
            self.assertNotIn("old_func", patcher.current_code)

            os.unlink(f.name)

    def test_rename_function_with_decorator(self):
        """Decorator usage should be updated when function is renamed."""
        code = """
def old_decorator(func):
    return func

@old_decorator
def some_function():
    pass
"""
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".py") as f:
            f.write(code)
            f.flush()

            patcher = SurgicalPatcher.from_file(f.name)
            result = patcher.rename_symbol("function", "old_decorator", "new_decorator")

            self.assertTrue(result.success)
            self.assertIn("def new_decorator(func):", patcher.current_code)
            self.assertIn("@new_decorator", patcher.current_code)
            self.assertNotIn("old_decorator", patcher.current_code)

            os.unlink(f.name)

    def test_rename_class_with_type_hints(self):
        """Type hints should be updated when class is renamed."""
        code = """
class OldClass:
    pass

def process(obj: OldClass) -> OldClass:
    return obj

instance: OldClass = OldClass()
"""
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".py") as f:
            f.write(code)
            f.flush()

            patcher = SurgicalPatcher.from_file(f.name)
            result = patcher.rename_symbol("class", "OldClass", "NewClass")

            self.assertTrue(result.success)
            self.assertIn("class NewClass:", patcher.current_code)
            self.assertIn("def process(obj: NewClass) -> NewClass:", patcher.current_code)
            self.assertIn("instance: NewClass = NewClass()", patcher.current_code)
            self.assertNotIn("OldClass", patcher.current_code)

            os.unlink(f.name)

    def test_rename_method_with_self_calls(self):
        """Method calls via self should be updated when method is renamed."""
        code = """
class MyClass:
    def old_method(self):
        return 42

    def other_method(self):
        return self.old_method()
"""
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".py") as f:
            f.write(code)
            f.flush()

            patcher = SurgicalPatcher.from_file(f.name)
            result = patcher.rename_symbol("method", "MyClass.old_method", "new_method")

            self.assertTrue(result.success)
            self.assertIn("def new_method(self):", patcher.current_code)
            self.assertIn("self.new_method()", patcher.current_code)
            self.assertNotIn("old_method", patcher.current_code)

            os.unlink(f.name)

    def test_rename_preserves_strings_and_comments(self):
        """String literals and comments should NOT be updated."""
        code = '''
def old_func():
    """This mentions old_func in docstring."""
    # This comment mentions old_func
    return "old_func is the name"

# Call old_func here
result = old_func()
'''
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".py") as f:
            f.write(code)
            f.flush()

            patcher = SurgicalPatcher.from_file(f.name)
            result = patcher.rename_symbol("function", "old_func", "new_func")

            self.assertTrue(result.success)
            # Definition and call should be renamed
            self.assertIn("def new_func():", patcher.current_code)
            self.assertIn("result = new_func()", patcher.current_code)
            # Strings and comments should preserve old name (tokenizer doesn't touch them)
            self.assertIn("old_func in docstring", patcher.current_code)
            self.assertIn('"old_func is the name"', patcher.current_code)

            os.unlink(f.name)

    def test_rename_reports_references_updated(self):
        """PatchResult should report number of references updated."""
        code = """
def old_func():
    pass

a = old_func()
b = old_func()
c = old_func
"""
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".py") as f:
            f.write(code)
            f.flush()

            patcher = SurgicalPatcher.from_file(f.name)
            result = patcher.rename_symbol("function", "old_func", "new_func")

            self.assertTrue(result.success)
            # lines_after should be 1 (definition) + number of references
            self.assertGreater(result.lines_after, 1)

            os.unlink(f.name)


if __name__ == "__main__":
    unittest.main()
