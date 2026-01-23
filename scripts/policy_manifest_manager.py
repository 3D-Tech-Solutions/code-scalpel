#!/usr/bin/env python3
"""
CLI utility for managing policy manifests.

Usage:
    # Create/update manifest
    python scripts/policy_manifest_manager.py sign --policy-dir .code-scalpel --signed-by admin@company.com

    # Verify policies
    python scripts/policy_manifest_manager.py verify --policy-dir .code-scalpel --source file

    # Show manifest info
    python scripts/policy_manifest_manager.py info --policy-dir .code-scalpel
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from code_scalpel.policy_engine.crypto_verify import (
    CryptographicPolicyVerifier,
    SecurityError,
)


def cmd_sign(args):
    """Sign policy files and create manifest."""
    print(f"Signing policy files in {args.policy_dir}...")

    policy_path = Path(args.policy_dir)
    if not policy_path.exists():
        print(f"Error: Directory not found: {args.policy_dir}")
        return 1

    # Find all policy files
    policy_files = []
    for ext in ["*.yaml", "*.yml", "*.json", "*.rego"]:
        files = list(policy_path.glob(ext))
        # Exclude manifest file
        files = [f for f in files if f.name != "policy.manifest.json"]
        policy_files.extend([f.name for f in files])

    if not policy_files:
        print(f"Warning: No policy files found in {args.policy_dir}")
        print("Looking for: *.yaml, *.yml, *.json, *.rego")
        return 1

    print(f"Found {len(policy_files)} policy files:")
    for f in sorted(policy_files):
        print(f"  - {f}")

    # Get signing secret
    if args.secret:
        secret = args.secret
    else:
        secret = os.environ.get("SCALPEL_MANIFEST_SECRET")
        if not secret:
            print("\nError: No signing secret provided.")
            print("Set SCALPEL_MANIFEST_SECRET environment variable or use --secret option.")
            print("\nGenerate a strong secret:")
            import secrets

            suggested = secrets.token_urlsafe(32)
            print(f"  export SCALPEL_MANIFEST_SECRET='{suggested}'")
            return 1

    # Get signer identity
    if not args.signed_by:
        # Try to get from git config
        try:
            import subprocess

            result = subprocess.run(
                ["git", "config", "user.email"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                args.signed_by = result.stdout.strip()
        except Exception:
            pass

        if not args.signed_by:
            print("\nError: --signed-by required (email or name of signer)")
            return 1

    try:
        # Create manifest
        manifest = CryptographicPolicyVerifier.create_manifest(
            policy_files=policy_files,
            secret_key=secret,
            signed_by=args.signed_by,
            policy_dir=args.policy_dir,
        )

        # Save manifest
        manifest_path = CryptographicPolicyVerifier.save_manifest(
            manifest,
            args.policy_dir,
        )

        print(f"\n✅ Manifest created: {manifest_path}")
        print(f"   Version: {manifest.version}")
        print(f"   Signed by: {manifest.signed_by}")
        print(f"   Created: {manifest.created_at}")
        print(f"   Files: {len(manifest.files)}")
        print(f"   Signature: hmac-sha256:{manifest.signature[:32]}...")

        print("\n📋 Next steps:")
        print(f"   1. Review the manifest: cat {manifest_path}")
        print(f"   2. Commit to git: git add {manifest_path} && git commit -m 'Update policy manifest'")
        print("   3. Ensure agents have SCALPEL_MANIFEST_SECRET set")

        return 0

    except Exception as e:
        print(f"\n❌ Error creating manifest: {e}")
        import traceback

        traceback.print_exc()
        return 1


def cmd_verify(args):
    """Verify policy integrity."""
    print(f"Verifying policies in {args.policy_dir}...")

    policy_path = Path(args.policy_dir)
    if not policy_path.exists():
        print(f"Error: Directory not found: {args.policy_dir}")
        return 1

    # Check for secret
    if not args.secret and "SCALPEL_MANIFEST_SECRET" not in os.environ:
        print("\nError: No signing secret provided.")
        print("Set SCALPEL_MANIFEST_SECRET environment variable or use --secret option.")
        return 1

    secret = args.secret or os.environ["SCALPEL_MANIFEST_SECRET"]

    try:
        # Temporarily set secret in environment
        os.environ["SCALPEL_MANIFEST_SECRET"] = secret

        # Create verifier
        verifier = CryptographicPolicyVerifier(
            manifest_source=args.source,
            policy_dir=args.policy_dir,
        )

        print(f"Loaded manifest from: {args.source}")

        # Verify
        result = verifier.verify_all_policies()

        if result.success:
            print("\n✅ Policy integrity verified!")
            print(f"   Manifest valid: {result.manifest_valid}")
            print(f"   Files verified: {result.files_verified}")

            if args.verbose and verifier.manifest:
                print("\n📄 Verified files:")
                for filename in sorted(verifier.manifest.files.keys()):
                    print(f"   - {filename}")

            return 0
        else:
            print("\n❌ Verification FAILED!")
            print(f"   Error: {result.error}")
            if result.files_failed:
                print(f"   Failed files: {', '.join(result.files_failed)}")
            return 1

    except SecurityError as e:
        print(f"\n❌ SECURITY ERROR: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Error during verification: {e}")
        import traceback

        traceback.print_exc()
        return 1


def cmd_info(args):
    """Show manifest information."""
    manifest_path = Path(args.policy_dir) / "policy.manifest.json"

    if not manifest_path.exists():
        print(f"Error: Manifest not found: {manifest_path}")
        print("\nCreate a manifest with:")
        print(f"  python scripts/policy_manifest_manager.py sign --policy-dir {args.policy_dir}")
        return 1

    try:
        with open(manifest_path) as f:
            manifest = json.load(f)

        print(f"📋 Manifest: {manifest_path}")
        print(f"\nVersion: {manifest.get('version', 'unknown')}")
        print(f"Created: {manifest.get('created_at', 'unknown')}")
        print(f"Signed by: {manifest.get('signed_by', 'unknown')}")

        files = manifest.get("files", {})
        print(f"\nFiles ({len(files)}):")
        for filename, file_hash in sorted(files.items()):
            if isinstance(file_hash, dict):
                file_hash = file_hash.get("hash", "unknown")
            print(f"  - {filename}")
            print(f"    Hash: {file_hash}")

        signature = manifest.get("signature", "none")
        print("\nSignature:")
        print(f"  {signature[:64]}...")

        # Check if files still exist and match
        if args.check:
            print("\nFile Status:")
            policy_path = Path(args.policy_dir)

            for filename in sorted(files.keys()):
                file_path = policy_path / filename
                if file_path.exists():
                    print(f"  ✓ {filename} (exists)")
                else:
                    print(f"  ✗ {filename} (MISSING)")

        return 0

    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in manifest: {e}")
        return 1
    except Exception as e:
        print(f"Error reading manifest: {e}")
        return 1


def cmd_rotate(args):
    """Rotate signing secret (regenerate manifest with new secret)."""
    print(f"Rotating signing secret for {args.policy_dir}...")

    # Get old and new secrets
    old_secret = args.old_secret or os.environ.get("SCALPEL_MANIFEST_SECRET")
    if not old_secret:
        print("\nError: Old secret required.")
        print("Set SCALPEL_MANIFEST_SECRET or use --old-secret option.")
        return 1

    if not args.new_secret:
        # Generate new secret
        import secrets

        args.new_secret = secrets.token_urlsafe(32)
        print(f"\nGenerated new secret: {args.new_secret}")
        print("Save this securely!")

    # Verify old manifest first
    print("\nVerifying old manifest...")
    os.environ["SCALPEL_MANIFEST_SECRET"] = old_secret

    try:
        verifier = CryptographicPolicyVerifier(
            manifest_source="file",
            policy_dir=args.policy_dir,
        )
        result = verifier.verify_all_policies()

        if not result.success:
            print(f"❌ Old manifest verification failed: {result.error}")
            return 1

        print("✓ Old manifest valid")

    except SecurityError as e:
        print(f"❌ Old manifest verification failed: {e}")
        return 1

    # Get signer identity
    signed_by = args.signed_by or verifier.manifest.signed_by

    # Get list of policy files from old manifest
    policy_files = list(verifier.manifest.files.keys())

    # Create new manifest with new secret
    print("\nCreating new manifest with new secret...")

    manifest = CryptographicPolicyVerifier.create_manifest(
        policy_files=policy_files,
        secret_key=args.new_secret,
        signed_by=signed_by,
        policy_dir=args.policy_dir,
    )

    # Backup old manifest
    manifest_path = Path(args.policy_dir) / "policy.manifest.json"
    backup_path = manifest_path.with_suffix(f".json.backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
    if manifest_path.exists():
        manifest_path.rename(backup_path)
        print(f"✓ Backed up old manifest: {backup_path}")

    # Save new manifest
    new_path = CryptographicPolicyVerifier.save_manifest(
        manifest,
        args.policy_dir,
    )

    print("\n✅ Secret rotated successfully!")
    print(f"   New manifest: {new_path}")
    print(f"   Old backup: {backup_path}")

    print("\n📋 Next steps:")
    print("   1. Update SCALPEL_MANIFEST_SECRET everywhere:")
    print(f"      export SCALPEL_MANIFEST_SECRET='{args.new_secret}'")
    print(f"   2. Commit new manifest: git add {new_path} && git commit -m 'Rotate policy secret'")
    print("   3. Update CI/CD secrets")
    print("   4. Restart all agents")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Policy Manifest Manager - Sign and verify policy files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create/update manifest
  %(prog)s sign --policy-dir .code-scalpel --signed-by admin@company.com
  
  # Verify policies
  %(prog)s verify --policy-dir .code-scalpel --source file
  
  # Show manifest info
  %(prog)s info --policy-dir .code-scalpel --check
  
  # Rotate secret
  %(prog)s rotate --policy-dir .code-scalpel --new-secret <new-secret>
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Sign command
    sign_parser = subparsers.add_parser("sign", help="Sign policy files and create manifest")
    sign_parser.add_argument("--policy-dir", default=".code-scalpel", help="Policy directory")
    sign_parser.add_argument("--signed-by", help="Email or name of signer (default: git user.email)")
    sign_parser.add_argument("--secret", help="Signing secret (default: SCALPEL_MANIFEST_SECRET env var)")

    # Verify command
    verify_parser = subparsers.add_parser("verify", help="Verify policy integrity")
    verify_parser.add_argument("--policy-dir", default=".code-scalpel", help="Policy directory")
    verify_parser.add_argument(
        "--source",
        default="file",
        choices=["file", "git", "env"],
        help="Manifest source",
    )
    verify_parser.add_argument("--secret", help="Signing secret (default: SCALPEL_MANIFEST_SECRET env var)")
    verify_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    # Info command
    info_parser = subparsers.add_parser("info", help="Show manifest information")
    info_parser.add_argument("--policy-dir", default=".code-scalpel", help="Policy directory")
    info_parser.add_argument("--check", action="store_true", help="Check if files still exist")

    # Rotate command
    rotate_parser = subparsers.add_parser("rotate", help="Rotate signing secret")
    rotate_parser.add_argument("--policy-dir", default=".code-scalpel", help="Policy directory")
    rotate_parser.add_argument(
        "--old-secret",
        help="Old signing secret (default: SCALPEL_MANIFEST_SECRET env var)",
    )
    rotate_parser.add_argument("--new-secret", help="New signing secret (default: auto-generate)")
    rotate_parser.add_argument("--signed-by", help="Email or name of signer (default: from old manifest)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "sign":
        return cmd_sign(args)
    elif args.command == "verify":
        return cmd_verify(args)
    elif args.command == "info":
        return cmd_info(args)
    elif args.command == "rotate":
        return cmd_rotate(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
