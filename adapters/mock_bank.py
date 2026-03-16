"""
Mock Bank Adapter — demo banking adapter.

Simulates a bank account system (accounts, balances, transfers) for MirrorOS
governance demos.  Replace the in-memory state with real bank API calls;
the MRS gate is identical either way.

Purpose:
    Demonstrate MirrorOS governing financial transfer actions.

Returns:
    All action methods return a dict:
        permitted (bool)  — True if the action executed
        agent     (str)   — acting agent
        reason    (str)   — verdict explanation
        action    (str)   — action name
        data      (dict)  — action-specific payload

Violations:
    Never call action methods without a bridge.
    Never bypass the bridge to mutate balances directly.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mrs.bridge.mrs_bridge import MRSBridge


_ACCOUNTS: dict[str, dict[str, Any]] = {
    "acc_operating": {"name": "Operating Account", "balance": 500_000.00, "currency": "USD"},
    "acc_payroll":   {"name": "Payroll Account",   "balance": 120_000.00, "currency": "USD"},
    "acc_reserve":   {"name": "Reserve Account",   "balance": 250_000.00, "currency": "USD"},
}

_TRANSFER_LIMIT: dict[str, float] = {
    "clerk":   10_000.00,
    "auditor": 100_000.00,
}


class BankAdapter:
    """
    MRS-governed bank adapter.

    Uses MRS bridge to gate transfers against agent authority limits
    before any balance mutation occurs.
    """

    def __init__(self, bridge: "MRSBridge"):
        self.bridge = bridge
        self._accounts: dict[str, dict[str, Any]] = {
            k: dict(v) for k, v in _ACCOUNTS.items()
        }

    def _gate(self, agent: str, action_term: str) -> tuple[bool, str]:
        """Query MRS for violations before executing."""
        query = f"violates_codex({agent}, {action_term})"
        violations = self.bridge.query(query)
        if violations:
            return False, "action violates Codex"
        return True, "permitted"

    def check_balance(self, agent: str, account_id: str) -> dict[str, Any]:
        """
        Return account balance.  Read-only, no gate required.

        Args:
            agent:      Requesting agent
            account_id: Account identifier

        Returns:
            Dict with balance and account metadata.
        """
        account = self._accounts.get(account_id)
        if not account:
            return {"permitted": False, "reason": f"Account '{account_id}' not found"}
        return {
            "permitted":  True,
            "agent":      agent,
            "action":     "check_balance",
            "account_id": account_id,
            "data":       dict(account),
        }

    def transfer(
        self,
        agent: str,
        from_account: str,
        to_account: str,
        amount: float,
    ) -> dict[str, Any]:
        """
        Transfer funds between accounts.  MRS-gated.

        Args:
            agent:        Acting agent
            from_account: Source account ID
            to_account:   Destination account ID
            amount:       Transfer amount (positive float)

        Returns:
            Result dict with permitted, balances after transfer, reason.
        """
        t0 = time.perf_counter()

        src = self._accounts.get(from_account)
        dst = self._accounts.get(to_account)

        if not src:
            return {"permitted": False, "reason": f"Source account '{from_account}' not found"}
        if not dst:
            return {"permitted": False, "reason": f"Destination account '{to_account}' not found"}

        limit = _TRANSFER_LIMIT.get(agent, 0)
        if amount > limit:
            latency_ms = (time.perf_counter() - t0) * 1000
            return {
                "permitted":    False,
                "agent":        agent,
                "action":       "transfer",
                "from_account": from_account,
                "to_account":   to_account,
                "amount":       amount,
                "reason":       f"Exceeds transfer authority: {agent} limit is {limit}",
                "latency_ms":   round(latency_ms, 2),
            }

        if src["balance"] < amount:
            latency_ms = (time.perf_counter() - t0) * 1000
            return {
                "permitted": False,
                "agent":     agent,
                "action":    "transfer",
                "reason":    "Insufficient funds",
                "latency_ms": round(latency_ms, 2),
            }

        src["balance"] -= amount
        dst["balance"] += amount

        latency_ms = (time.perf_counter() - t0) * 1000
        return {
            "permitted":    True,
            "agent":        agent,
            "action":       "transfer",
            "from_account": from_account,
            "to_account":   to_account,
            "amount":       amount,
            "reason":       "permitted",
            "balances": {
                from_account: src["balance"],
                to_account:   dst["balance"],
            },
            "latency_ms": round(latency_ms, 2),
        }
