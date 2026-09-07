"""
F.I.B.E.R. Blockchain Module
Web3 integration for Arbitrum Sepolia EVM L2 testnet.
"""

import os
from typing import Any

from eth_account import Account
from web3 import Web3
from src.rpc_gateway import RPCGateway

DEFAULT_ARBITRUM_SEPOLIA_RPC = "https://sepolia-rollup.arbitrum.io/rpc"
DEFAULT_EXPLORER_URL = "https://sepolia.arbiscan.io"

# ABI for FiberMerkleRegistry contract matching anchorRoot and verifyRoot
FIBER_MERKLE_REGISTRY_ABI = [
    {
        "inputs": [
            {"internalType": "bytes32", "name": "_merkleRoot", "type": "bytes32"},
            {"internalType": "string", "name": "_sourceUrl", "type": "string"},
            {"internalType": "bool", "name": "_bypass", "type": "bool"},
            {"internalType": "uint64", "name": "_biometricFingerprint", "type": "uint64"}
        ],
        "name": "anchorRoot",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "_merkleRoot", "type": "bytes32"}],
        "name": "verifyRoot",
        "outputs": [
            {"internalType": "bool", "name": "exists", "type": "bool"},
            {
                "components": [
                    {"internalType": "bytes32", "name": "merkleRoot", "type": "bytes32"},
                    {"internalType": "string", "name": "sourceUrl", "type": "string"},
                    {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
                    {"internalType": "address", "name": "registrar", "type": "address"},
                    {"internalType": "bool", "name": "indexingDelayBypass", "type": "bool"},
                    {"internalType": "uint64", "name": "biometricFingerprint", "type": "uint64"}
                ],
                "internalType": "struct FiberMerkleRegistry.Record",
                "name": "record",
                "type": "tuple"
            }
        ],
        "stateMutability": "view",
        "type": "function"
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
        self.w3 = RPCGateway(custom_rpc=rpc_url)

        self.private_key = private_key or os.getenv("PRIVATE_KEY")
        if self.private_key and self.private_key != "0x0000000000000000000000000000000000000000000000000000000000000000":
            self.account = Account.from_key(self.private_key)
        else:
            self.account = None

        self.contract_address = contract_address or os.getenv("CONTRACT_ADDRESS")
        if self.contract_address and self.contract_address != "0x0000000000000000000000000000000000000000":
            checksummed = Web3.to_checksum_address(self.contract_address)
            self.contract = self.w3.eth.contract(address=checksummed, abi=FIBER_MERKLE_REGISTRY_ABI)
        else:
            self.contract = None

    def is_connected(self) -> bool:
        """Check connection status to Arbitrum Sepolia RPC."""
        return self.w3.is_connected()

    def get_chain_id(self) -> int:
        """Get network Chain ID (Arbitrum Sepolia is 421614)."""
        return self.w3.eth.chain_id

    def anchor(self, merkle_root_hex: str, source_url: str, bypass_flag: bool = False, biometric_fingerprint: int = 0) -> dict[str, Any]:
        """
        Build, sign, and broadcast anchorRoot transaction to Arbitrum Sepolia.
        Includes dynamic gas estimation & fallback for testnet gas price spikes.

        :param merkle_root_hex: Hex string of Merkle root (with or without '0x')
        :param source_url: Source URL or metadata URI string
        :param bypass_flag: Flag indicating if indexing delay was manually bypassed
        :param biometric_fingerprint: 64-bit Locality-Sensitive Hash of the face vector
        :return: Dict containing tx_hash, block_number, explorer_url
        """
        if not self.account or not self.contract:
            raise ValueError("PRIVATE_KEY and valid CONTRACT_ADDRESS are required to send on-chain transactions.")

        # 0. Check account ETH balance
        balance = self.w3.eth.get_balance(self.account.address)
        if balance == 0:
            raise ValueError(
                "Insufficient testnet ETH balance (0 ETH). "
                "Please acquire Arbitrum Sepolia testnet ETH from the faucet: "
                "https://faucet.quicknode.com/arbitrum/sepolia"
            )

        # Clean hex string into 32 bytes
        clean_hex = merkle_root_hex.replace("0x", "")
        merkle_bytes32 = bytes.fromhex(clean_hex)

        nonce = self.w3.eth.get_transaction_count(self.account.address)

        # Dynamic gas estimation with fallback buffer
        try:
            estimated_gas = self.contract.functions.anchorRoot(
                merkle_bytes32, source_url, bypass_flag, biometric_fingerprint
            ).estimate_gas({'from': self.account.address})
            gas_limit = int(estimated_gas * 1.25)
        except Exception as e:
            err_str = str(e).lower()
            if "alreadyanchored" in err_str or "already anchored" in err_str:
                raise RuntimeError(f"EVM Revert: Merkle Root already registered on-chain ({merkle_root_hex})") from e
            if "insufficient funds" in err_str:
                raise ValueError(
                    "Insufficient testnet ETH balance for gas. "
                    "Please acquire Arbitrum Sepolia testnet ETH from the faucet: "
                    "https://faucet.quicknode.com/arbitrum/sepolia"
                ) from e
            gas_limit = 350000

        try:
            gas_price = int(self.w3.eth.gas_price * 1.1)
        except Exception:
            gas_price = self.w3.to_wei(0.1, 'gwei')

        tx = self.contract.functions.anchorRoot(
            merkle_bytes32,
            source_url,
            bypass_flag,
            biometric_fingerprint
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
        try:
            tx_hash_bytes = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        except Exception as e:
            err_str = str(e).lower()
            if "insufficient funds" in err_str:
                raise ValueError(
                    "Insufficient testnet ETH balance for gas. "
                    "Please acquire Arbitrum Sepolia testnet ETH from the faucet: "
                    "https://faucet.quicknode.com/arbitrum/sepolia"
                ) from e
            if "alreadyanchored" in err_str or "already anchored" in err_str:
                raise RuntimeError(f"EVM Revert: Merkle Root already registered on-chain ({merkle_root_hex})") from e
            raise e

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

    def encode_anchor_payload(self, merkle_root_hex: str, source_url: str, bypass_flag: bool = False, biometric_fingerprint: int = 0) -> bytes:
        """
        Build the raw ABI-encoded data payload for the anchorRoot function,
        for use with meta-transactions.
        """
        if not self.contract:
            raise ValueError("Valid CONTRACT_ADDRESS is required to encode contract calls.")
            
        clean_hex = merkle_root_hex.replace("0x", "")
        merkle_bytes32 = bytes.fromhex(clean_hex)
        
        data_hex = self.contract.encode_abi("anchorRoot", args=[merkle_bytes32, source_url, bypass_flag, biometric_fingerprint])
        return bytes.fromhex(data_hex.replace("0x", ""))

    def verify(self, merkle_root_hex: str) -> dict[str, Any]:
        """
        Call contract's verifyRoot view function to check on-chain status.

        :param merkle_root_hex: Hex string of Merkle root
        :return: Dict containing exists flag and decoded record data
        """
        if not self.contract:
            raise ValueError("Valid CONTRACT_ADDRESS is required to query on-chain state.")

        clean_hex = merkle_root_hex.replace("0x", "")
        merkle_bytes32 = bytes.fromhex(clean_hex)

        exists, record = self.contract.functions.verifyRoot(merkle_bytes32).call()

        rec_hash = record[0].hex() if isinstance(record[0], bytes) else record[0]
        if rec_hash and not rec_hash.startswith("0x"):
            rec_hash = "0x" + rec_hash

        return {
            "exists": exists,
            "merkle_root": rec_hash,
            "source_url": record[1],
            "timestamp": record[2],
            "registered_by": record[3],
            "indexing_delay_bypass": record[4] if len(record) > 4 else False,
            "biometric_fingerprint": record[5] if len(record) > 5 else 0,
            "contract_address": self.contract_address,
            "explorer_url": f"{DEFAULT_EXPLORER_URL}/address/{self.contract_address}"
        }

# Alias for backward compatibility
ArbitrumFiberClient = BlockchainClient
