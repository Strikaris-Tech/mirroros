"""
Demo UI server for the MirrorOS accounting governance demo.

Serves the invoice approval page and exposes REST endpoints that both
the browser and nova_demo.py interact with.  Tracks invoice state and
MRS verdict history in memory.

Usage:
    python examples/accounting_demo/server.py

    Then open http://localhost:7242 — or let nova_demo.py open it.

Endpoints:
    GET  /                      — invoice approval UI
    GET  /api/invoices          — current invoice state (JSON)
    POST /api/approve/{id}      — MRS-gated approval (browser-triggered)
    POST /api/mrs/verdict       — called by nova_demo.py to push a verdict
    GET  /api/verdicts          — full verdict + invoice state (for polling)
    POST /api/mark_approved/{id} — set invoice approved after Nova Act clicks (no gate re-run)
    POST /api/reset             — reset all invoices to pending, clear verdict log
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# ── Invoice state ─────────────────────────────────────────────────────────────

_INVOICE_DEFAULTS: dict[str, dict[str, Any]] = {
    # ── Invoices exercised by the 6-pulse demo ─────────────────────────────
    "inv_001": {"vendor": "acme_corp",        "vendor_name": "Acme Corp",           "amount":    200, "status": "pending"},
    "inv_002": {"vendor": "trusted_supplier", "vendor_name": "Trusted Supplier Inc","amount":  25000, "status": "pending"},
    "inv_003": {"vendor": "unknown_co",       "vendor_name": "Unknown Co",          "amount":    500, "status": "pending"},
    "inv_004": {"vendor": "city_utilities",   "vendor_name": "City Utilities",      "amount":    950, "status": "pending"},
    # ── Remaining AP queue (pending — show the real backlog) ───────────────
    "inv_005": {"vendor": "acme_corp",        "vendor_name": "Acme Corp",           "amount":    450, "status": "pending"},
    "inv_006": {"vendor": "global_parts_ltd", "vendor_name": "Global Parts Ltd",    "amount":   1850, "status": "pending"},
    "inv_007": {"vendor": "apex_consulting",  "vendor_name": "Apex Consulting",     "amount":   3200, "status": "pending"},
    "inv_008": {"vendor": "trusted_supplier", "vendor_name": "Trusted Supplier Inc","amount":    780, "status": "pending"},
    "inv_009": {"vendor": "city_utilities",   "vendor_name": "City Utilities",      "amount":    125, "status": "pending"},
    "inv_010": {"vendor": "unknown_co",       "vendor_name": "Unknown Co",          "amount":   2200, "status": "pending"},
    "inv_011": {"vendor": "apex_consulting",  "vendor_name": "Apex Consulting",     "amount":  62000, "status": "pending"},
    "inv_012": {"vendor": "global_parts_ltd", "vendor_name": "Global Parts Ltd",    "amount":    560, "status": "pending"},
    "inv_013": {"vendor": "acme_corp",        "vendor_name": "Acme Corp",           "amount":   8900, "status": "pending"},
    "inv_014": {"vendor": "trusted_supplier", "vendor_name": "Trusted Supplier Inc","amount":    450, "status": "pending"},
    "inv_015": {"vendor": "city_utilities",   "vendor_name": "City Utilities",      "amount":  11500, "status": "pending"},
}

def _fresh_invoices() -> dict[str, dict[str, Any]]:
    return {k: dict(v) for k, v in _INVOICE_DEFAULTS.items()}

INVOICES: dict[str, dict[str, Any]] = _fresh_invoices()

# Running verdict log — displayed in the UI decision panel
VERDICTS: list[dict[str, Any]] = []

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="MirrorOS Demo UI", docs_url=None, redoc_url=None)

UI_PATH = Path(__file__).parent / "demo_ui"


@app.get("/", response_class=HTMLResponse)
async def root():
    index = UI_PATH / "index.html"
    return HTMLResponse(index.read_text())


@app.get("/api/invoices")
async def get_invoices():
    return JSONResponse(INVOICES)


@app.post("/api/approve/{invoice_id}")
async def approve(invoice_id: str):
    """
    Browser-triggered approval endpoint.

    In the Nova Act demo this is called when Nova Act clicks the Approve
    button.  The MRS gate runs here — the browser never knew whether the
    action would be permitted until this response comes back.
    """
    invoice = INVOICES.get(invoice_id)
    if not invoice:
        return JSONResponse({"permitted": False, "reason": f"Invoice '{invoice_id}' not found"}, status_code=404)

    # Lazy-import bridge so the server starts without Prolog if needed
    try:
        from mrs.bridge.mrs_bridge import MRSBridge
        from ledger.immudb_client import MRSLedger

        bridge = _get_bridge()
        amount = invoice["amount"]
        t0 = time.perf_counter()

        violations = bridge.query(
            f"violates_accounting_policy(clerk, "
            f"approve_payment('{invoice_id}', {amount}), Reason)"
        )
        latency_ms = (time.perf_counter() - t0) * 1000

        permitted = not violations
        reason = str(violations[0].get("Reason", "policy violation")) if violations else "permitted"

        if permitted:
            INVOICES[invoice_id]["status"] = "approved"
        else:
            INVOICES[invoice_id]["status"] = "blocked"

    except Exception as exc:
        # Bridge not available — permit for UI testing only
        permitted = True
        reason = "permitted (bridge unavailable)"
        latency_ms = 0.0
        INVOICES[invoice_id]["status"] = "approved"

    result = {
        "permitted":  permitted,
        "agent":      "clerk",
        "action":     "approve_invoice",
        "invoice_id": invoice_id,
        "amount":     invoice["amount"],
        "reason":     reason,
        "latency_ms": round(latency_ms, 2),
        "time":       datetime.now().strftime("%H:%M:%S"),
    }
    VERDICTS.append(result)
    return JSONResponse(result)


@app.post("/api/mrs/verdict")
async def push_verdict(payload: dict):
    """
    Called by nova_demo.py to push a verdict into the UI verdict panel.

    nova_demo.py runs the MRS gate externally (so it can gate before
    Nova Act acts) and then POSTs the result here so the browser reflects it.
    """
    invoice_id = payload.get("invoice_id")
    permitted  = payload.get("permitted", False)

    if invoice_id and invoice_id in INVOICES:
        # Only pre-set "blocked" immediately — "approved" waits for Nova Act's actual click.
        if not permitted:
            INVOICES[invoice_id]["status"] = "blocked"

    payload.setdefault("time", datetime.now().strftime("%H:%M:%S"))
    VERDICTS.append(payload)
    return JSONResponse({"ok": True})


@app.get("/api/verdicts")
async def get_verdicts():
    return JSONResponse({"invoices": INVOICES, "verdicts": VERDICTS})


@app.post("/api/mark_approved/{invoice_id}")
async def mark_approved(invoice_id: str):
    """
    Mark an invoice approved without re-running the gate.

    Called by the Approve button in the browser UI after Nova Act clicks it.
    The governance decision was already made (and logged) by nova_demo.py;
    this endpoint simply updates the visible status so the UI reflects it.
    """
    invoice = INVOICES.get(invoice_id)
    if not invoice:
        return JSONResponse({"error": f"Invoice '{invoice_id}' not found"}, status_code=404)
    INVOICES[invoice_id]["status"] = "approved"
    return JSONResponse({
        "permitted":  True,
        "invoice_id": invoice_id,
        "amount":     invoice["amount"],
        "action":     "approve_invoice",
        "time":       datetime.now().strftime("%H:%M:%S"),
    })


@app.post("/api/reset")
async def reset():
    """Reset all invoices to pending and clear the verdict log. Call before each demo run."""
    global INVOICES, VERDICTS
    INVOICES = _fresh_invoices()
    VERDICTS = []
    return JSONResponse({"ok": True})


# ── Bridge singleton ──────────────────────────────────────────────────────────

_bridge_instance = None

def _get_bridge():
    global _bridge_instance
    if _bridge_instance is None:
        from mrs.bridge.mrs_bridge import MRSBridge
        from ledger.immudb_client import MRSLedger

        repo_root = Path(__file__).resolve().parents[2]
        _bridge_instance = MRSBridge(
            prolog_path=str(repo_root / "mrs" / "prolog"),
            memory_path=str(repo_root / "mrs" / "memory"),
            ledger=MRSLedger(),
        )
        compliance = repo_root / "examples" / "accounting_demo" / "accounting_compliance.pl"
        _bridge_instance.load_module(str(compliance))
    return _bridge_instance


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("MirrorOS Demo UI")
    print("  http://localhost:7242")
    print("  Ctrl+C to stop\n")
    uvicorn.run(app, host="0.0.0.0", port=7242, log_level="warning")
