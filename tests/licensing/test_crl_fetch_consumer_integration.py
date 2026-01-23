"""Consumer-side CRL fetch integration tests.

[20251228_TEST] Prove end-to-end behavior: a CRL served from
`/.well-known/license-crl.jwt` can be fetched/cached by the MCP server consumer
code and then used by the JWT validator to reject revoked JTIs.
"""

from __future__ import annotations

import http.server
import socket
import threading
from dataclasses import dataclass

import pytest


@dataclass(frozen=True)
class _Server:
    url: str
    shutdown: callable


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _serve_token(token: str) -> _Server:
    port = _free_port()

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write((token + "\n").encode("utf-8"))

        def log_message(self, fmt, *args):  # noqa: ANN001
            # Keep pytest output clean.
            return

    httpd = http.server.HTTPServer(("127.0.0.1", port), Handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()

    def _shutdown() -> None:
        httpd.shutdown()
        httpd.server_close()

    return _Server(url=f"http://127.0.0.1:{port}/.well-known/license-crl.jwt", shutdown=_shutdown)


@pytest.mark.usefixtures("disable_health_server")
def test_crl_fetch_then_validator_rejects_revoked_jti(
    monkeypatch,
    tmp_path,
    write_hs256_license_jwt,
    write_hs256_crl_jwt,
    set_hs256_license_env,
):
    from code_scalpel.licensing.crl_fetcher import ensure_crl_available
    from code_scalpel.licensing.jwt_validator import JWTLicenseValidator

    revoked_jti = "lic-revoked-via-http"
    license_path = write_hs256_license_jwt(jti=revoked_jti, base_dir=tmp_path)
    crl_path = write_hs256_crl_jwt(revoked_jtis=[revoked_jti], base_dir=tmp_path)
    crl_token = crl_path.read_text(encoding="utf-8").strip()

    server = _serve_token(crl_token)
    try:
        # Configure license env (HS256 enabled) but do NOT set CRL path/token.
        set_hs256_license_env(license_path=str(license_path), crl_path=None)

        # Enable CRL fetch and point to our local .well-known endpoint.
        monkeypatch.setenv("CODE_SCALPEL_ENABLE_CRL_FETCH", "1")
        monkeypatch.setenv("CODE_SCALPEL_LICENSE_CRL_URL", server.url)
        # Ensure cache writes go into temp by overriding XDG_CONFIG_HOME.
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))

        # Fetch/cache CRL and set CODE_SCALPEL_LICENSE_CRL_PATH internally.
        paths = ensure_crl_available()
        assert paths is not None

        validator = JWTLicenseValidator()
        token = validator.load_license_token()
        assert token

        result = validator.validate_token(token)
        assert not result.is_valid
        assert result.error_message
        assert "revoked" in result.error_message.lower()
    finally:
        server.shutdown()
