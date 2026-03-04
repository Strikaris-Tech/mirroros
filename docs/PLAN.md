# MirrorOS Open-Source Plan
# Amazon Nova Hackathon + Public Launch

> Branch: `opensource-prep` → new public repo `mirroros`
> Deadline: March 16, 2026 @ 5:00pm PDT
> Team: Brandon + Kevin

---

## The Play

Open-source MirrorOS Core as the substrate. The framework is public — the
compliance domain expertise, client integrations, and learning loop are the
product. People take the framework; they come to us for council.

Secondary: entering the Amazon Nova hackathon with a governed agent demo
(Nova Act driving a UI, MRS governing every action) establishes us as the
team that defined the architecture publicly, before the space fills up.

**Lift-off sentence:**
> "MirrorOS turns every AI action into a provable ledger entry. Seven runes,
> fifteen axioms, a sub-10ms verdict — now yours to fork."

---

## License

**AGPL-3.0 across the board** — core, UI, adapters, everything. Anyone running
any part of this as a service must open-source their modifications. Clean,
consistent, no confusion about which layer has which obligations.

Future field/sensor code: dual-licence (GPL community / commercial for DoD/prime
engagements) — revisit when the time comes.

---

## What Gets Open-Sourced vs. Stays Private

### Public (MirrorOS Core)
- `mrs/prolog/Codex_Laws.pl` — generic version, no Strikaris refs
- `mrs/prolog/concordance.pl` — the Z3↔Prolog drift prevention system
- `mrs/bridge/mrs_bridge.py` — core dual-gate (Prolog behavioral + Z3 structural)
- `mrs/bridge/datalog_bridge.py`
- `mrs/verifier/verify_codex.py` + `essence_runes.py`
- `forge/api.py`, `forge/router.py`, `forge/agent_loader.py` — Forge shell
- `mrs/console/` — FlameConsole UI
- `mrs/schemas/` — JSON schemas
- Generic demo agents (new names, not Zeek/Cindrell/Khan/Strikaris)
- Generic accounting compliance demo ruleset (not Financial_Compliance.pl)
- Nova Act integration
- `adapters/mock_bank.py`, `adapters/mock_ci.py` — community can build new adapters without touching live systems
- immudb integration (demo/testnet config — no production keys)
- `docs/` — public-safe documentation

### Private (Strikaris Enterprise)
- `mrs/compliance/` — the full DSL pipeline (YAML → IR → Prolog/Z3 codegen)
- `mrs/analysis/` — learning loop (BeliefManager, PatternDetector, ReflectionEngine)
- `mrs/prolog/Financial_Compliance.pl`, `Defense_Compliance.pl` — encoded domain expertise
- `mrs/prolog/Agent_Rules.pl` — Strikaris agent definitions
- `agents/` — all agent configs (Zeek, Cindrell, Khan, Strikaris)
- `mrs/mirrors/khan/` — NetSuite integration
- `mrs/mirrors/cindrell/` — financial mirror
- `forge/config.yaml` — deployment config
- All `.env*` files
- Hardware-key integration & production signing keys
- immudb production config, fork-handling, disaster-recovery scripts

---

## Phase 0 — Decisions (Complete before Phase 1)
- [x] License: AGPL-3.0 (full — core, UI, adapters, everything)
- [x] Nova approach: Nova Act (UI automation)
- [x] Team: Brandon + Kevin joint submission
- [x] Nova Act SDK access confirmed (Kevin). Using SDK directly, not CDK. Workflow definition available for cloud observability — useful for Devpost submission visuals.
- [x] Demo agent names — **LedgerLark** selected (clerk/auditor permission tiers)
- [ ] Public repo: `Strikaris-Tech/mirroros` org or new standalone `mirroros` org?
- [ ] Real Zoho free tier vs. mock accounting UI (Kevin to decide on Nova Act constraints)
- [ ] immudb: full integration or testnet-only for demo? (see Phase 2 note)

### Demo Mirror Name Candidates

These are the public-facing agent identities for the open-source demo — not
Zeek/Cindrell/Khan/Strikaris, which stay private to the Strikaris deployment.

