"""
chain_client.py -- Strikaris-Chain writ client.

Submits MRS decisions to strikaris-chain via POST /writ.
Drop-in replacement for the immudb MRSLedger interface.

Environment:
    CHAIN_URL   strikaris-chain base URL (default: http://localhost:7333)

Interface (matches MRSLedger):
    client = ChainClient()
    client.is_available()       -> bool
    client.seal(payload: dict)  -> {"verified": bool, "tx": int, "key": str, "error": str|None}
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

CHAIN_URL = os.getenv("CHAIN_URL", "http://localhost:7333")


class ChainClient:
    """Writ client for strikaris-chain. Same interface as MRSLedger."""

    def __init__(self, url: str = CHAIN_URL):
        self.url = url.rstrip("/")

    def is_available(self) -> bool:
        try:
            req = urllib.request.Request(f"{self.url}/chain/status", method="GET")
            with urllib.request.urlopen(req, timeout=3):
                return True
        except Exception:
            return False

    def seal(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Seal a decision as a writ on strikaris-chain.

        Maps payload fields to the /writ schema:
            mirror_id   <- payload["agent"]
            verb        <- "Log" (MRS decisions are structured log writs)
            body        <- full payload

        Returns:
            {"verified": True, "tx": block_id, "key": action_id} on success
            {"verified": False, "error": str}                     on failure
        """
        action_id = payload.get("action_id", "unknown")
        body = {
            "action_id": action_id,
            "agent":     payload.get("agent", "unknown"),
            "permitted": payload.get("permitted", False),
            "reason":    payload.get("reason", ""),
        }
        writ = json.dumps({
            "mirror_id": payload.get("agent", "mirroros"),
            "verb":      "Log",
            "body":      body,
        }).encode()

        try:
            req = urllib.request.Request(
                f"{self.url}/writ",
                data=writ,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read())
                return {
                    "verified": result.get("status") == "ASSERTED",
                    "tx":       result.get("id", 0),
                    "key":      action_id,
                    "error":    None,
                }
        except Exception as exc:
            logger.warning(f"chain_client.seal failed: {exc}")
            return {"verified": False, "tx": 0, "key": action_id, "error": str(exc)}


# Alias so demos can import as MRSLedger without changes
MRSLedger = ChainClient
