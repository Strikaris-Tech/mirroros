# MirrorOS

> Formal verification gate for AI agents. Every action proven before it executes, sealed after.

MirrorOS is an open-source governance substrate for agentic AI systems. Before any agent touches a system, MirrorOS runs a dual gate: SWI-Prolog behavioral verification and Z3 formal proof. If both gates pass, the action executes. If either gate fails, the action is blocked. The verdict is deterministic: no temperature, no hallucination, no prompt injection.

```bash
git clone https://github.com/Strikaris-Tech/mirroros && cd mirroros && bash quickstart.sh
```

---

## Why This Exists

Current AI agent safety is vibes-based. Guardrails are prompts. Prompts drift. A sufficiently clever input, a model update, or a long enough context window eventually gets through.

MirrorOS takes a different approach: treat agent authorization as a formal logic problem, not a language problem. Prolog defines what agents are allowed to do. Z3 proves that a given action is structurally consistent with those rules. Neither gate can be sweet-talked.

This is not novel in theory. Formal verification has been used in hardware and safety-critical software for decades. MirrorOS applies it to the agent action layer.

---

## How It Works

```
Agent declares intent
        ↓
Gate 1: Prolog (behavioral) -- Does this action violate any defined rule?
Gate 2: Z3 (structural)     -- Is this action formally consistent with the axioms?
        ↓
PERMITTED: action executes, decision sealed in ledger
REJECTED:  action blocked,  violation sealed in ledger
```

Both gates must pass. Either gate can block. The sealed ledger entry is cryptographically verifiable: you can prove after the fact exactly what was permitted, what was rejected, and why.

**Authority hierarchy:**
```
Prolog (Law) -> Z3 (Verification) -> Python (Bridge) -> Agents (Action)
```

---

## Run the Demo (no API key needed)

```bash
docker compose up -d
docker compose exec -w /app forge python examples/ledgerlark_demo/ap_demo.py --no-browser
```

LedgerLark is an accounts payable orchestrator. It routes expense bills through two MRS gates: a routing gate (which agent handles this?) and an approval gate (is that agent authorized for this amount?). Unknown vendors are blocked at the routing gate and never reach execution.

Sample output:

```
Expense 3/4  --  BILL-003  |  Unknown Vendor Co  |  $300
  Gate 1: routing
  Prolog    REJECTED  (0.8ms)

  REJECTED  ledgerlark  route_bill('BILL-003', 300, unknown_co)
  -> unapproved_vendor
  Ledger    sealed  key=mrs:ap_20260421_003_route  tx=13

  Nova Act  blocked -- browser untouched
```

The rejected vendor never reaches the browser. The violation is sealed in the ledger.

---

## Verify a Decision

Every sealed decision can be independently verified against the chain:

```bash
curl http://localhost:7333/writ/ap_20260421_001_route
# Returns: { "verified": true, "id": 3, "action_id": "ap_20260421_001_route" }
```

`verified: true` means the record exists and its hash matches the chain. It has not been altered since it was written.

To run your own chain instance, see [strikaris-chain](https://github.com/Strikaris-Tech/strikaris-chain).

---

## What's in This Repo

| Path | Purpose |
|------|---------|
| `mrs/prolog/Codex_Laws.pl` | Core Codex: fifteen axioms governing all agent actions |
| `mrs/prolog/concordance.pl` | Z3 and Prolog drift prevention: boot fails on drift |
| `mrs/prolog/Agent_Rules.pl` | Agent identities: LedgerLark, clerk, auditor, courier |
| `mrs/bridge/mrs_bridge.py` | Dual-gate bridge: Prolog behavioral + Z3 structural |
| `mrs/verifier/verify_codex.py` | Z3 formal verification engine + ProofArtifact |
| `ledger/chain_client.py` | strikaris-chain client: cryptographically sealed decision trail |
| `forge/api.py` | FastAPI: agent routing, MRS endpoints, WebSocket pulse stream |
| `adapters/` | Mock adapters for banking, CI/CD, accounting |
| `examples/ledgerlark_demo/` | AP orchestration: LedgerLark dual-gate routing |
| `examples/accounting_demo/` | Invoice approval: clerk and auditor governance with live UI |

---

## Prerequisites

Docker is all you need. Python and SWI-Prolog run inside the container.

Nova Act browser automation is optional (controls a real browser for the full demo). For the browser path you also need:

```bash
pip install nova-act
export NOVA_ACT_API_KEY=<key>
```

The `--no-browser` flag runs the full logic path without it.

---

## Adding Your Own Domain

1. Add agent facts to `mrs/prolog/Agent_Rules.pl`
2. Write domain compliance rules in `examples/<domain>/compliance.pl`
3. Load the module: `bridge.load_module("examples/<domain>/compliance.pl")`
4. Gate actions: `bridge.query("violates_<domain>_policy(Agent, Action, Reason)")`

The Codex is the base law. Domain rules extend it, they do not replace it.

---

## Invoice Approval UI (second demo)

Live UI with clerk and auditor agents, real-time verdict panel in the browser. No API key needed.

```bash
docker compose exec -w /app forge python examples/accounting_demo/server.py
# Open http://localhost:7242
```

---

## License

Apache 2.0. Free to use, modify, and distribute. See [LICENSE](LICENSE).

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Issues labelled `good-first-pulse` are a good starting point.

## Security

See [SECURITY.md](SECURITY.md) for the threat model and responsible disclosure address.
