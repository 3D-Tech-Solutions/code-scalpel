"""
[20260105_TEST] Conftest for get_graph_neighborhood licensing tests.

Provides fixtures for real license-based tier testing without MCP dependencies.
"""

# This file prevents pytest from loading the parent conftest.py
# which has MCP server dependencies that may not be installed.

# The fixtures are defined directly in the test files to avoid
# import issues with the MCP server module.
