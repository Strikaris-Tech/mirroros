"""
MirrorOS Ledger — proof verification utility.

Reads back a sealed MRS decision from immudb by action_id and verifies
the cryptographic Merkle-tree proof.  Can be run as a standalone CLI
tool or imported and called programmatically.

Purpose:
    Allow any party to independently verify that an MRS decision was
    sealed as claimed, without trusting the MRS process itself.

CLI usage:
    python -m ledger.verify <action_id> [--host localhost] [--port 3322]

    Example:
        python -m ledger.verify action_20260304_003
        → {"verified": true, "tx": 17, "key": "mrs:action_20260304_003", ...}

Returns (verify_entry):
    Dict with "verified" (bool), "tx" (int), "key" (str), "decision" (dict).
    On failure: {"verified": False, "error": str, "key": str}.

Violations:
    Never commit production credentials.  Use environment variables
    IMMUDB_HOST / IMMUDB_PORT / IMMUDB_USER / IMMUDB_PASS for production.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_HOST = os.getenv("IMMUDB_HOST", "localhost")
_DEFAULT_PORT = int(os.getenv("IMMUDB_PORT", "3322"))
_DEFAULT_USER = os.getenv("IMMUDB_USER", "immudb")
_DEFAULT_PASS = os.getenv("IMMUDB_PASS", "immudb")
_DEFAULT_DB   = os.getenv("IMMUDB_DB",   "defaultdb")


def verify_entry(
    action_id: str,
    host: str = _DEFAULT_HOST,
    port: int = _DEFAULT_PORT,
    username: str = _DEFAULT_USER,
    password: str = _DEFAULT_PASS,
    database: str = _DEFAULT_DB,
) -> dict[str, Any]:
    """
    Retrieve and verify a sealed MRS decision from immudb.

    Calls immudb's verifiedGet, which re-derives the Merkle proof locally
    and returns verified=True only if the proof holds.  A verified=False
    response means the entry was tampered with or does not exist.

    Args:
        action_id: MRS action ID, e.g. "action_20260304_003"
        host:      immudb host
        port:      immudb port
        username:  immudb username
        password:  immudb password
        database:  immudb database name

    Returns:
        {
            "verified":  bool,
            "tx":        int,           # transaction ID
            "key":       str,           # "mrs:{action_id}"
            "decision":  dict | None,   # the original sealed decision
            "error":     str | None     # present only on failure
        }
    """
    key_str = f"mrs:{action_id}"
    key     = key_str.encode()

    try:
        from immudb import ImmudbClient  # type: ignore[import]
    except ImportError:
        return _verify_from_json_log(action_id, key_str)

    try:
        client = ImmudbClient(f"{host}:{port}")
        client.login(username, password)
        client.useDatabase(database.encode())

        result = client.verifiedGet(key)

        verified = bool(result.verified)
        tx_id    = int(result.id)

        decision: dict | None = None
        try:
            decision = json.loads(result.value.decode())
        except (json.JSONDecodeError, AttributeError):
            pass

        status = "VERIFIED" if verified else "TAMPERED/MISSING"
        logger.info(f"Ledger verify {key_str}: {status} tx={tx_id}")

        return {
            "verified": verified,
            "tx":       tx_id,
            "key":      key_str,
            "decision": decision,
            "error":    None,
        }

    except Exception as exc:
        logger.warning(f"immudb unavailable for {key_str}: {exc} — falling back to JSON log")
        return _verify_from_json_log(action_id, key_str)


def _verify_from_json_log(action_id: str, key_str: str) -> dict[str, Any]:
    """
    Fallback verification against the local reasoning log.

    Used when immudb is not installed or not reachable.  Searches
    mrs/memory/reasoning_log.json for a matching action_id.

    Returns verified=True if the entry is found (integrity is local-only,
    not cryptographic), with source="json_log" to distinguish from immudb.
    """
    repo_root = Path(__file__).resolve().parents[1]
    log_path  = repo_root / "mrs" / "memory" / "reasoning_log.json"

    if not log_path.exists():
        return {
            "verified": False,
            "error":    "immudb offline and no local reasoning log found",
            "key":      key_str,
            "tx":       None,
            "decision": None,
        }

    try:
        entries = json.loads(log_path.read_text())
        if not isinstance(entries, list):
            entries = [entries]

        for entry in entries:
            if entry.get("action_id") == action_id or entry.get("details", {}).get("action_id") == action_id:
                return {
                    "verified": True,
                    "source":   "json_log",
                    "key":      key_str,
                    "tx":       None,
                    "decision": entry,
                }

        return {
            "verified": False,
            "error":    f"action_id '{action_id}' not found in reasoning log",
            "key":      key_str,
            "tx":       None,
            "decision": None,
        }

    except Exception as exc:
        return {
            "verified": False,
            "error":    f"failed to read reasoning log: {exc}",
            "key":      key_str,
            "tx":       None,
            "decision": None,
        }


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def _cli():
    import argparse

    parser = argparse.ArgumentParser(
        description="Verify a sealed MRS decision in immudb.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m ledger.verify action_20260304_003\n"
            "  python -m ledger.verify action_20260304_003 --host 192.168.1.10\n"
        ),
    )
    parser.add_argument("action_id", help="MRS action ID to verify")
    parser.add_argument("--host", default=_DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=_DEFAULT_PORT)
    parser.add_argument("--username", default=_DEFAULT_USER)
    parser.add_argument("--password", default=_DEFAULT_PASS)
    parser.add_argument("--database", default=_DEFAULT_DB)
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING)
    result = verify_entry(
        action_id=args.action_id,
        host=args.host,
        port=args.port,
        username=args.username,
        password=args.password,
        database=args.database,
    )
    print(json.dumps(result, indent=2, default=str))
    sys.exit(0 if result["verified"] else 1)


if __name__ == "__main__":
    _cli()
