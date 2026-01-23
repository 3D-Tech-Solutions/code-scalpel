from __future__ import annotations


def test_policy_engine_imports_without_optional_setup() -> None:
    """Guards against missing runtime dependencies (e.g., PyYAML).

    This should succeed in a clean CI environment after installing project deps.
    """

    # Importing the module (not just the package) ensures top-level deps are present.
    import code_scalpel.policy_engine.policy_engine  # noqa: F401
