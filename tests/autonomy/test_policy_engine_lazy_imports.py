"""Regression tests for `code_scalpel.policy_engine` import behavior.

The cryptographic policy integrity verifier must remain usable even when the
YAML/OPA policy engine dependencies are not installed in the current runtime.

This test guards against accidental eager imports of the YAML-based policy
engine from `code_scalpel.policy_engine.__init__`.
"""

from __future__ import annotations

import builtins
import importlib
import sys


def test_crypto_verifier_import_does_not_require_yaml(monkeypatch):
    real_import = builtins.__import__

    def blocked_yaml_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "yaml" or name.startswith("yaml."):
            raise ImportError("yaml blocked for test")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", blocked_yaml_import)

    # Force a clean import so we can detect any eager YAML imports.
    sys.modules.pop("code_scalpel.policy_engine", None)
    sys.modules.pop("code_scalpel.policy_engine.policy_engine", None)

    policy_engine_pkg = importlib.import_module("code_scalpel.policy_engine")

    # Importing the package should not require YAML.
    assert policy_engine_pkg is not None

    # The crypto verifier should remain importable from the package.
    from code_scalpel.policy_engine import CryptographicPolicyVerifier

    assert CryptographicPolicyVerifier is not None
