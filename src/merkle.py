"""
F.I.B.E.R. Merkle Module
Constructs a 3-leaf Merkle Tree for evidence commitment.
Pure Python using standard hashlib (SHA-256).
"""

import hashlib
import hmac
import json
from typing import Any

class EvidenceMerkleTree:
    """
    Constructs and verifies a 3-leaf Merkle Tree evidence commitment.
    
    Structure:
    - Leaf A: sha256(input_face_embedding_bytes) (Biometric Root)
    - Leaf B: sha256(matched_asset_image_bytes) (Visual Asset Root)
    - Leaf C: sha256(canonical_json_bytes) (Context Root)
    - Node AB: sha256(Leaf_A + Leaf_B)
    - Root: sha256(Node_AB + Leaf_C)
    """

    @staticmethod
    def _hash(data: bytes) -> bytes:
        """Compute SHA-256 digest of input bytes."""
        return hashlib.sha256(data).digest()

    @staticmethod
    def _canonical_json(metadata: dict[str, Any]) -> bytes:
        """
        Serialize metadata dictionary to canonical JSON bytes.
        Ensures keys are sorted and spaces removed for deterministic serialization.
        """
        return json.dumps(
            metadata,
            sort_keys=True,
            separators=(',', ':'),
            ensure_ascii=False
        ).encode('utf-8')

    @classmethod
    def build_tree(
        cls, 
        input_vector_bytes: bytes, 
        asset_bytes: bytes, 
        metadata: dict[str, Any],
        salt: bytes = None
    ) -> dict[str, Any]:
        """
        Builds the 3-leaf Merkle tree from raw inputs.
        
        :param input_vector_bytes: Raw bytes of the input face embedding
        :param asset_bytes: Raw bytes of the matched visual asset
        :param metadata: Dictionary containing context data (e.g. url, timestamp, author)
        :param salt: Optional 32-byte salt for blinded commitment
        :return: Dictionary containing the 0x-prefixed merkle root and leaf hashes
        """
        # Calculate Leaves (32 bytes each)
        if salt:
            leaf_a = hmac.new(salt, input_vector_bytes, hashlib.sha256).digest()
        else:
            leaf_a = cls._hash(input_vector_bytes)
            
        leaf_b = cls._hash(asset_bytes)
        leaf_c = cls._hash(cls._canonical_json(metadata))

        # Calculate Intermediate Node AB
        node_ab = cls._hash(leaf_a + leaf_b)
        
        # Calculate Merkle Root
        root = cls._hash(node_ab + leaf_c)

        return {
            "merkle_root": "0x" + root.hex(),
            "leaves": {
                "leaf_a": "0x" + leaf_a.hex(),
                "leaf_b": "0x" + leaf_b.hex(),
                "leaf_c": "0x" + leaf_c.hex()
            }
        }

    @classmethod
    def verify_integrity(
        cls, 
        merkle_root: str, 
        input_vector_bytes: bytes, 
        asset_bytes: bytes, 
        metadata: dict[str, Any],
        salt: bytes = None
    ) -> bool:
        """
        Verify the integrity of a provided Merkle root against raw inputs.
        
        :param merkle_root: The 0x-prefixed 32-byte hex root to verify
        :param input_vector_bytes: Original face embedding bytes
        :param asset_bytes: Original matched visual asset bytes
        :param metadata: Original context metadata
        :param salt: Optional 32-byte salt if the commitment was blinded
        :return: True if the recomputed root matches the provided root, False otherwise
        """
        # Ensure comparison is case-insensitive
        merkle_root = merkle_root.lower()
        if not merkle_root.startswith("0x"):
            merkle_root = "0x" + merkle_root
            
        recomputed_tree = cls.build_tree(input_vector_bytes, asset_bytes, metadata, salt)
        
        return recomputed_tree["merkle_root"] == merkle_root
