"""
MirrorOS + Nova Act — LedgerLark AP Orchestration Demo
=======================================================
LedgerLark (overseer agent) governs a full Accounts Payable workflow:
  - Scans the bill queue and routes each bill to clerk or auditor via MRS
  - MRS fires TWO gates per bill: routing gate + approval gate
  - Nova Act executes the approved actions in Zoho Books
  - Every decision sealed in ledger (immudb if available, JSON fallback)

What you'll see:
  - LedgerLark routes BILL-001 ($450, approved vendor) → clerk  → APPROVED
  - LedgerLark routes BILL-002 ($8,500, approved vendor) → auditor → APPROVED
  - LedgerLark routes BILL-003 ($300, unknown vendor)   → REJECTED at routing gate
  - LedgerLark routes BILL-004 ($15,000, approved vendor) → auditor → APPROVED

Browser:
  Uses ungoogled-chromium via CDP with a persistent Strikaris profile.
  Launches the browser automatically if not already running on CDP_PORT.

Prerequisites:
  export NOVA_ACT_API_KEY=<key>
  /Applications/Chromium.app must be installed (ungoogled-chromium)

Usage:
  python examples/ledgerlark_demo/ap_demo.py             # full demo with Nova Act
  python examples/ledgerlark_demo/ap_demo.py --no-browser  # terminal only

Architecture note:
  LedgerLark decides routing. MRS decides policy. Nova Act executes.
  Nova Act receives mechanical instructions only — no policy reasoning.
  Both gates fire and seal BEFORE Nova Act is invoked.
"""

from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

# ── Browser config ────────────────────────────────────────────────────────────

CHROME_BIN   = "/Applications/Chromium.app/Contents/MacOS/Chromium"
PROFILE_DIR  = Path.home() / ".mirroros" / "strikaris_profile"
CDP_PORT     = 9222
ZOHO_EXPENSES = "https://books.zoho.com/app/916562298#/expenses"

# ── Terminal colours ──────────────────────────────────────────────────────────

BOLD  = "\033[1m"
GREEN = "\033[32m"
RED   = "\033[31m"
AMBER = "\033[33m"
CYAN  = "\033[36m"
DIM   = "\033[2m"
RESET = "\033[0m"

# ── Bill queue ────────────────────────────────────────────────────────────────

BILLS = [
    {
        "bill_id":     "BILL-001",
        "vendor":      "office_supplies_co",
        "vendor_name": "Office Supplies Co",
        "amount":      450,
        "description": "Q1 office supplies",
        "note":        "$450, approved vendor → routes to clerk",
    },
    {
        "bill_id":     "BILL-002",
        "vendor":      "cloud_infra_ltd",
        "vendor_name": "Cloud Infra Ltd",
        "amount":      8_500,
        "description": "Monthly cloud infrastructure",
        "note":        "$8,500, approved vendor → routes to auditor (exceeds clerk limit)",
    },
    {
        "bill_id":     "BILL-003",
        "vendor":      "unknown_co",
        "vendor_name": "Unknown Vendor Co",
        "amount":      300,
        "description": "Miscellaneous services",
        "note":        "$300, UNKNOWN vendor → rejected at routing gate",
    },
    {
        "bill_id":     "BILL-004",
        "vendor":      "strikaris_dev",
        "vendor_name": "Strikaris Dev Services",
        "amount":      15_000,
        "description": "Development consulting — Phase 2",
        "note":        "$15,000, approved vendor → routes to auditor",
    },
]

ORCHESTRATOR = "ledgerlark"


# ── Output helpers ────────────────────────────────────────────────────────────

def _hr():
    print(f"{DIM}{'─' * 60}{RESET}")

def _header(text: str):
    print(f"\n{BOLD}{text}{RESET}")

def _gate_line(label: str, value: str, colour: str = ""):
    print(f"  {DIM}{label:<18}{RESET}{colour}{value}{RESET}")

def _verdict(permitted: bool, agent: str, action: str, reason: str, latency_ms: float):
    v = f"{GREEN}PERMITTED{RESET}" if permitted else f"{RED}REJECTED {RESET}"
    print(f"\n  {BOLD}{v}{RESET}  {AMBER}{agent}{RESET}  {action}")
    if reason and reason != "permitted":
        print(f"  {DIM}→ {reason}{RESET}")
    print(f"  {DIM}{latency_ms:.1f}ms{RESET}")

def _seal_line(result: dict):
    if result.get("verified"):
        print(f"  {DIM}Ledger   {RESET}{GREEN}sealed{RESET}  "
              f"{DIM}key={result['key']}  tx={result['tx']}{RESET}")
    elif result.get("error"):
        print(f"  {DIM}Ledger   {RESET}{DIM}offline ({result['error']}){RESET}")

def _nova_line(nova, instruction: str):
    if nova is not None:
        print(f"\n  {CYAN}Nova Act{RESET}  {DIM}\"{instruction}\"{RESET}")
        nova.act(instruction)
        print(f"  {GREEN}✓ executed{RESET}")
    else:
        print(f"\n  {CYAN}Nova Act{RESET}  {DIM}[no-browser] \"{instruction}\"{RESET}")


