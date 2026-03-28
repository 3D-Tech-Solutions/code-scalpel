"""Dashboard service for Code Scalpel telemetry.

Runs a FastAPI server alongside the MCP server to display telemetry events in a web UI.
Provides WebSocket endpoint for live event streaming and HTTP endpoint for fetching recent events.
"""

from __future__ import annotations

import asyncio
import json
import logging
import socket
import threading
from typing import Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import HTMLResponse
from uvicorn import Server, Config

logger = logging.getLogger(__name__)

# Store connected WebSocket clients
_WEBSOCKET_CLIENTS: set = set()


def get_available_port(start_port: int = 7654) -> int:
    """Find an available port starting from start_port.

    Args:
        start_port: Port to start searching from

    Returns:
        First available port found
    """
    port = start_port
    while port < 65535:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                s.close()
                return port
        except OSError:
            port += 1
    raise RuntimeError(f"No available port found starting from {start_port}")


def create_app() -> tuple[FastAPI, int]:
    """Create and configure the FastAPI dashboard app.

    Returns:
        Tuple of (app, port) where port is the assigned port number
    """
    app = FastAPI(title="Code Scalpel Dashboard")
    port = get_available_port()

    @app.get("/", response_class=HTMLResponse)
    async def serve_dashboard() -> str:
        """Serve the dashboard HTML UI."""
        return get_dashboard_html()

    @app.get("/api/events")
    async def get_events() -> dict[str, Any]:
        """Get recent telemetry events."""
        from code_scalpel import telemetry

        return {
            "events": telemetry.get_recent_events(limit=50),
            "stats": telemetry.get_event_stats(),
        }

    @app.get("/api/license")
    async def get_license_status() -> dict[str, Any]:
        """Get current license tier and status.

        Returns:
            License status from local JWT validation, with optional remote verification
            if CODE_SCALPEL_LICENSE_VERIFIER_URL is configured.
        """
        from code_scalpel.mcp.server import CURRENT_TIER
        from code_scalpel.licensing.jwt_validator import JWTLicenseValidator

        try:
            validator = JWTLicenseValidator()
            license_data = validator.validate()
            license_file = validator.find_license_file()

            result = {
                "current_tier": CURRENT_TIER,
                "is_valid": license_data.is_valid,
                "license_file": str(license_file) if license_file else None,
                "is_expired": getattr(license_data, "is_expired", False),
                "error_message": license_data.error_message,
            }

            # If remote verifier is configured, also include its decision
            try:
                from code_scalpel.licensing.remote_verifier import (
                    remote_verifier_configured,
                    authorize_token,
                )

                if remote_verifier_configured():
                    token = validator.load_license_token()
                    if token:
                        decision = authorize_token(token)
                        result["remote_verified"] = True
                        result["remote_allowed"] = decision.allowed
                        result["remote_reason"] = decision.reason
                        if decision.entitlements:
                            result["remote_tier"] = decision.entitlements.tier
                    else:
                        result["remote_verified"] = False
                        result["remote_reason"] = "No token found"
                else:
                    result["remote_verified"] = False
            except ImportError:
                # Remote verifier not available
                pass
            except Exception as e:
                logger.warning(f"Remote verification failed: {e}")
                result["remote_verified"] = False
                result["remote_error"] = str(e)

            return result

        except Exception as e:
            logger.error(f"License status check failed: {e}", exc_info=True)
            return {
                "current_tier": "community",
                "is_valid": False,
                "license_file": None,
                "is_expired": False,
                "error_message": f"License check error: {str(e)}",
            }

    @app.post("/api/license/upload")
    async def upload_license(file: UploadFile = File(None)) -> dict[str, Any]:
        """Upload and save a license file.

        License files are saved to ~/.code-scalpel/license/license.jwt
        Server restart may be required for changes to take effect.
        """
        from pathlib import Path
        from code_scalpel.licensing.jwt_validator import JWTLicenseValidator

        if not file:
            return {"success": False, "message": "No file provided"}

        try:
            # Read the uploaded file
            content = await file.read()

            # Validate it's a valid JWT
            validator = JWTLicenseValidator()

            # Save to user's .code-scalpel directory
            scalpel_home = Path.home() / ".code-scalpel" / "license"
            scalpel_home.mkdir(parents=True, exist_ok=True)
            license_path = scalpel_home / "license.jwt"

            license_path.write_bytes(content)

            # Validate the saved license
            license_data = validator.validate()

            return {
                "success": True,
                "message": f"License saved to {license_path}",
                "saved_path": str(license_path),
                "is_valid": license_data.is_valid,
                "tier": getattr(license_data, "tier", "unknown"),
                "note": "Server restart may be required for changes to take effect",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to save license: {str(e)}",
            }

    @app.get("/api/audit/events")
    async def get_audit_events(
        limit: int = 100,
        offset: int = 0,
        tool_name: str | None = None,
        request_id: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """Get audit log events with optional filtering.

        Query parameters:
        - limit: Max events to return (default: 100)
        - offset: Pagination offset (default: 0)
        - tool_name: Filter by tool name
        - request_id: Filter by request ID (correlates multiple calls)
        - status: Filter by status (success/failure/timeout)
        """
        from code_scalpel import telemetry

        try:
            audit_log = telemetry._AUDIT_LOG
            if not audit_log:
                return {
                    "error": "Audit log not initialized",
                    "events": [],
                    "stats": {},
                }

            events = audit_log.get_events(
                limit=limit,
                offset=offset,
                tool_name=tool_name,
                request_id=request_id,
                status=status,
            )

            stats = audit_log.get_stats()

            return {
                "events": events,
                "stats": stats,
                "pagination": {"limit": limit, "offset": offset},
                "filters": {
                    "tool_name": tool_name,
                    "request_id": request_id,
                    "status": status,
                },
            }
        except Exception as e:
            logger.error(f"Error querying audit log: {e}")
            return {
                "error": str(e),
                "events": [],
                "stats": {},
            }

    @app.get("/api/audit/call-chain")
    async def get_call_chain(request_id: str) -> dict[str, Any]:
        """Get all calls made during a single request.

        This correlates all tool calls that happened as part of a single MCP request.

        Query parameters:
        - request_id: The request ID to query
        """
        from code_scalpel import telemetry

        try:
            audit_log = telemetry._AUDIT_LOG
            if not audit_log:
                return {"error": "Audit log not initialized", "calls": []}

            calls = audit_log.get_events(
                limit=999999,
                request_id=request_id,
            )

            return {
                "request_id": request_id,
                "call_count": len(calls),
                "calls": calls,
            }
        except Exception as e:
            logger.error(f"Error fetching call chain: {e}")
            return {"error": str(e), "calls": []}

    @app.get("/api/audit/status")
    async def get_audit_status() -> dict[str, Any]:
        """Get audit log status and encryption info."""
        from code_scalpel import telemetry

        try:
            audit_log = telemetry._AUDIT_LOG
            if not audit_log:
                return {
                    "status": "not_initialized",
                    "encryption": None,
                }

            status = audit_log.get_encryption_status()
            stats = audit_log.get_stats()

            return {
                "status": "active",
                "encryption": {
                    "enabled": status["enabled"],
                    "has_key": status["has_key"],
                    "note": "Key exists only in memory during server runtime",
                },
                "database": {
                    "path": status["db_path"],
                    "session_id": status["session_id"],
                },
                "stats": stats,
            }
        except Exception as e:
            logger.error(f"Error getting audit status: {e}")
            return {"error": str(e), "status": "error"}

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        """WebSocket endpoint for live event streaming."""
        await websocket.accept()
        _WEBSOCKET_CLIENTS.add(websocket)
        try:
            while True:
                # Keep connection alive, listen for ping/pong
                await websocket.receive_text()
        except WebSocketDisconnect:
            _WEBSOCKET_CLIENTS.discard(websocket)
        except Exception as e:
            logger.warning(f"WebSocket error: {e}")
            _WEBSOCKET_CLIENTS.discard(websocket)

    return app, port


async def broadcast_event(event: dict[str, Any]) -> None:
    """Broadcast a telemetry event to all connected WebSocket clients."""
    if not _WEBSOCKET_CLIENTS:
        return

    message = json.dumps({"type": "tool_event", "data": event})
    disconnected = set()

    for websocket in _WEBSOCKET_CLIENTS:
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.debug(f"Failed to send to WebSocket: {e}")
            disconnected.add(websocket)

    # Clean up disconnected clients
    for ws in disconnected:
        _WEBSOCKET_CLIENTS.discard(ws)


def get_dashboard_html() -> str:
    """Get the HTML for the dashboard UI."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Code Scalpel Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }

        header {
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        header h1 {
            color: #667eea;
            margin-bottom: 10px;
            font-size: 28px;
        }

        header p {
            color: #666;
            font-size: 14px;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }

        .stat-card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .stat-label {
            font-size: 12px;
            color: #999;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }

        .stat-value {
            font-size: 32px;
            font-weight: bold;
            color: #667eea;
        }

        .events-container {
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            overflow: hidden;
        }

        .events-header {
            background: #f8f9fa;
            padding: 20px;
            border-bottom: 1px solid #e0e0e0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .events-header h2 {
            font-size: 18px;
            color: #333;
        }

        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
        }

        .status-connected {
            background: #d4edda;
            color: #155724;
        }

        .status-disconnected {
            background: #f8d7da;
            color: #721c24;
        }

        .events-list {
            max-height: 600px;
            overflow-y: auto;
        }

        .event-item {
            padding: 15px 20px;
            border-bottom: 1px solid #e0e0e0;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            transition: background-color 0.2s;
        }

        .event-item:hover {
            background-color: #f8f9fa;
        }

        .event-info {
            flex: 1;
        }

        .event-tool {
            font-weight: 600;
            color: #333;
            font-size: 14px;
            margin-bottom: 4px;
        }

        .event-details {
            font-size: 12px;
            color: #999;
            display: flex;
            gap: 15px;
            margin-top: 4px;
        }

        .event-status {
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 11px;
            font-weight: 600;
        }

        .status-success {
            background: #d4edda;
            color: #155724;
        }

        .status-failure {
            background: #f8d7da;
            color: #721c24;
        }

        .event-meta {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            gap: 8px;
        }

        .event-tier {
            font-size: 11px;
            color: #666;
            background: #f0f0f0;
            padding: 2px 8px;
            border-radius: 3px;
        }

        .event-duration {
            font-size: 12px;
            font-weight: 600;
            color: #667eea;
        }

        .empty-state {
            padding: 40px 20px;
            text-align: center;
            color: #999;
        }

        .empty-state-icon {
            font-size: 48px;
            margin-bottom: 10px;
            opacity: 0.5;
        }

        .tool-tags {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }

        .tag {
            background: #f0f0f0;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 11px;
            color: #666;
        }

        .license-panel {
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-left: 4px solid #667eea;
        }

        .license-panel.community {
            border-left-color: #ffc107;
            background: linear-gradient(to right, #fffbf0 0%, white 100%);
        }

        .license-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }

        .license-header h2 {
            font-size: 18px;
            color: #333;
            margin: 0;
        }

        .tier-badge {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 13px;
        }

        .tier-community {
            background: #fff3cd;
            color: #856404;
        }

        .tier-pro {
            background: #d1ecf1;
            color: #0c5460;
        }

        .tier-enterprise {
            background: #d4edda;
            color: #155724;
        }

        .license-status {
            font-size: 14px;
            color: #666;
            margin-bottom: 15px;
        }

        .license-status.invalid {
            color: #721c24;
        }

        .license-status.valid {
            color: #155724;
        }

        .upgrade-section {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            border: 1px dashed #dee2e6;
        }

        .upgrade-section h3 {
            font-size: 14px;
            font-weight: 600;
            color: #333;
            margin: 0 0 10px 0;
        }

        .file-upload-area {
            border: 2px dashed #667eea;
            border-radius: 6px;
            padding: 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
            margin: 10px 0;
        }

        .file-upload-area:hover {
            background: #f0f4ff;
            border-color: #764ba2;
        }

        .file-upload-area.dragover {
            background: #e8f1ff;
            border-color: #764ba2;
        }

        .file-upload-area input[type="file"] {
            display: none;
        }

        .upload-icon {
            font-size: 32px;
            margin-bottom: 10px;
        }

        .upload-text {
            color: #666;
            font-size: 14px;
        }

        .upload-subtext {
            color: #999;
            font-size: 12px;
            margin-top: 5px;
        }

        .upload-button {
            background: #667eea;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-weight: 600;
            font-size: 13px;
            margin-top: 10px;
            transition: background 0.3s;
        }

        .upload-button:hover {
            background: #764ba2;
        }

        .upload-message {
            margin-top: 10px;
            padding: 10px;
            border-radius: 4px;
            font-size: 13px;
            display: none;
        }

        .upload-message.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
            display: block;
        }

        .upload-message.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
            display: block;
        }

        .license-instructions {
            margin-top: 15px;
            font-size: 13px;
            color: #666;
            line-height: 1.6;
        }

        .license-instructions ol {
            margin: 10px 0 0 20px;
        }

        .license-instructions li {
            margin: 5px 0;
        }

        .event-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            width: 100%;
        }

        .event-details-panel {
            background: #f5f5f5;
            border-top: 1px solid #ddd;
            margin-top: 5px;
            padding: 15px;
            border-radius: 0 0 4px 4px;
            font-family: 'Monaco', 'Courier New', monospace;
        }

        .event-details-panel pre {
            background: #fff;
            padding: 10px;
            border-radius: 4px;
            border-left: 3px solid #007bff;
            overflow-x: auto;
            font-size: 12px;
            margin: 0 0 15px 0;
            max-height: 300px;
            overflow-y: auto;
        }

        .event-details-panel > div {
            margin-bottom: 15px;
        }

        .event-details-panel > div > div:first-child {
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
            font-size: 13px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 Code Scalpel Dashboard</h1>
            <p>Real-time telemetry for MCP tool calls</p>
        </header>

        <!-- License Panel -->
        <div class="license-panel" id="license-panel" style="display: none;">
            <div class="license-header">
                <h2>📜 License & Tier</h2>
                <span class="tier-badge" id="tier-badge">Community</span>
            </div>
            <div class="license-status" id="license-status">
                Loading license info...
            </div>
            <div class="license-status" id="remote-status" style="display: none; margin-top: 10px; padding: 10px; border-left: 3px solid #007bff;">
                <div id="remote-verification-badge" style="display: inline-block; font-weight: bold; margin-right: 10px;"></div>
                <div id="remote-details" style="font-size: 12px; color: #555; margin-top: 5px;"></div>
            </div>
            <div id="upgrade-prompt" style="display: none;">
                <div class="upgrade-section">
                    <h3>🚀 Upgrade Your Tier</h3>
                    <p style="margin: 0 0 15px 0; color: #666; font-size: 13px;">
                        Unlock advanced features (Pro/Enterprise) by uploading your license.
                    </p>

                    <div class="file-upload-area" id="upload-area">
                        <div class="upload-icon">📁</div>
                        <div class="upload-text">Click to select or drag your license.jwt file</div>
                        <div class="upload-subtext">Your license file enables Pro and Enterprise features</div>
                        <input type="file" id="license-file" accept=".jwt" />
                        <button class="upload-button" onclick="document.getElementById('license-file').click()">
                            Choose File
                        </button>
                    </div>
                    <div id="upload-message" class="upload-message"></div>

                    <div class="license-instructions">
                        <strong>Don't have a license?</strong>
                        <ol>
                            <li>Visit <a href="https://code-scalpel.dev" target="_blank">code-scalpel.dev</a></li>
                            <li>Purchase a Pro or Enterprise license</li>
                            <li>Download your license.jwt file</li>
                            <li>Upload it here using the file picker above</li>
                            <li>Restart the MCP server to apply the new tier</li>
                        </ol>
                    </div>

                    <div class="license-instructions" style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #ddd;">
                        <strong>🔧 License File Location (Alternative Methods)</strong>
                        <p style="margin: 10px 0 5px 0; font-size: 12px; color: #666;">
                            If upload doesn't work, you can place your <code style="background: #f0f0f0; padding: 2px 4px;">license.jwt</code> file at:
                        </p>
                        <ul style="margin: 5px 0; font-size: 12px; color: #555;">
                            <li><code style="background: #f0f0f0; padding: 2px 4px;">~/.code-scalpel/license/license.jwt</code> (recommended)</li>
                            <li><code style="background: #f0f0f0; padding: 2px 4px;">.code-scalpel/license/license.jwt</code> (project root)</li>
                            <li>Set <code style="background: #f0f0f0; padding: 2px 4px;">CODE_SCALPEL_LICENSE_PATH</code> environment variable to custom location</li>
                        </ul>
                        <p style="margin: 10px 0 0 0; font-size: 11px; color: #999;">
                            After placing the file, restart the MCP server for changes to take effect.
                        </p>
                    </div>
                </div>
            </div>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Calls</div>
                <div class="stat-value" id="stat-total">0</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Success Rate</div>
                <div class="stat-value" id="stat-success">0%</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Avg Duration</div>
                <div class="stat-value" id="stat-duration">0ms</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Connection</div>
                <div class="status-badge status-disconnected" id="status-badge">Disconnected</div>
            </div>
        </div>

        <div class="events-container">
            <div class="events-header">
                <h2>Recent Tool Calls</h2>
            </div>
            <div class="events-list" id="events-list">
                <div class="empty-state">
                    <div class="empty-state-icon">📭</div>
                    <p>Waiting for tool calls...</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        let ws = null;
        let events = [];

        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

            ws.onopen = () => {
                console.log('WebSocket connected');
                updateStatusBadge(true);
                // Ping every 30 seconds to keep connection alive
                setInterval(() => {
                    if (ws && ws.readyState === WebSocket.OPEN) {
                        ws.send('ping');
                    }
                }, 30000);
            };

            ws.onmessage = (event) => {
                try {
                    const msg = JSON.parse(event.data);
                    if (msg.type === 'tool_event') {
                        events.unshift(msg.data);
                        if (events.length > 50) {
                            events.pop();
                        }
                        renderEvents();
                        updateStats();
                    }
                } catch (e) {
                    console.error('Failed to parse message:', e);
                }
            };

            ws.onerror = (event) => {
                console.error('WebSocket error:', event);
                updateStatusBadge(false);
            };

            ws.onclose = () => {
                console.log('WebSocket disconnected');
                updateStatusBadge(false);
                setTimeout(connectWebSocket, 3000);
            };
        }

        function updateStatusBadge(connected) {
            const badge = document.getElementById('status-badge');
            if (connected) {
                badge.textContent = 'Connected';
                badge.className = 'status-badge status-connected';
            } else {
                badge.textContent = 'Disconnected';
                badge.className = 'status-badge status-disconnected';
            }
        }

        function updateStats() {
            const total = events.length;
            const success = events.filter(e => e.status === 'success').length;
            const successRate = total > 0 ? Math.round((success / total) * 100) : 0;
            const durations = events.filter(e => e.duration_ms > 0).map(e => e.duration_ms);
            const avgDuration = durations.length > 0
                ? Math.round(durations.reduce((a, b) => a + b, 0) / durations.length)
                : 0;

            document.getElementById('stat-total').textContent = total;
            document.getElementById('stat-success').textContent = successRate + '%';
            document.getElementById('stat-duration').textContent = avgDuration + 'ms';
        }

        function formatTime(timestamp) {
            const date = new Date(timestamp * 1000);
            return date.toLocaleTimeString();
        }

        function renderEvents() {
            const list = document.getElementById('events-list');

            if (events.length === 0) {
                list.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">📭</div>
                        <p>Waiting for tool calls...</p>
                    </div>
                `;
                return;
            }

            list.innerHTML = events.map((event, index) => `
                <div class="event-item">
                    <div class="event-header" onclick="toggleEventDetails('event-${index}')" style="cursor: pointer;">
                        <div class="event-info">
                            <div class="event-tool">${event.tool_name}</div>
                            <div class="event-details">
                                <span>${formatTime(event.timestamp)}</span>
                                <span class="event-status ${event.status === 'success' ? 'status-success' : 'status-failure'}">
                                    ${event.status.toUpperCase()}
                                </span>
                                ${event.error ? `<span style="color: #721c24;">Error</span>` : ''}
                            </div>
                        </div>
                        <div class="event-meta">
                            <span class="event-tier">Tier: ${event.tier_applied}</span>
                            <span class="event-duration">${event.duration_ms.toFixed(0)}ms</span>
                            <span style="cursor: pointer; margin-left: 10px; font-weight: bold;">▼</span>
                        </div>
                    </div>
                    <div class="event-details-panel" id="event-${index}" style="display: none; padding: 15px; background: #f5f5f5; border-top: 1px solid #ddd; margin-top: 5px;">
                        ${event.input_summary ? `
                            <div style="margin-bottom: 15px;">
                                <div style="font-weight: bold; color: #333; margin-bottom: 5px;">📥 Input</div>
                                <pre style="background: #fff; padding: 10px; border-radius: 4px; border-left: 3px solid #007bff; overflow-x: auto; font-size: 12px; margin: 0;">${JSON.stringify(event.input_summary, null, 2)}</pre>
                            </div>
                        ` : ''}
                        ${event.output_summary ? `
                            <div style="margin-bottom: 15px;">
                                <div style="font-weight: bold; color: #333; margin-bottom: 5px;">📤 Output</div>
                                <pre style="background: #fff; padding: 10px; border-radius: 4px; border-left: 3px solid #28a745; overflow-x: auto; font-size: 12px; margin: 0;">${JSON.stringify(event.output_summary, null, 2)}</pre>
                            </div>
                        ` : ''}
                        ${event.error ? `
                            <div style="margin-bottom: 15px;">
                                <div style="font-weight: bold; color: #721c24; margin-bottom: 5px;">⚠️ Error</div>
                                <pre style="background: #fff; padding: 10px; border-radius: 4px; border-left: 3px solid #dc3545; overflow-x: auto; font-size: 12px; margin: 0; color: #721c24;">${event.error}</pre>
                            </div>
                        ` : ''}
                        <div style="padding-top: 10px; border-top: 1px solid #ddd;">
                            <div style="font-size: 12px; color: #666;">
                                <span>Event ID: ${event.event_id}</span> |
                                <span>Duration: ${event.duration_ms.toFixed(1)}ms</span>
                                ${event.session_id ? `| <span>Session: ${event.session_id}</span>` : ''}
                            </div>
                        </div>
                    </div>
                </div>
            `).join('');
        }

        function toggleEventDetails(eventId) {
            const panel = document.getElementById(eventId);
            if (panel) {
                panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
            }
        }

        async function fetchInitialEvents() {
            try {
                // Fetch from audit log (persistent, with filtering support)
                const response = await fetch('/api/audit/events?limit=100');
                const data = await response.json();

                // Handle both audit log format and fallback to telemetry queue format
                if (data.events) {
                    events = data.events;
                    // Update stats from audit log if available
                    if (data.stats) {
                        document.getElementById('total-events').textContent = data.stats.total_events || 0;
                        document.getElementById('success-rate').textContent =
                            ((data.stats.success_rate || 0) * 100).toFixed(1) + '%';
                    }
                } else if (data.error) {
                    console.warn('Audit log not available:', data.error);
                    // Fallback to telemetry queue if audit log not initialized
                    const fallbackResponse = await fetch('/api/events');
                    const fallbackData = await fallbackResponse.json();
                    events = fallbackData.events || [];
                }

                renderEvents();
                updateStats();
            } catch (e) {
                console.error('Failed to fetch events:', e);
                // Try fallback to ephemeral queue on error
                try {
                    const fallbackResponse = await fetch('/api/events');
                    const fallbackData = await fallbackResponse.json();
                    events = fallbackData.events || [];
                    renderEvents();
                    updateStats();
                } catch (fallbackError) {
                    console.error('Fallback to ephemeral queue also failed:', fallbackError);
                }
            }
        }

        async function loadLicenseStatus() {
            try {
                const response = await fetch('/api/license');
                const data = await response.json();

                const panel = document.getElementById('license-panel');
                const tierBadge = document.getElementById('tier-badge');
                const statusDiv = document.getElementById('license-status');
                const remoteStatusDiv = document.getElementById('remote-status');
                const remoteBadge = document.getElementById('remote-verification-badge');
                const remoteDetails = document.getElementById('remote-details');
                const upgradePrompt = document.getElementById('upgrade-prompt');

                panel.style.display = 'block';

                // Update tier badge
                const tierClass = `tier-${data.current_tier}`;
                tierBadge.textContent = data.current_tier.toUpperCase();
                tierBadge.className = `tier-badge ${tierClass}`;

                // Update panel class
                if (data.current_tier === 'community') {
                    panel.classList.add('community');
                }

                // Update status text
                let statusText = '';
                if (data.is_valid) {
                    statusText = `<strong style="color: #155724;">✓ Valid License</strong> · Tier: ${data.current_tier.toUpperCase()}`;
                    if (data.license_file) {
                        statusText += ` · File: ${data.license_file}`;
                    }
                } else {
                    statusText = `<strong style="color: #721c24;">⚠ No valid license</strong>`;
                    if (data.error_message) {
                        statusText += ` · ${data.error_message}`;
                    }
                }

                statusDiv.innerHTML = statusText;
                statusDiv.className = data.is_valid ? 'license-status valid' : 'license-status invalid';

                // Update remote verification status (if available)
                if (data.remote_verified !== undefined) {
                    remoteStatusDiv.style.display = 'block';

                    // Map remote_reason to badge color and text
                    const reasonColors = {
                        'remote_verified': { color: '#155724', icon: '✓', text: 'Verified with central system' },
                        'cache_fresh': { color: '#004085', icon: '💾', text: 'Cached (still valid)' },
                        'offline_grace': { color: '#856404', icon: '⏱️', text: 'Offline grace period active' },
                        'offline_denied': { color: '#721c24', icon: '✗', text: 'Offline grace expired' },
                        'license_expired': { color: '#721c24', icon: '✗', text: 'License expired' }
                    };

                    const reasonInfo = reasonColors[data.remote_reason] || { color: '#666', icon: '?', text: data.remote_reason || 'Unknown' };
                    remoteBadge.style.color = reasonInfo.color;
                    remoteBadge.textContent = `${reasonInfo.icon} ${reasonInfo.text}`;

                    let detailsText = '';
                    if (data.remote_tier && data.remote_tier !== data.current_tier) {
                        detailsText += `Remote tier: ${data.remote_tier.toUpperCase()} | `;
                    }
                    if (data.remote_allowed === false) {
                        detailsText += 'Status: Not Allowed';
                    } else if (data.remote_allowed === true) {
                        detailsText += 'Status: Allowed';
                    }
                    remoteDetails.textContent = detailsText;
                } else {
                    remoteStatusDiv.style.display = 'none';
                }

                // Show upgrade prompt if community tier
                if (data.current_tier === 'community') {
                    upgradePrompt.style.display = 'block';
                    setupFileUpload();
                }
            } catch (e) {
                console.error('Failed to load license status:', e);
            }
        }

        function setupFileUpload() {
            const uploadArea = document.getElementById('upload-area');
            const fileInput = document.getElementById('license-file');
            const uploadMessage = document.getElementById('upload-message');

            // Drag and drop
            uploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadArea.classList.add('dragover');
            });

            uploadArea.addEventListener('dragleave', () => {
                uploadArea.classList.remove('dragover');
            });

            uploadArea.addEventListener('drop', async (e) => {
                e.preventDefault();
                uploadArea.classList.remove('dragover');

                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    await uploadLicense(files[0]);
                }
            });

            // File input change
            fileInput.addEventListener('change', async (e) => {
                if (e.target.files.length > 0) {
                    await uploadLicense(e.target.files[0]);
                }
            });
        }

        async function uploadLicense(file) {
            const uploadMessage = document.getElementById('upload-message');
            uploadMessage.textContent = 'Uploading license...';
            uploadMessage.className = 'upload-message';

            try {
                const formData = new FormData();
                formData.append('file', file);

                const response = await fetch('/api/license/upload', {
                    method: 'POST',
                    body: formData,
                });

                const result = await response.json();

                if (result.success) {
                    uploadMessage.innerHTML = `<strong>✓ License uploaded successfully!</strong><br/>
                    Saved to: ${result.saved_path}<br/>
                    Tier: ${result.tier}<br/>
                    <em>${result.note}</em>`;
                    uploadMessage.className = 'upload-message success';

                    // Reload license status after a delay
                    setTimeout(() => {
                        loadLicenseStatus();
                    }, 1000);
                } else {
                    uploadMessage.textContent = `✗ ${result.message}`;
                    uploadMessage.className = 'upload-message error';
                }
            } catch (e) {
                uploadMessage.textContent = `✗ Upload failed: ${e.message}`;
                uploadMessage.className = 'upload-message error';
            }
        }

        // Initialize
        loadLicenseStatus();
        fetchInitialEvents();
        connectWebSocket();
    </script>
</body>
</html>
"""


class DashboardServer:
    """Manages the dashboard service lifecycle."""

    def __init__(self, port: Optional[int] = None):
        """Initialize dashboard server.

        Args:
            port: Port to run on (None to auto-select)
        """
        self.app, self.port = create_app()
        self.server: Optional[Server] = None
        self.thread: Optional[threading.Thread] = None
        self._should_stop = False

    def start(self) -> int:
        """Start the dashboard server in a background thread.

        Returns:
            The port the server is running on
        """
        config = Config(
            app=self.app,
            host="127.0.0.1",
            port=self.port,
            log_level="error",
        )
        self.server = Server(config)

        def run_server():
            asyncio.run(self.server.serve())

        self.thread = threading.Thread(target=run_server, daemon=True)
        self.thread.start()

        # Give server time to start
        import time

        time.sleep(0.5)
        logger.info(f"Dashboard server started on http://127.0.0.1:{self.port}")
        return self.port

    def stop(self) -> None:
        """Stop the dashboard server."""
        if self.server:
            self.server.should_exit = True
        if self.thread:
            self.thread.join(timeout=5)

    def get_url(self) -> str:
        """Get the dashboard URL."""
        return f"http://127.0.0.1:{self.port}"


# Global dashboard instance
_dashboard_instance: Optional[DashboardServer] = None


def start_dashboard() -> str:
    """Start the dashboard service globally.

    Returns:
        Dashboard URL
    """
    global _dashboard_instance
    if _dashboard_instance is None:
        _dashboard_instance = DashboardServer()
        _dashboard_instance.start()
        return _dashboard_instance.get_url()
    return _dashboard_instance.get_url()


def stop_dashboard() -> None:
    """Stop the dashboard service globally."""
    global _dashboard_instance
    if _dashboard_instance:
        _dashboard_instance.stop()
        _dashboard_instance = None
