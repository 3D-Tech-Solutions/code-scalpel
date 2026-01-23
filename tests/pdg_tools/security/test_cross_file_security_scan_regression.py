"""Regression test for cross-file SQL injection detection.

This mirrors the Ninja Warrior `crossfile-hard` fixture:
- taint source in routes module (request.args.get)
- indirection in services module
- SQL sink in db module

The cross-file tracker should report at least one SQL injection flow.
"""

from __future__ import annotations

from pathlib import Path

from code_scalpel.security.analyzers import CrossFileTaintTracker


def test_cross_file_sql_injection_flow_detected(tmp_path: Path):
    pkg = tmp_path / "crossfile_hard"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("# test package\n")

    (pkg / "routes.py").write_text("""\
from flask import Flask, request
from .services import search_users, search_users_safe

app = Flask(__name__)

@app.get('/search')
def search_route() -> str:
    q = request.args.get('q', '')
    return search_users(q)

@app.get('/search-safe')
def search_route_safe() -> str:
    q = request.args.get('q', '')
    return search_users_safe(q)
""")

    (pkg / "sanitizers.py").write_text("""\
def sanitize_decoy(value: str) -> str:
    return value

def sanitize_allowlist_alpha(value: str) -> str:
    return ''.join(ch for ch in value if ch.isalnum() or ch in {'_', '-'})
""")

    (pkg / "services.py").write_text("""\
from . import sanitizers as s
from .db import run_query as rq

def search_users(raw_query: str) -> str:
    query = s.sanitize_decoy(raw_query)
    return rq(query)

def search_users_safe(raw_query: str) -> str:
    query = s.sanitize_allowlist_alpha(raw_query)
    return rq(query)
""")

    (pkg / "db.py").write_text("""\
import sqlite3

def run_query(user_supplied: str) -> str:
    sql = f"SELECT * FROM users WHERE name = '{user_supplied}'"
    conn = sqlite3.connect(':memory:')
    cur = conn.cursor()
    cur.execute(sql)
    conn.close()
    return sql
""")

    tracker = CrossFileTaintTracker(tmp_path)
    result = tracker.analyze(max_depth=8, timeout_seconds=10.0, max_modules=100)

    assert result.success is True
    assert len(result.taint_flows) >= 1
    assert any(v.cwe_id == "CWE-89" for v in result.vulnerabilities)

    # The safe route should not be flagged as vulnerable.
    assert all(flow.source_function != "search_route_safe" for flow in result.taint_flows)
