# MirrorOS

> Every AI agent action — proven before it executes, sealed after. Formal logic, not prompts.

MirrorOS is an open-source governance substrate for agentic AI systems. Before any agent touches a system, MirrorOS runs a dual gate: SWI-Prolog behavioral verification and Z3 formal proof. Decisions are sealed in a tamper-proof audit trail. The framework is public. The compliance expertise is the product.

```bash
git clone https://github.com/Strikaris-Tech/mirroros-core && cd mirroros-core && bash quickstart.sh
```

---

## How It Works

```
Agent declares intent
        ↓
Gate 1 — Prolog (behavioral):  Does this action violate any Codex law?
Gate 2 — Z3 (structural):      Is this action formally consistent with the axioms?
        ↓
PERMITTED → Nova Act executes → decision sealed in ledger
REJECTED  → Nova Act blocked  → violation sealed in ledger
```

Both gates must pass. Either gate can block. The verdict is deterministic — no temperature, no hallucination, no prompt injection.

**Authority hierarchy — never inverted:**
```
Prolog (Law) → Z3 (Verification) → Python (Bridge) → Agents (Action)
```

For the full architecture breakdown, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Demos

### 1. LedgerLark AP Orchestration (`examples/ledgerlark_demo/`)

LedgerLark (overseer agent) governs an accounts payable queue. Every expense passes two MRS gates: a routing gate (which agent handles it?) and an approval gate (is the agent authorized?). Nova Act records approved expenses in Zoho Books. Rejected vendors never reach the browser.

| Expense | Vendor | Result | Route |
|---------|--------|--------|-------|
| $450 | Office Supplies Co | PERMITTED | → clerk |
| $8,500 | Cloud Infra Ltd | PERMITTED | → auditor |
| $300 | Unknown Vendor Co | REJECTED | blocked at routing gate |
| $15,000 | Strikaris Dev Services | PERMITTED | → auditor |

```bash
export NOVA_ACT_API_KEY=<key>
python examples/ledgerlark_demo/ap_demo.py
python examples/ledgerlark_demo/ap_demo.py --no-browser  # terminal only
```

### 2. Governed Invoice Approval (`examples/accounting_demo/`)

Invoice approval with a live UI. Clerk and auditor agents, MRS-gated approvals, real-time verdict panel in the browser.

```bash
python examples/accounting_demo/server.py       # terminal 1
python examples/accounting_demo/nova_demo.py    # terminal 2
```

### 3. Zoho Quote-to-Cash (`examples/zoho_demo/`)

Full quote-to-cash workflow governed by MRS. Nova Act drives Zoho Books. Nova Vision (Amazon Nova Pro via Bedrock) reads a signed PO PDF and extracts line items. MRS evaluates document variance against a 2% tolerance before fulfillment proceeds. Requires AWS Bedrock access for live mode.

```bash
export NOVA_ACT_API_KEY=<key>
python examples/zoho_demo/quote_demo.py          # mock Nova Vision
python examples/zoho_demo/quote_demo.py --live   # real Nova Vision (needs AWS Bedrock)
```

---

## What's in This Repo

| Path | Purpose |
|------|---------|
| `mrs/prolog/Codex_Laws.pl` | Core Codex — fifteen axioms governing all agent actions |
| `mrs/prolog/concordance.pl` | Z3↔Prolog drift prevention — loaded at boot, boot fails on drift |
| `mrs/prolog/Agent_Rules.pl` | Agent identities: LedgerLark, clerk, auditor, courier |
| `mrs/bridge/mrs_bridge.py` | Dual-gate bridge: Prolog behavioral + Z3 structural |
| `mrs/verifier/verify_codex.py` | Z3 formal verification engine + `ProofArtifact` |
| `ledger/immudb_client.py` | immudb client — cryptographically sealed decision trail |
| `ledger/vision.py` | Nova Vision (Amazon Nova Pro) — PDF extraction via Bedrock |
| `ledger/po_generator.py` | PO PDF generator for quote-to-cash demo |
| `forge/api.py` | FastAPI: agent routing, MRS endpoints, WebSocket pulse stream |
| `adapters/` | Mock adapters for banking, CI/CD, accounting |
| `examples/zoho_demo/` | Quote-to-cash: Nova Act + Nova Vision + MRS |
| `examples/ledgerlark_demo/` | AP orchestration: LedgerLark dual-gate routing |
| `examples/accounting_demo/` | Invoice approval: clerk/auditor governance |

---

## Prerequisites

**Docker is all you need** — Python and SWI-Prolog run inside the container.

Nova Act browser automation is the only thing that runs on the host (it controls a real browser). For those demos you also need:
```bash
pip install nova-act
export NOVA_ACT_API_KEY=<key>
```

---

## Quickstart

```bash
bash quickstart.sh
```

Brings up Forge + immudb, runs 5 governed pulses, prints PERMITTED / REJECTED verdicts with latency. Docker only.

---

## Running the Demos

**Start services first:**
```bash
docker compose up -d
```

**LedgerLark AP Orchestration** — terminal only, no API key needed:
```bash
docker compose exec -w /app forge python examples/ledgerlark_demo/ap_demo.py --no-browser
```

**LedgerLark AP Orchestration** — with Nova Act (runs on host, controls browser):
```bash
python examples/ledgerlark_demo/ap_demo.py
```

**Invoice Approval UI** — no API key needed, open `http://localhost:7242`:
```bash
docker compose exec -w /app forge python examples/accounting_demo/server.py
```

**Zoho Quote-to-Cash** — with Nova Act:
```bash
python examples/zoho_demo/quote_demo.py          # mock Nova Vision
python examples/zoho_demo/quote_demo.py --live   # real Nova Vision (needs AWS Bedrock)
```

---

## Adding Your Own Domain

1. Add agent facts to `mrs/prolog/Agent_Rules.pl`
2. Write domain compliance rules in `examples/<domain>/compliance.pl`
3. Load the module: `bridge.load_module("examples/<domain>/compliance.pl")`
4. Gate actions: `bridge.query("violates_<domain>_policy(Agent, Action, Reason)")`

The Codex is the law. Your domain rules extend it — they never replace it.

---

## Verify a Decision

Every sealed decision can be independently verified:

```bash
python -m ledger.verify <action_id>
# Returns: { "verified": true, "tx": ..., "key": ... }
```

`verified: true` means the Merkle proof matches the tree root. The record has not been altered since it was written.

---

## License

Apache 2.0. Free to use, modify, and distribute. See [LICENSE](LICENSE).

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Issues labelled `good-first-pulse` are a good starting point.

## Security

See [SECURITY.md](SECURITY.md) for the threat model and responsible disclosure address.
