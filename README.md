# MirrorOS

> MirrorOS turns every AI action into a provable ledger entry. Seven runes, fifteen axioms, a sub-10ms verdict — now yours to fork.

MirrorOS is an open-source governance substrate for agentic AI systems. Every action an agent proposes passes through a dual gate — SWI-Prolog behavioral verification and Z3 formal proof — before it executes. Decisions are sealed in a tamper-proof audit trail. The framework is public. The compliance expertise is the product.

```bash
git clone https://github.com/your-org/mirroros && cd mirroros && ./quickstart.sh
```

---

## Architecture

```
Agent Intent
    ↓
MRS Dual Gate
    ├── Prolog (Codex_Laws.pl)  ← behavioral: does this violate any oath?
    └── Z3 Verifier             ← structural: does the proof hold formally?
    ↓
Permitted → Agent Executes → Decision Sealed in Ledger
Rejected  → PermissionError  → Violation Sealed in Ledger
```

**Authority hierarchy:**
```
Prolog (Law) → Z3 (Verification) → Python (Bridge) → Agents (Action)
```
This order is never inverted.

---

## What's in This Repo

| Path | Purpose |
|------|---------|
| `mrs/prolog/Codex_Laws.pl` | Core Codex — fifteen axioms governing all agent actions |
| `mrs/prolog/concordance.pl` | Z3↔Prolog drift prevention (loaded at boot) |
| `mrs/prolog/Agent_Rules.pl` | Demo agent identities (LedgerLark, clerk, auditor) |
| `mrs/bridge/mrs_bridge.py` | Dual-gate bridge: Prolog behavioral + Z3 structural |
| `mrs/bridge/datalog_bridge.py` | Verified fact store (CSV → DuckDB migration path) |
| `mrs/verifier/verify_codex.py` | Z3 formal verification engine + `ProofArtifact` |
| `forge/api.py` | FastAPI shell: agent routing, MRS endpoints, WebSocket pulse stream |
| `forge/router.py` | LLM backend router (OpenRouter, Ollama, MLX) |
| `adapters/` | Mock adapters for banking, CI/CD, accounting — build your own here |
| `ledger/` | immudb client — cryptographically sealed decision trail |
| `examples/accounting_demo/` | Hackathon demo: invoice approval workflow with full governance |
| `mrs/console/` | FlameConsole — Svelte UI for real-time pulse stream |

---

## The Demo Scenario

LedgerLark governs an accounting approval workflow. The `clerk` and `auditor` agents attempt a series of actions. MRS decides. Every decision is sealed.

| Action | Agent | Result | Why |
|--------|-------|--------|-----|
| Approve invoice ($200) | clerk | ✅ Permitted | Within approval limit |
| Approve invoice ($25,000) | clerk | ❌ Rejected | Exceeds clerk authority |
| Pay unverified vendor | clerk | ❌ Rejected | Vendor not in approved list |
| Same invoice via auditor | auditor | ✅ Permitted | Authority level satisfied |

---

## Quickstart

**Prerequisites:** Docker, Docker Compose

```bash
./quickstart.sh
```

This brings up Forge (port 8765), the MRS bridge, and runs 5 demo pulses. You should see verified decisions printed to stdout in under 60 seconds.

**Manual setup:**

```bash
# Install Python dependencies
pip install -r forge/requirements.txt

# Start Forge locally
cd forge && uvicorn api:app --host 0.0.0.0 --port 8765

# Build FlameConsole (optional)
cd mrs/console && npm run build
```

---

## Adding Your Own Agent

1. Create `agents/<name>/config.json` and `agents/<name>/prompt.md`
2. Add the agent entry to `forge/config.yaml`
3. Add agent facts to `mrs/prolog/Agent_Rules.pl`
4. Define your domain rules in `examples/<your_domain>/compliance.pl`

See `docs/architecture.md` for the full wiring diagram.

---

## License

AGPL-3.0. Anyone running any part of MirrorOS as a service must open-source their modifications.

See [LICENSE](LICENSE).

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). First-time contributors: look for issues labelled `good-first-pulse`.

## Security

See [SECURITY.md](SECURITY.md) for the threat model and responsible disclosure address.
