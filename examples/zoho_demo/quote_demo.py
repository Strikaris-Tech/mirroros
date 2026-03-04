"""
MirrorOS + Nova Act + Nova Vision — Governed Quote-to-Cash Demo
===============================================================
Demonstrates MRS governing a complete Strikaris → Khan Mall workflow
with Nova Act driving Zoho Books and Nova Vision reading the PO response.

What you'll see:
  - Nova Act opens Zoho Books and creates the quote (stage 1)
  - Khan Mall PO response PDF generated with randomised variations (stage 2)
  - Nova Vision (Amazon Nova Pro) reads the signed PO (stage 3)
  - MRS evaluates document variance against strict 2% tolerance
  - MATCH:    Nova Act marks quote Accepted → converts to Invoice (stages 4-5)
  - MISMATCH: workflow halts, variance detail sealed in ledger

Stages:
  1  create_quote       — MRS gates, Nova Act creates quote in Zoho Books
  2  po_receipt         — generate Khan Mall's PO response PDF
  3  approve_document   — Nova Vision extracts PO, MRS compares to quote
  4  start_fulfillment  — MRS gates, Nova Act marks quote Accepted
  5  generate_invoice   — MRS gates, Nova Act converts quote to Invoice

Prerequisites:
  export NOVA_ACT_API_KEY=<key>          # Nova Act browser automation
  export AWS_BEARER_TOKEN_BEDROCK=<key>  # Nova Vision (--live mode only)
  pip install reportlab                   # PDF generation

Usage:
  python examples/zoho_demo/quote_demo.py              # EXACT match, dry-run Nova Vision
  python examples/zoho_demo/quote_demo.py --seed 99    # PRICE_COUNTER (exception path)
  python examples/zoho_demo/quote_demo.py --live       # real Nova Vision via Bedrock
  python examples/zoho_demo/quote_demo.py --no-browser # terminal-only, no Nova Act

Architecture note:
  Nova Act receives mechanical instructions, not policy reasoning.
  MRS gates fire BEFORE Nova Act is invoked — the decision is already
  made and sealed by the time Nova Act moves the cursor.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

# ── Zoho Books ────────────────────────────────────────────────────────────────

ZOHO_URL  = "https://books.zoho.com/app/916562298"
QUOTE_TITLE = f"Shopify Dev Services {datetime.now().strftime('%b %d, %Y')}"

# ── Terminal colours ───────────────────────────────────────────────────────────

BOLD  = "\033[1m"
GREEN = "\033[32m"
RED   = "\033[31m"
AMBER = "\033[33m"
CYAN  = "\033[36m"
DIM   = "\033[2m"
RESET = "\033[0m"

QUOTE_ID    = "STR-2026-Q-018"
QUOTE_TOTAL = 15_000
AGENT       = "sales_rep"


def _hr():
    print(f"{DIM}{'─' * 60}{RESET}")

def _header(text: str):
    print(f"\n{BOLD}{text}{RESET}")

def _gate_line(label: str, value: str, colour: str = ""):
    print(f"  {DIM}{label:<16}{RESET}{colour}{value}{RESET}")

def _verdict(permitted: bool, action: str, reason: str, latency_ms: float):
    v = f"{GREEN}PERMITTED{RESET}" if permitted else f"{RED}REJECTED {RESET}"
    print(f"\n  {BOLD}{v}{RESET}  {action}")
    if reason and reason != "permitted":
        print(f"  {DIM}→ {reason}{RESET}")
    print(f"  {DIM}{latency_ms:.1f}ms{RESET}")

def _seal_line(result: dict):
    if result.get("verified"):
        print(f"  {DIM}Ledger  {RESET}{GREEN}sealed{RESET}  "
              f"{DIM}key={result['key']}  tx={result['tx']}{RESET}")
    elif result.get("error"):
        print(f"  {DIM}Ledger  {RESET}{DIM}offline ({result['error']}){RESET}")

def _nova_line(nova, instruction: str):
    """Execute a Nova Act instruction, or print dry-run notice."""
    if nova is not None:
        print(f"\n  {CYAN}Nova Act{RESET}  {DIM}\"{instruction}\"{RESET}")
        nova.act(instruction)
        print(f"  {GREEN}✓ executed{RESET}")
    else:
        print(f"\n  {CYAN}Nova Act{RESET}  {DIM}[no-browser] \"{instruction}\"{RESET}")


# ── MRS gate helper ────────────────────────────────────────────────────────────

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


def _seal(ledger, action_id: str, action: str, permitted: bool,
          reason: str, extra: dict | None = None) -> dict:
    payload = {
        "action_id": action_id,
        "agent":     AGENT,
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


# ── Demo ───────────────────────────────────────────────────────────────────────

def run(nova, seed: int, live_vision: bool):
    print(f"\n{BOLD}MirrorOS — Governed Quote-to-Cash Demo{RESET}")
    print(f"{DIM}Strikaris → Khan Mall  |  Shopify Development Services{RESET}")
    print(f"{DIM}Quote: {QUOTE_ID}  |  ${QUOTE_TOTAL:,}  |  \"{QUOTE_TITLE}\"{RESET}")
    _hr()

    # ── Bridge + ledger ───────────────────────────────────────────────────────
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
    compliance = REPO_ROOT / "examples" / "zoho_demo" / "quote_compliance.pl"
    result     = bridge.load_module(str(compliance))

    ledger_status = (f"{GREEN}connected{RESET}" if ledger.is_available()
                     else f"{DIM}offline — JSON only{RESET}")
    codex_status  = (f"{GREEN}loaded{RESET}" if result["success"]
                     else f"{RED}FAILED{RESET}")
    nova_status   = (f"{GREEN}ready{RESET}" if nova is not None
                     else f"{DIM}no-browser mode{RESET}")
    vision_source = f"{CYAN}Nova Pro (live){RESET}" if live_vision else f"{DIM}mock{RESET}"

    print(f"  {DIM}MRS bridge  {RESET}{GREEN}ready{RESET}")
    print(f"  {DIM}Codex       {RESET}{codex_status}")
    print(f"  {DIM}immudb      {RESET}{ledger_status}")
    print(f"  {DIM}Nova Act    {RESET}{nova_status}")
    print(f"  {DIM}Nova Vision {RESET}{vision_source}")
    _hr()

    run_date = datetime.now().strftime("%Y%m%d")

    # ─────────────────────────────────────────────────────────────────────────
    # Stage 1 — Quote creation
    # ─────────────────────────────────────────────────────────────────────────
    _header(f"Stage 1/5  —  quote_creation")
    print(f"  {DIM}{AGENT} → create_quote('{QUOTE_ID}', {QUOTE_TOTAL}){RESET}\n")

    permitted, reason, latency_ms = _gate(
        bridge,
        f"violates_quote_policy({AGENT}, create_quote('{QUOTE_ID}', {QUOTE_TOTAL}), Reason)",
    )
    _verdict(permitted, f"create_quote('{QUOTE_ID}', {QUOTE_TOTAL})", reason, latency_ms)
    _seal_line(_seal(ledger, f"quote_{run_date}_001", "create_quote", permitted, reason,
                     {"quote_id": QUOTE_ID, "amount": QUOTE_TOTAL}))

    if not permitted:
        print(f"\n{RED}Workflow halted at stage 1.{RESET}\n")
        return

    _nova_line(nova,
        f'In Zoho Books, create a new quote for customer "Khan Mall" with subject '
        f'"{QUOTE_TITLE}". Add these three line items exactly: '
        f'(1) "Shopify Discovery & Architecture", quantity 1, rate 2500; '
        f'(2) "Sprint 1 Implementation", quantity 1, rate 8500; '
        f'(3) "Platform Integration", quantity 1, rate 4000. '
        f'Save the quote.'
    )
    _hr()

    # ─────────────────────────────────────────────────────────────────────────
    # Stage 2 — PO receipt
    # ─────────────────────────────────────────────────────────────────────────
    _header("Stage 2/5  —  po_receipt")
    print(f"  {DIM}Generating Khan Mall PO response (seed={seed})...{RESET}")

    from ledger.po_generator import generate_po
    po = generate_po(seed=seed)

    variance_pct = abs(po["po_total"] - po["quote_total"]) / po["quote_total"] * 100
    var_colour   = RED if variance_pct > 2 else ""
    print(f"  {DIM}Variation   {RESET}{AMBER}{po['variation']}{RESET}  "
          f"{DIM}{po['label']}{RESET}")
    print(f"  {DIM}PO total    {RESET}${po['po_total']:,}  "
          f"{DIM}(quoted ${po['quote_total']:,}){RESET}")
    print(f"  {DIM}Variance    {RESET}"
          f"{var_colour}{variance_pct:.1f}%{RESET if var_colour else ''}")
    print(f"  {DIM}PDF         {RESET}{DIM}{po['pdf_path']}{RESET}")
    _hr()

    # ─────────────────────────────────────────────────────────────────────────
    # Stage 3 — Document verification (Nova Vision + MRS)
    # ─────────────────────────────────────────────────────────────────────────
    _header("Stage 3/5  —  document_verification")
    source_label = "Nova Pro" if live_vision else "mock"
    print(f"  {DIM}Nova Vision ({source_label})  extracting PO...{RESET}\n")

    from ledger.vision import extract_po
    extracted = extract_po(po["pdf_path"], mock=not live_vision, mock_data=po)

    po_total     = extracted.get("grand_total") or 0
    sig_present  = extracted.get("signature_present", False)
    sig_colour   = GREEN if sig_present else RED

    print(f"  {DIM}PO number   {RESET}{extracted.get('po_number', '—')}")
    print(f"  {DIM}Reference   {RESET}{extracted.get('reference_quote', '—')}")
    print(f"  {DIM}Line items  {RESET}{len(extracted.get('line_items', []))}")
    print(f"  {DIM}PO total    {RESET}${po_total:,}")
    print(f"  {DIM}Signature   {RESET}{sig_colour}"
          f"{'present' if sig_present else 'MISSING'}{RESET}")

    permitted, reason, latency_ms = _gate(
        bridge,
        (f"violates_quote_policy(_, "
         f"approve_document('{QUOTE_ID}', {po_total}, {QUOTE_TOTAL}), Reason)"),
    )
    _verdict(permitted, f"approve_document('{QUOTE_ID}', {po_total}, {QUOTE_TOTAL})",
             reason, latency_ms)
    _seal_line(_seal(ledger, f"quote_{run_date}_002", "approve_document", permitted, reason,
                     {"quote_id": QUOTE_ID, "po_total": po_total,
                      "quote_total": QUOTE_TOTAL, "variance_pct": round(variance_pct, 2)}))

    if permitted:
        bridge.assert_fact(f"document_verified('{QUOTE_ID}')")
        print(f"  {DIM}→ document_verified('{QUOTE_ID}') asserted{RESET}")
    else:
        print(f"\n{RED}Workflow halted — fulfillment blocked.{RESET}")
        print(f"{DIM}Variance detail sealed. Rejection notice should be drafted.{RESET}\n")
        return

    _hr()

    # ─────────────────────────────────────────────────────────────────────────
    # Stage 4 — Fulfillment authorisation
    # ─────────────────────────────────────────────────────────────────────────
    _header("Stage 4/5  —  fulfillment_auth")
    print(f"  {DIM}{AGENT} → start_fulfillment('{QUOTE_ID}'){RESET}\n")

    permitted, reason, latency_ms = _gate(
        bridge,
        f"violates_quote_policy(_, start_fulfillment('{QUOTE_ID}'), Reason)",
    )
    _verdict(permitted, f"start_fulfillment('{QUOTE_ID}')", reason, latency_ms)
    _seal_line(_seal(ledger, f"quote_{run_date}_003", "start_fulfillment", permitted, reason,
                     {"quote_id": QUOTE_ID}))

    if not permitted:
        print(f"\n{RED}Workflow halted at stage 4.{RESET}\n")
        return

    _nova_line(nova,
        f'In Zoho Books, find the quote titled "{QUOTE_TITLE}" for Khan Mall '
        f'and mark it as Accepted.'
    )
    _hr()

    # ─────────────────────────────────────────────────────────────────────────
    # Stage 5 — Invoice generation
    # ─────────────────────────────────────────────────────────────────────────
    _header("Stage 5/5  —  invoice_generation")
    print(f"  {DIM}{AGENT} → generate_invoice('{QUOTE_ID}', {QUOTE_TOTAL}){RESET}\n")

    permitted, reason, latency_ms = _gate(
        bridge,
        f"violates_quote_policy(_, generate_invoice('{QUOTE_ID}', {QUOTE_TOTAL}), Reason)",
    )
    _verdict(permitted, f"generate_invoice('{QUOTE_ID}', {QUOTE_TOTAL})", reason, latency_ms)
    _seal_line(_seal(ledger, f"quote_{run_date}_004", "generate_invoice", permitted, reason,
                     {"quote_id": QUOTE_ID, "amount": QUOTE_TOTAL}))

    if not permitted:
        print(f"\n{RED}Workflow halted at stage 5.{RESET}\n")
        return

    _nova_line(nova,
        f'In Zoho Books, find the quote titled "{QUOTE_TITLE}" for Khan Mall '
        f'that is now Accepted and convert it to an Invoice. Save the invoice.'
    )
    _hr()

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{BOLD}Done.{RESET}  {QUOTE_ID} → invoice generated in Zoho Books.")
    print(f"  PDF:            {po['pdf_path']}")
    print(f"  Reasoning log:  mrs/memory/reasoning_log.json")
    if ledger.is_available():
        print(f"  Verify a seal:  {CYAN}python -m ledger.verify quote_{run_date}_001{RESET}")
    print()


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MirrorOS Zoho Quote-to-Cash Demo")
    parser.add_argument("--seed",       type=int, default=42,
                        help="PO variation seed  (42=EXACT  99=PRICE_COUNTER  "
                             "77=QUANTITY_CHANGE  55=PARTIAL_ACCEPTANCE)")
    parser.add_argument("--live",       action="store_true",
                        help="Use real Nova Vision via Bedrock "
                             "(requires AWS_BEARER_TOKEN_BEDROCK)")
    parser.add_argument("--no-browser", action="store_true",
                        help="Skip Nova Act browser automation (terminal only)")
    args = parser.parse_args()

    nova_available = bool(os.getenv("NOVA_ACT_API_KEY")) and not args.no_browser

    if not nova_available and not args.no_browser:
        print(f"{AMBER}NOVA_ACT_API_KEY not set — running in no-browser mode.{RESET}")
        print(f"{DIM}MRS gates and Nova Vision run fully. "
              f"Nova Act instructions printed but not executed.{RESET}\n")

    try:
        from nova_act import NovaAct
        _nova_import = True
    except ImportError:
        _nova_import = False
        if nova_available:
            print(f"{RED}nova-act not installed: pip install nova-act{RESET}\n")
            nova_available = False

    if nova_available and _nova_import:
        with NovaAct(starting_page=ZOHO_URL, ignore_https_errors=True) as nova:
            run(nova, seed=args.seed, live_vision=args.live)
    else:
        run(None, seed=args.seed, live_vision=args.live)
