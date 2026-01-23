from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.fixture(autouse=True)
def disable_license_discovery(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")


@pytest.fixture
def community_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODE_SCALPEL_TIER", "community")
    monkeypatch.setenv("CODE_SCALPEL_TEST_FORCE_TIER", "1")


@pytest.fixture
def pro_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODE_SCALPEL_TIER", "pro")
    monkeypatch.setenv("CODE_SCALPEL_TEST_FORCE_TIER", "1")


@pytest.fixture
def enterprise_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODE_SCALPEL_TIER", "enterprise")
    monkeypatch.setenv("CODE_SCALPEL_TEST_FORCE_TIER", "1")


@pytest.fixture
def small_python_project(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    root.mkdir()
    _write(root / "main.py", "def main():\n    return 1\n")
    _write(root / "utils.py", "def helper():\n    return 2\n")
    return root


@pytest.fixture
def multilang_project(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    root.mkdir()
    _write(root / "a.py", "def f():\n    return 1\n")
    _write(root / "b.js", "export function g(){ return 2; }\n")
    _write(root / "c.java", "class C { int h(){ return 3; } }\n")
    return root


@pytest.fixture
def large_python_project(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    root.mkdir()
    for i in range(120):
        _write(root / f"file_{i}.py", "def f():\n    return 1\n")
    return root


@pytest.fixture
def clean_cache() -> Callable[[Path], None]:
    def _clean(root: Path) -> None:
        cache_dir = root / ".scalpel_cache"
        if cache_dir.exists():
            shutil.rmtree(cache_dir)

    return _clean


@pytest.fixture
def small_python_extended(tmp_path: Path) -> Path:
    """Extended small Python project with entry point and test structure."""
    root = tmp_path / "small_py_ext"
    root.mkdir()

    # Main with entry point
    _write(
        root / "main.py",
        '''"""Main entry point."""
from utils import calculate

def main():
    """Run application."""
    result = calculate(10, 20)
    print(f"Result: {result}")

if __name__ == "__main__":
    main()
''',
    )

    # Utilities
    _write(
        root / "utils.py",
        '''"""Utility functions."""

def calculate(a: int, b: int) -> int:
    """Calculate sum."""
    return a + b

def process(data: list) -> list:
    """Process data list."""
    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)
    return result
''',
    )

    # Config
    _write(
        root / "config.py",
        '''"""Configuration module."""

DEBUG = True
MAX_RETRIES = 3
TIMEOUT = 30
''',
    )

    # Tests
    _write(
        root / "tests/test_utils.py",
        '''"""Tests for utils module."""
import pytest
from utils import calculate, process

def test_calculate():
    """Test calculate function."""
    assert calculate(10, 20) == 30

def test_process():
    """Test process with data."""
    assert process([1, 2, 3]) == [2, 4, 6]
''',
    )

    return root


@pytest.fixture
def large_project(tmp_path: Path) -> Path:
    """Large project with 150+ files (exceeds Community 100-file limit)."""
    root = tmp_path / "large_proj"
    root.mkdir()

    # Create 7 modules with 20 files each = 140 files
    src = root / "src"
    src.mkdir()

    for mod_num in range(7):
        mod_dir = src / f"module{mod_num}"
        mod_dir.mkdir()
        _write(mod_dir / "__init__.py", f'"""Module {mod_num}."""\n')

        for file_num in range(1, 20):
            _write(
                mod_dir / f"file{file_num}.py",
                f'''"""File {file_num} in module {mod_num}."""

def func_{file_num}():
    """Function {file_num}."""
    return {file_num}

class Class{file_num}:
    """Class {file_num}."""
    pass
''',
            )

    # Add 30 test files
    tests = root / "tests"
    tests.mkdir()
    for test_num in range(30):
        _write(
            tests / f"test_{test_num}.py",
            f'''"""Test {test_num}."""

def test_{test_num}():
    """Test {test_num}."""
    assert True
''',
        )

    return root


@pytest.fixture
def project_with_gitignore(tmp_path: Path) -> Path:
    """Project with .gitignore file for pattern testing."""
    root = tmp_path / "gitignore_proj"
    root.mkdir()

    # Create .gitignore
    _write(
        root / ".gitignore",
        """# Python
__pycache__/
*.pyc
*.pyo
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/

# Virtual environments
venv/
ENV/
env/
.venv

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Node (in monorepo)
node_modules/
package-lock.json

# Testing
.pytest_cache/
.coverage

# OS
.DS_Store
.env
""",
    )

    # Create source files
    _write(
        root / "main.py",
        '''"""Main module."""
def run():
    pass
''',
    )

    # Create venv (should be ignored)
    _write(
        root / "venv/lib/python3.9/site-packages/pkg.py",
        """# Should be ignored
def pkg_func():
    pass
""",
    )

    # Create __pycache__ (should be ignored)
    _write(root / "__pycache__/module.pyc", "compiled")

    # Create node_modules (should be ignored)
    _write(root / "node_modules/lodash/index.js", "// Should be ignored")

    # Create build dir (should be ignored)
    _write(root / "build/lib.py", "# Build artifact")

    return root


@pytest.fixture
def project_with_custom_config(tmp_path: Path) -> Path:
    """Project with .code-scalpel/crawl_project.json custom config."""
    import json

    root = tmp_path / "config_proj"
    root.mkdir()

    # Create config
    scalpel_dir = root / ".code-scalpel"
    scalpel_dir.mkdir()

    config = {
        "include_extensions": [".py"],  # Only Python
        "exclude_dirs": ["node_modules", "venv", ".venv", "vendor"],
    }

    (scalpel_dir / "crawl_project.json").write_text(json.dumps(config, indent=2))

    # Create source files
    _write(
        root / "src/app.py",
        '''"""Application."""
def run():
    pass
''',
    )

    _write(
        root / "src/utils.py",
        '''"""Utilities."""
def helper():
    pass
''',
    )

    # This should be excluded by extension
    _write(
        root / "src/service.js",
        """// Service module
function process() {}
""",
    )

    # These should be excluded by config
    _write(root / "node_modules/pkg/index.py", "# In node_modules")
    _write(root / "vendor/lib/code.py", "# In vendor")

    return root


@pytest.fixture
def flask_project(tmp_path: Path) -> Path:
    """Flask application project for framework detection."""
    root = tmp_path / "flask_proj"
    root.mkdir()

    _write(
        root / "requirements.txt",
        """Flask==2.0.0
Werkzeug==2.0.0
""",
    )

    _write(
        root / "app.py",
        '''"""Flask application."""
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def hello():
    """Hello endpoint."""
    return jsonify({"message": "Hello, World!"})

@app.route('/api/data')
def get_data():
    """Get data endpoint."""
    return jsonify({"data": [1, 2, 3]})

@app.post('/api/submit')
def submit_data():
    """Submit data endpoint."""
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(debug=True)
''',
    )

    _write(
        root / "config.py",
        '''"""Flask config."""
DEBUG = True
SECRET_KEY = "dev-key"
''',
    )

    return root


@pytest.fixture
def django_project(tmp_path: Path) -> Path:
    """Django application project for framework detection."""
    root = tmp_path / "django_proj"
    root.mkdir()

    _write(
        root / "requirements.txt",
        """Django==4.0.0
django-rest-framework==3.12.0
""",
    )

    _write(
        root / "manage.py",
        """#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
""",
    )

    app_dir = root / "myapp"
    app_dir.mkdir()

    _write(app_dir / "__init__.py", "")

    _write(
        app_dir / "urls.py",
        '''"""URL configuration."""
from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
]
''',
    )

    _write(
        app_dir / "views.py",
        '''"""Views."""
from django.http import JsonResponse

def home(request):
    """Home view."""
    return JsonResponse({"message": "Home"})

def about(request):
    """About view."""
    return JsonResponse({"message": "About"})
''',
    )

    return root


@pytest.fixture
def fastapi_project(tmp_path: Path) -> Path:
    """FastAPI application project for framework detection."""
    root = tmp_path / "fastapi_proj"
    root.mkdir()

    _write(
        root / "requirements.txt",
        """FastAPI==0.100.0
uvicorn==0.23.0
""",
    )

    _write(
        root / "main.py",
        '''"""FastAPI application."""
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    """Root endpoint."""
    return {"message": "Hello, World!"}

@app.get("/items/{item_id}")
def read_item(item_id: int):
    """Read item endpoint."""
    return {"item_id": item_id}

@app.post("/items")
def create_item(item: dict):
    """Create item endpoint."""
    return {"created": item}
''',
    )

    return root


@pytest.fixture
def nextjs_project(tmp_path: Path) -> Path:
    """Next.js application project for framework detection."""
    root = tmp_path / "nextjs_proj"
    root.mkdir()

    _write(
        root / "package.json",
        """{
  "name": "nextjs-app",
  "dependencies": {
    "next": "13.0.0",
    "react": "18.0.0"
  }
}
""",
    )

    # Pages Router
    pages = root / "pages"
    pages.mkdir()
    _write(
        pages / "index.tsx",
        """import React from "react";

export default function Home() {
  return <h1>Home</h1>;
}
""",
    )

    _write(
        pages / "api/hello.ts",
        """import { NextApiRequest, NextApiResponse } from "next";

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  res.status(200).json({ message: "Hello" });
}
""",
    )

    # App Router
    app = root / "app"
    app.mkdir()
    _write(
        app / "layout.tsx",
        """export default function RootLayout({ children }) {
  return <html><body>{children}</body></html>;
}
""",
    )

    _write(
        app / "page.tsx",
        """export default function Home() {
  return <h1>Home</h1>;
}
""",
    )

    return root
