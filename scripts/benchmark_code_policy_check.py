#!/usr/bin/env python3
"""Benchmark harness for the code_policy_check policy engine.

This benchmarks the in-process engine (`CodePolicyChecker.check_files`) rather
than the MCP server wrapper, so results are stable and reproducible without
licensing setup.

Usage:
  python scripts/benchmark_code_policy_check.py --tier community --files 100 --iterations 5

Outputs a single JSON blob to stdout.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import random
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from code_scalpel.policy_engine.code_policy_check import CodePolicyChecker


@dataclass(frozen=True)
class BenchmarkResult:
    tier: str
    requested_files: int
    iterations: int
    seconds: list[float]
    min_s: float
    avg_s: float
    max_s: float
    python: str
    platform: str
    cpu: str


def _cpu_model() -> str:
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.exists():
        try:
            for line in cpuinfo.read_text(errors="ignore").splitlines():
                if line.lower().startswith("model name"):
                    return line.split(":", 1)[1].strip()
        except Exception:
            pass
    return platform.processor() or "unknown"


def _write_synthetic_files(root: Path, count: int, seed: int) -> None:
    rng = random.Random(seed)

    # Mix of content to exercise AST parsing + regex patterns.
    templates = [
        """def ok_{i}():\n    return 1\n""",
        """def bare_except_{i}():\n    try:\n        1/0\n    except:\n        return 0\n""",
        """def mutable_default_{i}(items=[]):\n    items.append(1)\n    return items\n""",
        """import hashlib\n\ndef weak_hash_{i}(data: bytes):\n    return hashlib.md5(data).hexdigest()\n""",
        """import subprocess\n\ndef shell_true_{i}(cmd):\n    return subprocess.run(cmd, shell=True)\n""",
    ]

    root.mkdir(parents=True, exist_ok=True)
    for idx in range(count):
        content = rng.choice(templates).format(i=idx)
        (root / f"bench_{idx:05d}.py").write_text(content, encoding="utf-8")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Benchmark CodePolicyChecker.check_files")
    parser.add_argument("--tier", choices=["community", "pro", "enterprise"], required=True)
    parser.add_argument("--files", type=int, default=100, help="Number of synthetic files to generate")
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--seed", type=int, default=1337)

    args = parser.parse_args(argv)

    requested_files = max(1, args.files)
    iterations = max(1, args.iterations)

    with tempfile.TemporaryDirectory(prefix="code_policy_check_bench_") as tmp:
        root = Path(tmp)
        project = root / "project"
        _write_synthetic_files(project, requested_files, seed=args.seed)

        checker = CodePolicyChecker(tier=args.tier)

        seconds: list[float] = []
        for _ in range(iterations):
            start = time.perf_counter()
            _ = checker.check_files(paths=[str(project)])
            seconds.append(time.perf_counter() - start)

    min_s = min(seconds)
    max_s = max(seconds)
    avg_s = sum(seconds) / len(seconds)

    result = BenchmarkResult(
        tier=args.tier,
        requested_files=requested_files,
        iterations=iterations,
        seconds=seconds,
        min_s=min_s,
        avg_s=avg_s,
        max_s=max_s,
        python=sys.version.split()[0],
        platform=f"{platform.system()} {platform.release()}",
        cpu=_cpu_model(),
    )

    json.dump(asdict(result), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write(os.linesep)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
