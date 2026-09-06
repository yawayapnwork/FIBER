"""
F.I.B.E.R. Crypto Module
Canonical manifest creation, SHA-256 / Keccak-256 fingerprinting, and ECDSA message signing.
"""

import hashlib
import io
import json
from typing import Any

from eth_account import Account
from eth_account.messages import encode_defunct
from PIL import Image
from web3 import Web3


def generate_evidence_hash(evidence_data: dict) -> tuple[str, bytes]:
    """
    Generate canonical evidence hash according to RFC 8785 JSON formatting.

    1. Sort keys deterministically and serialize without whitespace.
    2. Compute SHA-256 digest (32 bytes).
    3. Return tuple of (hex string starting with '0x', 32-byte representation).

    :param evidence_data: Dictionary containing evidence parameters/manifest
    :return: Tuple[str, bytes] -> ("0x...", 32-bytes)
    """
    if not isinstance(evidence_data, dict):
        raise TypeError("evidence_data must be a dictionary")

    # RFC 8785 canonical JSON formatting
    canonical_json_bytes = json.dumps(
        evidence_data,
        sort_keys=True,
        separators=(',', ':'),
        ensure_ascii=False
    ).encode('utf-8')

    digest_bytes = hashlib.sha256(canonical_json_bytes).digest()
    hex_str = "0x" + digest_bytes.hex()
    return hex_str, digest_bytes

class FiberCrypto:
    @staticmethod
    def generate_evidence_hash(evidence_data: dict) -> tuple[str, bytes]:
        """Wrapper for generate_evidence_hash."""
        return generate_evidence_hash(evidence_data)

    @staticmethod
    def hash_image_bytes(image_bytes: bytes) -> tuple[str, bytes]:
        """Calculate SHA-256 hash of raw image bytes returning (0x-hex, bytes32)."""
        digest = hashlib.sha256(image_bytes).digest()
        return "0x" + digest.hex(), digest

    @staticmethod
    def hash_pil_image(img: Image.Image) -> bytes:
        """Calculate Keccak-256 hash of a PIL image (32-byte representation for EVM contracts)."""
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        raw_bytes = buffer.getvalue()
        return Web3.solidity_keccak(["bytes"], [raw_bytes])

    @staticmethod
    def hash_string_to_bytes32(text: str) -> bytes:
        """Calculate Keccak-256 of text string as bytes32."""
        return Web3.solidity_keccak(["string"], [text])

    @staticmethod
    def sign_facial_record(private_key: str, face_hash: bytes, metadata_uri: str) -> dict[str, Any]:
        """
        Sign a facial record off-chain using private key.
        """
        msg_text = f"FIBER_RECORD:{face_hash.hex() if isinstance(face_hash, bytes) else face_hash}:{metadata_uri}"
        message = encode_defunct(text=msg_text)
        signed_message = Account.sign_message(message, private_key=private_key)

        return {
            "message": msg_text,
            "signature": signed_message.signature.hex(),
            "r": signed_message.r.hex() if hasattr(signed_message.r, 'hex') else hex(signed_message.r),
            "s": signed_message.s.hex() if hasattr(signed_message.s, 'hex') else hex(signed_message.s),
            "v": signed_message.v
        }
