"""
QA & Automation Unit Tests for src/blockchain.py
Using pytest and unittest.mock.
"""

import pytest
from unittest.mock import patch, MagicMock
from src.blockchain import BlockchainClient

class TestBlockchainModule:
    def test_blockchain_client_initialization_defaults(self):
        client = BlockchainClient(rpc_url="https://sepolia-rollup.arbitrum.io/rpc")
        assert client.rpc_url == "https://sepolia-rollup.arbitrum.io/rpc"
        assert client.account is None
        assert client.contract is None

    @patch("src.blockchain.Web3")
    def test_is_connected_mocked(self, mock_web3_cls):
        mock_w3_inst = MagicMock()
        mock_w3_inst.is_connected.return_value = True
        mock_web3_cls.return_value = mock_w3_inst

        client = BlockchainClient(rpc_url="https://sepolia-rollup.arbitrum.io/rpc")
        assert client.is_connected() is True

    @patch("src.blockchain.Web3")
    @patch("src.blockchain.Account")
    def test_anchor_evidence_offline_mock(self, mock_account_cls, mock_web3_cls):
        # Mock Web3 instance and transaction signing
        mock_w3_inst = MagicMock()
        mock_w3_inst.is_connected.return_value = True
        mock_w3_inst.eth.chain_id = 421614
        mock_w3_inst.eth.get_transaction_count.return_value = 5
        mock_w3_inst.eth.gas_price = 100000000

        # Mock contract function
        mock_contract = MagicMock()
        mock_func = MagicMock()
        mock_func.build_transaction.return_value = {
            "chainId": 421614,
            "gas": 300000,
            "gasPrice": 100000000,
            "nonce": 5,
            "from": "0x1234567890123456789012345678901234567890"
        }
        mock_contract.functions.anchorEvidence.return_value = mock_func
        mock_w3_inst.eth.contract.return_value = mock_contract

        # Mock transaction signing & raw submission
        mock_signed_tx = MagicMock()
        mock_signed_tx.rawTransaction = b"signed_tx_raw_bytes"
        mock_w3_inst.eth.account.sign_transaction.return_value = mock_signed_tx
        mock_w3_inst.eth.send_raw_transaction.return_value = b"\xaa" * 32

        # Mock transaction receipt
        mock_receipt = MagicMock()
        mock_receipt.transactionHash = b"\xaa" * 32
        mock_receipt.blockNumber = 14920381
        mock_receipt.gasUsed = 45000
        mock_receipt.status = 1
        mock_w3_inst.eth.wait_for_transaction_receipt.return_value = mock_receipt

        mock_web3_cls.return_value = mock_w3_inst

        # Instantiate BlockchainClient with mock key & contract address
        client = BlockchainClient(
            rpc_url="https://sepolia-rollup.arbitrum.io/rpc",
            private_key="0x" + "11" * 32,
            contract_address="0x" + "22" * 20
        )
        client.w3 = mock_w3_inst
        client.contract = mock_contract
        client.account = MagicMock(address="0x1234567890123456789012345678901234567890")

        evidence_hash_hex = "0x" + "44" * 32
        source_url = "https://twitter.com/target_user/status/123456789"

        result = client.anchor(evidence_hash_hex, source_url)

        assert "tx_hash" in result
        assert result["block_number"] == 14920381
        assert "explorer_url" in result
        assert "sepolia.arbiscan.io" in result["explorer_url"]

    @patch("src.blockchain.Web3")
    def test_verify_evidence_offline_mock(self, mock_web3_cls):
        mock_w3_inst = MagicMock()
        mock_contract = MagicMock()

        # Mock verifyEvidence view call
        evidence_hash_bytes = b"\x44" * 32
        mock_record_tuple = (
            evidence_hash_bytes,
            "https://twitter.com/target_user/status/123456789",
            1757149500,
            "0x1234567890123456789012345678901234567890"
        )
        mock_contract.functions.verifyEvidence.return_value.call.return_value = (True, mock_record_tuple)
        mock_w3_inst.eth.contract.return_value = mock_contract

        client = BlockchainClient(
            rpc_url="https://sepolia-rollup.arbitrum.io/rpc",
            contract_address="0x" + "22" * 20
        )
        client.w3 = mock_w3_inst
        client.contract = mock_contract

        res = client.verify("0x" + "44" * 32)

        assert res["exists"] is True
        assert res["source_url"] == "https://twitter.com/target_user/status/123456789"
        assert res["registered_by"] == "0x1234567890123456789012345678901234567890"
        assert res["timestamp"] == 1757149500
