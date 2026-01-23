"""Code Policy Check - Built-in policy templates.

Templates provide a lightweight "policy templates library" for Pro/Enterprise.
They are intended to be composed via the policy loader using `extends`.

Templates are JSON-serializable dictionaries.
"""

from __future__ import annotations

from typing import Any

POLICY_TEMPLATES: dict[str, dict[str, Any]] = {
    "python-default": {
        "include_extensions": [".py"],
        "complexity": {"python": 15},
        "exclude_dirs": [".git", "__pycache__", ".venv", "venv", "node_modules"],
        "eslint": {"enabled": False},
    },
    "python-security": {
        "include_extensions": [".py"],
        "complexity": {"python": 15},
        "exclude_dirs": [".git", "__pycache__", ".venv", "venv", "node_modules"],
        "eslint": {"enabled": False},
    },
    "javascript-default": {
        "include_extensions": [".js", ".jsx"],
        "complexity": {"javascript": 20},
        "exclude_dirs": [".git", "__pycache__", ".venv", "venv", "node_modules"],
        "eslint": {
            "enabled": True,
            "bin": "eslint",
            "args": ["-f", "json"],
        },
    },
    "fullstack-default": {
        "extends": ["template:python-default", "template:javascript-default"],
    },
}


def get_policy_template(name: str) -> dict[str, Any] | None:
    return POLICY_TEMPLATES.get(name)
