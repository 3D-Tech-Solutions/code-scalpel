<!-- [20251221_DOCS] README claims → demo scripts + evidence capture plan (v1.0 fork readiness) -->

# README Claims → Demo + Evidence Plan (v1.0)

This document maps **each concrete claim in the public README** to a **short, recordable demo** plus a recommended **evidence artifact** (terminal output, JSON, logs) suitable for a Ninja Warrior evidence repo.

## Evidence capture conventions

- Prefer **copy/pasteable commands** and deterministic inputs.
- Save evidence as **raw outputs** (stdout/stderr), plus a short `README.md` per demo describing what was run and what “pass” looks like.
- If a claim includes a number (tests passed, tool count, LOC/sec, speedups), record:
  - the exact command used
  - timestamp + version string
  - environment (OS/Python) if relevant
  - raw output

Suggested evidence layout (adapt for Ninja Warrior repo):

```
evidence/readme_claims/
  01_install_and_health/
  02_mcp_tools_inventory/
  03_surgical_extractor/
  04_token_efficiency/
  05_security_scan/
  06_cross_file_security/
  07_symbolic_and_tests/
  08_dependency_scan/
  09_polyglot/
  10_performance_cache/
```

---

## Claim set A — Installability + basic UX

### Claim: “pip install works” / “uvx recommended” / “easy to run”

**Demo:** clean install + `--help` smoke

- Commands (record terminal):
  - `python -m venv .venv && source .venv/bin/activate`
  - `pip install -U pip`
  - `pip install code-scalpel`
  - `code-scalpel --help`
  - `uvx code-scalpel --help` (if demonstrating uv)

**Evidence:**
- `evidence/readme_claims/01_install_and_health/install_help.txt`

### Claim: “init creates .code-scalpel/ governance configs”

**Demo:** run init in a scratch repo and show created files

- Commands:
  - `mkdir -p demo_project && cd demo_project`
  - `code-scalpel init`
  - `find .code-scalpel -maxdepth 1 -type f -print`

**Evidence:**
- `evidence/readme_claims/01_install_and_health/init_tree.txt`
- Optional: `evidence/readme_claims/01_install_and_health/init_config_samples/` (copy of generated files)

---

## Claim set B — MCP server (health, transports, tool inventory)

### Claim: “Supports stdio + HTTP (+ Docker)”

**Demo:** start stdio server (smoke) + start HTTP server + hit health endpoint

- Commands:
  - `code-scalpel mcp --http --port 8593`
  - In another terminal: `curl http://localhost:8594/health`

**Evidence:**
- `evidence/readme_claims/01_install_and_health/health_endpoint.txt`

### Claim: “MCP tools count is N” (README currently lists 19)

**Demo:** capture server tool inventory output

- Preferred approach:
  - Use the tool inventory JSON produced by the server/docs process (whatever is authoritative in your workflow).

**Evidence:**
- `evidence/readme_claims/02_mcp_tools_inventory/tools_inventory.json`

**Notes:**
- If README claims a specific number, update the README to match the inventory you captured (don’t adjust the evidence to fit the README).

---

## Claim set C — Surgical Extractor enhancements (token efficiency + metadata)

README claims include: token counting, rich metadata, `to_prompt()`, `trim_to_budget()`, decorator extraction, `find_callers()`, caching speedup.

### Demo: Extract a function with metadata + prompt formatting

- Use a small target file (or reuse an existing example):
  - `examples/surgical_extractor_enhanced_example.py` (if you want an existing script)
  - or create a small `demo_app.py` with 2–3 functions and a decorator

- Minimal Python snippet (record output):

```python
import time
from code_scalpel.surgical_extractor import SurgicalExtractor

code = """
import functools

def dec(fn):
    @functools.wraps(fn)
    def w(*a, **k):
        return fn(*a, **k)
    return w

@dec
async def process_payment(x: int) -> int:
    """Process payment."""
    return x + 1

def caller():
    return process_payment(1)
"""

ex = SurgicalExtractor(code)
result = ex.get_function_with_context("process_payment")
print(result.to_prompt("Add error handling"))
print("token_estimate=", result.token_estimate)
print("decorators=", result.decorators)
print("is_async=", result.is_async)
print("callers=", ex.find_callers("process_payment"))
print("trimmed_tokens=", result.trim_to_budget(max_tokens=50).token_estimate)
```

**Evidence:**
- `evidence/readme_claims/03_surgical_extractor/metadata_prompt_demo.txt`

### Demo: Caching speedup claim (README says “2.8x faster with LRU cache”)

**Demo:** micro-benchmark showing cache miss vs hit

- Use your existing caching performance snippet (record output) and save:

**Evidence:**
- `evidence/readme_claims/10_performance_cache/surgical_extractor_cache_benchmark.txt`

**Notes:**
- The number is environment-dependent; treat your captured number as authoritative evidence.

---

## Claim set D — Token efficiency (“99% token reduction”)

