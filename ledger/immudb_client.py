"""
MRSLedger — cryptographically sealed MRS decision trail.

Every MRS verdict (PERMITTED, REJECTED, CONTRADICTION) is written as a
verified immudb entry.  The key is deterministic from action_id so any
entry can be retrieved and re-verified independently.

immudb's verifiedSet guarantees:
  - The write is included in the Merkle tree
  - The server returns a cryptographic proof on the same call
  - result.verified == True means the proof checked locally

Purpose:
    Provide tamper-proof, provable audit trail for every MRS decision.

Args (MRSLedger.__init__):
    host:     immudb host (default: "localhost")
    port:     immudb port (default: 3322)
    username: immudb username (default: "immudb" — demo credentials only)
    password: immudb password (default: "immudb" — demo credentials only)
    database: immudb database name (default: "defaultdb")

Returns (seal):
    Dict with "verified" (bool), "tx" (int), "key" (str).
    If immudb is unavailable, returns {"verified": False, "error": str}.

Violations:
    Never commit production credentials to this file.
    Demo defaults are intentionally public.  Production deployments inject
    credentials via environment variables — see SECURITY.md.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Environment-variable overrides for production deployments.
# Demo defaults are safe to commit (testnet/local only).
_DEFAULT_HOST = os.getenv("IMMUDB_HOST", "localhost")
_DEFAULT_PORT = int(os.getenv("IMMUDB_PORT", "3322"))
_DEFAULT_USER = os.getenv("IMMUDB_USER", "immudb")
_DEFAULT_PASS = os.getenv("IMMUDB_PASS", "immudb")
_DEFAULT_DB   = os.getenv("IMMUDB_DB",   "defaultdb")


class MRSLedger:
    """
    Thin wrapper around the immudb Python client for MRS decision sealing.

    Connection is established lazily on first seal() call so that MRS
    starts cleanly even when immudb is not yet running.

    Usage:
        ledger = MRSLedger()                         # default: localhost:3322
        result = ledger.seal(decision_dict)
        # result == {"verified": True, "tx": 42, "key": "mrs:action_20260304_001"}
    """

    def __init__(
        self,
        host: str = _DEFAULT_HOST,
        port: int = _DEFAULT_PORT,
        username: str = _DEFAULT_USER,
        password: str = _DEFAULT_PASS,
        database: str = _DEFAULT_DB,
    ):
        self.host     = host
        self.port     = port
        self.username = username
        self.password = password
        self.database = database

        self._client   = None   # lazy — created on first use
        self._ready    = False  # True after successful login
        self._unavail  = False  # True after first failed connect (stop retrying)

    # ─────────────────────────────────────────────────────────────────────────
    # Connection
    # ─────────────────────────────────────────────────────────────────────────

    def _connect(self) -> bool:
        """
        Establish connection and log in.  Called once on first seal().

        Returns:
            True if connected and authenticated, False otherwise.
        """
        if self._unavail:
            return False
        if self._ready:
            return True

        try:
            from immudb import ImmudbClient  # type: ignore[import]

            self._client = ImmudbClient(f"{self.host}:{self.port}")
            self._client.login(self.username, self.password)
            self._client.useDatabase(self.database.encode())
            self._ready = True
            logger.info(f"MRSLedger connected: {self.host}:{self.port}/{self.database}")
            return True

        except ImportError:
            logger.warning(
                "immudb-py not installed — ledger sealing disabled. "
                "Install with: pip install immudb-py"
            )
            self._unavail = True
            return False

        except Exception as exc:
            logger.warning(
                f"MRSLedger could not connect to {self.host}:{self.port}: {exc}. "
                "MRS continues without ledger sealing."
            )
            self._unavail = True
            return False

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def is_available(self) -> bool:
        """Return True if immudb is reachable and authenticated."""
        return self._connect()

    def seal(self, decision: dict[str, Any]) -> dict[str, Any]:
        """
        Write a verified ledger entry for an MRS decision.

        The key is deterministic: ``mrs:{action_id}``.  The value is the
        full decision dict serialised as UTF-8 JSON.  immudb's verifiedSet
        performs a Merkle-tree inclusion proof on the same round-trip.

        Args:
            decision: Dict containing at minimum "action_id" and "status".
                      Typically the full _log_reasoning entry.

        Returns:
            On success: {"verified": bool, "tx": int, "key": str}
            On failure: {"verified": False, "error": str, "key": str}
        """
        action_id = decision.get("action_id") or decision.get("details", {}).get("action_id", "unknown")
        key_str   = f"mrs:{action_id}"
        key       = key_str.encode()
        value     = json.dumps(decision, default=str).encode()

        if not self._connect():
            return {"verified": False, "error": "immudb unavailable", "key": key_str}

        try:
            result = self._client.verifiedSet(key, value)
            verified = bool(result.verified)
            tx_id    = int(result.id)

            if verified:
                logger.info(f"Ledger sealed: {key_str} tx={tx_id} verified=True")
            else:
                logger.warning(f"Ledger write unverified: {key_str} tx={tx_id}")

            return {"verified": verified, "tx": tx_id, "key": key_str}

        except Exception as exc:
            logger.error(f"Ledger seal failed for {key_str}: {exc}")
            return {"verified": False, "error": str(exc), "key": key_str}
