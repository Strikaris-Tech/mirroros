# MirrorOS Open-Source Plan
# Amazon Nova Hackathon + Public Launch

> Deadline: March 16, 2026 @ 5:00pm PDT
> Team: Brandon + Kevin
> Active branch: `phase2-nova-demo`

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

**AGPL-3.0 across the board** — core, UI, adapters, everything.

---

## What Gets Open-Sourced vs. Stays Private

### Public (MirrorOS Core)
- `mrs/prolog/Codex_Laws.pl`, `concordance.pl`, demo `Agent_Rules.pl`
- `mrs/bridge/mrs_bridge.py` — dual-gate (Prolog + Z3)
- `mrs/bridge/datalog_bridge.py`
- `mrs/verifier/verify_codex.py`, `essence_runes.py`
- `forge/api.py`, `forge/router.py`, `forge/agent_loader.py`
- `mrs/console/` — FlameConsole UI
- `mrs/schemas/` — JSON schemas
- `adapters/mock_bank.py`, `mock_ci.py`, `mock_accounting.py`
- `ledger/immudb_client.py`, `ledger/verify.py`
- `examples/accounting_demo/` — accounting governance demo
- `examples/zoho_demo/` — quote-to-cash demo (planned)
- `docs/` — public-safe documentation

### Private (Strikaris Enterprise)
- `mrs/compliance/` — DSL pipeline (YAML → IR → Prolog/Z3 codegen)
- `mrs/analysis/` — learning loop
- `mrs/prolog/Financial_Compliance.pl`, `Defense_Compliance.pl`, `Agent_Rules.pl`
- `agents/` — all agent configs (Zeek, Cindrell, Khan, Strikaris)
- `mrs/mirrors/khan/` — NetSuite integration
- `mrs/mirrors/cindrell/` — financial mirror
- `forge/config.yaml`, all `.env*` files
- Production immudb config, signing keys
- `netsuite-sdf-analyzer/` — Khan Agent ecosystem (separate private repo)

---

## Phase 0 — Decisions ✓ Complete

- [x] License: AGPL-3.0
- [x] Nova approach: Nova Act SDK (local, not CDK)
- [x] Team: Brandon + Kevin joint submission
- [x] Demo agent names: LedgerLark (clerk/auditor tiers)
- [x] Nova Act SDK access confirmed (Kevin)
- [x] Deployment: video submission + public repo (no live server required for judging)
- [x] Demo video recorded locally (Mac screen capture) — browser visible
- [x] Existing t4g.small hosts Strikaris website; upgrade to t4g.medium for MirrorOS deployment post-launch
- [ ] Public repo: `Strikaris-Tech/mirroros-core` (current) or standalone org?
- [ ] Bedrock access: Brandon confirming Nova Pro (multimodal) for Zoho demo

---

## Phase 1 — Extract, Scrub & Harden ✓ Complete

### Brandon ✓
- [x] Secret scanning (trufflehog + gitleaks — clean)
- [x] Genericize `Codex_Laws.pl`
- [x] Write public `Agent_Rules.pl` (LedgerLark, clerk, auditor, courier)
- [x] Public `README.md`, `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`
- [x] Strip `CLAUDE.md` → public contributor guide (added: no AI co-author refs in commits)
- [x] Write `quickstart.sh`
- [x] Audit all files for internal references

### Kevin
- [x] Nova Act SDK access confirmed
- [ ] Review extracted codebase pre-publish
- [ ] AGPL-3.0 sign-off

---

## Phase 2 — immudb + Accounting Demo ✓ Largely Complete

