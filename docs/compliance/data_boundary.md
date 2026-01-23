# Data Boundary and Telemetry (v1.5.4)

- Processing model: all MCP tool operations run locally; code and analysis artifacts stay on host unless a client explicitly exports them.
- Network use: outbound network only for dependency scans (OSV/pip-audit) when invoked, and optional Sigstore/Cosign verification if configured.
- Telemetry: none collected or sent by default. Any future telemetry must be opt-in and documented.
- Sensitive data: users should avoid supplying secrets to analysis; secret detection is best-effort and does not exfiltrate content.
- Storage: release artifacts and evidence remain under `release_artifacts/`; no cloud uploads are performed by tools.
