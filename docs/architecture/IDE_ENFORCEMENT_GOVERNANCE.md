# Code Scalpel IDE Enforcement Governance

**Document Status:** Architecture Design
**Version:** 1.0
**Date:** January 2026
**Purpose:** Design for universal enforcement of AI code governance across IDEs

---

## Executive Summary

This document describes the architecture for **mandatory enforcement** of Code Scalpel governance for all file operations in development environments. The goal is to ensure that **no code change escapes audit**—whether made by AI agents, developers, or external tools.

### The Problem

Current Code Scalpel governance only applies when AI agents voluntarily use the MCP server. AI tools (Claude Code, GitHub Copilot, Cursor) can bypass governance by:
- Using native file edit tools
- Running bash commands (`sed`, `echo >`, etc.)
- Direct filesystem access

### The Solution

A multi-layer enforcement architecture that:
1. **IDE Extensions** - Intercept file operations at the editor level
2. **Claude Code Hooks** - Enforce governance for Claude Code specifically
3. **Git Hooks** - Block commits without audit coverage
4. **Filesystem Daemon** - Monitor all file changes as last line of defense

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     ENFORCEMENT LAYERS                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Layer 1: IDE Extension (Proactive)                                  │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  VS Code Extension / JetBrains Plugin                        │    │
│  │  - Intercepts all file save operations                       │    │
│  │  - Validates changes against Code Scalpel                    │    │
│  │  - Blocks non-compliant saves with user notification         │    │
│  │  - Logs all operations to audit trail                        │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              ↓                                       │
│  Layer 2: Claude Code Hooks (AI-Specific)                            │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  PreToolUse / PostToolUse Hooks                              │    │
│  │  - Intercept Edit, Write, Bash tools                         │    │
│  │  - Route file operations through Code Scalpel MCP            │    │
│  │  - Block direct file modifications                           │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              ↓                                       │
│  Layer 3: Git Hooks (Commit-Time)                                    │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  pre-commit Hook                                             │    │
│  │  - Verify audit coverage for all staged changes              │    │
│  │  - Block commits without Code Scalpel audit entries          │    │
│  │  - Require manual override with justification                │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              ↓                                       │
│  Layer 4: Filesystem Daemon (Detective)                              │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  Background Process                                          │    │
│  │  - Monitor file changes via inotify/FSEvents                 │    │
│  │  - Detect changes without audit entries                      │    │
│  │  - Alert or auto-rollback non-compliant changes              │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Layer 1: IDE Extension

### VS Code Extension

**Approach:** Use `workspace.onWillSaveTextDocument` event to intercept saves.

```typescript
// src/extension.ts
import * as vscode from 'vscode';
import { ScalpelClient } from './scalpelClient';

export function activate(context: vscode.ExtensionContext) {
    const scalpelClient = new ScalpelClient();

    // Intercept all file saves
    const saveDisposable = vscode.workspace.onWillSaveTextDocument(
        async (event: vscode.TextDocumentWillSaveEvent) => {
            const document = event.document;

            // Skip non-code files
            if (!isCodeFile(document.uri)) return;

            // Get the changes being saved
            const originalContent = await getOriginalContent(document.uri);
            const newContent = document.getText();

            // Validate through Code Scalpel
            const validation = await scalpelClient.validateChange({
                file: document.uri.fsPath,
                originalContent,
                newContent,
                operator: detectOperator(), // 'human', 'copilot', 'claude', etc.
            });

            if (!validation.approved) {
                // Block the save
                event.waitUntil(
                    Promise.reject(new Error(
                        `Code Scalpel: ${validation.reason}\n` +
                        `Policy: ${validation.violatedPolicy}`
                    ))
                );

                // Show notification
                vscode.window.showErrorMessage(
                    `Save blocked by Code Scalpel: ${validation.reason}`,
                    'View Details', 'Override'
                ).then(selection => {
                    if (selection === 'Override') {
                        requestOverride(document.uri, validation);
                    }
                });
                return;
            }

            // Log to audit trail
            await scalpelClient.logAuditEntry({
                timestamp: new Date().toISOString(),
                operator: validation.operator,
                file: document.uri.fsPath,
                operation: 'save',
                hash: computeHash(newContent),
                validation: validation,
            });
        }
    );

    context.subscriptions.push(saveDisposable);
}

function detectOperator(): string {
    // Heuristics to detect if change came from AI
    // - Check if Copilot extension is active and recently suggested
    // - Check clipboard for AI-generated patterns
    // - Check if change matches recent AI completion
    return 'human'; // Default
}

function isCodeFile(uri: vscode.Uri): boolean {
    const codeExtensions = ['.py', '.js', '.ts', '.java', '.go', '.rs', '.cpp', '.c'];
    return codeExtensions.some(ext => uri.fsPath.endsWith(ext));
}
```