### Done
- [x] `ledger/immudb_client.py` — MRSLedger, verifiedSet, graceful fallback
- [x] `ledger/verify.py` — verify_entry() + CLI (`python -m ledger.verify <action_id>`)
- [x] `mrs/bridge/mrs_bridge.py` — optional `ledger=` param, seals every verdict in `_log_reasoning()`; health check reports `ledger_available`
- [x] `adapters/mock_accounting.py` — AccountingAdapter, MRS-gated via `violates_accounting_policy/3`
- [x] `adapters/mock_bank.py` — BankAdapter
- [x] `adapters/mock_ci.py` — CIAdapter
- [x] `examples/accounting_demo/accounting_compliance.pl` — approval limits, vendor registry, multifile `violates_codex/2` extension
- [x] `examples/accounting_demo/demo_config.toml`
- [x] `examples/accounting_demo/run_demo.py` — 5-pulse demo script
- [x] `examples/accounting_demo/demo_ui/index.html` — dark-theme invoice UI, live verdict panel (800ms poll)
- [x] `examples/accounting_demo/server.py` — FastAPI server (port 7242), MRS-gated `/api/approve/:id`, push endpoint for nova_demo
- [x] `examples/accounting_demo/nova_demo.py` — governed agent loop; dry-run without key; rich terminal output with latency + immudb seal per pulse
- [x] `docs/EXPLAINER_TO_JUDGES.md` — architecture explainer, cursor-not-decision-maker framing

### Known Issues / In Progress
- [ ] **Pulse 3 bug**: `inv_003` (unknown_co) shows PERMITTED — vendor check fires on `pay_vendor/2` but demo queries `approve_payment/2`. Fix: add `invoice_vendor/2` facts to `accounting_compliance.pl` and extend `approve_payment` rule to check vendor.
- [ ] **Pulse sequence redesign**: Reorder to clerk-processes-full-queue → auditor-handles-escalations (see below)
- [ ] Nova Act `nova_demo.py` — tested in dry-run; needs live test with API key

### Corrected pulse sequence (pending fix)

| # | Agent | Invoice | Expected | Why |
|---|-------|---------|----------|-----|
| 1 | clerk | inv_001 ($200) | PERMITTED | Within limit |
| 2 | clerk | inv_002 ($25,000) | REJECTED | Exceeds clerk limit → escalate |
| 3 | clerk | inv_003 ($500, unknown_co) | REJECTED | Bad vendor → escalate |
| 4 | clerk | inv_004 ($950) | PERMITTED | Within limit |
| 5 | auditor | inv_002 ($25,000) | PERMITTED | Authority satisfied |
| 6 | auditor | inv_003 ($500, unknown_co) | REJECTED | Vendor policy — no role overrides |

Pulse 6 is the critical one: auditor can override a *limit* (role authority) but cannot
override a *vendor violation* (absolute rule). This distinction is the demo's key point.

---

## Phase 3 — Zoho Quote-to-Cash Demo (Mar 5–10)

**Scenario:** Strikaris quotes Khan Mall for Shopify development services.
Full quote-to-cash workflow governed by MRS at every stage. Nova Vision
reads Khan Mall's signed PO response and compares against the original quote.

### Participants
- **Strikaris** — vendor, Zoho Books account
- **Khan Mall** — client, Zoho Invoice account
- **We control both sides** — scripted round-trip, no real email loop

### Demo product
Shopify development services (Discovery, Sprint 1, Integration — 3 line items).
Khan Mall is a Shopify dev shop — natural fit.

### Workflow

```
[1] QUOTE CREATION
    Nova Act (Strikaris) → Zoho Books
    Create quote: Khan Mall — Shopify Dev Services
    MRS: sales_rep authorized to create quote this size?
    Nova Act sends quote via email
    immudb: quote_sent sealed

[2] PO RESPONSE (generated — no real email loop)
    po_generator.py creates Khan Mall's PO response PDF (reportlab)
    Randomly varies: signature+initials (always), quantity change (30%),
    partial acceptance (20%), price counter-offer (10%)
    Seeded mode for video rehearsal; unseeded for live runs

[3] DOCUMENT VERIFICATION (Nova Vision)
    PDF → image (pdf2image)
    Amazon Nova Pro (Bedrock) extracts: PO#, line items, totals, signature
    MRS evaluates comparison against original quote:
      MATCH    → quote_approved
      MISMATCH → document_rejected, variance detail sealed

[4] FULFILLMENT AUTH
    MRS: document_verified(QuoteId) must hold
    Nova Act marks quote → Accepted in Zoho Books

[5] INVOICE GENERATION
    Nova Act converts approved quote → Invoice in Zoho Books
    immudb: invoice_generated sealed

[EXCEPTION PATH — triggered by MISMATCH]
    Nova Act drafts exception email to sales rep
    immudb: document_rejected, variance_detail sealed
    Workflow halts — fulfillment blocked
```

