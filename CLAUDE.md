# CLAUDE.md — MirrorOS Contributor Guide

Guidance for AI coding assistants working inside the MirrorOS codebase.

## Primary Directives

1. **Respect Codex Sovereignty** — Never alter `mrs/prolog/Codex_Laws.pl` or `mrs/prolog/concordance.pl` without explicit instruction.
2. **Maintain Logic Integrity** — Keep Prolog predicates, variable names, and comments consistent with Codex language.
3. **Preserve Symbolic Alignment** — Prolog = Law, Z3 = Verification, Python = Bridge, Agents = Action.
4. **Human-Readable Expression** — Brief, precise, neutral tone.

## Authority Hierarchy

```
Prolog (Law) → Z3 (Verification) → Python (Bridge) → Agents (Action)
```

Never invert this order.

## File Structure

```
forge/          ← API hub (FastAPI, agent routing)
mrs/
  bridge/       ← MRS core (Prolog bridge, Datalog)
  verifier/     ← Z3 verification
  prolog/       ← Codex Laws + Agent Rules
  console/      ← FlameConsole (Svelte UI)
  memory/       ← Runtime state (gitignored)
adapters/       ← System adapters (mock + community)
ledger/         ← immudb client
examples/       ← Demo scenarios
agents/         ← Agent configs (gitignored in production)
docs/           ← Architecture and reference docs
```

## Coding Standards

- All public methods: docstrings with Purpose, Args, Returns, Violations.
- Every MRS interaction logged to `memory/reasoning_log.json`.
- Never bypass `MRSBridge.assert_fact()` — all facts go through the bridge.
- Never assert directly to Prolog without Codex validation.

## Safeguards

- Do not modify `.env` or Docker infrastructure without confirmation.
- Do not write to `memory/` directly — use `MRSBridge` or `DatalogBridge`.
- Do not introduce external dependencies without discussion.
- Do not commit API keys, tokens, or production credentials.
- Do not add `Co-Authored-By` or AI attribution lines to commit messages.
  MirrorOS is a human-led project; keep the git history clean for contributors.

## Quick Commands

```bash
# Start services
docker compose up

# Run Forge locally
cd forge && uvicorn api:app --host 0.0.0.0 --port 8765

# Build FlameConsole
cd mrs/console && npm run build

# Run demo pulses
./quickstart.sh
```
