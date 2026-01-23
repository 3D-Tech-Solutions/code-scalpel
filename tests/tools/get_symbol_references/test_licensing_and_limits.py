import pytest


@pytest.mark.asyncio
async def test_invalid_license_falls_back_to_community(
    make_project, patch_capabilities, patch_license_validator, monkeypatch
):
    """[20260104_TEST] Invalid license should clamp tier to community limits."""
    import code_scalpel.mcp.tools.context as server

    class _InvalidLicense:
        is_valid = False
        tier = "enterprise"
        error_message = "revoked license"
        is_expired = False

    project = make_project(
        {f"src/file_{i}.py": """
from shared.target import target

def use():
    return target()
""" for i in range(6)}
        | {
            "shared/target.py": """
def target():
    return 1
""",
        }
    )

    patch_license_validator(_InvalidLicense())
    patch_capabilities(
        {
            "limits": {"max_files_searched": 2, "max_references": 2},
            "capabilities": [],
        }
    )

    # Request a higher tier; validator should downgrade to community.
    monkeypatch.setenv("CODE_SCALPEL_TIER", "enterprise")

    result = await server.get_symbol_references("target", project_root=str(project))

    assert result.success is True
    # Expect truncation because limits are applied after fallback.
    assert result.files_truncated is True
    assert result.references_truncated is True
    assert result.files_scanned == 2
    assert len(result.references) == 2


@pytest.mark.asyncio
async def test_expired_license_falls_back_to_community(
    make_project, patch_capabilities, patch_license_validator, monkeypatch
):
    """[20260109_TEST] Expired license should clamp tier to community limits."""
    import code_scalpel.mcp.tools.context as server

    class _ExpiredLicense:
        is_valid = False
        tier = "pro"
        error_message = "license expired"
        is_expired = True

    project = make_project(
        {f"src/file_{i}.py": """
from shared.target import target

def use():
    return target()
""" for i in range(3)}
        | {
            "shared/target.py": """
def target():
    return 1
""",
        }
    )

    patch_license_validator(_ExpiredLicense())
    patch_capabilities(
        {
            "limits": {"max_files_searched": 2, "max_references": 2},
            "capabilities": [],
        }
    )

    monkeypatch.setenv("CODE_SCALPEL_TIER", "pro")

    result = await server.get_symbol_references("target", project_root=str(project))

    assert result.success is True
    assert result.files_truncated is True
    assert result.files_scanned == 2
    assert len(result.references) == 2


@pytest.mark.asyncio
async def test_invalid_signature_falls_back_to_community(
    make_project, patch_capabilities, patch_license_validator, monkeypatch
):
    """[20260109_TEST] Invalid license signature should clamp tier to community limits."""
    import code_scalpel.mcp.tools.context as server

    class _InvalidSignature:
        is_valid = False
        tier = "pro"
        error_message = "invalid signature"
        is_expired = False

    project = make_project(
        {f"src/file_{i}.py": """
from shared.target import target

def use():
    return target()
""" for i in range(3)}
        | {
            "shared/target.py": """
def target():
    return 1
""",
        }
    )

    patch_license_validator(_InvalidSignature())
    patch_capabilities(
        {
            "limits": {"max_files_searched": 2, "max_references": 2},
            "capabilities": [],
        }
    )

    monkeypatch.setenv("CODE_SCALPEL_TIER", "pro")

    result = await server.get_symbol_references("target", project_root=str(project))

    assert result.success is True
    assert result.files_truncated is True
    assert result.files_scanned == 2


@pytest.mark.asyncio
async def test_malformed_jwt_falls_back_to_community(
    make_project, patch_capabilities, patch_license_validator, monkeypatch
):
    """[20260109_TEST] Malformed JWT should clamp tier to community limits."""
    import code_scalpel.mcp.tools.context as server

    class _MalformedJWT:
        is_valid = False
        tier = "enterprise"
        error_message = "malformed JWT token"
        is_expired = False

    project = make_project(
        {f"src/file_{i}.py": """
from shared.target import target

def use():
    return target()
""" for i in range(4)}
        | {
            "shared/target.py": """
def target():
    return 1
""",
        }
    )

    patch_license_validator(_MalformedJWT())
    patch_capabilities(
        {
            "limits": {"max_files_searched": 2, "max_references": 2},
            "capabilities": [],
        }
    )

    monkeypatch.setenv("CODE_SCALPEL_TIER", "enterprise")

    result = await server.get_symbol_references("target", project_root=str(project))

    assert result.success is True
    assert result.files_truncated is True
    assert result.references_truncated is True
    assert result.files_scanned == 2
    assert len(result.references) == 2
