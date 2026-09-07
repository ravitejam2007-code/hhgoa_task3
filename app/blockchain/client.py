"""
app.blockchain.client — Web3 Ethereum Sepolia client for EvidenceRegistry.

Handles connecting to RPC, building, signing, and broadcasting transactions,
extracting evidence IDs from event logs, and verifying hashes on-chain.
Never logs private keys.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from web3 import Web3
from web3.exceptions import Web3Exception

from app.blockchain.abi import EVIDENCE_REGISTRY_ABI

logger = logging.getLogger(__name__)


class BlockchainError(Exception):
    """Raised when a blockchain or Web3 operation fails."""

    def __init__(self, message: str, code: str = "BLOCKCHAIN_ERROR") -> None:
        super().__init__(message)
        self.code = code


class BlockchainClient:
    """
    Client for interacting with the on-chain EvidenceRegistry contract.
    """

    def __init__(
        self,
        rpc_url: str | None = None,
        private_key: str | None = None,
        contract_address: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.rpc_url = (rpc_url or os.getenv("SEPOLIA_RPC_URL", "")).strip()
        raw_pk = (private_key or os.getenv("WALLET_PRIVATE_KEY", "")).strip()
        self.private_key = raw_pk if not raw_pk or raw_pk.startswith("0x") else f"0x{raw_pk}"
        self.contract_address = (contract_address or os.getenv("CONTRACT_ADDRESS", "")).strip()
        self.timeout = timeout

        self._w3: Web3 | None = None
        self._account = None
        self._contract = None

    def _ensure_connected(self) -> Web3:
        """Verify RPC connection and initialize contract and signer."""
        if self._w3 is not None:
            return self._w3

        if not self.rpc_url:
            raise BlockchainError(
                "ERROR: SEPOLIA_RPC_URL is missing.\n"
                "Please configure SEPOLIA_RPC_URL in your .env file or pass rpc_url.",
                code="MISSING_RPC_URL",
            )

        w3 = Web3(Web3.HTTPProvider(self.rpc_url, request_kwargs={"timeout": self.timeout}))
        if not w3.is_connected():
            raise BlockchainError(
                f"ERROR: Unable to connect to blockchain RPC at '{self.rpc_url}'.\n"
                "Check SEPOLIA_RPC_URL and your internet / proxy connectivity.",
                code="RPC_CONNECTION_FAILED",
            )

        if not self.contract_address:
            raise BlockchainError(
                "ERROR: CONTRACT_ADDRESS is missing.\n"
                "Please deploy EvidenceRegistry and configure CONTRACT_ADDRESS in .env.",
                code="MISSING_CONTRACT_ADDRESS",
            )

        checksum_addr = Web3.to_checksum_address(self.contract_address)

        if self.private_key:
            try:
                self._account = w3.eth.account.from_key(self.private_key)
            except Exception as exc:
                raise BlockchainError(
                    f"ERROR: Invalid WALLET_PRIVATE_KEY provided: {exc}",
                    code="INVALID_PRIVATE_KEY",
                )

        self._contract = w3.eth.contract(address=checksum_addr, abi=EVIDENCE_REGISTRY_ABI)
        self._w3 = w3
        return self._w3

    @property
    def w3(self) -> Web3:
        return self._ensure_connected()

    @property
    def contract(self):
        self._ensure_connected()
        return self._contract

    @property
    def account_address(self) -> str | None:
        self._ensure_connected()
        return self._account.address if self._account else None

    def anchor_evidence(
        self,
        evidence_hash_bytes: bytes,
        source_url: str,
        search_provider: str,
        run_dir: Path | None = None,
    ) -> dict[str, Any]:
        """
        Broadcast evidence hash and metadata to the EvidenceRegistry contract.
        Signs the transaction with the configured private key, waits for receipt,
        and saves runs/<run_id>/blockchain_receipt.json.
        """
        w3 = self._ensure_connected()

        if not self._account:
            raise BlockchainError(
                "ERROR: WALLET_PRIVATE_KEY is missing.\n"
                "Add it to your .env file to submit transactions to the blockchain.",
                code="MISSING_PRIVATE_KEY",
            )

        if len(evidence_hash_bytes) != 32:
            raise BlockchainError(
                f"Evidence hash must be 32 bytes, got {len(evidence_hash_bytes)}",
                code="INVALID_HASH_LENGTH",
            )

        sender = self._account.address
        nonce = w3.eth.get_transaction_count(sender)
        chain_id = w3.eth.chain_id

        # Build transaction call
        fn = self.contract.functions.recordEvidence(
            evidence_hash_bytes,
            source_url,
            search_provider,
        )

        try:
            estimated_gas = fn.estimate_gas({"from": sender})
            gas_limit = int(estimated_gas * 1.3)
        except Exception as exc:
            logger.warning("Gas estimation failed (%s); using conservative gas limit 200,000", exc)
            gas_limit = 200000

        # Build transaction dictionary with dynamic gas / legacy fallback
        tx_data: dict[str, Any] = {
            "from": sender,
            "nonce": nonce,
            "gas": gas_limit,
            "chainId": chain_id,
        }

        try:
            latest_block = w3.eth.get_block("latest")
            base_fee = latest_block.get("baseFeePerGas")
            if base_fee is not None:
                max_priority_fee = w3.eth.max_priority_fee
                tx_data["maxFeePerGas"] = int(base_fee * 1.5) + max_priority_fee
                tx_data["maxPriorityFeePerGas"] = max_priority_fee
            else:
                tx_data["gasPrice"] = w3.eth.gas_price
        except Exception:
            tx_data["gasPrice"] = w3.eth.gas_price

        built_tx = fn.build_transaction(tx_data)

        # Sign transaction
        signed_tx = w3.eth.account.sign_transaction(built_tx, private_key=self.private_key)

        # Send raw transaction
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        logger.info("Transaction broadcast: %s", tx_hash.hex())

        # Wait for receipt
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=self.timeout)

        if receipt.get("status") != 1:
            raise BlockchainError(
                f"Transaction {tx_hash.hex()} failed on-chain (status=0).",
                code="TRANSACTION_REVERTED",
            )

        # Parse EvidenceRecorded event to extract evidenceId
        evidence_id = None
        try:
            events = self.contract.events.EvidenceRecorded().process_receipt(receipt)
            if events:
                evidence_id = int(events[0]["args"]["evidenceId"])
        except Exception as exc:
            logger.warning("Could not parse EvidenceRecorded event from receipt: %s", exc)

        # Fallback if event parsing did not return ID: read totalEvidence
        if evidence_id is None:
            try:
                evidence_id = int(self.contract.functions.totalEvidence().call())
            except Exception:
                evidence_id = 1

        network_name = "sepolia" if chain_id == 11155111 else f"chain-{chain_id}"
        receipt_data = {
            "network": network_name,
            "chain_id": chain_id,
            "transaction_hash": tx_hash.hex(),
            "contract_address": self.contract_address,
            "evidence_id": evidence_id,
            "block_number": receipt.get("blockNumber"),
            "status": receipt.get("status"),
        }

        if run_dir:
            run_dir.mkdir(parents=True, exist_ok=True)
            out_file = run_dir / "blockchain_receipt.json"
            out_file.write_text(json.dumps(receipt_data, indent=2), encoding="utf-8")

        return receipt_data

    def read_evidence(self, evidence_id: int) -> dict[str, Any]:
        """Read evidence record from contract by ID."""
        self._ensure_connected()
        try:
            record = self.contract.functions.getEvidence(evidence_id).call()
            # Returns (evidenceHash, sourceUrl, searchProvider, createdAt, submitter)
            hash_bytes = record[0]
            return {
                "evidence_id": evidence_id,
                "evidence_hash": hash_bytes.hex() if isinstance(hash_bytes, bytes) else str(hash_bytes),
                "source_url": record[1],
                "search_provider": record[2],
                "created_at": record[3],
                "submitter": record[4],
            }
        except Exception as exc:
            raise BlockchainError(
                f"Failed to read evidence ID {evidence_id} from contract: {exc}",
                code="READ_EVIDENCE_FAILED",
            )

    def verify_evidence(self, evidence_id: int, evidence_hash_bytes: bytes) -> bool:
        """Call verifyEvidence view function on-chain."""
        self._ensure_connected()
        try:
            return bool(self.contract.functions.verifyEvidence(evidence_id, evidence_hash_bytes).call())
        except Exception as exc:
            raise BlockchainError(
                f"Failed to verify evidence on-chain: {exc}",
                code="VERIFY_CALL_FAILED",
            )
