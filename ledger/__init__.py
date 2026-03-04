"""
MirrorOS Ledger — cryptographically sealed decision trail via immudb.

Exports:
    MRSLedger   — write verified entries to immudb
    verify_entry — read back and verify a sealed decision by action_id
"""

from .immudb_client import MRSLedger
from .verify import verify_entry

__all__ = ["MRSLedger", "verify_entry"]