### Prolog rules needed (`examples/zoho_demo/quote_compliance.pl`)

```prolog
% Stage transition enforcement — cannot skip steps
valid_transition(quote_sent, po_received).
valid_transition(po_received, quote_approved).
valid_transition(quote_approved, fulfillment_started).
valid_transition(fulfillment_started, invoice_sent).

violates_codex(_, advance_stage(From, To)) :-
    \+ valid_transition(From, To).

% Quote approval limits
approval_limit(sales_rep, 10000).
approval_limit(manager,  100000).

% Document comparison — 2% tolerance
violates_codex(_, approve_document(QuoteId, POAmount, QuoteAmount), Reason) :-
    Variance is abs(POAmount - QuoteAmount) / QuoteAmount * 100,
    Variance > 2.0,
    format(atom(Reason), 'Document variance ~1f% exceeds 2% tolerance', [Variance]).

% Fulfillment requires verified document
violates_codex(_, start_fulfillment(QuoteId)) :-
    \+ document_verified(QuoteId).
```

### Build order
1. `examples/zoho_demo/quote_compliance.pl` — Prolog rules
2. `ledger/po_generator.py` — reportlab PDF with randomized variations
3. `ledger/vision.py` — Bedrock Nova Pro call, structured extraction
4. `examples/zoho_demo/quote_demo.py` — orchestrator (same terminal output pattern as nova_demo.py)
5. Nova Act instructions tuned against real Zoho Books UI (requires test run)

### Dependencies
- `reportlab` — PDF generation
- `pdf2image` + `poppler` — PDF → image for Nova Vision
- `boto3` — Bedrock API (Nova Pro)
- Bedrock access with Nova Pro enabled in us-east-1 (Brandon confirming)

### Risks
- Nova Act + Zoho UI requires tuning against real account — budget time
- Nova Vision extraction accuracy depends on prompt engineering — one test run needed
- Bedrock access gate (confirming)

---

## Phase 3b — SDF Analyzer + LedgerLark Demo (Exploring)

**What the SDF Analyzer is:**
A static analysis tool for NetSuite SDF projects (Kevin's work, private repo
`Strikaris-Tech/netsuite-sdf-analyzer`, Phase 1 complete). Parses SuiteScripts
via AST (Acorn), reads deployment XML, builds dependency graphs, produces JSON
reports and PlantUML diagrams. Designed to feed the Khan Agent AI system.

**The MRS governance angle:**
The analyzer is read-only and deterministic. What needs governance is what
Khan Agent is permitted to DO with the analysis results.

```
sdf-analyzer analyze <project>
        ↓ JSON output
LedgerLark reads automation inventory
        ↓
MRS asserts facts from analysis:
  - script X deployed to RELEASED with parse errors
  - circular dependency detected: A → B → A
  - scheduled script running DAILY (policy: max WEEKLY for this tier)
        ↓
MRS evaluates each finding:
  PERMITTED → Khan Agent may document/recommend
  REJECTED  → Khan Agent blocked from auto-deploying/modifying
        ↓
immudb seals the analysis event + each governance decision
```

**Why this is compelling:**
- The SDF Analyzer output is structured JSON — clean MRS input, no parsing needed
- Governance on AI actions over a client's NetSuite codebase is a real problem
- Khan Mall is an existing NetSuite client — fixture data could be real (or anonymized)
- No browser needed for the analysis step — terminal-only, very fast to demo
- Complements the Zoho demo: Khan Mall's NetSuite + Strikaris's Zoho Books = one client story

**Prolog rules needed:**
```prolog
% Deployment policy
violates_codex(_, deploy_to_production(ScriptId)) :-
    script_has_parse_errors(ScriptId).

violates_codex(_, deploy_to_production(ScriptId)) :-
    script_in_circular_dependency(ScriptId).

% Schedule frequency limits
violates_codex(_, approve_schedule(ScriptId, Frequency)) :-
    exceeds_schedule_policy(Frequency).

exceeds_schedule_policy('DAILY') :- client_tier(standard).
```

