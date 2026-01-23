"""Tests for remote-only verifier + 24h refresh + 24h offline grace.

[20251228_TEST] Validate the authorization policy described in the MCP↔verifier contract.
"""

from __future__ import annotations

import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from code_scalpel.licensing import remote_verifier


def _b64url_decode(segment: str) -> bytes:
    padded = segment + "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def _decode_jwt_payload_unverified(token: str) -> dict:
    parts = token.strip().split(".")
    if len(parts) < 2:
        return {}
    payload = json.loads(_b64url_decode(parts[1]).decode("utf-8"))
    return payload if isinstance(payload, dict) else {}


class _VerifierHandler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        if self.path != "/verify":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length).decode("utf-8")
        req = json.loads(body)
        token = str(req.get("token") or "")

        # Minimal fake verifier: trust payload fields (unverified) but behaves like a
        # remote authority from MCP perspective.
        claims = _decode_jwt_payload_unverified(token)
        tier = str(claims.get("tier") or "community")
        exp = int(claims.get("exp") or 0)
        features = claims.get("features") or []
        if not isinstance(features, list):
            features = []

        resp = {
            "valid": token != "invalid",
            "license": {
                "tier": tier,
                "features": features,
                "exp": exp,
                "customer_id": str(claims.get("sub") or ""),
                "organization": claims.get("organization"),
            },
        }

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(resp).encode("utf-8"))

    def log_message(self, format, *args):  # noqa: A002
        # Keep tests quiet.
        return


@pytest.fixture(scope="function")
def verifier_url(tmp_path: Path):
    server = ThreadingHTTPServer(("127.0.0.1", 0), _VerifierHandler)
    port = server.server_address[1]

    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    url = f"http://127.0.0.1:{port}"
    yield url

    server.shutdown()
    server.server_close()


def _set_env(monkeypatch, *, url: str, cache_path: Path):
    monkeypatch.setenv(remote_verifier.VERIFIER_BASE_URL_ENV_VAR, url)
    monkeypatch.setenv(remote_verifier.LICENSE_CACHE_PATH_ENV_VAR, str(cache_path))
    monkeypatch.delenv(remote_verifier.VERIFIER_ENVIRONMENT_ENV_VAR, raising=False)


def test_remote_verify_populates_cache_and_allows_when_valid(tmp_path: Path, verifier_url: str, monkeypatch):
    cache_path = tmp_path / "license_cache.json"
    _set_env(monkeypatch, url=verifier_url, cache_path=cache_path)

    remote_verifier._IN_MEMORY_CACHE = None

    token = "header.eyJ0aWVyIjoicHJvIiwiZXhwIjo5OTk5OTk5OTk5LCJmZWF0dXJlcyI6W119.signature"

    decision = remote_verifier.authorize_token(token)
    assert decision.allowed is True
    assert decision.entitlements is not None
    assert decision.entitlements.tier == "pro"
    assert cache_path.exists()


def test_cache_fresh_skips_remote_call(tmp_path: Path, verifier_url: str, monkeypatch):
    cache_path = tmp_path / "license_cache.json"
    _set_env(monkeypatch, url=verifier_url, cache_path=cache_path)

    remote_verifier._IN_MEMORY_CACHE = None

    token = "header.eyJ0aWVyIjoicHJvIiwiZXhwIjo5OTk5OTk5OTk5LCJmZWF0dXJlcyI6W119.signature"

    # First call hits remote and writes cache.
    decision1 = remote_verifier.authorize_token(token)
    assert decision1.allowed is True

    # Second call is within 24h. Force urlopen to explode if called.
    def _boom(*args, **kwargs):
        raise AssertionError("remote called during fresh cache")

    monkeypatch.setattr(remote_verifier.urllib.request, "urlopen", _boom)

    decision2 = remote_verifier.authorize_token(token)
    assert decision2.allowed is True
    assert decision2.reason == "cache_fresh"


