"""
app.blockchain — smart contract interaction and Web3 client.
"""

from app.blockchain.abi import EVIDENCE_REGISTRY_ABI
from app.blockchain.client import BlockchainClient, BlockchainError

__all__ = [
    "EVIDENCE_REGISTRY_ABI",
    "BlockchainClient",
    "BlockchainError",
]
