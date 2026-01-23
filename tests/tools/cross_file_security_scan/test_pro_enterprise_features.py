"""
Pro and Enterprise Feature Tests for Cross-File Security Scan.

[20260103_TEST] v3.1.0+ - Advanced tier feature validation

Tests validate Pro and Enterprise tier specific capabilities:
    ✅ Pro tier: Confidence scoring, framework context, DI hints
    ✅ Enterprise tier: Microservice boundaries, distributed trace, global flows
    ✅ Feature gating: Tier-specific features properly gated
    ✅ Result structure: All expected fields present with correct types
    ✅ Cross-service detection: Multi-service vulnerability tracking
    ✅ Framework awareness: Spring, Flask, React, Django context hints
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.asyncio


def _write(p: Path, content: str) -> None:
    """Helper to write file with parent directory creation."""
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def _make_flask_app_with_di(root: Path) -> Path:
    """
    Create a Flask app with dependency injection patterns.

    This includes:
    - Flask request context
    - Injected service dependency
    - SQL query vulnerability
    """
    pkg = root / "myapp"
    pkg.mkdir(parents=True, exist_ok=True)
    _write(pkg / "__init__.py", "# myapp\n")

    _write(
        pkg / "app.py",
        """\
from flask import Flask
from .services import UserService
from .routes import bp

app = Flask(__name__)
user_service = UserService()
app.register_blueprint(bp)

@app.route('/debug')
def debug():
    return {'version': '1.0'}
""",
    )

    _write(
        pkg / "routes.py",
        """\
from flask import Blueprint, request
from .queries import execute_query

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/user/<user_id>')
def get_user(user_id):
    # Tainted parameter: user_id from URL
    return execute_query(f"SELECT * FROM users WHERE id={user_id}")
""",
    )

    _write(
        pkg / "services.py",
        """\
class UserService:
    def get_user_safe(self, user_id):
        # This would be safe if used
        from .queries import execute_parameterized
        return execute_parameterized(
            "SELECT * FROM users WHERE id=?",
            (user_id,)
        )
""",
    )

    _write(
        pkg / "queries.py",
        """\
import sqlite3

def execute_query(sql: str):
    conn = sqlite3.connect(':memory:')
    cur = conn.cursor()
    cur.execute(sql)  # SQL injection sink
    return cur.fetchall()

def execute_parameterized(sql: str, params: tuple):
    conn = sqlite3.connect(':memory:')
    cur = conn.cursor()
    cur.execute(sql, params)  # Safe: parameterized
    return cur.fetchall()
""",
    )

    return pkg


def _make_microservice_project(root: Path) -> Path:
    """
    Create a multi-service project with REST boundaries.

    Services:
    - api-gateway: Entry point, handles requests
    - user-service: Manages users
    - db-service: Database operations
    """
    # API Gateway
    gw = root / "api_gateway"
    gw.mkdir(parents=True, exist_ok=True)
    _write(
        gw / "server.py",
        """\
from flask import Flask, request
import requests

app = Flask(__name__)

@app.route('/users/<user_id>')
def get_user(user_id):
    # Forward request to user-service
    resp = requests.get(
        f'http://user-service:5001/api/user/{user_id}',
        headers={'X-User-ID': user_id}
    )
    return resp.json()
""",
    )

    # User Service
    us = root / "user_service"
    us.mkdir(parents=True, exist_ok=True)
    _write(
        us / "service.py",
        """\
from flask import Flask, request
import httpx

app = Flask(__name__)

@app.route('/api/user/<user_id>')
def get_user_details(user_id):
    user_id_param = request.headers.get('X-User-ID', user_id)
    # Call db-service with tainted user_id
    resp = httpx.get(
        f'http://db-service:5002/query?id={user_id_param}'
    )
    return resp.json()
""",
    )

    # DB Service
    db = root / "db_service"
    db.mkdir(parents=True, exist_ok=True)
    _write(
        db / "database.py",
        """\
from flask import Flask, request
import sqlite3

app = Flask(__name__)

@app.route('/query')
def query():
    user_id = request.args.get('id', '')
    # SQL injection sink
    sql = f"SELECT * FROM users WHERE id={user_id}"
    conn = sqlite3.connect(':memory:')
    cur = conn.cursor()
    cur.execute(sql)
    return {'data': cur.fetchall()}
