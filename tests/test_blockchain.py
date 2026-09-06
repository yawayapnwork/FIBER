"""
Unit tests for src/blockchain.py module.
"""

import unittest
from unittest.mock import patch, MagicMock
from src.blockchain import BlockchainClient, ArbitrumFiberClient

class TestBlockchainClient(unittest.TestCase):
    def test_client_init_defaults(self):
        client = BlockchainClient(rpc_url="https://sepolia-rollup.arbitrum.io/rpc")
        self.assertEqual(client.rpc_url, "https://sepolia-rollup.arbitrum.io/rpc")
        self.assertIsNone(client.account)
        self.assertIsNone(client.contract)

    @patch("src.blockchain.Web3")
    def test_is_connected(self, mock_web3_cls):
        mock_w3_instance = MagicMock()
        mock_w3_instance.is_connected.return_value = True
        mock_web3_cls.return_value = mock_w3_instance

        client = BlockchainClient(rpc_url="https://sepolia-rollup.arbitrum.io/rpc")
        self.assertTrue(client.is_connected())

    def test_verify_no_contract_raises(self):
        client = BlockchainClient(rpc_url="https://sepolia-rollup.arbitrum.io/rpc")
        with self.assertRaises(ValueError):
            client.verify("0x" + "00" * 32)

    def test_anchor_no_account_raises(self):
        client = BlockchainClient(rpc_url="https://sepolia-rollup.arbitrum.io/rpc")
        with self.assertRaises(ValueError):
            client.anchor("0x" + "11" * 32, "https://example.com")

if __name__ == "__main__":
    unittest.main()