**Key Features:**
- Intercepts ALL file saves in the IDE
- Validates changes through Code Scalpel MCP
- Blocks non-compliant saves with user notification
- Provides override mechanism with justification
- Logs all operations to audit trail

### JetBrains Plugin

**Approach:** Use `VirtualFileListener.beforeContentsChange` to intercept file modifications.

```kotlin
// src/main/kotlin/com/codescalpel/plugin/FileChangeListener.kt
package com.codescalpel.plugin

import com.intellij.openapi.vfs.*
import com.intellij.openapi.vfs.newvfs.BulkFileListener
import com.intellij.openapi.vfs.newvfs.events.*

class ScalpelFileListener : BulkFileListener {

    private val scalpelClient = ScalpelClient()

    override fun before(events: List<VFileEvent>) {
        for (event in events) {
            when (event) {
                is VFileContentChangeEvent -> {
                    val file = event.file
                    if (!isCodeFile(file)) continue

                    val validation = scalpelClient.validateChange(
                        file = file.path,
                        originalContent = String(file.contentsToByteArray()),
                        newContent = event.newContent,
                        operator = detectOperator()
                    )

                    if (!validation.approved) {
                        // Throw exception to block the save
                        throw PolicyViolationException(
                            "Code Scalpel blocked this change: ${validation.reason}"
                        )
                    }

                    // Log to audit trail
                    scalpelClient.logAuditEntry(
                        file = file.path,
                        operation = "save",
                        validation = validation
                    )
                }
            }
        }
    }
}

// Register in plugin.xml
// <applicationListeners>
//   <listener class="com.codescalpel.plugin.ScalpelFileListener"
//             topic="com.intellij.openapi.vfs.newvfs.BulkFileListener"/>
// </applicationListeners>
```

### Extension Configuration

```json
// .code-scalpel/ide-extension.json
{
    "enforcement": {
        "enabled": true,
        "mode": "block",  // "block" | "warn" | "audit-only"
        "override": {
            "allowed": true,
            "requireJustification": true,
            "requireApproval": false,  // Enterprise: require manager approval
            "notifyChannel": "slack://security-alerts"
        }
    },
    "policies": {
        "syntaxValidation": true,
        "securityScan": true,
        "changeBudget": true,
        "customPolicies": true
    },
    "exclusions": {
        "paths": [
            "**/node_modules/**",
            "**/.git/**",
            "**/dist/**"
        ],
        "operators": []  // No operator exclusions by default
    },
    "audit": {
        "logAllSaves": true,
        "logReadOnly": false,
        "destination": ".code-scalpel/audit.jsonl"
    }
}
```

---

## Layer 2: Claude Code Hooks

Claude Code supports hooks that run before/after tool execution. We can use these to enforce governance for Claude Code specifically.

### Hook Configuration

```json
// .claude/settings.json
{
    "hooks": {
        "PreToolUse": [
            {
                "name": "code-scalpel-governance",
                "match": {
                    "tools": ["Edit", "Write", "Bash", "MultiEdit"]
                },
                "command": "code-scalpel hook pre-tool-use",
                "timeout": 10000,
                "onFailure": "block"
            }
        ],
        "PostToolUse": [
            {
                "name": "code-scalpel-audit",
                "match": {
                    "tools": ["Edit", "Write", "Bash", "MultiEdit"]
                },
                "command": "code-scalpel hook post-tool-use",
                "timeout": 5000,
                "onFailure": "warn"
            }
        ]
    }
}
```

### Hook Implementation