| Mirror | Target System | Primary Verbs | Why It Fits |
|--------|--------------|---------------|-------------|
| **LedgerLark** | Zoho Books / Invoices | `Sync`, `Consent`, `Report` | Lark = songbird keeping daily rhythm — perfect for accounting beats. Strong fit for the hackathon demo. |
| **CourierSpark** | Gmail IMAP/SMTP | `Fetch`, `Filter`, `Route` | Spark carries messages at light-speed; mirrors email pulses. |
| **WelcomeWarden** | HR Onboarding (Bamboo/Workday) | `Create_Record`, `Validate_Doc`, `Notify` | Warden safeguards the gate; ensures every entrant completes rites. |
| **OnboardOwl** | HR knowledge base (Confluence) | `Sense_Change`, `Update_Page` | Owl sees in dusk — tracks quiet policy shifts, writes before dawn. |
| **MailMirror-Lite** | Gmail → Slack bridge | `Transform`, `Forward` | Simplest possible pulse chain: email → pulse → chat. Good intro example. |

**For the hackathon demo:** LedgerLark is the obvious pick — it maps directly
to the accounting approval scenario (Zoho Books, invoice governance, audit trail).
The `clerk`/`auditor` roles from the demo scenario become LedgerLark operating
in two permission tiers.

---

## Phase 1 — Extract, Scrub & Harden (Days 1–2, ~Mar 3–4)

The public repo starts from a **clean initial commit** — no fork, no history
from this private repo.

### Security first — run before anything goes public
```bash
# Scan for secrets, tokens, internal references
trufflehog filesystem . --only-verified
gitleaks detect --source . --verbose
```
Fix every finding before the first public commit. No exceptions.

### Brandon
- [x] Run secret scanning on all files earmarked for extraction (trufflehog + gitleaks — clean)
- [x] Genericize `Codex_Laws.pl` — remove all Strikaris references
- [x] Write public `Agent_Rules.pl` with demo agents only (LedgerLark, clerk, auditor, courier)
- [x] Write public `README.md` — 7-line vision, 1-line run command, IPO formula
- [x] Add `LICENSE` (AGPL-3.0), `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`
- [x] Strip `CLAUDE.md` → replace with public contributor guide
- [x] Write `quickstart.sh` — Docker Compose up, proves 5 demo pulses in < 60s
- [x] Audit every file for internal rune names, codenames, client references

### Kevin
- ~~Confirm Nova Act SDK access~~ ✓ Done
- Scope the demo UI (Zoho free tier or mock — needs to be driveable by Nova Act SDK)
- Set up workflow definition in AWS console (for Devpost visuals)
- Review extracted codebase for anything that shouldn't be public
- Review AGPL-3.0 license terms — confirm comfortable before public commit

### Public repo skeleton
```
mirroros/
  README.md               — 7-line vision, 1-line run command
  LICENSE                 — AGPL-3.0
  CONTRIBUTING.md
  SECURITY.md             — threat model + responsible disclosure email
  CODE_OF_CONDUCT.md
  quickstart.sh           — Docker Compose + 5 demo pulses < 60s
  mrs/
    prolog/               — Codex_Laws.pl, concordance.pl, demo rules
    bridge/               — MRSBridge core, DatalogBridge
    verifier/             — CodexVerifier, EssenceRunes
    schemas/              — JSON schemas
    console/              — FlameConsole UI
  forge/                  — API shell, router, agent loader
  adapters/
    mock_bank.py          — demo adapter: banking actions
    mock_ci.py            — demo adapter: CI/CD actions
    mock_accounting.py    — demo adapter: Zoho-shaped accounting actions
  ledger/
    immudb_client.py      — immudb integration (testnet config)
    verify.py             — proof verification utility
  examples/
    accounting_demo/      — the hackathon demo scenario
      demo_config.toml
      accounting_compliance.pl
  docs/
    architecture.md
    MRS_IPO.md
    CONTRIBUTING.md
```

---

## Phase 2 — immudb + Nova Act Integration (Days 2–5, ~Mar 4–7)

