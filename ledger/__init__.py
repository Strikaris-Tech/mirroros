"""
MirrorOS Ledger -- writ client for strikaris-chain.

Exports:
    MRSLedger   -- seals MRS decisions as writs on strikaris-chain
    ChainClient -- same class, explicit name
"""

from .chain_client import ChainClient, MRSLedger

__all__ = ["ChainClient", "MRSLedger"]
