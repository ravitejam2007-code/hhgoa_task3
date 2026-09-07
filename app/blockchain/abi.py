"""
app.blockchain.abi — ABI definition for the EvidenceRegistry smart contract.
"""

from __future__ import annotations

EVIDENCE_REGISTRY_ABI = [
    {
        "inputs": [
            {"internalType": "bytes32", "name": "evidenceHash", "type": "bytes32"},
            {"internalType": "string", "name": "sourceUrl", "type": "string"},
            {"internalType": "string", "name": "searchProvider", "type": "string"},
        ],
        "name": "recordEvidence",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "evidenceId", "type": "uint256"}],
        "name": "getEvidence",
        "outputs": [
            {"internalType": "bytes32", "name": "evidenceHash", "type": "bytes32"},
            {"internalType": "string", "name": "sourceUrl", "type": "string"},
            {"internalType": "string", "name": "searchProvider", "type": "string"},
            {"internalType": "uint256", "name": "createdAt", "type": "uint256"},
            {"internalType": "address", "name": "submitter", "type": "address"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "evidenceId", "type": "uint256"},
            {"internalType": "bytes32", "name": "evidenceHash", "type": "bytes32"},
        ],
        "name": "verifyEvidence",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "totalEvidence",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "uint256", "name": "evidenceId", "type": "uint256"},
            {"indexed": True, "internalType": "bytes32", "name": "evidenceHash", "type": "bytes32"},
            {"indexed": False, "internalType": "string", "name": "sourceUrl", "type": "string"},
            {"indexed": False, "internalType": "string", "name": "searchProvider", "type": "string"},
            {"indexed": True, "internalType": "address", "name": "submitter", "type": "address"},
        ],
        "name": "EvidenceRecorded",
        "type": "event",
    },
]
