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
        |
Gate 1: Prolog (behavioral) -- Does this action violate any defined rule?
Gate 2: Z3 (structural)     -- Is this action formally consistent with the axioms?
        |
PERMITTED: action executes, decision sealed in ledger
REJECTED:  action blocked,  violation sealed in ledger
```

Both gates must pass. Either gate can block. The sealed ledger entry is cryptographically verifiable: you can prove after the fact exactly what was permitted, what was rejected, and why.

**Authority hierarchy:**
```
Prolog (Law) -> Z3 (Verification) -> Python (Bridge) -> Agents (Action)
```

---

## What's in This Repo

| Path | Purpose |
|------|---------|
| `mrs/prolog/Codex_Laws.pl` | Core Codex: fifteen axioms governing all agent actions |
| `mrs/prolog/concordance.pl` | Z3 and Prolog drift prevention: boot fails on drift |
| `mrs/prolog/Agent_Rules.pl` | Agent identity and role definitions |
| `mrs/bridge/mrs_bridge.py` | Dual-gate bridge: Prolog behavioral + Z3 structural |
| `mrs/verifier/verify_codex.py` | Z3 formal verification engine + ProofArtifact |
| `ledger/chain_client.py` | strikaris-chain client: cryptographically sealed decision trail |
| `forge/api.py` | FastAPI: agent routing, MRS endpoints, WebSocket writ stream |
| `adapters/` | Mock adapters for banking, CI/CD, accounting |

---

## Ledger

MirrorOS seals every decision as a writ on [strikaris-chain](https://github.com/Strikaris-Tech/strikaris-chain). To run your own chain instance:

```bash
git clone https://github.com/Strikaris-Tech/strikaris-chain && cd strikaris-chain && docker compose up -d
```

Set `CHAIN_URL` in your env to point MirrorOS at it. Without a chain running, decisions are still logged to JSON locally.

---

## Verify a Decision

Every sealed decision can be independently verified:

```bash
curl http://localhost:7333/writ/<action_id>
# Returns: { "verified": true, "id": 3, "action_id": "..." }
```

`verified: true` means the record exists and its hash matches the chain. It has not been altered since it was written.

---

## Prerequisites

Docker is all you need. Python and SWI-Prolog run inside the container.

---

## Adding Your Own Domain

1. Add agent facts to `mrs/prolog/Agent_Rules.pl`
2. Write domain compliance rules in a new `.pl` file
3. Load the module: `bridge.load_module("path/to/compliance.pl")`
4. Gate actions: `bridge.query("violates_<domain>_policy(Agent, Action, Reason)")`

The Codex is the base law. Domain rules extend it, they do not replace it.

---

## License

Apache 2.0. Free to use, modify, and distribute. See [LICENSE](LICENSE).

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Issues labelled `good-first-issue` are a good starting point.

## Security

See [SECURITY.md](SECURITY.md) for the threat model and responsible disclosure address.