```python
# src/code_scalpel/cli/hooks.py
"""Claude Code hooks for governance enforcement."""

import json
import sys
from pathlib import Path
from code_scalpel.governance import GovernanceEngine
from code_scalpel.audit import AuditLogger

def pre_tool_use():
    """Run before a tool is used. Block if policy violated."""
    # Read hook context from stdin
    context = json.load(sys.stdin)

    tool_name = context.get('tool')
    tool_input = context.get('input', {})

    engine = GovernanceEngine()

    # Check if this tool modifies files
    if tool_name in ('Edit', 'Write', 'MultiEdit'):
        file_path = tool_input.get('file_path')
        new_content = tool_input.get('content') or tool_input.get('new_string')

        # Validate the change
        result = engine.validate_change(
            file=file_path,
            content=new_content,
            operator='claude-code'
        )

        if not result.approved:
            # Output rejection to Claude Code
            print(json.dumps({
                "status": "blocked",
                "reason": result.reason,
                "policy": result.violated_policy,
                "suggestion": "Use Code Scalpel MCP tools for governance-compliant modifications"
            }))
            sys.exit(1)

    elif tool_name == 'Bash':
        command = tool_input.get('command', '')

        # Check for file modification commands
        if is_file_modifying_command(command):
            print(json.dumps({
                "status": "blocked",
                "reason": "Direct file modification via bash is not allowed under governance policy",
                "suggestion": "Use Code Scalpel update_symbol or MCP Edit tools instead"
            }))
            sys.exit(1)

    # Allow the operation
    print(json.dumps({"status": "allowed"}))
    sys.exit(0)

def post_tool_use():
    """Run after a tool is used. Log to audit trail."""
    context = json.load(sys.stdin)

    tool_name = context.get('tool')
    tool_input = context.get('input', {})
    tool_output = context.get('output', {})

    logger = AuditLogger()

    # Log the operation
    logger.log({
        "timestamp": datetime.now().isoformat(),
        "operator": "claude-code",
        "tool": tool_name,
        "input": sanitize_input(tool_input),
        "success": tool_output.get('success', True),
        "files_modified": extract_modified_files(tool_name, tool_input),
    })

    print(json.dumps({"status": "logged"}))
    sys.exit(0)

def is_file_modifying_command(command: str) -> bool:
    """Check if bash command modifies files."""
    dangerous_patterns = [
        r'\becho\s+.*>',      # echo redirection
        r'\bcat\s+.*>',       # cat redirection
        r'\bsed\s+-i',        # sed in-place
        r'\bawk\s+.*>',       # awk redirection
        r'\brm\s+',           # file deletion
        r'\bmv\s+',           # file move
        r'\bcp\s+',           # file copy
        r'\btouch\s+',        # file creation
        r'\btruncate\s+',     # file truncation
    ]
    return any(re.search(p, command) for p in dangerous_patterns)
```

### Managed Hooks for Enterprise

For organizations, deploy hooks via managed settings:

```json
// /etc/claude-code/managed-settings.json (Linux)
// C:\ProgramData\claude-code\managed-settings.json (Windows)
{
    "hooks": {
        "PreToolUse": [
            {
                "name": "enterprise-governance",
                "match": { "tools": ["Edit", "Write", "Bash", "MultiEdit"] },
                "command": "/usr/local/bin/code-scalpel hook pre-tool-use",
                "onFailure": "block"
            }
        ]
    },
    "allowManagedHooksOnly": true  // Prevent users from disabling
}
```

---

## Layer 3: Git Hooks

Git hooks provide commit-time enforcement as a safety net.

### pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

set -e

echo "Code Scalpel: Verifying audit coverage..."

# Get list of staged files
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM)

if [ -z "$STAGED_FILES" ]; then
    exit 0
fi

# Check audit coverage for each file
UNCOVERED_FILES=""
for FILE in $STAGED_FILES; do
    # Skip non-code files
    if [[ ! "$FILE" =~ \.(py|js|ts|java|go|rs|cpp|c)$ ]]; then
        continue
    fi

    # Check if file has audit entry for recent changes
    if ! code-scalpel verify-audit-coverage "$FILE"; then
        UNCOVERED_FILES="$UNCOVERED_FILES\n  - $FILE"
    fi
