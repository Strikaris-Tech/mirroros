"""
MirrorOS Accounting Governance Demo
====================================
Runs the 5-pulse demo scenario defined in demo_config.toml.

Every action is gated by MRS (Prolog + Z3 dual-gate) before execution.
Every decision is sealed in immudb as a cryptographically verified entry.

Usage:
    # From the repo root:
    python examples/accounting_demo/run_demo.py

    # Without immudb running (decisions logged to JSON only):
    IMMUDB_ENABLED=false python examples/accounting_demo/run_demo.py

    # Point at a remote immudb:
    IMMUDB_HOST=192.168.1.10 python examples/accounting_demo/run_demo.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

try:
    from mrs.bridge.mrs_bridge import MRSBridge
    from adapters.mock_accounting import AccountingAdapter
    from ledger.immudb_client import MRSLedger
except ImportError as exc:
    print(f"ERROR: Could not import MirrorOS modules: {exc}")
    print("Run from the repo root or install dependencies: pip install -r forge/requirements.txt")
    sys.exit(1)

# ── Terminal colours ──────────────────────────────────────────────────────────
BOLD  = "\033[1m"
GREEN = "\033[32m"
RED   = "\033[31m"
CYAN  = "\033[36m"
DIM   = "\033[2m"
RESET = "\033[0m"

# ── Demo pulse sequence ───────────────────────────────────────────────────────
# Mirrors demo_config.toml — define here for self-contained execution.
PULSES = [
    {
        "agent":      "clerk",
        "action":     "approve_invoice",
        "invoice_id": "inv_001",
        "expected":   "PERMITTED",
        "why":        "inv_001 is $200 — within clerk limit of $1,000",
    },
    {
        "agent":      "clerk",
        "action":     "approve_invoice",
        "invoice_id": "inv_002",
        "expected":   "REJECTED",
        "why":        "inv_002 is $25,000 — exceeds clerk limit of $1,000",
    },
    {
        "agent":     "clerk",
        "action":    "pay_vendor",
        "vendor_id": "unknown_co",
        "amount":    500,
        "expected":  "REJECTED",
        "why":       "unknown_co is not in the approved vendor registry",
    },
    {
        "agent":      "auditor",
        "action":     "approve_invoice",
        "invoice_id": "inv_002",
        "expected":   "PERMITTED",
        "why":        "inv_002 is $25,000 — within auditor limit of $50,000",
    },
    {
        "agent":    "auditor",
        "action":   "compliance_check",
        "expected": "PERMITTED",
        "why":      "Read-only compliance summary — always permitted",
    },
]


def _verdict_str(permitted: bool, expected: str) -> str:
    actual   = "PERMITTED" if permitted else "REJECTED"
    correct  = actual == expected
    colour   = GREEN if permitted else RED
    marker   = "" if correct else f" {RED}[unexpected]{RESET}"
    return f"{colour}{actual}{RESET}{marker}"


def run_demo() -> None:
    print(f"\n{BOLD}MirrorOS — Accounting Governance Demo{RESET}")
    print("─" * 56)

    # ── Ledger ────────────────────────────────────────────────────────────────
    immudb_enabled = os.getenv("IMMUDB_ENABLED", "true").lower() != "false"
    ledger: MRSLedger | None = None

    if immudb_enabled:
        ledger = MRSLedger(
            host     = os.getenv("IMMUDB_HOST", "localhost"),
            port     = int(os.getenv("IMMUDB_PORT", "3322")),
            username = os.getenv("IMMUDB_USER", "immudb"),
            password = os.getenv("IMMUDB_PASS", "immudb"),
            database = os.getenv("IMMUDB_DB",   "defaultdb"),
        )
        if ledger.is_available():
            print(f"Ledger:  {GREEN}immudb connected{RESET} — decisions will be cryptographically sealed")
        else:
            print(f"Ledger:  {DIM}immudb not reachable — decisions logged to JSON only{RESET}")
            ledger = None
    else:
        print(f"Ledger:  {DIM}disabled (IMMUDB_ENABLED=false){RESET}")

    # ── Bridge ────────────────────────────────────────────────────────────────
    prolog_path = str(REPO_ROOT / "mrs" / "prolog")
    memory_path = str(REPO_ROOT / "mrs" / "memory")

    print("MRS:     initialising bridge...")
    bridge = MRSBridge(
        prolog_path = prolog_path,
        memory_path = memory_path,
        ledger      = ledger,
    )

    # Load accounting compliance rules
    compliance_pl = str(REPO_ROOT / "examples" / "accounting_demo" / "accounting_compliance.pl")
    result = bridge.load_module(compliance_pl)
    if result["success"]:
        print(f"Codex:   {GREEN}accounting_compliance.pl loaded{RESET}")
    else:
        print(f"Codex:   {RED}WARNING — compliance module failed to load: {result.get('reason')}{RESET}")

    print()

    # ── Adapter ───────────────────────────────────────────────────────────────
    adapter = AccountingAdapter(bridge)

    # ── Run pulses ────────────────────────────────────────────────────────────
    print(f"{BOLD}Running {len(PULSES)} governed pulses...{RESET}\n")

    results = []

    for i, pulse in enumerate(PULSES, 1):
        agent    = pulse["agent"]
        action   = pulse["action"]
        expected = pulse["expected"]

        if action == "approve_invoice":
            result = adapter.approve_invoice(agent, pulse["invoice_id"])
        elif action == "pay_vendor":
            result = adapter.pay_vendor(agent, pulse["vendor_id"], pulse["amount"])
        elif action == "compliance_check":
            result = adapter.compliance_check(agent)
        else:
            result = {"permitted": False, "reason": f"unknown action: {action}", "latency_ms": 0}

        permitted  = result.get("permitted", False)
        reason     = result.get("reason", "")
        latency_ms = result.get("latency_ms", 0.0)
        verdict    = _verdict_str(permitted, expected)

        amount_str = ""
        if "amount" in result:
            amount_str = f"  ${result['amount']:,}"

        print(f"  {i}. {verdict}  {agent:<10} {action:<18}{amount_str}")
        if reason and reason != "permitted":
            print(f"          {DIM}→ {reason}{RESET}")
        print(f"          {DIM}{pulse['why']}{RESET}  ({latency_ms:.1f}ms)")
        print()

        results.append({
            "pulse":     i,
            "agent":     agent,
            "action":    action,
            "permitted": permitted,
            "expected":  expected,
            "reason":    reason,
            "latency_ms": latency_ms,
        })

    # ── Ledger summary ────────────────────────────────────────────────────────
    print("─" * 56)
    reasoning_log = REPO_ROOT / "mrs" / "memory" / "reasoning_log.json"
    if reasoning_log.exists():
        with open(reasoning_log) as f:
            entries = json.load(f)
        print(f"Reasoning log:  {len(entries)} entries → {reasoning_log.relative_to(REPO_ROOT)}")

    if ledger and ledger.is_available():
        print(f"Ledger:         {GREEN}decisions sealed in immudb — verified=True on every write{RESET}")
        print(f"Verify any entry:  python -m ledger.verify <action_id>")
    else:
        print(f"Ledger:         {DIM}decisions logged to JSON (immudb not connected){RESET}")

    # ── Pass/fail summary ─────────────────────────────────────────────────────
    total    = len(results)
    correct  = sum(1 for r in results if ("PERMITTED" if r["permitted"] else "REJECTED") == r["expected"])
    print()
    print(f"Result:  {correct}/{total} pulses matched expected verdict", end="")
    if correct == total:
        print(f"  {GREEN}✓{RESET}")
    else:
        print(f"  {RED}— check reasoning_log.json for details{RESET}")
    print()


if __name__ == "__main__":
    run_demo()
