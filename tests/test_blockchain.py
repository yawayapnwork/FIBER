"""
Unit tests for src/blockchain.py module.
"""

import unittest
from unittest.mock import patch, MagicMock
from src.blockchain import ArbitrumFiberClient

class TestArbitrumFiberClient(unittest.TestCase):
    def test_client_init_defaults(self):
        client = ArbitrumFiberClient(rpc_url="https://sepolia-rollup.arbitrum.io/rpc")
        self.assertEqual(client.rpc_url, "https://sepolia-rollup.arbitrum.io/rpc")
        self.assertIsNone(client.account)
        self.assertIsNone(client.contract)

    @patch("src.blockchain.Web3")
    def test_is_connected(self, mock_web3_cls):
        mock_w3_instance = MagicMock()
        mock_w3_instance.is_connected.return_value = True
        mock_web3_cls.return_value = mock_w3_instance

        client = ArbitrumFiberClient(rpc_url="https://sepolia-rollup.arbitrum.io/rpc")
        self.assertTrue(client.is_connected())

if __name__ == "__main__":
    unittest.main()
