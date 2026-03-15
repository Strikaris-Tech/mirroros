"""
MirrorOS Ledger — cryptographically sealed decision trail via immudb.

Exports:
    MRSLedger    — write verified entries to immudb

verify_entry is available via ledger.verify or the CLI:
    python -m ledger.verify <action_id>
"""

from .immudb_client import MRSLedger

__all__ = ["MRSLedger"]
