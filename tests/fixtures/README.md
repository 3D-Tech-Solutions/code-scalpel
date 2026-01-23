# Benchmark Fixtures

This directory contains scripts and data for large-project performance benchmarks.

## Usage

```bash
# Generate synthetic 1200-file project with random import graph
python tests/fixtures/generate_fixture.py --synthetic 1200

# Clone Django (shallow) for real-world benchmark
python tests/fixtures/generate_fixture.py --clone django

# Note Python stdlib path for benchmarking
python tests/fixtures/generate_fixture.py --stdlib
```

## Structure

- `generate_fixture.py` – Script to create/clone fixtures
- `data/` – Generated fixtures (gitignored)
  - `synthetic/` – Synthetic project with random imports
  - `django/` – Cloned Django repo
  - `stdlib` – File noting stdlib Lib path

## Notes

- Fixtures under `data/` are gitignored to avoid bloating the repo.
- Benchmark tests should skip gracefully if fixtures are missing.
