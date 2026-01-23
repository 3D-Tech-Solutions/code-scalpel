# Local Release Pipeline

This directory contains tools to run the full release pipeline locally, ensuring release readiness without waiting for remote CI.

## Option 1: The Quick Python Orchestrator (Recommended)

Requires Python 3.10+. This script runs all checks (Lint, Type, Security, Test, Build) sequentially and outputs artifacts to `release_artifacts/local_build/`.

```bash
python local_pipeline/pipeline.py
```

## Option 2: Local Jenkins

If you prefer a full CI environment with history and UI:

1.  Start Jenkins:
    ```bash
    cd local_pipeline
    docker-compose up -d
    ```
2.  Open http://localhost:8080
3.  Create a "Pipeline" job.
4.  In the Pipeline definition, choose "Pipeline script from SCM" -> Git -> Repository URL (point to your local path `file:///mnt/k/backup/Develop/code-scalpel/.git` or just allow it to read the mapped volume).
5.  Or simply paste the content of `Jenkinsfile` into the "Pipeline Script" box.

## Artifacts

Both methods produce:
- `dist/*.whl` and `dist/*.tar.gz`
- Security scan reports
- Test results