**Status:** Exploring — not yet started. Kevin to advise on SDF analyzer output
format and Khan Agent integration points. This could be a Phase 4 / post-hackathon
item if the Zoho demo takes priority.

---

## Phase 4 — Demo Video + Submission (Mar 11–14)

**Demo video (3 minutes):**
- 0:00–0:30 — The problem: AI agents acting without proof
- 0:30–1:30 — Live: Nova Act driving Zoho, MRS governing each action
- 1:30–2:30 — The ledger: immudb sealing decisions, `verified == True`
- 2:30–3:00 — Architecture overview: Codex → Z3 → Bridge → Agents

**Recording setup:**
- Run demo locally on Mac (QuickTime / OBS screen capture)
- Three panes visible: Chromium (Nova Act), Zoho UI, terminal (MRS verdicts)
- Seeded PDF generator for reproducible run

**Devpost submission:**

*Title:* MirrorOS — Governed Agentic AI with Formal Verification

*Category:* Agentic AI

*Tagline:* The ink that writes itself. Every agent action proven before
it executes, sealed in a record that cannot be changed.

*Key differentiator (from EXPLAINER_TO_JUDGES.md):*
Nova Act receives mechanical instructions, not policy reasoning. The decision
surface is a deterministic Prolog query. The LLM is a cursor.

---

## Phase 5 — Public Launch (Mar 14–16)

- Publish public repo (confirm org: `Strikaris-Tech/mirroros-core` or standalone)
- Submit to Devpost (repo must be public)
- Remove `docs/PLAN.md` before public commit
- LinkedIn/social from Strikaris — lead with lift-off sentence
- Tag #AmazonNova

---

## Community Ignition (Post Mar 16)

| Week | Action | Hook |
|------|--------|------|
| 0 | GitHub public + social | "Proof-bound agent actions in 60s." |
| 1 | Hacker News "Show HN: MirrorOS" | Stay in comments 24h |
| 2 | Dev.to tutorial — build a custom adapter | Drive first PRs |
| 4 | First **Rune Jam** — virtual hack day | Award best adapter |
| Ongoing | Label issues `good-first-pulse` | Grow contributor swarm |

---

## Responsibilities

| Task | Owner | Status |
|------|-------|--------|
| Secret scanning + extraction | Brandon | ✓ Done |
| Generic Codex + Agent_Rules | Brandon | ✓ Done |
| Public README + docs | Brandon | ✓ Done |
| LICENSE, community files | Brandon | ✓ Done |
| quickstart.sh | Brandon | ✓ Done |
| immudb ledger integration | Brandon | ✓ Done |
| Mock adapters (bank, CI, accounting) | Brandon | ✓ Done |
| Accounting demo (run_demo.py, server, UI) | Brandon | ✓ Done |
| nova_demo.py (dry-run tested) | Brandon | In progress |
| Pulse sequence fix (vendor check + reorder) | Brandon | Pending |
| Zoho demo — po_generator.py | Brandon | Planned |
| Zoho demo — vision.py (Nova Vision/Bedrock) | Brandon | Pending Bedrock access |
| Zoho demo — quote_demo.py orchestrator | Brandon | Planned |
| Nova Act instructions (Zoho Books UI) | Brandon + Kevin | Planned |
| Nova Act SDK integration | Kevin | In progress |
| AWS workflow definition (Devpost visuals) | Kevin | Pending |
| SDF Analyzer → LedgerLark demo | Kevin + Brandon | Exploring |
| Code review — pre-publish | Kevin | Pending |
| AGPL-3.0 sign-off | Kevin | Pending |
| Demo video production | Both | Planned |
| Devpost submission | Brandon | Planned |
| Remove PLAN.md before public launch | Brandon | Pre-launch |

---

## Open Questions

- [ ] Bedrock access — Nova Pro in us-east-1 enabled? (Brandon confirming)
- [ ] Public repo org: `Strikaris-Tech/mirroros-core` or standalone `mirroros` org?
- [ ] SDF Analyzer demo: hackathon scope or post-hackathon?
- [ ] Verify sub-10ms verdict claim in messaging before using it
- [ ] Khan Mall NetSuite fixture: use Strikaris fixture or anonymized Khan data for SDF demo?