# ── MRS gate helper ───────────────────────────────────────────────────────────

def _gate(bridge, query: str) -> tuple[bool, str, float]:
    _gate_line("MRS gate", "running...", DIM)
    t0 = time.perf_counter()
    violations = bridge.query(query)
    latency_ms = (time.perf_counter() - t0) * 1000
    permitted  = not violations
    reason     = str(violations[0].get("Reason", "policy violation")) if violations else "permitted"
    colour     = GREEN if permitted else RED
    _gate_line("Prolog", f"{'PERMITTED' if permitted else 'REJECTED'}  ({latency_ms:.1f}ms)", colour)
    return permitted, reason, latency_ms


def _seal(ledger, action_id: str, action: str, agent: str,
          permitted: bool, reason: str, extra: dict | None = None) -> dict:
    payload = {
        "action_id": action_id,
        "agent":     agent,
        "action":    action,
        "permitted": permitted,
        "reason":    reason,
        "timestamp": datetime.now().isoformat(),
        **(extra or {}),
    }
    return (
        ledger.seal(payload)
        if ledger.is_available()
        else {"verified": False, "error": "offline"}
    )


# ── Browser launch ────────────────────────────────────────────────────────────

def _cdp_running() -> bool:
    with socket.socket() as s:
        return s.connect_ex(("localhost", CDP_PORT)) == 0


