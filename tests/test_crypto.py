"""
QA & Automation Unit Tests for src/crypto.py
Using pytest.
"""

from eth_account import Account

from src.crypto import FiberCrypto, generate_evidence_hash


class TestCryptoModule:
    def test_rfc8785_canonical_json_determinism(self):
        manifest_v1 = {
            "source_url": "https://twitter.com/user/status/100",
            "metadata": {"discovered_at": 1757149500, "confidence": 0.98},
            "facial_crop_keccak256": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        }

        manifest_v2 = {
            "facial_crop_keccak256": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            "metadata": {"confidence": 0.98, "discovered_at": 1757149500},
            "source_url": "https://twitter.com/user/status/100"
        }

        hex_1, bytes_1 = generate_evidence_hash(manifest_v1)
        hex_2, bytes_2 = generate_evidence_hash(manifest_v2)

        assert hex_1 == hex_2
        assert bytes_1 == bytes_2

    def test_hash_format_and_length(self):
        sample_payload = {"evidence": "test_data_123"}
        hex_str, bytes32_val = generate_evidence_hash(sample_payload)

        assert hex_str.startswith("0x")
        assert len(hex_str) == 66
        assert isinstance(bytes32_val, bytes)
        assert len(bytes32_val) == 32

    def test_sign_facial_record_ecdsa(self):
        acc = Account.create()
        sample_hash = b"\xaa" * 32
        signed = FiberCrypto.sign_facial_record(
            private_key=acc.key.hex(),
            face_hash=sample_hash,
            metadata_uri="https://fiber.enforcement/match"
        )

        assert "signature" in signed
        assert "r" in signed
        assert "s" in signed
        assert "v" in signed
