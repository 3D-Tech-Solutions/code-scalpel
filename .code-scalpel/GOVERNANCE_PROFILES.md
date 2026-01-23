# Governance Profile Selection Guide

> [20251226_DOCS] Guide for selecting the right governance profile based on team size, budget, and compliance requirements.

## Quick Selection Matrix

| Profile | Team Size | Budget | Compliance Need | Agent Token Overhead |
|---------|-----------|--------|-----------------|---------------------|
| **permissive** | Solo/Hobby | $0 | None | 0 tokens |
| **minimal** | 1-5 devs | Limited | Basic audit | ~50 tokens |
| **default** | 5-20 devs | Moderate | Standard | ~100 tokens |
| **restrictive** | 20+ devs | Enterprise | SOC2/ISO/HIPAA | ~150 tokens |

## Design Philosophy

### Server-Side Governance = Zero Agent Overhead

Code Scalpel's governance is **server-side**, not agent-side:

```
┌─────────────────────────────────────────────────────────────┐
│  AI Agent Context Window (limited - 8K-128K tokens)         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  • User prompt                                       │   │
│  │  • Extracted code snippet (50-500 tokens)           │   │
│  │  • Tool response: "ALLOW" or "DENY: reason"         │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ MCP call (minimal tokens)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Code Scalpel MCP Server (unlimited memory)                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  • 680-line governance policies (cached, parsed once)│   │
│  │  • Full codebase index                              │   │
│  │  • OPA/Rego evaluation engine                       │   │
│  │  • Audit logging                                    │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**The AI agent never sees the policy files.** It only receives pass/fail responses.

---

## Profile Details

### 1. Permissive (`config.permissive.json`)

**Use When:**
- Solo development, side projects
- Rapid prototyping / hackathons
- Learning and experimentation

**Configuration:**
```json
{
  "governance": {
    "change_budgeting": { "enabled": false },
    "blast_radius": { "enabled": false },
    "audit": { "log_all_changes": false }
  }
}
```

**What's Disabled:**
- All governance policies
- Change budgeting
- Audit logging

---

### 2. Minimal (`config.minimal.json`) ⭐ NEW

**Use When:**
- Contractors delivering client projects
- Small teams (2-5 devs) with limited budget
- Startups needing audit trail without process overhead
- Solo developers with compliance requirements

**Configuration:**
- `config.minimal.json` - Relaxed limits, essential controls only
- `dev-governance.minimal.yaml` - ~70 lines vs 680 in full profile

**What's Included:**
- ✅ Security policies (secrets detection, dangerous functions)
- ✅ Change scope limits (prevent runaway AI)
- ✅ Audit logging (compliance evidence)
- ✅ Blast radius protection (optional critical paths)

**What's Excluded:**
- ❌ Documentation requirements (process overhead)
- ❌ Design review requirements (process overhead)
- ❌ Sprint/backlog integration (process overhead)
- ❌ Full OPA/Rego policies (complexity overhead)

**Break-Even Analysis:**
| Annual Dev Cost | Setup Time | ROI Threshold |
|-----------------|------------|---------------|
| $50K (contractor) | 2 hours | 1 prevented bug |
| $150K (small team) | 4 hours | 1 security incident avoided |

---

### 3. Default (`config.json`)

**Use When:**
- Teams of 5-20 developers
- Standard enterprise development
- Multi-agent orchestration
- Projects requiring architectural governance

**Configuration:**
- `config.json` - Balanced limits
- `dev-governance.yaml` - Full 680-line policy set

**What's Included:**
- Everything in Minimal, plus:
- ✅ Documentation requirements
- ✅ Architecture review requirements
- ✅ Project management integration
- ✅ Module boundary enforcement

---

### 4. Restrictive (`config.restrictive.json`)

**Use When:**
- Regulated industries (finance, healthcare)
- SOC2/ISO/HIPAA compliance requirements
- Enterprise with dedicated compliance team
- High-security environments

**Configuration:**
- `config.restrictive.json` - Strict limits
- `dev-governance.yaml` + custom OPA/Rego policies

**What's Included:**
- Everything in Default, plus:
- ✅ Cryptographic policy verification (`verify_policy_integrity`)
- ✅ Mandatory sandbox execution
- ✅ Approval workflows for all security changes
- ✅ Extended audit retention (90+ days)

---

## Switching Profiles

### Via Environment Variable

```bash
export CODE_SCALPEL_CONFIG_PROFILE=minimal
```

### Via MCP Configuration

```json
{
  "mcpServers": {
    "code-scalpel": {
      "command": "uvx",
      "args": ["code-scalpel"],
      "env": {
        "CODE_SCALPEL_CONFIG_PROFILE": "minimal"
      }
    }
  }
}
```

### Via Project Config

Create/edit `.code-scalpel/config.json`:
```json
{
  "profile": "minimal"
}
```

---

## Cost-Benefit Analysis

### When Governance Is NOT Worth It

| Scenario | Recommendation |
|----------|----------------|
| Solo hobby project | Skip governance entirely |
| One-off script | Use `permissive` profile |
| Hackathon/prototype | Disable temporarily |
| Learning/experimentation | Use `permissive` |

### When Governance IS Worth It

| Scenario | Minimum Profile | Reason |
|----------|-----------------|--------|
| Client deliverable | `minimal` | Audit trail for CYA |
| Team > 2 people | `minimal` | Coordination |
| Any paid project | `minimal` | Liability protection |
| Production code | `default` | Quality assurance |
| Regulated industry | `restrictive` | Legal requirement |

---

## Token Efficiency Impact

Governance adds **minimal** token overhead to AI agents:

| Operation | Without Governance | With Minimal | With Full |
|-----------|-------------------|--------------|-----------|
| `extract_code` | ~50 tokens | ~50 tokens | ~50 tokens |
| `update_symbol` | ~100 tokens | ~150 tokens | ~200 tokens |
| `security_scan` | ~200 tokens | ~200 tokens | ~200 tokens |
| Policy check | N/A | ~50 tokens | ~100 tokens |

**Key insight:** Governance prevents wasted tokens by failing fast on policy violations.

---

## Migration Path

```
permissive → minimal → default → restrictive
     ↑           ↑          ↑          ↑
   Hobby    Contractor   Team    Enterprise
```

Start with the minimum viable profile and upgrade as needs grow.
