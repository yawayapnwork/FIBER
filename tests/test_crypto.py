"""
Unit tests for src/crypto.py module.
"""

import unittest
from PIL import Image
from eth_account import Account
from src.crypto import FiberCrypto, generate_evidence_hash

class TestFiberCrypto(unittest.TestCase):
    def setUp(self):
        self.test_img = Image.new('RGB', (100, 100), color='red')
        self.test_account = Account.create()

    def test_generate_evidence_hash(self):
        payload_a = {"b": 2, "a": 1, "c": [3, 4]}
        payload_b = {"a": 1, "c": [3, 4], "b": 2}

        hex_a, bytes_a = generate_evidence_hash(payload_a)
        hex_b, bytes_b = generate_evidence_hash(payload_b)

        # RFC 8785 key sorting ensures determinism
        self.assertEqual(hex_a, hex_b)
        self.assertEqual(bytes_a, bytes_b)
        self.assertTrue(hex_a.startswith("0x"))
        self.assertEqual(len(hex_a), 66)  # '0x' + 64 hex chars
        self.assertEqual(len(bytes_a), 32)

    def test_hash_image_bytes(self):
        data = b"fiber_test_data"
        hex_val, digest_bytes = FiberCrypto.hash_image_bytes(data)
        self.assertTrue(hex_val.startswith("0x"))
        self.assertEqual(len(hex_val), 66)
        self.assertEqual(len(digest_bytes), 32)

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
