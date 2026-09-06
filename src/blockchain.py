"""
F.I.B.E.R. Blockchain Module
Web3 integration for Arbitrum Sepolia EVM L2 testnet.
"""

import os
from typing import Dict, Any, Optional
from web3 import Web3
from eth_account import Account

DEFAULT_ARBITRUM_SEPOLIA_RPC = "https://sepolia-rollup.arbitrum.io/rpc"

# Updated ABI matching FiberRegistry.sol (anchorEvidence, verifyEvidence)
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

class ArbitrumFiberClient:
    def __init__(self, rpc_url: Optional[str] = None, private_key: Optional[str] = None, contract_address: Optional[str] = None):
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

    def anchor_evidence(self, evidence_hash: bytes, source_url: str) -> Dict[str, Any]:
        """
        Send transaction to anchor evidence on Arbitrum Sepolia.
        """
        if not self.account or not self.contract:
            raise ValueError("Private key and valid contract address are required for on-chain transactions.")

        nonce = self.w3.eth.get_transaction_count(self.account.address)
        gas_price = self.w3.eth.gas_price

        tx = self.contract.functions.anchorEvidence(
            evidence_hash,
            source_url
        ).build_transaction({
            'chainId': self.get_chain_id(),
            'gas': 300000,
            'gasPrice': gas_price,
            'nonce': nonce,
            'from': self.account.address
        })

        signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        return {
            "status": "submitted",
            "tx_hash": tx_hash.hex(),
            "from": self.account.address
        }

    def verify_evidence(self, evidence_hash: bytes) -> Dict[str, Any]:
        """
        Query evidence record from FiberRegistry contract.
        """
        if not self.contract:
            raise ValueError("Valid contract address is required to query state.")

        exists, record = self.contract.functions.verifyEvidence(evidence_hash).call()
        return {
            "exists": exists,
            "evidence_hash": record[0].hex() if isinstance(record[0], bytes) else record[0],
            "source_url": record[1],
            "timestamp": record[2],
            "registered_by": record[3]
        }

    # Aliases for backward compatibility
    register_record_onchain = anchor_evidence
    fetch_record = verify_evidence
