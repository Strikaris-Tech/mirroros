# MirrorOS — Explainer for Judges

**One sentence:** MirrorOS makes every AI agent action provable before it
executes and permanently sealed after — using formal logic, not prompts.

---

## The Problem

AI agents are taking consequential actions in financial, legal, and operational
workflows right now. They approve invoices, trigger deployments, route payments,
modify records. The governance story for almost all of them is: "we prompted it
carefully and it usually does the right thing."

That is not governance. It is hope.

When an auditor asks "why did the agent approve that $25,000 payment?" the
answer should not be "the LLM thought it was appropriate." It should be a
specific, verifiable clause in a machine-executable ruleset — with a
cryptographic proof that the answer was the same at the time of execution.

---

## What MirrorOS Does

MirrorOS is a reasoning substrate that sits between an agent's *intent* and
its *action*. Before any agent touches a system, MirrorOS runs a dual-gate:

```
Agent declares intent
        ↓
Gate 1 — Prolog (behavioral): Does this action violate any law?
Gate 2 — Z3 (structural):     Is this action formally consistent with the axioms?
        ↓
PERMITTED → action executes, decision sealed in immudb
REJECTED  → action is blocked, violation sealed in immudb
```

Both gates must pass. Either gate can block. The result is deterministic,
machine-verifiable, and permanently recorded.

---

## The Architecture

```
Prolog (Law)
    ↓
Z3 Theorem Prover (Verification)
    ↓
Python MRS Bridge (Adjudication)
    ↓
Agent / Executor (Action)
    ↓
immudb (Sealed Record)
```

This order is sovereign. It never inverts. The executor — whether that is
Nova Act, an API call, a database write, or a scanner — only runs after the
bridge has issued a PERMITTED verdict.

**The Codex:** Governance rules are written as Prolog — machine-executable law,
not English prose. A rule like "a clerk may not approve payments over $1,000"
is not a prompt instruction. It is a predicate:

```prolog
violates_codex(Agent, approve_payment(_, Amount)) :-
    approval_limit(Agent, Limit),
    Amount > Limit.
```

If the agent is `clerk` and the amount is `25000`, Prolog returns a violation.
Deterministic. Same answer every time. No temperature, no hallucination.

---

## How Nova Act Fits In

This is the key architectural distinction from every other Nova Act integration
in this competition.

**Standard Nova Act pattern:**
```python
# The LLM does the reasoning
nova.act(
    "Go to invoices, find #1042 for $25,000, check if it's within "
    "approval limits and the vendor is verified, then approve if compliant"
)
```
The LLM decides whether to approve. The governance is inside the prompt.
It is probabilistic, non-deterministic, and cannot be audited.

**MirrorOS pattern:**
```python
# Prolog already ruled — verdict is PERMITTED
# Nova Act is a cursor, not a decision-maker

nova.act(f"Approve invoice {invoice_id}")
```

By the time Nova Act receives an instruction, MirrorOS has already:
1. Evaluated the action against the Codex (Prolog)
2. Verified structural consistency (Z3)
3. Sealed the verdict in immudb with a cryptographic proof

Nova Act is never asked whether the action is allowed. It is only told
what to click. The policy reasoning happened upstream, in formal logic,
before the browser was touched.

**The consequence:** Nova Act cannot be prompt-injected into approving
a prohibited payment. It was never asked. The gate is not in the LLM —
it is upstream of it.

---

## The Demo Scenario

Five governed pulses. Two agents. One invoice page. Every decision sealed.

| # | Agent | Action | MRS Result | Why |
|---|-------|--------|------------|-----|
| 1 | clerk | Approve inv_001 ($200) | PERMITTED | Within clerk limit ($1,000) |
| 2 | clerk | Approve inv_002 ($25,000) | REJECTED | Exceeds clerk limit |
| 3 | clerk | Pay unknown_co ($500) | REJECTED | Vendor not in approved list |
| 4 | auditor | Approve inv_002 ($25,000) | PERMITTED | Within auditor limit ($50,000) |
| 5 | auditor | Compliance check | PERMITTED | Read-only, always permitted |

**What you see during the demo:**
- Browser opens on the invoice approval page
- For PERMITTED actions: Nova Act clicks Approve — invoice status updates
- For REJECTED actions: Nova Act never moves — terminal shows the specific
  Prolog predicate that blocked it
- After all pulses: `python -m ledger.verify action_..._002` returns
  `"verified": true` — cryptographic proof the rejection was recorded
  at the time it happened, and has not been altered

---

## What Makes This Different

**Formal verification, not prompt engineering.**
The rules are Prolog predicates and Z3 axioms. They are not instructions
to an LLM. They cannot be rephrased, sweet-talked, or hallucinated around.

**The executor is the least privileged component.**
Nova Act (or any executor) is a cursor. It has no access to the policy layer.
It cannot reason about whether an action should be permitted. That question
was answered before it was invoked.

**Tamper-proof audit trail.**
immudb uses a Merkle tree structure. Every write returns a cryptographic proof.
`verified == True` means the ledger entry matches the tree root — the record
cannot be altered after the fact without breaking the proof. This is not
application-level logging. It is structural immutability.

**Sub-10ms governance.**
The Prolog gate on a loaded Codex runs in single-digit milliseconds. Governance
does not add meaningful latency to agentic workflows.

**Jurisdiction-ready.**
The EU AI Act requires traceability and human oversight for high-risk AI.
SOX requires audit trails for financial controls. DFARS requires provenance
for defense systems. MirrorOS delivers these structurally — not as add-ons,
but as the substrate.

---

## Technical Stack

| Component | Technology | Role |
|-----------|-----------|------|
| Codex | SWI-Prolog | Machine-executable law |
| Verification | Z3 Theorem Prover | Structural consistency |
| Bridge | Python (MRSBridge) | Dual-gate adjudication |
| Executor | Amazon Nova Act | Browser automation |
| Ledger | immudb | Tamper-proof audit trail |
| API | FastAPI (Forge) | Agent routing + REST |
| UI | FlameConsole (Svelte) | Real-time pulse stream |

---

## Running It

```bash
git clone https://github.com/Strikaris-Tech/mirroros-core
cd mirroros-core
docker compose up
./quickstart.sh
```

Five governed pulses in under 60 seconds. No API keys required for the
core MRS demo. Nova Act integration requires an Amazon Nova Act API key.

---

## Open Source

MirrorOS Core is AGPL-3.0. The framework is public. The compliance domain
expertise, client integrations, and learning loop are the product.

Fork it. Build on it. If you run it as a service, open your modifications.

> "The ink that writes itself. Every agent action proven before it executes,
> sealed in a record that cannot be changed."