### immudb (ambitious but worth it — it's the money shot)

immudb replaces the JSON audit trail for the demo. Every MRS decision is
written as a cryptographically verified ledger entry. The demo shows the
proof in real-time — this is what no one else has.

```python
# ledger/immudb_client.py — testnet config, no production keys in repo
from immudb import ImmudbClient

class MRSLedger:
    def __init__(self, host="localhost", port=3322):
        self.client = ImmudbClient(f"{host}:{port}")
        self.client.login("immudb", "immudb")  # demo credentials only

    def seal(self, decision: dict) -> dict:
        key = f"mrs:{decision['action_id']}".encode()
        result = self.client.verifiedSet(key, json.dumps(decision).encode())
        return {"verified": result.verified, "tx": result.id}
```

Community builds sign with the testnet key. Production mirrors use private
keys never committed to the repo — this line holds publicly.

### Nova Act integration

Nova Act SDK drives the browser. MRS wraps Nova Act — not the other way around.
Nova Act describes what it wants to do; MRS decides whether it's allowed.
If rejected, Nova Act never touches the page.

```python
from nova_act import NovaAct

with NovaAct(starting_page="https://books.zoho.com/...") as agent:
    # MRS gate runs before Nova Act acts
    auth = bridge.check_authorization("ledgerlark", "approve_payment", invoice_id)

    if auth:
        agent.act("Click the Approve button for invoice #1042")
        ledger.seal({"action": "approve_payment", "result": "permitted", ...})
    else:
        # Nova Act never touches the UI — MRS stopped it
        ledger.seal({"action": "approve_payment", "result": "rejected", ...})
```

Workflow definition (cloud observability) — configure for Devpost submission
visuals showing the full architecture in AWS console.

```
Nova Act SDK (describes intent)
    → MRS auth gate (MRSBridge.check_authorization)
    → Prolog + Z3 dual-gate
    → Permitted: Nova Act executes, decision sealed in immudb
    → Denied: PermissionError, violation sealed in immudb
```

Router addition — `forge/router.py` gets a `nova_act` backend alongside
OpenRouter and Ollama.

**Kevin leads on Nova Act + scenarios. Brandon leads on immudb.**

### Phase 2 Status
- [x] `ledger/immudb_client.py` — MRSLedger with verifiedSet, graceful fallback
- [x] `ledger/verify.py` — proof verification + CLI
- [x] `mrs/bridge/mrs_bridge.py` — ledger= param wired into _log_reasoning()
- [x] `adapters/mock_accounting.py` — AccountingAdapter, MRS-gated actions
- [x] `adapters/mock_bank.py` — BankAdapter
- [x] `adapters/mock_ci.py` — CIAdapter
- [x] `examples/accounting_demo/accounting_compliance.pl` — Prolog compliance rules
- [x] `examples/accounting_demo/demo_config.toml`
- [x] `examples/accounting_demo/run_demo.py` — 5-pulse demo script
- [ ] Nova Act backend in `forge/router.py` — Kevin
- [ ] `mrs/console/` FlameConsole UI
- [ ] Deployment (EC2 / Docker Compose — see docs/DEPLOYMENT.md)

---

## Phase 3 — Demo Scenario (Days 5–9, ~Mar 7–11)

### The Scenario: Accounting Approval Workflow

Demo agent (`clerk`) attempts a series of actions. MRS governs each one.
Every decision is sealed in immudb in real-time.

| Action | Agent | MRS Result | Why |
|--------|-------|------------|-----|
| Approve invoice ($200) | clerk | ✅ Permitted | Within approval limit |
| Approve invoice ($25,000) | clerk | ❌ Rejected | Exceeds clerk authority |
| Pay unverified vendor | clerk | ❌ Rejected | Vendor not in approved list |
| Same invoice via auditor | auditor | ✅ Permitted | Authority level satisfied |
| View immudb ledger | — | All 4 decisions, cryptographically sealed | |

The ledger sequence at the end is the money shot. `result.verified == True`
on screen. That's the proof.