def _launch_chromium():
    """Launch ungoogled-chromium with CDP and the shared Strikaris profile."""
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.Popen([
        CHROME_BIN,
        f"--remote-debugging-port={CDP_PORT}",
        f"--user-data-dir={PROFILE_DIR}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-features=Translate",
        "--window-size=1600,900",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # Wait for CDP port to open
    for _ in range(20):
        time.sleep(0.5)
        if _cdp_running():
            return
    raise RuntimeError(f"Chromium CDP did not open on port {CDP_PORT} in time")


# ── Demo ─────────────────────────────────────────────────────────────────────

def run(nova, bridge, ledger):
    run_date = datetime.now().strftime("%Y%m%d")

    print(f"\n{BOLD}MirrorOS — LedgerLark AP Orchestration Demo{RESET}")
    print(f"{DIM}LedgerLark routes bills → MRS gates → Nova Act executes{RESET}")
    _hr()

    nova_status   = f"{GREEN}ready{RESET}" if nova is not None else f"{DIM}no-browser mode{RESET}"
    ledger_status = f"{GREEN}connected{RESET}" if ledger.is_available() else f"{DIM}offline — JSON only{RESET}"
    print(f"  {DIM}MRS bridge   {RESET}{GREEN}ready{RESET}")
    print(f"  {DIM}immudb       {RESET}{ledger_status}")
    print(f"  {DIM}Nova Act     {RESET}{nova_status}")
    print(f"  {DIM}Orchestrator {RESET}{AMBER}ledgerlark{RESET}")
    _hr()

    for i, bill in enumerate(BILLS, 1):
        bill_id     = bill["bill_id"]
        vendor      = bill["vendor"]
        vendor_name = bill["vendor_name"]
        amount      = bill["amount"]

        _header(f"Expense {i}/{len(BILLS)}  —  {bill_id}  |  {vendor_name}  |  ${amount:,}")
        print(f"  {DIM}{bill['note']}{RESET}")

        # ── Gate 1: LedgerLark routing ────────────────────────────────────────
        print(f"\n  {DIM}Gate 1  — routing{RESET}")
        _gate_line("agent", ORCHESTRATOR, AMBER)

        permitted_route, reason_route, latency_route = _gate(
            bridge,
            f"violates_ap_policy({ORCHESTRATOR}, "
            f"route_bill('{bill_id}', {amount}, {vendor}), Reason)",
        )
        _verdict(permitted_route, ORCHESTRATOR,
                 f"route_bill('{bill_id}', {amount}, {vendor})",
                 reason_route, latency_route)
        bridge._log_reasoning(
            agent=ORCHESTRATOR,
            action=f"route_bill('{bill_id}', {amount}, {vendor})",
            status="PERMITTED" if permitted_route else "REJECTED",
            details={"bill_id": bill_id, "vendor": vendor, "amount": amount,
                     "reason": reason_route, "latency_ms": round(latency_route, 2)},
        )
        _seal_line(_seal(ledger, f"ap_{run_date}_{i:03d}_route", "route_bill",
                         ORCHESTRATOR, permitted_route, reason_route,
                         {"bill_id": bill_id, "vendor": vendor, "amount": amount}))

        if not permitted_route:
            print(f"\n  {CYAN}Nova Act{RESET}  {DIM}blocked — browser untouched{RESET}")
            _hr()
            continue

        # Determine routed agent and assert fact
        routed_agent = "clerk" if amount <= 1000 else "auditor"
        bridge.assert_fact(f"routed_to('{bill_id}', {routed_agent})")
        _gate_line("routed to", routed_agent, AMBER)

        # ── Gate 2: Agent approval ────────────────────────────────────────────
        print(f"\n  {DIM}Gate 2  — approval ({routed_agent}){RESET}")
        _gate_line("agent", routed_agent, AMBER)

        permitted_approve, reason_approve, latency_approve = _gate(
            bridge,
            f"violates_ap_policy({routed_agent}, "
            f"approve_bill('{bill_id}', {amount}), Reason)",
        )
        _verdict(permitted_approve, routed_agent,
                 f"approve_bill('{bill_id}', {amount})",
                 reason_approve, latency_approve)
        bridge._log_reasoning(
            agent=routed_agent,
            action=f"approve_bill('{bill_id}', {amount})",
            status="PERMITTED" if permitted_approve else "REJECTED",
            details={"bill_id": bill_id, "vendor": vendor, "amount": amount,
                     "routed_agent": routed_agent, "reason": reason_approve,
                     "latency_ms": round(latency_approve, 2)},
        )
        _seal_line(_seal(ledger, f"ap_{run_date}_{i:03d}_approve", "approve_bill",
                         routed_agent, permitted_approve, reason_approve,
                         {"bill_id": bill_id, "vendor": vendor, "amount": amount,
                          "routed_agent": routed_agent}))

        if permitted_approve and nova is not None:
            _nova_line(nova,
                f'In Zoho Books Expenses, click "New Expense" or "Record Expense". '
                f'Set the amount to {amount}. '
                f'In the Notes or Description field enter: '
                f'"[{bill_id}] {vendor_name} — APPROVED by {routed_agent} via MirrorOS MRS".'
            )
            _nova_line(nova,
                f'For the "Paid Through" field type "Petty Cash" and press Enter. '
                f'For the "Expense Account" field type "General" and select "General (g-001)" from the dropdown. '
                f'For any other required dropdown, type a value and press Enter. '
                f'Then save the expense.'
            )

        _hr()
        time.sleep(0.8)

    # ── Summary ───────────────────────────────────────────────────────────────
    approved = sum(1 for b in BILLS if bridge.query(
        f"routed_to('{b['bill_id']}', _)"
    ) or True)  # ledger tells the real story
    print(f"\n{BOLD}Done.{RESET}")
    print(f"  {len(BILLS)} bills processed by LedgerLark")
    print(f"  Reasoning log:  mrs/memory/reasoning_log.json")
    if ledger.is_available():
        print(f"  Verify a seal:  {CYAN}python -m ledger.verify ap_{run_date}_001_route{RESET}")
    print()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="MirrorOS LedgerLark AP Orchestration Demo"
    )
    parser.add_argument("--no-browser", action="store_true",
                        help="Skip Nova Act browser automation (terminal only)")
    args = parser.parse_args()

    nova_key_set = bool(os.getenv("NOVA_ACT_API_KEY"))
    use_browser  = nova_key_set and not args.no_browser

    if not use_browser and not args.no_browser:
        print(f"{AMBER}NOVA_ACT_API_KEY not set — running in no-browser mode.{RESET}\n")

    try:
        from mrs.bridge.mrs_bridge import MRSBridge
        from ledger.immudb_client import MRSLedger
    except ImportError as exc:
        print(f"{RED}ERROR: {exc}{RESET}")
        sys.exit(1)

    ledger = MRSLedger()
    bridge = MRSBridge(
        prolog_path=str(REPO_ROOT / "mrs" / "prolog"),
        memory_path=str(REPO_ROOT / "mrs" / "memory"),
        ledger=ledger,
    )
    compliance = REPO_ROOT / "examples" / "ledgerlark_demo" / "ap_compliance.pl"
    result = bridge.load_module(str(compliance))
    if not result["success"]:
        print(f"{RED}ERROR: ap_compliance.pl failed to load: {result.get('reason')}{RESET}")
        sys.exit(1)

    if use_browser:
        try:
            from nova_act import NovaAct
        except ImportError:
            print(f"{RED}nova-act not installed: pip install nova-act{RESET}")
            sys.exit(1)

        chromium_available = Path(CHROME_BIN).exists()

        if chromium_available:
            if not _cdp_running():
                print(f"{DIM}Launching ungoogled-chromium on CDP port {CDP_PORT}...{RESET}")
                _launch_chromium()
                print(f"{GREEN}Browser ready.{RESET}  Profile: {PROFILE_DIR}\n")
            else:
                print(f"{DIM}Connecting to existing browser on port {CDP_PORT}.{RESET}\n")
            nova_kwargs = dict(
                cdp_endpoint_url=f"http://localhost:{CDP_PORT}",
                starting_page=ZOHO_EXPENSES,
                ignore_https_errors=True,
                ignore_screen_dims_check=True,
            )
        else:
            print(f"{DIM}Chromium not found — Nova Act will manage its own browser.{RESET}\n")
            nova_kwargs = dict(starting_page=ZOHO_EXPENSES)

        with NovaAct(**nova_kwargs) as nova:
            run(nova, bridge, ledger)
    else:
        run(None, bridge, ledger)
