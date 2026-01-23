# [20251214_DOCS] Minimal DX smoke script for v1.5.4
# Runs lint, format check, fast tests, and a dry-run vulnerability scan.

python -m ruff check .
python -m black --check .
python -m pytest tests/test_path_resolver.py::TestPathResolverInit::test_default_initialization tests/test_symbolic_smoke.py::TestSymbolicImports::test_import_engine -q
python -m pip-audit --dry-run
