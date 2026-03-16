"""
Mock Accounting Adapter — Zoho-Books-shaped demo adapter.

Simulates an accounting system (invoices, vendors, payments) for the
MirrorOS governance demo.  Every action is gated by MRS before execution:
the adapter never touches data unless the bridge permits it.

This is an open-source demo adapter.  Replace with a real Zoho Books
(or equivalent) client to connect a live system — the MRS gate is
identical either way.

Purpose:
    Demonstrate MirrorOS governing accounting actions.  Plug in real
    API calls in place of the in-memory state mutations.

Args (AccountingAdapter.__init__):
    bridge: Initialised MRSBridge instance with accounting_compliance.pl
            already loaded.

Returns:
    All action methods return a dict:
        permitted (bool)  — True if MRS allowed the action and it executed
        agent     (str)   — acting agent
        reason    (str)   — human-readable verdict explanation
        action    (str)   — action name
        data      (dict)  — payload specific to the action

Violations:
    Never call adapter action methods without a bridge.
    Never bypass _gate() to write state directly.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mrs.bridge.mrs_bridge import MRSBridge


# ─────────────────────────────────────────────────────────────────────────────
# Mock data — replace with live API calls for production
# ─────────────────────────────────────────────────────────────────────────────

_INVOICES: dict[str, dict[str, Any]] = {
    "inv_001": {"vendor": "acme_corp",        "amount": 200,   "currency": "USD", "status": "pending"},
    "inv_002": {"vendor": "trusted_supplier", "amount": 25000, "currency": "USD", "status": "pending"},
    "inv_003": {"vendor": "unknown_co",       "amount": 500,   "currency": "USD", "status": "pending"},
    "inv_004": {"vendor": "acme_corp",        "amount": 950,   "currency": "USD", "status": "pending"},
}

_VENDORS: dict[str, dict[str, Any]] = {
    "acme_corp":        {"name": "Acme Corp",          "verified": True,  "category": "supplies"},
    "trusted_supplier": {"name": "Trusted Supplier Inc","verified": True,  "category": "services"},
    "unknown_co":       {"name": "Unknown Co",          "verified": False, "category": "unknown"},
}


class AccountingAdapter:
    """
    MRS-governed accounting adapter.

    All write operations run through _gate(), which queries Prolog for policy
    violations before any state change occurs.  If the bridge reports a
    violation, the method returns immediately with permitted=False and the
    system state is untouched.
    """

    def __init__(self, bridge: "MRSBridge"):
        self.bridge = bridge
        # Mutable in-session state (deep copy so demo resets don't pollute)
        self._invoices: dict[str, dict[str, Any]] = {
            k: dict(v) for k, v in _INVOICES.items()
        }
        self._vendors: dict[str, dict[str, Any]] = {
            k: dict(v) for k, v in _VENDORS.items()
        }

    # ─────────────────────────────────────────────────────────────────────────
    # MRS gate
    # ─────────────────────────────────────────────────────────────────────────

    def _gate(self, agent: str, action_term: str) -> tuple[bool, str]:
        """
        Query MRS for policy violations before executing an action.

        Args:
            agent:       Agent name (Prolog atom, e.g. "clerk")
            action_term: Fully-formed Prolog action term, e.g.
                         "approve_payment('inv_001', 200)"

        Returns:
            (permitted, reason) — if permitted is False, reason explains why.
        """
        query = f"violates_accounting_policy({agent}, {action_term}, Reason)"
        violations = self.bridge.query(query)

        if violations:
            reason = str(violations[0].get("Reason", "policy violation"))
            return False, reason

        return True, "permitted"

    # ─────────────────────────────────────────────────────────────────────────
    # Actions
    # ─────────────────────────────────────────────────────────────────────────

    def approve_invoice(self, agent: str, invoice_id: str) -> dict[str, Any]:
        """
        Approve a pending invoice.

        MRS checks approval_limit and vendor_verified before execution.

        Args:
            agent:      Acting agent ("clerk" or "auditor")
            invoice_id: Invoice identifier (e.g. "inv_001")

        Returns:
            Result dict with permitted, agent, invoice_id, amount, reason.
        """
        t0 = time.perf_counter()

        invoice = self._invoices.get(invoice_id)
        if not invoice:
            return {
                "permitted": False, "agent": agent,
                "action": "approve_invoice", "invoice_id": invoice_id,
                "reason": f"Invoice '{invoice_id}' not found",
                "latency_ms": 0.0,
            }

        amount = invoice["amount"]
        action_term = f"approve_payment('{invoice_id}', {amount})"
        permitted, reason = self._gate(agent, action_term)

        if permitted:
            invoice["status"] = "approved"

        latency_ms = (time.perf_counter() - t0) * 1000
        return {
            "permitted": permitted,
            "agent":      agent,
            "action":     "approve_invoice",
            "invoice_id": invoice_id,
            "amount":     amount,
            "vendor":     invoice["vendor"],
            "reason":     reason,
            "latency_ms": round(latency_ms, 2),
        }

    def pay_vendor(self, agent: str, vendor_id: str, amount: float) -> dict[str, Any]:
        """
        Submit a payment to a vendor.

        MRS checks vendor_verified before execution.

        Args:
            agent:     Acting agent
            vendor_id: Vendor identifier (e.g. "acme_corp")
            amount:    Payment amount

        Returns:
            Result dict with permitted, agent, vendor_id, amount, reason.
        """
        t0 = time.perf_counter()

        vendor = self._vendors.get(vendor_id)
        if not vendor:
            return {
                "permitted": False, "agent": agent,
                "action": "pay_vendor", "vendor_id": vendor_id,
                "reason": f"Vendor '{vendor_id}' not found in system",
                "latency_ms": 0.0,
            }

        action_term = f"pay_vendor({vendor_id}, {amount})"
        permitted, reason = self._gate(agent, action_term)

        latency_ms = (time.perf_counter() - t0) * 1000
        return {
            "permitted":  permitted,
            "agent":      agent,
            "action":     "pay_vendor",
            "vendor_id":  vendor_id,
            "vendor_name": vendor["name"],
            "amount":     amount,
            "reason":     reason,
            "latency_ms": round(latency_ms, 2),
        }

    def view_invoice(self, agent: str, invoice_id: str) -> dict[str, Any]:
        """
        Read an invoice record.  Read-only — no MRS gate required.

        Args:
            agent:      Requesting agent
            invoice_id: Invoice identifier

        Returns:
            Invoice data dict or error.
        """
        invoice = self._invoices.get(invoice_id)
        if not invoice:
            return {"permitted": False, "reason": f"Invoice '{invoice_id}' not found"}
        return {"permitted": True, "agent": agent, "action": "view_invoice",
                "invoice_id": invoice_id, "data": dict(invoice)}

    def list_invoices(self, status_filter: str | None = None) -> list[dict[str, Any]]:
        """
        Return all invoices, optionally filtered by status.

        Args:
            status_filter: "pending" | "approved" | "rejected" | None (all)

        Returns:
            List of invoice dicts with their IDs.
        """
        invoices = [
            {"invoice_id": k, **v}
            for k, v in self._invoices.items()
        ]
        if status_filter:
            invoices = [i for i in invoices if i["status"] == status_filter]
        return invoices

    def compliance_check(self, agent: str, scope: str = "all") -> dict[str, Any]:
        """
        Run a read-only compliance summary.  No MRS gate — observation only.

        Args:
            agent: Requesting agent
            scope: "all" | "pending" | invoice_id

        Returns:
            Summary dict with counts and pending items.
        """
        all_invoices = self.list_invoices()
        pending  = [i for i in all_invoices if i["status"] == "pending"]
        approved = [i for i in all_invoices if i["status"] == "approved"]

        return {
            "permitted": True,
            "agent":     agent,
            "action":    "compliance_check",
            "scope":     scope,
            "summary": {
                "total":    len(all_invoices),
                "pending":  len(pending),
                "approved": len(approved),
                "pending_items": [i["invoice_id"] for i in pending],
            },
        }
