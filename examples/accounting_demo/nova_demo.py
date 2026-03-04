"""
MirrorOS + Nova Act — Governed Accounting Demo
===============================================
Runs the 6-pulse demo with a real browser you can watch.

What you'll see:
  - Browser opens on the invoice approval page (localhost:7242)
  - Terminal shows MRS gate firing before each browser action
  - PERMITTED: Nova Act clicks Approve — invoice status updates live
  - REJECTED:  Nova Act sits still — terminal shows the Prolog violation
  - After all pulses: verify any decision in immudb

Prerequisites:
  1. Start the demo UI server (in a separate terminal):
       python examples/accounting_demo/server.py

  2. Install Nova Act SDK:
       pip install nova-act

  3. Set your Nova Act API key:
       export NOVA_ACT_API_KEY=<your-key>

  4. Run this script:
       python examples/accounting_demo/nova_demo.py

Architecture note:
  Nova Act receives mechanical instructions, not policy reasoning.
  The MRS gate fires BEFORE Nova Act is invoked.  By the time Nova Act
  gets a call, the decision is already made, logged, and sealed.
  Nova Act is a cursor — not a decision-maker.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

# ── Terminal output ───────────────────────────────────────────────────────────

BOLD  = "\033[1m"
GREEN = "\033[32m"
RED   = "\033[31m"
AMBER = "\033[33m"
CYAN  = "\033[36m"
DIM   = "\033[2m"
RESET = "\033[0m"

def _hr():
    print(f"{DIM}{'─' * 60}{RESET}")

def _header(text: str):
    print(f"\n{BOLD}{text}{RESET}")

def _gate_line(label: str, value: str, colour: str = ""):
    print(f"  {DIM}{label:<14}{RESET}{colour}{value}{RESET}")

def _verdict(permitted: bool, agent: str, action: str, reason: str, latency_ms: float):
    v = f"{GREEN}PERMITTED{RESET}" if permitted else f"{RED}REJECTED {RESET}"
    print(f"\n  {BOLD}{v}{RESET}  {AMBER}{agent}{RESET}  {action}")
    if reason and reason != "permitted":
        print(f"  {DIM}→ {reason}{RESET}")
    print(f"  {DIM}{latency_ms:.1f}ms{RESET}")

def _seal_line(result: dict):
    if result.get("verified"):
        print(f"  {DIM}Ledger  {RESET}{GREEN}sealed{RESET}  "
              f"{DIM}key={result['key']}  tx={result['tx']}{RESET}")
    elif result.get("error"):
        print(f"  {DIM}Ledger  {RESET}{DIM}offline ({result['error']}){RESET}")


# ── Demo pulses ───────────────────────────────────────────────────────────────

PULSES = [
    # ── Clerk processes the full queue ────────────────────────────────────────
    {
        "agent":      "clerk",
        "invoice_id": "inv_001",
        "amount":     200,
        "expected":   "PERMITTED",
        "note":       "$200 — within clerk limit ($1,000)",
    },
    {
        "agent":      "clerk",
        "invoice_id": "inv_002",
        "amount":     25000,
        "expected":   "REJECTED",
        "note":       "$25,000 — exceeds clerk limit → escalate to auditor",
    },
    {
        "agent":      "clerk",
        "invoice_id": "inv_003",
        "amount":     500,
        "expected":   "REJECTED",
        "note":       "unknown_co — vendor not in approved list → escalate",
    },
    {
        "agent":      "clerk",
        "invoice_id": "inv_004",
        "amount":     950,
        "expected":   "PERMITTED",
        "note":       "$950 — within clerk limit ($1,000)",
    },
    # ── Auditor handles escalations ───────────────────────────────────────────
    {
        "agent":      "auditor",
        "invoice_id": "inv_002",
        "amount":     25000,
        "expected":   "PERMITTED",
        "note":       "$25,000 — within auditor limit ($50,000); limit overridden",
    },
    {
        "agent":      "auditor",
        "invoice_id": "inv_003",
        "amount":     500,
        "expected":   "REJECTED",
        "note":       "unknown_co — vendor policy is absolute; no role can override",
    },
]


# ── Push verdict to demo UI ───────────────────────────────────────────────────

def _push_to_ui(verdict: dict):
    """POST the verdict to the demo server so the browser panel updates."""
    try:
        data = json.dumps(verdict).encode()
        req  = urllib.request.Request(
            "http://localhost:7242/api/mrs/verdict",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=2)
    except Exception:
        pass  # UI server down — non-fatal


def _reset_ui():
    """Reset server state so every demo run starts with all invoices pending."""
    try:
        req = urllib.request.Request(
            "http://localhost:7242/api/reset",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=2)
    except Exception:
        pass  # UI server down — non-fatal


# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    print(f"\n{BOLD}MirrorOS — Governed Accounting Demo{RESET}")
    print(f"{DIM}Nova Act drives the browser. MRS decides what it may touch.{RESET}")
    _hr()

    # ── Bridge + ledger ───────────────────────────────────────────────────────
    try:
        from mrs.bridge.mrs_bridge import MRSBridge
        from ledger.immudb_client import MRSLedger
    except ImportError as exc:
        print(f"{RED}ERROR: {exc}{RESET}")
        print("Install dependencies: pip install -r forge/requirements.txt")
        sys.exit(1)

    ledger = MRSLedger()
    bridge = MRSBridge(
        prolog_path=str(REPO_ROOT / "mrs" / "prolog"),
        memory_path=str(REPO_ROOT / "mrs" / "memory"),
        ledger=ledger,
    )
    compliance = REPO_ROOT / "examples" / "accounting_demo" / "accounting_compliance.pl"
    result = bridge.load_module(str(compliance))

    ledger_status = f"{GREEN}connected{RESET}" if ledger.is_available() else f"{DIM}offline — JSON only{RESET}"
    codex_status  = f"{GREEN}loaded{RESET}"    if result["success"]      else f"{RED}FAILED{RESET}"

    print(f"  {DIM}MRS bridge  {RESET}{GREEN}ready{RESET}")
    print(f"  {DIM}Codex       {RESET}{codex_status}")
    print(f"  {DIM}immudb      {RESET}{ledger_status}")
    _hr()

    # ── Nova Act ──────────────────────────────────────────────────────────────
    nova_available = bool(os.getenv("NOVA_ACT_API_KEY"))

    if not nova_available:
        print(f"{AMBER}NOVA_ACT_API_KEY not set — running in dry-run mode.{RESET}")
        print(f"{DIM}MRS gate runs fully. Nova Act calls are printed but not executed.{RESET}")
        print(f"{DIM}Set NOVA_ACT_API_KEY and re-run for live browser automation.{RESET}\n")

    try:
        from nova_act import NovaAct
        _nova_import = True
    except ImportError:
        _nova_import = False
        if nova_available:
            print(f"{RED}nova-act not installed: pip install nova-act{RESET}\n")
            nova_available = False

    # ── Reset UI state so every run starts clean ──────────────────────────────
    _reset_ui()

    # ── Run pulses ────────────────────────────────────────────────────────────
    print(f"{BOLD}Running {len(PULSES)} governed pulses...{RESET}\n")

    def _run_with_nova(nova):
        for i, pulse in enumerate(PULSES, 1):
            agent      = pulse["agent"]
            invoice_id = pulse["invoice_id"]
            amount     = pulse["amount"]

            _header(f"Pulse {i}/{len(PULSES)}  —  {agent}  →  approve_payment('{invoice_id}', {amount})")
            print(f"  {DIM}{pulse['note']}{RESET}\n")

            # ── MRS gate ──────────────────────────────────────────────────────
            _gate_line("MRS gate", "running...", DIM)
            t0 = time.perf_counter()

            violations = bridge.query(
                f"violates_accounting_policy({agent}, "
                f"approve_payment('{invoice_id}', {amount}), Reason)"
            )

            latency_ms = (time.perf_counter() - t0) * 1000
            permitted  = not violations
            reason     = str(violations[0].get("Reason", "policy violation")) if violations else "permitted"

            _gate_line("Prolog", f"{'PERMITTED' if permitted else 'REJECTED'}  ({latency_ms:.1f}ms)",
                       GREEN if permitted else RED)

            # ── Verdict ───────────────────────────────────────────────────────
            _verdict(permitted, agent, f"approve_payment('{invoice_id}', {amount})", reason, latency_ms)

            # ── immudb seal ───────────────────────────────────────────────────
            action_id = f"nova_{datetime.now().strftime('%Y%m%d')}_{i:03d}"
            seal_result = ledger.seal({
                "action_id":  action_id,
                "agent":      agent,
                "action":     "approve_payment",
                "invoice_id": invoice_id,
                "amount":     amount,
                "permitted":  permitted,
                "reason":     reason,
                "timestamp":  datetime.now().isoformat(),
            }) if ledger.is_available() else {"verified": False, "error": "offline"}

            _seal_line(seal_result)

            # ── Push to UI ────────────────────────────────────────────────────
            _push_to_ui({
                "agent":      agent,
                "action":     "approve_invoice",
                "invoice_id": invoice_id,
                "amount":     amount,
                "permitted":  permitted,
                "reason":     reason,
                "latency_ms": round(latency_ms, 2),
            })

            # ── Nova Act executes (or doesn't) ────────────────────────────────
            if permitted:
                instruction = f"Click the Approve button for invoice {invoice_id}"
                if nova is not None:
                    print(f"\n  {CYAN}Nova Act{RESET}  {DIM}\"{instruction}\"{RESET}")
                    nova.act(instruction)
                    print(f"  {GREEN}✓ executed{RESET}")
                else:
                    print(f"\n  {CYAN}Nova Act{RESET}  {DIM}[dry-run] \"{instruction}\"{RESET}")
            else:
                print(f"\n  {CYAN}Nova Act{RESET}  {DIM}blocked — browser untouched{RESET}")

            _hr()
            time.sleep(1.2)  # brief pause so the browser update is visible

    # ── Execute with or without Nova Act ─────────────────────────────────────
    if nova_available and _nova_import:
        with NovaAct(starting_page="http://localhost:7242", ignore_https_errors=True) as nova:
            _run_with_nova(nova)
    else:
        _run_with_nova(None)

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{BOLD}Done.{RESET}")
    print(f"  Reasoning log:  mrs/memory/reasoning_log.json")
    if ledger.is_available():
        print(f"  Verify a seal:  {CYAN}python -m ledger.verify <action_id>{RESET}")
    print()


if __name__ == "__main__":
    run()