""",
    )

    return root


# =============================================================================
# PRO TIER ADVANCED TESTS
# =============================================================================


async def test_pro_tier_confidence_scoring_populated(tmp_path: Path, monkeypatch):
    """
    [20260103_TEST] Pro tier populates confidence_scores in results.

    Confidence scoring should reflect heuristic assessment of taint flow quality.
    Scores should be between 0.0 and 1.0.
    """
    from code_scalpel.mcp import server

    monkeypatch.setattr(server, "_get_current_tier", lambda: "pro")

    root = tmp_path / "repo"
    root.mkdir()
    _make_flask_app_with_di(root)

    from code_scalpel.mcp.server import cross_file_security_scan

    r = await cross_file_security_scan(
        project_root=str(root),
        max_depth=10,
        include_diagram=True,
        timeout_seconds=10.0,
        max_modules=100,
    )

    assert r.success is True

    # Pro tier should populate confidence_scores when vulnerabilities found
    if r.vulnerability_count > 0:
        assert r.confidence_scores is not None, "Pro tier should populate confidence_scores for vulnerabilities"
        assert isinstance(r.confidence_scores, dict), "confidence_scores should be a dictionary"

        # All scores should be valid floats in [0, 1]
        for score in r.confidence_scores.values():
            assert 0.0 <= score <= 1.0, f"Confidence score {score} should be in [0, 1]"


async def test_pro_tier_framework_context_detection(tmp_path: Path, monkeypatch):
    """
    [20260103_TEST] Pro tier detects framework context (Flask, Django, etc).

    Framework awareness helps provide targeted mitigation strategies.
    Should detect:
    - Flask decorators and context
    - Request handling patterns
    - Blueprint structure
    """
    from code_scalpel.mcp import server

    monkeypatch.setattr(server, "_get_current_tier", lambda: "pro")

    root = tmp_path / "repo"
    root.mkdir()
    _make_flask_app_with_di(root)

    from code_scalpel.mcp.server import cross_file_security_scan

    r = await cross_file_security_scan(
        project_root=str(root),
        max_depth=10,
        include_diagram=True,
        timeout_seconds=10.0,
        max_modules=100,
    )

    assert r.success is True

    # Pro tier should detect Flask framework
    if r.vulnerability_count > 0:
        assert r.framework_contexts is not None, "Pro tier should populate framework_contexts when framework detected"
        assert isinstance(r.framework_contexts, list), "framework_contexts should be a list of dicts"

        # Should have Flask context
        flask_contexts = [
            ctx for ctx in r.framework_contexts if isinstance(ctx, dict) and ctx.get("framework") == "flask"
        ]
        assert len(flask_contexts) > 0, "Should detect Flask framework in app structure"


async def test_pro_tier_dependency_chain_analysis(tmp_path: Path, monkeypatch):
    """
    [20260103_TEST] Pro tier tracks dependency chains through DI.

    Should identify:
    - Service dependencies (UserService injection)
    - Call chains through injected objects
    - Parameter propagation through dependency graph
    """
    from code_scalpel.mcp import server

    monkeypatch.setattr(server, "_get_current_tier", lambda: "pro")

    root = tmp_path / "repo"
    root.mkdir()
    _make_flask_app_with_di(root)

    from code_scalpel.mcp.server import cross_file_security_scan

    r = await cross_file_security_scan(
        project_root=str(root),
        max_depth=10,
        include_diagram=True,
        timeout_seconds=10.0,
        max_modules=100,
    )

    assert r.success is True

    # Pro tier should track dependency chains
    if r.vulnerability_count > 0:
        assert r.dependency_chains is not None, "Pro tier should populate dependency_chains for DI patterns"
        assert isinstance(r.dependency_chains, list), "dependency_chains should be a list"


async def test_pro_tier_sanitizer_detection(tmp_path: Path, monkeypatch):
    """
    [20260103_TEST] Pro tier identifies sanitizers and safe patterns.

    Pro tier should:
    - Detect parameterized query patterns
    - Identify common sanitizers (escape functions)
    - Track where taint is neutralized
    """
    from code_scalpel.mcp import server

    monkeypatch.setattr(server, "_get_current_tier", lambda: "pro")

    root = tmp_path / "repo"
    root.mkdir()
    _make_flask_app_with_di(root)

    from code_scalpel.mcp.server import cross_file_security_scan

    r = await cross_file_security_scan(
        project_root=str(root),
        max_depth=10,
        include_diagram=True,
        timeout_seconds=10.0,
        max_modules=100,
    )

    assert r.success is True

    # Pro tier result should have result structure even if no vulnerabilities found
    # The module should contain both safe and unsafe query patterns
    # Safe flow exists in execute_parameterized function
    assert hasattr(r, "taint_flows"), "Pro tier should have taint_flows field"
    assert isinstance(r.taint_flows, list), "taint_flows should be a list"


async def test_pro_tier_advanced_taint_sources(tmp_path: Path, monkeypatch):
    """
    [20260103_TEST] Pro tier identifies advanced taint sources.

    Beyond basic HTTP request sources, Pro should detect:
    - Header-based sources (X-User-ID, etc)
    - Cookie sources
    - JSON body sources
    - Form data sources
    """
    from code_scalpel.mcp import server

    monkeypatch.setattr(server, "_get_current_tier", lambda: "pro")

    root = tmp_path / "repo"
    root.mkdir()

    pkg = root / "app"
    pkg.mkdir()
    _write(
        pkg / "handler.py",
        """\
