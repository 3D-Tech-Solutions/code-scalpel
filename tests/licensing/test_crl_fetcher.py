"""Tests for CRL fetch/cache behavior.

[20251228_TEST] Deterministic CRL fetch and offline cache fallback.
"""

from __future__ import annotations

import io
import os
import urllib.error

from code_scalpel.licensing import crl_fetcher


class _FakeHTTPResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_ensure_crl_available_fetches_and_sets_env(monkeypatch, tmp_path):
    monkeypatch.setenv(crl_fetcher.CRL_ENABLE_FETCH_ENV_VAR, "1")
    monkeypatch.delenv(crl_fetcher.CRL_PATH_ENV_VAR, raising=False)

    # Force cache into tmpdir
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    token = "header.payload.signature"

    def _fake_urlopen(req, timeout=0):
        return _FakeHTTPResponse((token + "\n").encode("utf-8"))

    monkeypatch.setattr(crl_fetcher.urllib.request, "urlopen", _fake_urlopen)

    paths = crl_fetcher.ensure_crl_available()
    assert paths is not None
    assert os.environ.get(crl_fetcher.CRL_PATH_ENV_VAR) == str(paths.token_path)
    assert paths.token_path.read_text(encoding="utf-8").strip() == token
    assert paths.meta_path.exists()


def test_ensure_crl_available_uses_fresh_cache_on_fetch_failure(monkeypatch, tmp_path):
    monkeypatch.setenv(crl_fetcher.CRL_ENABLE_FETCH_ENV_VAR, "1")
    monkeypatch.delenv(crl_fetcher.CRL_PATH_ENV_VAR, raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    token = "cached.header.payload.signature"
    paths = crl_fetcher.write_cache(token)

    def _fake_urlopen(req, timeout=0):
        raise urllib.error.URLError("network down")

    monkeypatch.setattr(crl_fetcher.urllib.request, "urlopen", _fake_urlopen)

    used = crl_fetcher.ensure_crl_available()
    assert used is not None
    assert os.environ.get(crl_fetcher.CRL_PATH_ENV_VAR) == str(paths.token_path)


def test_ensure_crl_available_rejects_stale_cache(monkeypatch, tmp_path):
    monkeypatch.setenv(crl_fetcher.CRL_ENABLE_FETCH_ENV_VAR, "1")
    monkeypatch.delenv(crl_fetcher.CRL_PATH_ENV_VAR, raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    # Set offline cache window to 0 days => any non-zero age is stale.
    monkeypatch.setenv(crl_fetcher.CRL_MAX_CACHE_AGE_DAYS_ENV_VAR, "0")

    token = "cached.header.payload.signature"
    paths = crl_fetcher.write_cache(token)

    # Make the cached meta look old.
    paths.meta_path.write_text('{"fetched_at": 0}', encoding="utf-8")

    def _fake_urlopen(req, timeout=0):
        raise urllib.error.URLError("network down")

    monkeypatch.setattr(crl_fetcher.urllib.request, "urlopen", _fake_urlopen)

    used = crl_fetcher.ensure_crl_available()
    assert used is None
    assert os.environ.get(crl_fetcher.CRL_PATH_ENV_VAR) is None
