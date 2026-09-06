"""
F.I.B.E.R. Blockchain Module
Web3 integration for Arbitrum Sepolia EVM L2 testnet.
"""

import os
from typing import Dict, Any, Optional
from web3 import Web3
from eth_account import Account

DEFAULT_ARBITRUM_SEPOLIA_RPC = "https://sepolia-rollup.arbitrum.io/rpc"

# ABI for FiberRegistry contract
FIBER_REGISTRY_ABI = [
    {
        "inputs": [
            {"internalType": "bytes32", "name": "faceHash", "type": "bytes32"},
            {"internalType": "string", "name": "metadataUri", "type": "string"}
        ],
        "name": "registerRecord",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "faceHash", "type": "bytes32"},
            {"internalType": "uint8", "name": "newStatus", "type": "uint8"}
        ],
        "name": "updateStatus",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "faceHash", "type": "bytes32"}],
        "name": "getRecord",
        "outputs": [
            {"internalType": "bytes32", "name": "hashVal", "type": "bytes32"},
            {"internalType": "string", "name": "metadataUri", "type": "string"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
            {"internalType": "address", "name": "owner", "type": "address"},
            {"internalType": "uint8", "name": "status", "type": "uint8"},
            {"internalType": "bool", "name": "exists", "type": "bool"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "totalRecords",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
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

    def register_record_onchain(self, face_hash: bytes, metadata_uri: str) -> Dict[str, Any]:
        """
        Send a transaction to register a face record on Arbitrum Sepolia.
        """
        if not self.account or not self.contract:
            raise ValueError("Private key and valid contract address are required for on-chain transactions.")

        nonce = self.w3.eth.get_transaction_count(self.account.address)
        gas_price = self.w3.eth.gas_price

        tx = self.contract.functions.registerRecord(
            face_hash,
            metadata_uri
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

    def fetch_record(self, face_hash: bytes) -> Dict[str, Any]:
        """
        Read face record from FiberRegistry contract.
        """
        if not self.contract:
            raise ValueError("Valid contract address is required to query state.")

        hash_val, uri, ts, owner, status, exists = self.contract.functions.getRecord(face_hash).call()
        return {
            "face_hash": hash_val.hex(),
            "metadata_uri": uri,
            "timestamp": ts,
            "owner": owner,
            "status": status,
            "exists": exists
        }
