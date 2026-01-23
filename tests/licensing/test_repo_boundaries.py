"""Repo boundary checks for issuer/consumer separation.

[20251228_TEST] Prevent issuer-side code and private keys from creeping back into
the consumer (code-scalpel) repository.
"""

from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    # tests/licensing/test_repo_boundaries.py -> repo root
    return Path(__file__).resolve().parents[2]


def test_no_issuer_directory_in_repo() -> None:
    root = _repo_root()

    # Issuer service lives in a separate repository.
    assert not (root / "issuer").exists()
    assert not (root / "code_scalpel_tier_management").exists()
    assert not (root / "license-management").exists()
    assert not (root / "tier-management").exists()


def test_no_private_keys_present() -> None:
    root = _repo_root()

    # [20251228_TEST] Only enforce key hygiene in the consumer repo's
    # source/control-plane directories. Evidence and release artifacts can
    # legitimately contain signed blobs or historical materials.
    scan_roots = [
        root / "src",
        root / "tests",
        root / ".github",
        root / "scripts",
    ]
    scan_roots = [p for p in scan_roots if p.exists()]

    # We allow TLS/cert fixtures; those are not licensing keys.
    allow_dirs = {root / "certs"}

    suspicious_suffixes = {".key", ".p8", ".p12", ".pfx"}
    suspicious_names = {
        "private_key.pem",
        "license_signing_private_key.pem",
        "jwt_private_key.pem",
    }

    def _is_allowed(path: Path) -> bool:
        return any(str(path).startswith(str(d)) for d in allow_dirs)

    hits: list[str] = []
    for base in scan_roots:
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if _is_allowed(path):
                continue

            if path.suffix.lower() in suspicious_suffixes:
                hits.append(str(path.relative_to(root)))
                continue

            name_lower = path.name.lower()
            if name_lower in suspicious_names:
                hits.append(str(path.relative_to(root)))
                continue

            # Catch common private key PEM naming patterns, but avoid flagging public keys.
            if name_lower.endswith(".pem") and any(
                marker in name_lower for marker in ("private", "privkey", "signing", "rsa_private")
            ):
                hits.append(str(path.relative_to(root)))

    assert not hits, f"Private-key-like files must not exist here: {hits}"