**Generic compliance rules (safe to open-source):**
```prolog
% examples/accounting_demo/accounting_compliance.pl
violates_approval_policy(Agent, approve_payment(_, Amount), Reason) :-
    approval_limit(Agent, Limit),
    Amount > Limit,
    atom_concat('Exceeds approval authority: limit is ', Limit, Reason).

violates_vendor_policy(_, pay_vendor(Vendor, _), Reason) :-
    \+ vendor_verified(Vendor),
    Reason = 'Vendor not in approved list'.

approval_limit(clerk, 1000).
approval_limit(auditor, 50000).
vendor_verified(acme_corp).
vendor_verified(trusted_supplier).
```

---

## Phase 4 — Submission (Days 9–12, ~Mar 11–14)

**Demo video (3 minutes):**
- 0:00–0:30 — The problem: AI agents taking consequential actions with no proof
- 0:30–1:30 — Live demo: Nova Act driving the UI, MRS governing actions
- 1:30–2:30 — The ledger: immudb sealing every decision in real-time, `verified == True`
- 2:30–3:00 — The architecture: Codex → Z3 → Bridge → Agents, never inverted

**Devpost submission:**

*Title:* MirrorOS — Governed Agentic AI with Formal Verification

*Category:* Agentic AI

*Tagline:* The ink that writes itself. Every agent action proven before
it executes, sealed in a record that cannot be changed.

*Technical implementation (60%):*
- Amazon Nova Act driving real UI automation
- SWI-Prolog Codex: machine-executable law governing every action
- Z3 theorem prover: formal proof that constraints hold
- Dual-gate architecture: behavioral + structural verification
- immudb: cryptographically tamper-proof audit trail, verified on write

*Enterprise impact (20%):*
AI agents taking consequential actions in financial, legal, and regulated
workflows is no longer hypothetical. MirrorOS provides the governance
substrate that makes those deployments auditable, provable, and compliant.
The EU AI Act, SOX, DFARS — all require what MirrorOS delivers structurally.

---

## Phase 5 — Public Launch (Mar 14–16)

- Publish the new public `mirroros` repo
- Submit to Devpost (repo must be public at submission)
- LinkedIn/social post from Strikaris — lead with the lift-off sentence
- Tag the hackathon #AmazonNova

---

## Community Ignition (Post Mar 16)

| Week | Action | Hook |
|------|--------|------|
| 0 | GitHub public + social post | "Proof-bound agent actions in 60s." |
| 1 | Hacker News "Show HN: MirrorOS" | Stay in comments 24h answering proofs |
| 2 | Dev.to tutorial — build a custom adapter | Drive first PRs |
| 4 | First **Rune Jam** — virtual hack day | Award contributors for best adapter |
| Ongoing | Label issues `good-first-pulse` | Grow contributor swarm |

---

## Post-Hackathon

- Monitor traction (stars, forks, issues) for 30 days
- If traction: Discord or GitHub Discussions, respond to community
- If no traction: archive cleanly, no harm done
- Either way: Strikaris enterprise product is unaffected

---

## Responsibilities

| Task | Owner |
|------|-------|
| Secret scanning + file extraction | Brandon |
| Generic Codex + Agent_Rules (demo) | Brandon |
| Public README + docs | Brandon |
| LICENSE, community files | Brandon |
| `quickstart.sh` | Brandon |
| Generic Prolog demo rules | Brandon |
| Nova Act SDK integration | Kevin |
| AWS workflow definition (observability) | Kevin |
| Demo scenarios (3 minimum, more if possible) | Kevin |
| Code review — extracted files pre-publish | Kevin |
| License review (AGPL-3.0 sign-off) | Kevin |
| immudb setup + `MRSLedger` client | Brandon |
| Deployment (EC2 + Docker Compose) | Brandon |
| Video production | Both |
| Devpost submission | Brandon |

---

## Open Questions

- [ ] `Strikaris-Tech/mirroros` or standalone `mirroros` org?
- [ ] Real Zoho or mock UI? (Kevin + Nova Act constraints)
- [ ] Verify the sub-10ms verdict claim before using in messaging
- [ ] Deployment target — see docs/DEPLOYMENT.md