### Demo: Full file tokens vs extracted slice tokens

**Demo:** measure estimated tokens for:
- full file content
- a single extracted function + minimal dependencies

**Approach:**
- Choose a file that is large enough to show a meaningful reduction.
- Record:
  - “full file token estimate”
  - “extracted slice token estimate”
  - computed reduction percentage

**Evidence:**
- `evidence/readme_claims/04_token_efficiency/token_reduction_report.txt`

---

## Claim set E — Security scanning (“17+ vuln types”, CWE mapping, secrets)

### Demo: SQL injection taint flow (Python)

- Command:
  - `code-scalpel scan evidence/demos/vibe_check.py`

**Evidence:**
- `evidence/readme_claims/05_security_scan/vibe_check_scan.txt`

### Demo: Multi-vulnerability app scan (FastAPI / Django)

- Commands:
  - `code-scalpel scan evidence/demos/real_world/fastapi_app.py`
  - `code-scalpel scan evidence/demos/real_world/django_views.py`

**Evidence:**
- `evidence/readme_claims/05_security_scan/fastapi_app_scan.txt`
- `evidence/readme_claims/05_security_scan/django_views_scan.txt`

### Demo: Secrets detection

If the public README references a file like `demos/config.py`, ensure the demo file exists in the evidence repo. Otherwise, use an existing sample or a minimal `secrets_demo.py` containing test-only fake keys.

**Evidence:**
- `evidence/readme_claims/05_security_scan/secrets_scan.txt`

---

## Claim set F — Cross-file security analysis

### Demo: Cross-file taint tracking (Python)

**Demo:** pick a small multi-file mini-app where input in one file reaches a sink in another.

- Command:
  - `code-scalpel cross-file-security-scan /path/to/project` (or the exact CLI/tool invocation you use)

**Evidence:**
- `evidence/readme_claims/06_cross_file_security/cross_file_security_scan.json`

**Notes:**
- If you run this via MCP tool instead of CLI, capture the JSON response payload as evidence.

---

## Claim set G — Symbolic execution + test generation + refactor safety

### Demo: Symbolic execution finds all paths

- Command:
  - `code-scalpel analyze evidence/demos/test_gen_scenario.py --json`

**Evidence:**
- `evidence/readme_claims/07_symbolic_and_tests/symbolic_paths.json`

### Demo: Unit test generation

- Demo method:
  - Use the MCP tool or the direct API to generate pytest/unittest from the scenario function.

**Evidence:**
- `evidence/readme_claims/07_symbolic_and_tests/generated_tests.py`
- `evidence/readme_claims/07_symbolic_and_tests/generated_tests_run.txt`

### Demo: Safe refactor verification

- If you have a refactor demo file, run it and capture results.

**Evidence:**
- `evidence/readme_claims/07_symbolic_and_tests/simulate_refactor_demo.txt`

---

## Claim set H — Dependency scanning

### Demo: dependency vulnerability scan

- Run whatever dependency scanner is canonical for the release (OSV / pip-audit / internal tool) and store raw output.

**Evidence:**
- `evidence/readme_claims/08_dependency_scan/dependency_scan.json`

---

## Claim set I — Polyglot / multi-language analysis

README claims list 4 languages (Python, JavaScript, TypeScript, Java). The repo demo suite currently includes Java + JSX + Python; for TypeScript, use a minimal scratch file.

### Demo: Java call graph / analysis

- Command:
  - `code-scalpel analyze evidence/demos/enterprise/AuthController.java --json`

**Evidence:**
- `evidence/readme_claims/09_polyglot/java_analyze.json`

### Demo: JavaScript/React (JSX) analysis

- Command:
  - `code-scalpel analyze evidence/demos/real_world/UserDashboard.jsx --json`

**Evidence:**
- `evidence/readme_claims/09_polyglot/jsx_analyze.json`

### Demo: TypeScript analysis (scratch)

Create `TypeScriptDemo.ts` with a small function and run analysis.

**Evidence:**
- `evidence/readme_claims/09_polyglot/typescript_analyze.json`

---

## Claim set J — Performance and caching

README includes claims like “200x cache speedup” and mentions Z3 timeout.

### Demo: Cache speedup on repeated project analysis

- Run the same analysis twice over the same project and compare timings.
- Record the exact command + timings.

**Evidence:**
- `evidence/readme_claims/10_performance_cache/project_cache_benchmark.txt`

### Demo: Z3 timeout prevents hangs

- Create a small snippet that would otherwise branch-explode and show:
  - it returns within the configured timeout
  - it reports partial results / timeout cleanly

**Evidence:**
- `evidence/readme_claims/10_performance_cache/z3_timeout_demo.txt`

---

## “Already exists” demos you can reuse

The repo already contains an evidence demo suite with runnable scenarios. If you want a fast start, mirror the structure and reuse the commands:
- `evidence/demos/README.md`
