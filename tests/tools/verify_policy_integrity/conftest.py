"""
Shared fixtures for verify_policy_integrity tests.

# [20260103_TEST] Created fixtures for policy verification testing
"""

import hashlib
import hmac
import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import pytest


@pytest.fixture
def create_policy_file() -> Callable[[Path, str, str], Path]:
    """
    Factory fixture to create policy files.

    Returns:
        Function that creates a policy file and returns its path
    """

    def _create(policy_dir: Path, filename: str = "policy.yaml", content: str = "rules: []") -> Path:
        policy_dir.mkdir(parents=True, exist_ok=True)
        policy_file = policy_dir / filename
        policy_file.write_text(content, encoding="utf-8")
        return policy_file

    return _create


@pytest.fixture
def create_manifest() -> Callable[[Path, str, list[str]], Path]:
    """
    Factory fixture to create signed policy manifests.

    Returns:
        Function that creates a manifest file and returns its path
    """

    def _create(policy_dir: Path, secret: str, filenames: list[str]) -> Path:
        policy_dir.mkdir(parents=True, exist_ok=True)

        # Calculate hashes for each file
        files = {}
        for filename in filenames:
            file_path = policy_dir / filename
            if file_path.exists():
                hasher = hashlib.sha256()
                with open(file_path, "rb") as f:
                    hasher.update(f.read())
                files[filename] = "sha256:" + hasher.hexdigest()

        # Create manifest data
        manifest_data = {
            "version": "1.0",
            "files": files,
            "created_at": datetime.now().isoformat(),
            "signed_by": "test-admin",
        }

        # Sign with HMAC-SHA256
        message = json.dumps(manifest_data, sort_keys=True, separators=(",", ":"))
        signature = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()

        manifest_data["signature"] = signature

        # Write manifest file
        manifest_path = policy_dir / "policy.manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest_data, f, indent=2)

        return manifest_path

    return _create


@pytest.fixture
def create_multiple_policies() -> Callable[[Path, int], list[Path]]:
    """
    Factory fixture to create multiple policy files.

    Returns:
        Function that creates N policy files and returns their paths
    """

    def _create(policy_dir: Path, count: int) -> list[Path]:
        policy_dir.mkdir(parents=True, exist_ok=True)
        policy_files = []

        for i in range(count):
            policy_file = policy_dir / f"policy_{i:03d}.yaml"
            policy_file.write_text(f"# Policy {i}\nrules: []\n", encoding="utf-8")
            policy_files.append(policy_file)

        return policy_files

    return _create


@pytest.fixture
def mock_community_license(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock a Community tier license."""
    monkeypatch.setenv(
        "SCALPEL_LICENSE_JWT",
        "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0aWVyIjoiY29tbXVuaXR5In0.test",
    )


@pytest.fixture
def mock_pro_license(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock a Pro tier license."""
    monkeypatch.setenv(
        "SCALPEL_LICENSE_JWT",
        "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0aWVyIjoicHJvIn0.test",
    )


@pytest.fixture
def mock_enterprise_license(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock an Enterprise tier license."""
    monkeypatch.setenv(
        "SCALPEL_LICENSE_JWT",
        "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0aWVyIjoiZW50ZXJwcmlzZSJ9.test",
    )


@pytest.fixture
def mock_invalid_license(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock an invalid/malformed license."""
    monkeypatch.setenv("SCALPEL_LICENSE_JWT", "invalid.jwt.token")


@pytest.fixture
def mock_expired_license(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock an expired license."""
    # JWT with exp claim in the past (Jan 1, 2020)
    monkeypatch.setenv(
        "SCALPEL_LICENSE_JWT",
        "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0aWVyIjoicHJvIiwiZXhwIjoxNTc3ODM2ODAwfQ.test",
    )
