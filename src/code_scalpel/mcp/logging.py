"""Compatibility wrapper for MCP logging.

Why this exists:
- The MCP server is sometimes executed as a *script* (e.g. `python path/to/server.py`).
- In that mode, Python adds the script directory to `sys.path[0]`.
- A sibling file named `logging.py` then *shadows* the stdlib `logging` package.

This wrapper prevents that shadowing by:
- If imported as top-level `logging`, proxying to the real stdlib module.
- Otherwise, re-exporting Code Scalpel's MCP logging utilities.

[20251228_BUGFIX] Prevent stdlib `logging` shadowing.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import sysconfig


def _load_stdlib_logging() -> None:
    stdlib_dir = sysconfig.get_paths().get("stdlib")
    if not stdlib_dir:
        raise ImportError("Could not locate stdlib path to load logging")

    logging_init = os.path.join(stdlib_dir, "logging", "__init__.py")
    spec = importlib.util.spec_from_file_location("logging", logging_init)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not create spec for stdlib logging: {logging_init}")

    module = importlib.util.module_from_spec(spec)
    sys.modules["logging"] = module
    spec.loader.exec_module(module)
    globals().clear()
    globals().update(module.__dict__)


# If Python is trying to import top-level `logging`, do the proxy trick.
if __name__ == "logging":
    _load_stdlib_logging()
else:
    from .mcp_logging import *  # noqa: F403
    from .mcp_logging import _sanitize_params as _sanitize_params
