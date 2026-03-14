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

---

## Demos

### 1. Zoho Quote-to-Cash (`examples/zoho_demo/`)

A governed Strikaris → Khan Mall sales workflow. Nova Act drives Zoho Books. Nova Vision (Amazon Nova Pro) reads the signed PO PDF and extracts line items. MRS evaluates the document variance against a strict 2% tolerance before any fulfillment or invoicing action proceeds.

| Stage | Action | Gate result |
|-------|--------|-------------|
| 1 | Create quote | Prolog + Z3 |
| 2 | Receive Khan Mall PO | PDF → Nova Vision extraction |
| 3 | Approve document | MRS compares PO vs quote |
| 4 | Start fulfillment | Prolog + Z3 |
| 5 | Generate invoice | Prolog + Z3 |

```bash
export NOVA_ACT_API_KEY=<key>
export AWS_ACCESS_KEY_ID=<key>
export AWS_SECRET_ACCESS_KEY=<key>
python examples/zoho_demo/quote_demo.py --live   # real Nova Vision
python examples/zoho_demo/quote_demo.py          # mock Nova Vision, real Nova Act
```

### 2. LedgerLark AP Orchestration (`examples/ledgerlark_demo/`)

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

### 3. Governed Invoice Approval (`examples/accounting_demo/`)

The original demo. Six pulses, clerk and auditor, live browser via Nova Act.

```bash
python examples/accounting_demo/server.py       # terminal 1
python examples/accounting_demo/nova_demo.py    # terminal 2
```

---

## What's in This Repo

| Path | Purpose |
|------|---------|
| `mrs/prolog/Codex_Laws.pl` | Core Codex — fifteen axioms governing all agent actions |
| `mrs/prolog/concordance.pl` | Z3↔Prolog drift prevention — loaded at boot, boot fails on drift |
| `mrs/prolog/Agent_Rules.pl` | Agent identities: LedgerLark, clerk, auditor, courier |
| `mrs/bridge/mrs_bridge.py` | Dual-gate bridge: Prolog behavioral + Z3 structural |
| `mrs/verifier/essence_runes.py` | Z3 Layer 1 physics substrate — 8 essence runes, L2 relational verbs |
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

**Quickstart only needs Docker.** Everything runs inside the container.

To run demos directly (outside Docker), you also need:
```bash
pip install -r forge/requirements.txt
pip install z3-solver reportlab nova-act
```

SWI-Prolog must be on PATH:
- macOS: `brew install swi-prolog`
- Ubuntu: `apt install swi-prolog`
- Windows: see `docs/KHAN_GUIDE.md`

---

## Quickstart

```bash
bash quickstart.sh
```

Docker only — no local Python or Prolog install needed. Brings up Forge + immudb, runs 5 governed pulses, prints PERMITTED / REJECTED verdicts with latency.

**To run demos directly (no Docker):**

```bash
# LedgerLark Invoice UI — open http://localhost:7242 after starting
python examples/accounting_demo/server.py       # terminal 1 (no API key needed)
python examples/accounting_demo/nova_demo.py    # terminal 2 (Nova Act automation, optional)

# LedgerLark AP Orchestration — Zoho Books
python examples/ledgerlark_demo/ap_demo.py --no-browser   # terminal only
python examples/ledgerlark_demo/ap_demo.py                 # with Nova Act

# Zoho Quote-to-Cash
python examples/zoho_demo/quote_demo.py          # mock Nova Vision
python examples/zoho_demo/quote_demo.py --live   # real Nova Vision (needs AWS)
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

AGPL-3.0. Anyone running any part of MirrorOS as a service must open-source their modifications.

See [LICENSE](LICENSE).

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Issues labelled `good-first-pulse` are a good starting point.

## Security

See [SECURITY.md](SECURITY.md) for the threat model and responsible disclosure address.