done

if [ -n "$UNCOVERED_FILES" ]; then
    echo ""
    echo "❌ COMMIT BLOCKED: Files modified without Code Scalpel audit trail:"
    echo -e "$UNCOVERED_FILES"
    echo ""
    echo "To fix this:"
    echo "  1. Make changes through Code Scalpel MCP tools, OR"
    echo "  2. Use 'code-scalpel audit-retroactive <file>' to create audit entry, OR"
    echo "  3. Use 'git commit --no-verify' with justification (logged)"
    echo ""

    # Log the blocked commit attempt
    code-scalpel log-blocked-commit "$STAGED_FILES"

    exit 1
fi

echo "✅ All changes have audit coverage"
exit 0
```

### Audit Verification Command

```python
# src/code_scalpel/cli/verify_audit.py
"""Verify audit coverage for file changes."""

import click
from pathlib import Path
from code_scalpel.audit import AuditLog

@click.command()
@click.argument('file_path')
def verify_audit_coverage(file_path: str) -> bool:
    """Check if file changes have corresponding audit entries."""

    audit_log = AuditLog()
    file_path = Path(file_path).resolve()

    # Get file's current hash
    current_hash = compute_file_hash(file_path)

    # Check if there's an audit entry for this hash
    entries = audit_log.get_entries_for_file(str(file_path))

    for entry in entries:
        if entry.get('hash') == current_hash:
            return True

        # Also check if entry covers the current content
        if entry.get('new_content_hash') == current_hash:
            return True

    return False
```

### Install Script

```bash
#!/bin/bash
# scripts/install-git-hooks.sh

REPO_ROOT=$(git rev-parse --show-toplevel)
HOOKS_DIR="$REPO_ROOT/.git/hooks"

echo "Installing Code Scalpel git hooks..."

# Install pre-commit hook
cat > "$HOOKS_DIR/pre-commit" << 'EOF'
#!/bin/bash
# Code Scalpel pre-commit hook
exec code-scalpel git-hook pre-commit "$@"
EOF
chmod +x "$HOOKS_DIR/pre-commit"

# Install commit-msg hook (for audit logging)
cat > "$HOOKS_DIR/commit-msg" << 'EOF'
#!/bin/bash
# Code Scalpel commit-msg hook
exec code-scalpel git-hook commit-msg "$@"
EOF
chmod +x "$HOOKS_DIR/commit-msg"

echo "✅ Git hooks installed"
```

---

## Layer 4: Filesystem Daemon

A background daemon provides the final layer of defense by monitoring all file changes.

### Daemon Architecture

```python
# src/code_scalpel/daemon/watcher.py
"""Filesystem watcher daemon for detecting ungoverned changes."""

import os
import hashlib
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
from code_scalpel.audit import AuditLog
from code_scalpel.notifications import NotificationService

class GovernanceWatcher(FileSystemEventHandler):
    """Watch for file changes and verify audit coverage."""

    def __init__(self, workspace: Path, config: dict):
        self.workspace = workspace
        self.config = config
        self.audit_log = AuditLog(workspace / '.code-scalpel' / 'audit.jsonl')
        self.notifications = NotificationService(config.get('notifications', {}))
        self.file_hashes = {}  # Track file states

        # Initialize file hashes
        self._scan_existing_files()

    def on_modified(self, event):
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Skip non-code files
        if not self._is_code_file(file_path):
            return

        # Skip audit file itself
        if 'audit.jsonl' in str(file_path):
            return

        # Check if this modification has audit coverage
        new_hash = self._compute_hash(file_path)

        if not self._has_audit_coverage(file_path, new_hash):
            self._handle_ungoverned_change(file_path, new_hash)

        # Update tracked hash
        self.file_hashes[str(file_path)] = new_hash

    def _has_audit_coverage(self, file_path: Path, file_hash: str) -> bool:
        """Check if file change has audit entry."""
        entries = self.audit_log.get_recent_entries(
            file=str(file_path),
            within_seconds=5  # Allow 5 second window for audit lag
        )

        for entry in entries:
            if entry.get('hash') == file_hash:
                return True
            if entry.get('new_content_hash') == file_hash:
                return True

        return False

    def _handle_ungoverned_change(self, file_path: Path, file_hash: str):
        """Handle a file change without audit coverage."""
        mode = self.config.get('enforcement', {}).get('mode', 'warn')

        if mode == 'block':
            # Rollback the change
            previous_hash = self.file_hashes.get(str(file_path))
            if previous_hash:
                self._rollback_file(file_path, previous_hash)

            self.notifications.alert(
                level='critical',
                message=f'Blocked ungoverned change to {file_path}',
                file=str(file_path)
            )

        elif mode == 'warn':
            self.notifications.alert(
                level='warning',
                message=f'Ungoverned change detected: {file_path}',
                file=str(file_path)
            )

            # Log the ungoverned change
            self.audit_log.log_ungoverned({
                'file': str(file_path),
                'hash': file_hash,
                'detected_at': datetime.now().isoformat(),
                'action': 'warned'
            })

        else:  # audit-only
            self.audit_log.log_ungoverned({
                'file': str(file_path),
                'hash': file_hash,
                'detected_at': datetime.now().isoformat(),
                'action': 'logged'
            })