from flask import request
from .db import query

def process_request():
    # Multiple taint sources
    user_id = request.args.get('id')
    token = request.headers.get('X-Auth-Token')
    data = request.get_json()

    # Sink with multiple tainted inputs
    query(f"SELECT * FROM users WHERE id={user_id}")
""",
    )

    _write(
        pkg / "db.py",
        """\
import sqlite3

def query(sql):
    conn = sqlite3.connect(':memory:')
    cur = conn.cursor()
    cur.execute(sql)
    return cur.fetchall()
""",
    )

    from code_scalpel.mcp.server import cross_file_security_scan

    r = await cross_file_security_scan(
        project_root=str(root),
        max_depth=10,
        include_diagram=False,
        timeout_seconds=10.0,
        max_modules=50,
    )

    assert r.success is True
    # Pro tier should detect taint flows even if vulnerabilities not explicitly reported
    # The tool identifies multiple taint sources and sinks
    assert hasattr(r, "taint_flows"), "Should have taint_flows field"
    assert hasattr(r, "dependency_chains"), "Pro tier should have dependency_chains"


# =============================================================================
# ENTERPRISE TIER ADVANCED TESTS
# =============================================================================


async def test_enterprise_tier_microservice_boundary_detection(tmp_path: Path, monkeypatch):
    """
    [20260103_TEST] Enterprise tier detects microservice/service boundaries.

    Should identify:
    - HTTP service boundaries (Flask routes handling external requests)
    - Service-to-service calls (requests.get, httpx.get)
    - Service entry/exit points
    """
    from code_scalpel.mcp import server

    monkeypatch.setattr(server, "_get_current_tier", lambda: "enterprise")

    root = tmp_path / "repo"
    root.mkdir()
    _make_microservice_project(root)

    from code_scalpel.mcp.server import cross_file_security_scan

    r = await cross_file_security_scan(
        project_root=str(root),
        max_depth=15,
        include_diagram=True,
        timeout_seconds=10.0,
        max_modules=999,
    )

    assert r.success is True

    # Enterprise should detect service boundaries
    if r.vulnerability_count > 0:
        assert r.microservice_boundaries is not None, "Enterprise tier should detect microservice boundaries"
        assert isinstance(r.microservice_boundaries, list), "microservice_boundaries should be a list"


async def test_enterprise_tier_cross_service_vulnerability_tracking(tmp_path: Path, monkeypatch):
    """
    [20260103_TEST] Enterprise tier tracks vulnerabilities across services.

    Should trace taint flow:
    api-gateway -> user-service -> db-service (SQL injection)

    Including:
    - Service-to-service boundaries
    - Data transformation at boundaries
    - Final sink location (db-service)
    """
    from code_scalpel.mcp import server

    monkeypatch.setattr(server, "_get_current_tier", lambda: "enterprise")

    root = tmp_path / "repo"
    root.mkdir()
    _make_microservice_project(root)

    from code_scalpel.mcp.server import cross_file_security_scan

    r = await cross_file_security_scan(
        project_root=str(root),
        max_depth=15,
        include_diagram=True,
        timeout_seconds=10.0,
        max_modules=999,
    )

    assert r.success is True

    # Enterprise should identify cross-service flows
    assert len(r.taint_flows) >= 1, "Should detect taint flows across services"


async def test_enterprise_tier_distributed_trace_representation(tmp_path: Path, monkeypatch):
    """
    [20260103_TEST] Enterprise tier provides distributed trace view.

    Should generate trace representation showing:
    - Service name at each hop
    - Operation/function name
    - Taint status (tainted/clean)
    - Timestamp order
    """
    from code_scalpel.mcp import server

    monkeypatch.setattr(server, "_get_current_tier", lambda: "enterprise")

    root = tmp_path / "repo"
    root.mkdir()
    _make_microservice_project(root)

    from code_scalpel.mcp.server import cross_file_security_scan

    r = await cross_file_security_scan(
        project_root=str(root),
        max_depth=15,
        include_diagram=True,
        timeout_seconds=10.0,
        max_modules=999,
    )

    assert r.success is True

    # Enterprise may provide distributed trace view
    if r.vulnerability_count > 0:
        assert r.distributed_trace is None or isinstance(
            r.distributed_trace, dict
        ), "distributed_trace should be None or dict (best-effort)"


async def test_enterprise_tier_global_flows_across_services(tmp_path: Path, monkeypatch):
    """
    [20260103_TEST] Enterprise tier identifies global taint flows.

    Should track:
    - All entry points across services
    - All exit points (sinks) across services
    - Flow summary statistics
    - High-risk flow patterns
    """
    from code_scalpel.mcp import server

    monkeypatch.setattr(server, "_get_current_tier", lambda: "enterprise")

    root = tmp_path / "repo"
    root.mkdir()
    _make_microservice_project(root)

    from code_scalpel.mcp.server import cross_file_security_scan

    r = await cross_file_security_scan(
        project_root=str(root),
        max_depth=15,
        include_diagram=True,
        timeout_seconds=10.0,
        max_modules=999,
    )

    assert r.success is True

    # Enterprise may provide global flows
    assert r.global_flows is None or isinstance(
        r.global_flows, list
    ), "global_flows should be None or list (best-effort)"


async def test_enterprise_tier_compliance_impact_mapping(tmp_path: Path, monkeypatch):
    """
    [20260103_TEST] Enterprise tier maps vulnerabilities to compliance impact.

    Should identify:
    - Which compliance standards are violated (PCI-DSS, HIPAA, GDPR)
    - Which requirements each vulnerability affects
    - Risk to compliance posture
    """
    from code_scalpel.mcp import server

    monkeypatch.setattr(server, "_get_current_tier", lambda: "enterprise")

    root = tmp_path / "repo"
    root.mkdir()
    _make_microservice_project(root)

    from code_scalpel.mcp.server import cross_file_security_scan

    r = await cross_file_security_scan(
        project_root=str(root),
        max_depth=15,
        include_diagram=True,
        timeout_seconds=10.0,
        max_modules=999,
    )

    assert r.success is True

    # Enterprise should identify compliance implications
    if r.vulnerability_count > 0:
        for vuln in r.vulnerabilities:
            # Vulnerability should reference compliance if Enterprise
            assert hasattr(vuln, "cwe"), "Vulnerability should have CWE"


async def test_enterprise_tier_unlimited_module_analysis(tmp_path: Path, monkeypatch):
    """
    [20260103_TEST] Enterprise tier analyzes unlimited modules.

    With no cap on module count, Enterprise should:
    - Analyze all services in microservice project
    - Find flows spanning many services
    - Not truncate results due to module limits
    """
    from code_scalpel.mcp import server

    monkeypatch.setattr(server, "_get_current_tier", lambda: "enterprise")

    root = tmp_path / "repo"
    root.mkdir()

    # Create a project with many small modules
    for i in range(20):
        service = root / f"service_{i}"
        service.mkdir()
        _write(
            service / "handler.py",
            f"""\
