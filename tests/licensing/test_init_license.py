import tempfile
from pathlib import Path

from code_scalpel.config.init_config import init_config_dir


def test_init_creates_license_dir():
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Testing in {temp_dir}")
        result = init_config_dir(temp_dir)

        if not result["success"]:
            print(f"Init failed: {result['message']}")
            exit(1)

        config_dir = Path(temp_dir) / ".code-scalpel"
        license_dir = config_dir / "license"
        license_readme = license_dir / "README.md"

        if not license_dir.exists():
            print("FAIL: License directory not created")
            exit(1)

        if not license_readme.exists():
            print("FAIL: License README not created")
            exit(1)

        print("SUCCESS: License directory and README created")
        print(f"Files created: {result['files_created']}")


if __name__ == "__main__":
    test_init_creates_license_dir()