def run_daemon(workspace: Path, config: dict):
    """Start the governance watcher daemon."""
    handler = GovernanceWatcher(workspace, config)
    observer = Observer()

    observer.schedule(handler, str(workspace), recursive=True)
    observer.start()

    print(f"Code Scalpel daemon watching: {workspace}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()
```

### Systemd Service (Linux)

```ini
# /etc/systemd/system/code-scalpel-daemon.service
[Unit]
Description=Code Scalpel Governance Daemon
After=network.target

[Service]
Type=simple
User=developer
ExecStart=/usr/local/bin/code-scalpel daemon --workspace /home/developer/project
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### LaunchAgent (macOS)

```xml
<!-- ~/Library/LaunchAgents/com.codescalpel.daemon.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.codescalpel.daemon</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/code-scalpel</string>
        <string>daemon</string>
        <string>--workspace</string>
        <string>/Users/developer/project</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

---

## Integration Points

### Scalpel Client (Shared)

```python
# src/code_scalpel/client.py
"""Client for IDE extensions and hooks to communicate with Code Scalpel."""

import subprocess
import json
from pathlib import Path

class ScalpelClient:
    """Client for Code Scalpel governance operations."""

    def __init__(self, workspace: Path = None):
        self.workspace = workspace or Path.cwd()
        self.mcp_url = self._get_mcp_url()

    def validate_change(
        self,
        file: str,
        original_content: str,
        new_content: str,
        operator: str
    ) -> dict:
        """Validate a file change against governance policies."""

        # Call Code Scalpel MCP server
        result = self._call_mcp('code_policy_check', {
            'file_path': file,
            'content': new_content,
            'original_content': original_content,
            'operator': operator
        })

        if result.get('error'):
            return {
                'approved': False,
                'reason': result['error'],
                'violated_policy': 'system_error'
            }

        # Check syntax validation
        syntax_result = self._call_mcp('analyze_code', {
            'file_path': file,
            'content': new_content,
            'validate_only': True
        })

        if syntax_result.get('syntax_error'):
            return {
                'approved': False,
                'reason': f"Syntax error: {syntax_result['syntax_error']}",
                'violated_policy': 'syntax_validation'
            }

        # Check security scan
        security_result = self._call_mcp('security_scan', {
            'file_path': file,
            'content': new_content
        })

        critical_vulns = [v for v in security_result.get('vulnerabilities', [])
                         if v.get('severity') == 'critical']

        if critical_vulns:
            return {
                'approved': False,
                'reason': f"Critical vulnerability: {critical_vulns[0]['type']}",
                'violated_policy': 'security_scan',
                'vulnerabilities': critical_vulns
            }

        return {
            'approved': True,
            'operator': operator,
            'validations': ['syntax', 'security', 'policy']
        }

    def log_audit_entry(self, entry: dict):
        """Log an entry to the audit trail."""
        audit_file = self.workspace / '.code-scalpel' / 'audit.jsonl'
        audit_file.parent.mkdir(parents=True, exist_ok=True)

        with open(audit_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
```

---

## Deployment Guide

### For Individual Developers

```bash
# Install IDE extension
code --install-extension code-scalpel.governance

# Enable governance
code-scalpel init --governance

# Configure enforcement mode
echo '{"enforcement": {"mode": "warn"}}' > .code-scalpel/ide-extension.json
```

### For Teams (Pro)

```bash
# Install Claude Code hooks
code-scalpel install-hooks

# Install git hooks
code-scalpel install-git-hooks

# Configure team settings
cat > .code-scalpel/config.yaml << EOF
tier: pro
governance:
  enforcement: block
  audit: required
  notifications:
    slack: https://hooks.slack.com/...
EOF
```

### For Enterprise

```bash
# Deploy managed settings (as admin)
sudo code-scalpel install-enterprise \
    --managed-settings /etc/claude-code/managed-settings.json \
    --ide-policy /etc/code-scalpel/ide-policy.json

# Install system daemon
sudo systemctl enable code-scalpel-daemon
sudo systemctl start code-scalpel-daemon

# Configure SIEM integration
code-scalpel configure-siem --splunk https://splunk.corp.com
```

---

## Enforcement Modes

| Mode | IDE Extension | Claude Hooks | Git Hooks | Daemon |
|------|---------------|--------------|-----------|--------|
| **audit-only** | Log all saves | Log all tools | Log commits | Log changes |
| **warn** | Warn on violation | Warn on violation | Warn on commit | Alert on detection |
| **block** | Block saves | Block tools | Block commits | Rollback changes |

### Recommended Rollout

1. **Week 1-2:** Deploy in `audit-only` mode, gather baseline data
2. **Week 3-4:** Switch to `warn` mode, train developers
3. **Week 5+:** Enable `block` mode for critical paths
4. **Ongoing:** Full `block` mode with override workflow

---

## Override Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    OVERRIDE REQUEST FLOW                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Developer attempts blocked save                                 │
│            │                                                     │
│            ▼                                                     │
│  ┌─────────────────┐                                            │
│  │ Override Dialog │                                            │
│  │ - Reason field  │                                            │
│  │ - Category      │                                            │
│  │ - Expiry        │                                            │
│  └────────┬────────┘                                            │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐    No    ┌─────────────────┐              │
│  │ Require Manager │────────→│ Log + Allow     │              │
│  │ Approval?       │          └─────────────────┘              │
│  └────────┬────────┘                                            │
│           │ Yes                                                  │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │ Send to Manager │                                            │
│  │ via Slack/Email │                                            │
│  └────────┬────────┘                                            │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐  Approved  ┌─────────────────┐            │
│  │ Manager Review  │──────────→│ Grant Override  │            │
│  └────────┬────────┘            │ Log Decision    │            │
│           │ Denied              └─────────────────┘            │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │ Block Maintained│                                            │
│  │ Log Denial      │                                            │
│  └─────────────────┘                                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Security Considerations

### Extension Tampering

- Sign IDE extension with verified certificate
- Use managed settings for enterprise (admin-only)
- Monitor for extension disable events

### Hook Bypass

- Use `allowManagedHooksOnly` in enterprise
- Monitor for `--no-verify` commits
- Alert on hook configuration changes

### Daemon Evasion

- Run daemon as system service (not user process)
- Use filesystem ACLs to protect audit files
- Cross-check audit log with git history

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Audit coverage | >95% of commits | Commits with audit entries / Total commits |
| Override rate | <5% | Override requests / Total blocks |
| False positive rate | <2% | Incorrect blocks / Total blocks |
| Developer friction | <30s per save | Average validation time |
| Detection latency | <5s | Time from change to audit entry |

---

## References

- [VS Code Extension API - FileSystemWatcher](https://code.visualstudio.com/api/references/vscode-api)
- [VS Code Extension Samples - FSProvider](https://github.com/microsoft/vscode-extension-samples/blob/main/fsprovider-sample/src/fileSystemProvider.ts)
- [JetBrains VirtualFileListener](https://plugins.jetbrains.com/docs/intellij/virtual-file-system.html)
- [Claude Code Hooks System](https://code.claude.com/docs/en/settings)
- [Claude Code Security Best Practices](https://www.mintmcp.com/blog/claude-code-security)
