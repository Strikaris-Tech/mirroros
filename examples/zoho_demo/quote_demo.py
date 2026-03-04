"""
MirrorOS + Nova Vision — Governed Quote-to-Cash Demo
=====================================================
Demonstrates MRS governing a complete Strikaris → Khan Mall workflow.

What you'll see:
  - Terminal shows MRS gate firing at every stage transition
  - Khan Mall PO response PDF generated with randomised variations
  - Nova Vision (Amazon Nova Pro) reads the signed PO
  - MRS evaluates document variance against strict 2% tolerance
  - MATCH:    workflow proceeds through fulfillment → invoice generated
  - MISMATCH: workflow halts, variance detail sealed in ledger

Stages:
  1  create_quote       — sales_rep authorised for $15,000?
  2  po_receipt         — generate Khan Mall's PO response PDF
  3  approve_document   — Nova Vision extracts PO, MRS compares to quote
  4  start_fulfillment  — document verified?  (blocked if stage 3 failed)
  5  generate_invoice   — document verified?  (blocked if stage 3 failed)

Usage:
  python examples/zoho_demo/quote_demo.py              # EXACT match (happy path)
  python examples/zoho_demo/quote_demo.py --seed 99    # PRICE_COUNTER (exception)
  python examples/zoho_demo/quote_demo.py --live       # real Nova Vision via Bedrock
  python examples/zoho_demo/quote_demo.py --open-pdf   # open generated PDF after stage 2

Architecture note:
  Nova Vision receives an extraction task, not a policy decision.
  MRS evaluates the extracted numbers against Prolog rules.
  The LLM reads — MRS decides.
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

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


# ── MRS gate helper ────────────────────────────────────────────────────────────

def _gate(bridge, ledger, query: str, action_label: str) -> tuple[bool, str, float]:
    """Run a gate query, return (permitted, reason, latency_ms)."""
    _gate_line("MRS gate", "running...", DIM)
    t0 = time.perf_counter()
    violations = bridge.query(query)
    latency_ms = (time.perf_counter() - t0) * 1000
    permitted  = not violations
    reason     = str(violations[0].get("Reason", "policy violation")) if violations else "permitted"
    colour     = GREEN if permitted else RED
    _gate_line("Prolog", f"{'PERMITTED' if permitted else 'REJECTED'}  ({latency_ms:.1f}ms)", colour)
    return permitted, reason, latency_ms


def _seal(ledger, action_id: str, agent: str, action: str, permitted: bool,
          reason: str, extra: dict | None = None) -> dict:
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


# ── Demo stages ────────────────────────────────────────────────────────────────

def run(seed: int, live_vision: bool, open_pdf: bool):
    print(f"\n{BOLD}MirrorOS — Governed Quote-to-Cash Demo{RESET}")
    print(f"{DIM}Strikaris → Khan Mall  |  Shopify Development Services{RESET}")
    print(f"{DIM}Quote: {QUOTE_ID}  |  ${QUOTE_TOTAL:,}{RESET}")
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
    vision_source = f"{CYAN}Nova Pro (live){RESET}" if live_vision else f"{DIM}mock{RESET}"

    print(f"  {DIM}MRS bridge  {RESET}{GREEN}ready{RESET}")
    print(f"  {DIM}Codex       {RESET}{codex_status}")
    print(f"  {DIM}immudb      {RESET}{ledger_status}")
    print(f"  {DIM}Nova Vision {RESET}{vision_source}")
    _hr()

    run_date = datetime.now().strftime("%Y%m%d")

    # ─────────────────────────────────────────────────────────────────────────
    # Stage 1 — Quote creation
    # ─────────────────────────────────────────────────────────────────────────
    _header(f"Stage 1/5  —  quote_creation")
    print(f"  {DIM}{AGENT} → create_quote('{QUOTE_ID}', {QUOTE_TOTAL}){RESET}\n")

    permitted, reason, latency_ms = _gate(
        bridge, ledger,
        f"violates_quote_policy({AGENT}, create_quote('{QUOTE_ID}', {QUOTE_TOTAL}), Reason)",
        "create_quote",
    )
    _verdict(permitted, f"create_quote('{QUOTE_ID}', {QUOTE_TOTAL})", reason, latency_ms)
    seal = _seal(ledger, f"quote_{run_date}_001", AGENT, "create_quote", permitted, reason,
                 {"quote_id": QUOTE_ID, "amount": QUOTE_TOTAL})
    _seal_line(seal)

    if not permitted:
        print(f"\n{RED}Workflow halted at stage 1.{RESET}\n")
        return

    _hr()

    # ─────────────────────────────────────────────────────────────────────────
    # Stage 2 — PO receipt
    # ─────────────────────────────────────────────────────────────────────────
    _header("Stage 2/5  —  po_receipt")
    print(f"  {DIM}Generating Khan Mall PO response (seed={seed})...{RESET}")

    from ledger.po_generator import generate_po
    po = generate_po(seed=seed)

    print(f"  {DIM}Variation   {RESET}{AMBER}{po['variation']}{RESET}  {DIM}{po['label']}{RESET}")
    print(f"  {DIM}PO total    {RESET}${po['po_total']:,}  "
          f"{DIM}(quoted ${po['quote_total']:,}){RESET}")
    variance_pct = abs(po["po_total"] - po["quote_total"]) / po["quote_total"] * 100
    print(f"  {DIM}Variance    {RESET}"
          f"{'%s%.1f%%%s' % (RED, variance_pct, RESET) if variance_pct > 2 else '%.1f%%' % variance_pct}")
    print(f"  {DIM}PDF         {RESET}{DIM}{po['pdf_path']}{RESET}")

    if open_pdf:
        import subprocess
        subprocess.run(["open", po["pdf_path"]], check=False)

    _hr()

    # ─────────────────────────────────────────────────────────────────────────
    # Stage 3 — Document verification (Nova Vision + MRS)
    # ─────────────────────────────────────────────────────────────────────────
    _header("Stage 3/5  —  document_verification")
    source_label = "Nova Pro" if live_vision else "mock"
    print(f"  {DIM}Nova Vision ({source_label})  extracting PO...{RESET}\n")

    from ledger.vision import extract_po
    extracted = extract_po(po["pdf_path"], mock=not live_vision, mock_data=po)

    po_total    = extracted.get("grand_total") or 0
    sig_present = extracted.get("signature_present", False)
    init_present = extracted.get("initials_present", False)

    print(f"  {DIM}PO number   {RESET}{extracted.get('po_number', '—')}")
    print(f"  {DIM}Reference   {RESET}{extracted.get('reference_quote', '—')}")
    print(f"  {DIM}Line items  {RESET}{len(extracted.get('line_items', []))}")
    print(f"  {DIM}PO total    {RESET}${po_total:,}")
    sig_colour = GREEN if sig_present else RED
    print(f"  {DIM}Signature   {RESET}{sig_colour}{'present' if sig_present else 'MISSING'}{RESET}")

    permitted, reason, latency_ms = _gate(
        bridge, ledger,
        (f"violates_quote_policy(_, "
         f"approve_document('{QUOTE_ID}', {po_total}, {QUOTE_TOTAL}), Reason)"),
        "approve_document",
    )
    _verdict(permitted, f"approve_document('{QUOTE_ID}', {po_total}, {QUOTE_TOTAL})",
             reason, latency_ms)
    seal = _seal(ledger, f"quote_{run_date}_002", AGENT, "approve_document", permitted, reason,
                 {"quote_id": QUOTE_ID, "po_total": po_total, "quote_total": QUOTE_TOTAL,
                  "variance_pct": round(variance_pct, 2)})
    _seal_line(seal)

    if permitted:
        # Assert document_verified so stages 4 and 5 are unblocked
        bridge.assert_fact(f"document_verified('{QUOTE_ID}')")
        print(f"  {DIM}→ document_verified('{QUOTE_ID}') asserted{RESET}")
    else:
        print(f"\n{RED}Workflow halted — fulfillment blocked.{RESET}")
        print(f"{DIM}Variance detail sealed. Exception path: draft rejection notice.{RESET}\n")
        return

    _hr()

    # ─────────────────────────────────────────────────────────────────────────
    # Stage 4 — Fulfillment authorisation
    # ─────────────────────────────────────────────────────────────────────────
    _header("Stage 4/5  —  fulfillment_auth")
    print(f"  {DIM}{AGENT} → start_fulfillment('{QUOTE_ID}'){RESET}\n")

    permitted, reason, latency_ms = _gate(
        bridge, ledger,
        f"violates_quote_policy(_, start_fulfillment('{QUOTE_ID}'), Reason)",
        "start_fulfillment",
    )
    _verdict(permitted, f"start_fulfillment('{QUOTE_ID}')", reason, latency_ms)
    seal = _seal(ledger, f"quote_{run_date}_003", AGENT, "start_fulfillment", permitted, reason,
                 {"quote_id": QUOTE_ID})
    _seal_line(seal)

    if not permitted:
        print(f"\n{RED}Workflow halted at stage 4.{RESET}\n")
        return

    _hr()

    # ─────────────────────────────────────────────────────────────────────────
    # Stage 5 — Invoice generation
    # ─────────────────────────────────────────────────────────────────────────
    _header("Stage 5/5  —  invoice_generation")
    print(f"  {DIM}{AGENT} → generate_invoice('{QUOTE_ID}', {QUOTE_TOTAL}){RESET}\n")

    permitted, reason, latency_ms = _gate(
        bridge, ledger,
        f"violates_quote_policy(_, generate_invoice('{QUOTE_ID}', {QUOTE_TOTAL}), Reason)",
        "generate_invoice",
    )
    _verdict(permitted, f"generate_invoice('{QUOTE_ID}', {QUOTE_TOTAL})", reason, latency_ms)
    seal = _seal(ledger, f"quote_{run_date}_004", AGENT, "generate_invoice", permitted, reason,
                 {"quote_id": QUOTE_ID, "amount": QUOTE_TOTAL})
    _seal_line(seal)

    if not permitted:
        print(f"\n{RED}Workflow halted at stage 5.{RESET}\n")
        return

    _hr()

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{BOLD}Done.{RESET}  Quote {QUOTE_ID} → invoice generated.")
    print(f"  PDF:            {po['pdf_path']}")
    print(f"  Reasoning log:  mrs/memory/reasoning_log.json")
    if ledger.is_available():
        print(f"  Verify a seal:  {CYAN}python -m ledger.verify quote_{run_date}_001{RESET}")
    print()


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MirrorOS Zoho Quote-to-Cash Demo")
    parser.add_argument("--seed",     type=int, default=42,
                        help="PO variation seed (42=EXACT, 99=PRICE_COUNTER, "
                             "77=QUANTITY_CHANGE, 55=PARTIAL_ACCEPTANCE)")
    parser.add_argument("--live",     action="store_true",
                        help="Use real Nova Vision via Bedrock "
                             "(requires AWS_BEARER_TOKEN_BEDROCK)")
    parser.add_argument("--open-pdf", action="store_true",
                        help="Open generated PO PDF after stage 2")
    args = parser.parse_args()
    run(seed=args.seed, live_vision=args.live, open_pdf=args.open_pdf)