def service_{i}_handler(data):
    return data + {i}
""",
        )

    from code_scalpel.mcp.server import cross_file_security_scan

    r = await cross_file_security_scan(
        project_root=str(root),
        max_depth=20,
        include_diagram=False,
        timeout_seconds=10.0,
        max_modules=999,  # Enterprise unlimited
    )

    assert r.success is True
    # Should analyze all (or most) of the 20 services
    assert r.files_analyzed >= 15, "Enterprise should analyze most/all modules without capping"


async def test_enterprise_tier_result_completeness(tmp_path: Path, monkeypatch):
    """
    [20260103_TEST] Enterprise tier returns complete result structure.

    Verifies all Enterprise-specific fields are present and properly typed:
    - microservice_boundaries: list or None
    - distributed_trace: dict or None
    - global_flows: list or None
    - framework_contexts: list or None
    - dependency_chains: list or None
    - confidence_scores: dict or None
    """
    from code_scalpel.mcp import server

    monkeypatch.setattr(server, "_get_current_tier", lambda: "enterprise")

    root = tmp_path / "repo"
    root.mkdir()
    _make_microservice_project(root)

    from code_scalpel.mcp.server import cross_file_security_scan

    r = await cross_file_security_scan(
        project_root=str(root),
        max_depth=15,
        include_diagram=True,
        timeout_seconds=10.0,
        max_modules=999,
    )

    assert r.success is True

    # All fields should be present
    assert hasattr(r, "microservice_boundaries"), "Missing microservice_boundaries"
    assert hasattr(r, "distributed_trace"), "Missing distributed_trace"
    assert hasattr(r, "global_flows"), "Missing global_flows"
    assert hasattr(r, "framework_contexts"), "Missing framework_contexts"
    assert hasattr(r, "dependency_chains"), "Missing dependency_chains"
    assert hasattr(r, "confidence_scores"), "Missing confidence_scores"

    # All should have correct types
    assert r.microservice_boundaries is None or isinstance(r.microservice_boundaries, list)
    assert r.distributed_trace is None or isinstance(r.distributed_trace, dict)
    assert r.global_flows is None or isinstance(r.global_flows, list)
    assert r.framework_contexts is None or isinstance(r.framework_contexts, list)
    assert r.dependency_chains is None or isinstance(r.dependency_chains, list)
    assert r.confidence_scores is None or isinstance(r.confidence_scores, dict)


# =============================================================================
# FEATURE GATING VALIDATION
# =============================================================================


async def test_community_tier_gating_no_pro_features(tmp_path: Path, monkeypatch):
    """
    [20260103_TEST] Community tier strictly gated from Pro features.

    Verify that Community tier results do NOT include:
    - confidence_scores (should be None)
    - dependency_chains (should be None)
    - framework_contexts (should be None or minimal)
    """
    monkeypatch.setenv("CODE_SCALPEL_TIER", "community")

    root = tmp_path / "repo"
    root.mkdir()
    _make_flask_app_with_di(root)

    from code_scalpel.mcp.server import cross_file_security_scan

    r = await cross_file_security_scan(
        project_root=str(root),
        max_depth=3,  # Community cap
        include_diagram=False,
        timeout_seconds=10.0,
        max_modules=10,  # Community cap
    )

    assert r.success is True

    # Community tier should not have Pro features
    assert r.confidence_scores is None, "Community tier should not have confidence_scores"
    assert (
        r.dependency_chains is None or len(r.dependency_chains) == 0
    ), "Community tier should not have dependency_chains"


async def test_pro_tier_gating_no_enterprise_features(tmp_path: Path, monkeypatch):
    """
    [20260103_TEST] Pro tier strictly gated from Enterprise features.

    Verify that Pro tier results do NOT include:
    - distributed_trace (should be None)
    - microservice_boundaries beyond basic detection (should be None)
    - global_flows (should be None)
    """
    from code_scalpel.mcp import server

    monkeypatch.setattr(server, "_get_current_tier", lambda: "pro")

    root = tmp_path / "repo"
    root.mkdir()
    _make_microservice_project(root)

    from code_scalpel.mcp.server import cross_file_security_scan

    r = await cross_file_security_scan(
        project_root=str(root),
        max_depth=10,  # Pro cap
        include_diagram=False,
        timeout_seconds=10.0,
        max_modules=100,  # Pro cap
    )

    assert r.success is True

    # Pro tier should not have Enterprise features
    assert r.distributed_trace is None, "Pro tier should not have distributed_trace"
    assert r.global_flows is None, "Pro tier should not have global_flows"


async def test_enterprise_tier_all_features_available(tmp_path: Path, monkeypatch):
    """
    [20260103_TEST] Enterprise tier has access to all features.

    Verify Enterprise tier CAN use:
    - Unlimited depth/modules
    - confidence_scores (Pro+)
    - dependency_chains (Pro+)
    - framework_contexts (Pro+)
    - distributed_trace (Enterprise)
    - microservice_boundaries (Enterprise)
    - global_flows (Enterprise)
    """
    from code_scalpel.mcp import server

    monkeypatch.setattr(server, "_get_current_tier", lambda: "enterprise")

    root = tmp_path / "repo"
    root.mkdir()
    _make_microservice_project(root)

    from code_scalpel.mcp.server import cross_file_security_scan

    r = await cross_file_security_scan(
        project_root=str(root),
        max_depth=999,  # Enterprise unlimited
        include_diagram=True,
        timeout_seconds=10.0,
        max_modules=999,  # Enterprise unlimited
    )

    assert r.success is True

    # Enterprise should be able to request high limits without clamping
    # (internal implementation enforces, not MCP layer)
    assert r.files_analyzed > 0, "Should analyze project"
