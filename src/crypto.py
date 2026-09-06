"""
F.I.B.E.R. Crypto Module
Cryptographic hashing (SHA-256, Keccak-256) and ECDSA message signing for facial identification records.
"""

import hashlib
from typing import Dict, Any
from PIL import Image
import io
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3

class FiberCrypto:
    @staticmethod
    def hash_image_bytes(image_bytes: bytes) -> str:
        """Calculate SHA-256 hash of raw image bytes (hex string)."""
        return hashlib.sha256(image_bytes).hexdigest()

    @staticmethod
    def hash_pil_image(img: Image.Image) -> bytes:
        """Calculate Keccak-256 hash of a PIL image (bytes32 format for EVM contracts)."""
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        raw_bytes = buffer.getvalue()
        return Web3.solidity_keccak(["bytes"], [raw_bytes])

    @staticmethod
    def hash_string_to_bytes32(text: str) -> bytes:
        """Calculate Keccak-256 of text string as bytes32."""
        return Web3.solidity_keccak(["string"], [text])

    @staticmethod
    def sign_facial_record(private_key: str, face_hash: bytes, metadata_uri: str) -> Dict[str, Any]:
        """
        Sign a facial record off-chain using private key.
        """
        msg_text = f"FIBER_RECORD:{face_hash.hex()}:{metadata_uri}"
        message = encode_defunct(text=msg_text)
        signed_message = Account.sign_message(message, private_key=private_key)

        return {
            "message": msg_text,
            "signature": signed_message.signature.hex(),
            "r": signed_message.r,
            "s": signed_message.s,
            "v": signed_message.v
        }
