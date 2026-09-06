"""
F.I.B.E.R. Blockchain Module
Web3 integration for Arbitrum Sepolia EVM L2 testnet.
"""

import os
from typing import Any

from eth_account import Account
from web3 import Web3

DEFAULT_ARBITRUM_SEPOLIA_RPC = "https://sepolia-rollup.arbitrum.io/rpc"
DEFAULT_EXPLORER_URL = "https://sepolia.arbiscan.io"

# ABI for FiberRegistry contract matching anchorEvidence and verifyEvidence
FIBER_REGISTRY_ABI = [
    {
        "inputs": [
            {"internalType": "bytes32", "name": "_evidenceHash", "type": "bytes32"},
            {"internalType": "string", "name": "_sourceUrl", "type": "string"}
        ],
        "name": "anchorEvidence",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "_evidenceHash", "type": "bytes32"}],
        "name": "verifyEvidence",
        "outputs": [
            {"internalType": "bool", "name": "exists", "type": "bool"},
            {
                "components": [
                    {"internalType": "bytes32", "name": "evidenceHash", "type": "bytes32"},
                    {"internalType": "string", "name": "sourceUrl", "type": "string"},
                    {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
                    {"internalType": "address", "name": "registeredBy", "type": "address"}
                ],
                "internalType": "struct FiberRegistry.Evidence",
                "name": "record",
                "type": "tuple"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
        "name": "records",
        "outputs": [
            {"internalType": "bytes32", "name": "evidenceHash", "type": "bytes32"},
            {"internalType": "string", "name": "sourceUrl", "type": "string"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
            {"internalType": "address", "name": "registeredBy", "type": "address"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "bytes32", "name": "evidenceHash", "type": "bytes32"},
            {"indexed": False, "internalType": "string", "name": "sourceUrl", "type": "string"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"},
            {"indexed": True, "internalType": "address", "name": "registrar", "type": "address"}
        ],
        "name": "EvidenceAnchored",
        "type": "event"
    }
]

class BlockchainClient:
    def __init__(
        self,
        rpc_url: str | None = None,
        private_key: str | None = None,
        contract_address: str | None = None
    ):
        self.rpc_url = rpc_url or os.getenv("ARBITRUM_SEPOLIA_RPC", DEFAULT_ARBITRUM_SEPOLIA_RPC)
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))

        self.private_key = private_key or os.getenv("PRIVATE_KEY")
        if self.private_key and self.private_key != "0x0000000000000000000000000000000000000000000000000000000000000000":
            self.account = Account.from_key(self.private_key)
        else:
            self.account = None

        self.contract_address = contract_address or os.getenv("CONTRACT_ADDRESS")
        if self.contract_address and self.contract_address != "0x0000000000000000000000000000000000000000":
            checksummed = Web3.to_checksum_address(self.contract_address)
            self.contract = self.w3.eth.contract(address=checksummed, abi=FIBER_REGISTRY_ABI)
        else:
            self.contract = None

    def is_connected(self) -> bool:
        """Check connection status to Arbitrum Sepolia RPC."""
        return self.w3.is_connected()

    def get_chain_id(self) -> int:
        """Get network Chain ID (Arbitrum Sepolia is 421614)."""
        return self.w3.eth.chain_id

    def anchor(self, evidence_hash_hex: str, source_url: str) -> dict[str, Any]:
        """
        Build, sign, and broadcast anchorEvidence transaction to Arbitrum Sepolia.
        Includes dynamic gas estimation & fallback for testnet gas price spikes.

        :param evidence_hash_hex: Hex string of evidence hash (with or without '0x')
        :param source_url: Source URL or metadata URI string
        :return: Dict containing tx_hash, block_number, explorer_url
        """
        if not self.account or not self.contract:
            raise ValueError("PRIVATE_KEY and valid CONTRACT_ADDRESS are required to send on-chain transactions.")

        # Clean hex string into 32 bytes
        clean_hex = evidence_hash_hex.replace("0x", "")
        evidence_bytes32 = bytes.fromhex(clean_hex)

        nonce = self.w3.eth.get_transaction_count(self.account.address)

        # Dynamic gas estimation with fallback buffer
        try:
            estimated_gas = self.contract.functions.anchorEvidence(
                evidence_bytes32, source_url
            ).estimate_gas({'from': self.account.address})
            gas_limit = int(estimated_gas * 1.25)
        except Exception:
            gas_limit = 350000

        try:
            gas_price = int(self.w3.eth.gas_price * 1.1)
        except Exception:
            gas_price = self.w3.to_wei(0.1, 'gwei')

        tx = self.contract.functions.anchorEvidence(
            evidence_bytes32,
            source_url
        ).build_transaction({
            'chainId': self.get_chain_id(),
            'gas': gas_limit,
            'gasPrice': gas_price,
            'nonce': nonce,
            'from': self.account.address
        })

        # Sign transaction
        signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=self.private_key)

        # Broadcast transaction
        tx_hash_bytes = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        tx_hash_hex = tx_hash_bytes.hex()
        if not tx_hash_hex.startswith("0x"):
            tx_hash_hex = "0x" + tx_hash_hex

        # Wait for block confirmation receipt
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash_bytes, timeout=120)
        receipt_tx_hash = receipt.transactionHash.hex()
        if not receipt_tx_hash.startswith("0x"):
            receipt_tx_hash = "0x" + receipt_tx_hash

        if receipt.status == 0:
            raise RuntimeError(f"Transaction reverted on-chain! Tx Hash: {receipt_tx_hash}")

        explorer_url = f"{DEFAULT_EXPLORER_URL}/tx/{receipt_tx_hash}"

        return {
            "tx_hash": receipt_tx_hash,
            "block_number": receipt.blockNumber,
            "explorer_url": explorer_url,
            "gas_used": receipt.gasUsed,
            "status": receipt.status
        }

    def verify(self, evidence_hash_hex: str) -> dict[str, Any]:
        """
        Call contract's verifyEvidence view function to check on-chain status.

        :param evidence_hash_hex: Hex string of evidence hash
        :return: Dict containing exists flag and decoded record data
        """
        if not self.contract:
            raise ValueError("Valid CONTRACT_ADDRESS is required to query on-chain state.")

        clean_hex = evidence_hash_hex.replace("0x", "")
        evidence_bytes32 = bytes.fromhex(clean_hex)

        exists, record = self.contract.functions.verifyEvidence(evidence_bytes32).call()

        rec_hash = record[0].hex() if isinstance(record[0], bytes) else record[0]
        if rec_hash and not rec_hash.startswith("0x"):
            rec_hash = "0x" + rec_hash

        return {
            "exists": exists,
            "evidence_hash": rec_hash,
            "source_url": record[1],
            "timestamp": record[2],
            "registered_by": record[3],
            "contract_address": self.contract_address,
            "explorer_url": f"{DEFAULT_EXPLORER_URL}/address/{self.contract_address}"
        }

# Alias for backward compatibility
ArbitrumFiberClient = BlockchainClient