def test_offline_grace_allows_only_with_hash_match_and_recent_cache(tmp_path: Path, verifier_url: str, monkeypatch):
    cache_path = tmp_path / "license_cache.json"
    _set_env(monkeypatch, url=verifier_url, cache_path=cache_path)

    remote_verifier._IN_MEMORY_CACHE = None

    token = "header.eyJ0aWVyIjoicHJvIiwiZXhwIjo5OTk5OTk5OTk5LCJmZWF0dXJlcyI6W119.signature"

    base_time = 10_000.0
    monkeypatch.setattr(remote_verifier.time, "time", lambda: base_time)

    # Prime cache with a successful verify.
    decision1 = remote_verifier.authorize_token(token)
    assert decision1.allowed is True

    # Now stale (>24h) but within offline grace (<=48h), and remote is down.
    monkeypatch.setattr(
        remote_verifier.time,
        "time",
        lambda: base_time + remote_verifier.REFRESH_SECONDS + 10,
    )

    def _down(*args, **kwargs):
        raise remote_verifier.urllib.error.URLError("down")

    monkeypatch.setattr(remote_verifier.urllib.request, "urlopen", _down)

    decision2 = remote_verifier.authorize_token(token)
    assert decision2.allowed is True
    assert decision2.reason == "offline_grace"

    # Hash mismatch => deny.
    token2 = token + "x"
    decision3 = remote_verifier.authorize_token(token2)
    assert decision3.allowed is False


def test_expiry_denies_even_during_grace(tmp_path: Path, verifier_url: str, monkeypatch):
    cache_path = tmp_path / "license_cache.json"
    _set_env(monkeypatch, url=verifier_url, cache_path=cache_path)

    remote_verifier._IN_MEMORY_CACHE = None

    now = 20_000.0
    monkeypatch.setattr(remote_verifier.time, "time", lambda: now)

    # exp in the past.
    token = "header.eyJ0aWVyIjoicHJvIiwiZXhwIjoxMDAwLCJmZWF0dXJlcyI6W119.signature"

    decision = remote_verifier.authorize_token(token)
    assert decision.allowed is False
    assert decision.reason == "license_expired"


def test_remote_verify_error_message_never_leaks_token(tmp_path: Path, verifier_url: str, monkeypatch):
    cache_path = tmp_path / "license_cache.json"
    _set_env(monkeypatch, url=verifier_url, cache_path=cache_path)

    token = "header.eyJ0aWVyIjoicHJvIiwiZXhwIjo5OTk5OTk5OTk5LCJmZWF0dXJlcyI6W119.signature"

    def _down(*args, **kwargs):
        raise remote_verifier.urllib.error.URLError(f"network down: {token}")

    monkeypatch.setattr(remote_verifier.urllib.request, "urlopen", _down)

    with pytest.raises(RuntimeError) as excinfo:
        remote_verifier.remote_verify(token, environment=None)

    msg = str(excinfo.value)
    assert token not in msg


def test_atomic_write_json_retries_on_transient_enoent(tmp_path: Path, monkeypatch):
    # [20251228_TEST] Guard against flaky ENOENT-on-rename behavior sometimes seen
    # on Docker bind mounts backed by non-POSIX filesystems.
    target = tmp_path / "license_cache.json"

    original_replace = remote_verifier.Path.replace
    calls = {"n": 0}

    def _flaky_replace(self, dst):  # type: ignore[no-untyped-def]
        if str(self).endswith(".tmp") and calls["n"] == 0:
            calls["n"] += 1
            raise FileNotFoundError("simulated transient rename ENOENT")
        return original_replace(self, dst)

    monkeypatch.setattr(remote_verifier.Path, "replace", _flaky_replace)

    remote_verifier._atomic_write_json(target, {"ok": True})
    assert target.exists()


def test_atomic_write_json_falls_back_to_direct_write_on_persistent_enoent(tmp_path: Path, monkeypatch):
    # [20251228_TEST] If rename keeps failing, we should still persist the cache
    # best-effort rather than crash the server.
    target = tmp_path / "license_cache.json"

    def _always_enoent(self, dst):  # type: ignore[no-untyped-def]
        raise FileNotFoundError("simulated persistent rename ENOENT")

    monkeypatch.setattr(remote_verifier.Path, "replace", _always_enoent)

    remote_verifier._atomic_write_json(target, {"ok": True})
    assert target.exists()
