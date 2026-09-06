"""
Unit tests for src/crypto.py module.
"""

import unittest
from PIL import Image
from eth_account import Account
from src.crypto import FiberCrypto

class TestFiberCrypto(unittest.TestCase):
    def setUp(self):
        # Create a simple test PIL Image
        self.test_img = Image.new('RGB', (100, 100), color='red')
        self.test_account = Account.create()

    def test_hash_image_bytes(self):
        data = b"fiber_test_data"
        hash_val = FiberCrypto.hash_image_bytes(data)
        self.assertIsInstance(hash_val, str)
        self.assertEqual(len(hash_val), 64)

    def test_hash_pil_image(self):
        hash_bytes = FiberCrypto.hash_pil_image(self.test_img)
        self.assertIsInstance(hash_bytes, bytes)
        self.assertEqual(len(hash_bytes), 32)

    def test_hash_string_to_bytes32(self):
        hash_bytes = FiberCrypto.hash_string_to_bytes32("test_string")
        self.assertIsInstance(hash_bytes, bytes)
        self.assertEqual(len(hash_bytes), 32)

    def test_sign_facial_record(self):
        face_hash = FiberCrypto.hash_pil_image(self.test_img)
        signed = FiberCrypto.sign_facial_record(
            private_key=self.test_account.key.hex(),
            face_hash=face_hash,
            metadata_uri="ipfs://QmTest"
        )
        self.assertIn("signature", signed)
        self.assertIn("r", signed)
        self.assertIn("s", signed)
        self.assertIn("v", signed)

if __name__ == "__main__":
    unittest.main()
