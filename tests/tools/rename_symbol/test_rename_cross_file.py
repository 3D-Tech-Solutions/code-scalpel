import tempfile
import unittest
from pathlib import Path

from code_scalpel.surgery.rename_symbol_refactor import rename_references_across_project


class TestRenameCrossFile(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def _write(self, rel: str, content: str) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def _read(self, rel: str) -> str:
        return (self.root / rel).read_text(encoding="utf-8")

    def test_function_from_import_updates_import_and_calls(self):
        a = self._write(
            "a.py",
            """
def old_func():
    return 1
""".lstrip(),
        )
        self._write(
            "b.py",
            """
from a import old_func

def run():
    return old_func()
""".lstrip(),
        )

        res = rename_references_across_project(
            project_root=self.root,
            target_file=a,
            target_type="function",
            target_name="old_func",
            new_name="new_func",
            create_backup=False,
            max_files_searched=None,
            max_files_updated=None,
        )
        self.assertTrue(res.success)

        b = self._read("b.py")
        self.assertIn("from a import new_func", b)
        self.assertIn("return new_func()", b)

    def test_function_from_import_with_alias_updates_import_only(self):
        a = self._write(
            "a.py",
            """
def old_func():
    return 1
""".lstrip(),
        )
        self._write(
            "b.py",
            """
from a import old_func as f

def run():
    return f()
""".lstrip(),
        )

        res = rename_references_across_project(
            project_root=self.root,
            target_file=a,
            target_type="function",
            target_name="old_func",
            new_name="new_func",
            create_backup=False,
            max_files_searched=None,
            max_files_updated=None,
        )
        self.assertTrue(res.success)

        b = self._read("b.py")
        self.assertIn("from a import new_func as f", b)
        self.assertIn("return f()", b)
        self.assertNotIn("new_func()", b)

    def test_function_module_import_updates_attribute(self):
        a = self._write(
            "a.py",
            """
def old_func():
    return 1
""".lstrip(),
        )
        self._write(
            "b.py",
            """
import a

def run():
    return a.old_func()
""".lstrip(),
        )

        res = rename_references_across_project(
            project_root=self.root,
            target_file=a,
            target_type="function",
            target_name="old_func",
            new_name="new_func",
            create_backup=False,
            max_files_searched=None,
            max_files_updated=None,
        )
        self.assertTrue(res.success)

        b = self._read("b.py")
        self.assertIn("return a.new_func()", b)

    def test_method_class_reference_updates(self):
        a = self._write(
            "a.py",
            """
class OldClass:
    def old_method(self):
        return 1
""".lstrip(),
        )
        self._write(
            "b.py",
            """
from a import OldClass

def run():
    return OldClass.old_method
""".lstrip(),
        )

        res = rename_references_across_project(
            project_root=self.root,
            target_file=a,
            target_type="method",
            target_name="OldClass.old_method",
            new_name="new_method",
            create_backup=False,
            max_files_searched=None,
            max_files_updated=None,
        )
        self.assertTrue(res.success)

        b = self._read("b.py")
        self.assertIn("return OldClass.new_method", b)

    def test_method_module_reference_updates(self):
        a = self._write(
            "a.py",
            """
class OldClass:
    def old_method(self):
        return 1
""".lstrip(),
        )
        self._write(
            "b.py",
            """
import a

def run():
    return a.OldClass.old_method
""".lstrip(),
        )

        res = rename_references_across_project(
            project_root=self.root,
            target_file=a,
            target_type="method",
            target_name="OldClass.old_method",
            new_name="new_method",
            create_backup=False,
            max_files_searched=None,
            max_files_updated=None,
        )
        self.assertTrue(res.success)

        b = self._read("b.py")
        self.assertIn("return a.OldClass.new_method", b)

    def test_method_instance_call_updates(self):
        a = self._write(
            "a.py",
            """
class OldClass:
    def old_method(self):
        return 1
""".lstrip(),
        )
        self._write(
            "b.py",
            """
from a import OldClass

def run():
    inst = OldClass()
    return inst.old_method()
""".lstrip(),
        )

        res = rename_references_across_project(
            project_root=self.root,
            target_file=a,
            target_type="method",
            target_name="OldClass.old_method",
            new_name="new_method",
            create_backup=False,
            max_files_searched=None,
            max_files_updated=None,
        )
        self.assertTrue(res.success)

        b = self._read("b.py")
        self.assertIn("return inst.new_method()", b)

    def test_method_instance_call_with_module_alias_updates(self):
        a = self._write(
            "a.py",
            """
class OldClass:
    def old_method(self):
        return 1
""".lstrip(),
        )
        self._write(
            "b.py",
            """
import a as lib

def run():
    obj = lib.OldClass()
    return obj.old_method()
""".lstrip(),
        )

        res = rename_references_across_project(
            project_root=self.root,
            target_file=a,
            target_type="method",
            target_name="OldClass.old_method",
            new_name="new_method",
            create_backup=False,
            max_files_searched=None,
            max_files_updated=None,
        )
        self.assertTrue(res.success)

        b = self._read("b.py")
        self.assertIn("return obj.new_method()", b)


if __name__ == "__main__":
    unittest.main()
