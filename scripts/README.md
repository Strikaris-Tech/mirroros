# scripts/

Demo runner scripts for MirrorOS. Both scripts run the same 5-step sequence —
they differ only in pacing.

---

## auto_demo.sh

Timed demo for video recording. Each step runs automatically with countdown
pauses between steps so narration audio can be laid in during post-production.
Tune the `PAUSE_*` variables at the top of the file to match your narration.

```bash
bash scripts/auto_demo.sh
```

## manual_demo.sh

Enter-key paced demo for live presentations and walkthroughs. Identical steps
to `auto_demo.sh` but advances only when you press Enter, giving full control
over pacing.

```bash
bash scripts/manual_demo.sh
```

---

## The 5 Steps

| # | Step | What it shows |
|---|------|---------------|
| 1 | AP Orchestration (terminal) | LedgerLark routes 4 bills through the dual-gate MRS engine. Each bill gets a PERMITTED or REJECTED verdict with latency and an immudb seal. The arch diagram opens in the browser after. |
| 2 | AP + Nova Act + Zoho Books | Same dual-gate routing, but approved bills are recorded in Zoho Books by Nova Act. Rejected bills never touch the browser — they are blocked before Nova Act is invoked. Requires `NOVA_ACT_API_KEY`. |
| 3 | LedgerLark Invoice UI | MRS-gated invoice approval with a live verdict panel at `localhost:7242`. Nova Act clicks through approvals if a key is set; otherwise approve manually in the browser. |
| 4 | Ledger verification | Runs `python -m ledger.verify` against the sealed routing decision for the rejected bill (BILL-003). Prints the Merkle proof and `verified: true` — proof the record has not been altered since it was written. |
| 5 | Cold start | Tears down all services and runs `quickstart.sh` from scratch. Demonstrates the system boots clean and runs 5 governed pulses in under 60 seconds with Docker only. |

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Docker | Required. All MRS services run inside the container. |
| `NOVA_ACT_API_KEY` | Optional. Steps 2 and 3 skip gracefully if not set. |
| Chromium / system browser | Optional. The arch diagram in Step 1 opens in Chromium if available, falls back to the system default browser, silently skips if neither is found. |

Both scripts must be run from the repo root:

```bash
# correct
bash scripts/auto_demo.sh

# incorrect — relative paths inside the scripts will break
cd scripts && bash auto_demo.sh
```

---

## Running Individual Examples

Each example can also be run standalone without the full demo sequence.

### LedgerLark AP Orchestration (`examples/ledgerlark_demo/`)

LedgerLark governs an accounts payable queue. Every bill passes two MRS gates:
a routing gate (which agent handles it?) and an approval gate (is the agent
authorized for this amount?). Approved bills are recorded in Zoho Books via
Nova Act. Rejected bills are blocked before the browser is touched.

```bash
# Terminal only — no API key required, runs inside Docker
docker compose exec -w /app forge python examples/ledgerlark_demo/ap_demo.py --no-browser

# With Nova Act — controls a real browser, records to Zoho Books
export NOVA_ACT_API_KEY=<key>
python examples/ledgerlark_demo/ap_demo.py

# Limit to first N bills (useful for partial runs)
python examples/ledgerlark_demo/ap_demo.py --max-bills 2
```

### Invoice Approval UI (`examples/accounting_demo/`)

MRS-gated invoice approval with a live browser UI. A clerk and auditor agent
process a queue of invoices. The verdict panel updates in real time — PERMITTED
actions show the approval; REJECTED actions show the Prolog violation and the
browser is never touched. Demonstrates the role-limit distinction: an auditor
can override an amount limit, but cannot override a vendor policy violation.

```bash
# Terminal 1 — start the UI server
python examples/accounting_demo/server.py
# open http://localhost:7242

# Terminal 2 — run the governed agent loop (dry-run without API key)
python examples/accounting_demo/nova_demo.py

# Terminal only — no browser, no API key required
python examples/accounting_demo/run_demo.py
```
