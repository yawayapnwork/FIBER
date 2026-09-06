import hashlib
import io
import json
import pytest
import torch
from PIL import Image, ImageDraw
from eth_account import Account
from eth_account.messages import encode_defunct

# --- Mocks for the pipeline ---

def extract_biometric_commitment(tensor: torch.Tensor) -> bytes:
    """
    Mock extracting a deterministically reproducible 32-byte vectorRoot.
    In production, this would pass the tensor through InceptionResnetV1.
    """
    # Deterministic hash based on tensor data to simulate vector root
    return hashlib.sha256(tensor.numpy().tobytes()).digest()

def phash(image: Image.Image) -> str:
    """
    Mock perceptual hashing (64-bit).
    Resizes to 8x8, converts to grayscale, and binarizes based on the mean pixel value.
    """
    image = image.convert("L").resize((8, 8), Image.Resampling.LANCZOS)
    pixels = list(image.getdata() if not hasattr(image, 'get_flattened_data') else image.get_flattened_data())
    avg = sum(pixels) / len(pixels)
    bits = "".join(["1" if p > avg else "0" for p in pixels])
    return bits

def hamming_distance(hash1: str, hash2: str) -> int:
    """Calculate the Hamming distance between two binary strings of equal length."""
    return sum(c1 != c2 for c1, c2 in zip(hash1, hash2))

def get_sha256(image: Image.Image) -> bytes:
    """Calculate the exact SHA-256 hash of a PIL Image when saved as JPEG."""
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=100)
    return hashlib.sha256(buffer.getvalue()).digest()

# --- Tests ---

def test_extract_biometric_commitment():
    """
    Requirement 1: Mock MTCNN & InceptionResnetV1
    Provide a synthetic 160x160 RGB tensor and verify deterministic 32-byte vectorRoot.
    """
    # Create a synthetic 160x160 RGB tensor
    # Fix the seed so it's reproducible across runs for testing if needed,
    # but the function itself should be deterministic for the *same* input.
    torch.manual_seed(42)
    tensor = torch.rand(3, 160, 160)
    
    vectorRoot1 = extract_biometric_commitment(tensor)
    vectorRoot2 = extract_biometric_commitment(tensor)
    
    assert len(vectorRoot1) == 32
    assert vectorRoot1 == vectorRoot2, "vectorRoot must be deterministically reproducible"

def test_perceptual_hashing_and_hamming():
    """
    Requirement 2: Mock Perceptual Hashing & Hamming Distance
    Create clean and perturbed synthetic images. Assert exact SHA-256 changes while 
    64-bit phash retains a Hamming distance <= 2.
    """
    # Create clean synthetic image with some features
    clean_img = Image.new("RGB", (256, 256), color=(200, 200, 200))
    draw = ImageDraw.Draw(clean_img)
    draw.rectangle([50, 50, 200, 200], fill=(50, 100, 150))
    draw.ellipse([100, 100, 150, 150], fill=(255, 0, 0))
    
    # Create perturbed image with slight JPEG noise
    buffer = io.BytesIO()
    clean_img.save(buffer, format="JPEG", quality=15)
    buffer.seek(0)
    perturbed_img = Image.open(buffer)
    
    sha_clean = get_sha256(clean_img)
    sha_perturbed = get_sha256(perturbed_img)
    
    # Exact SHA-256 must change due to JPEG compression noise
    assert sha_clean != sha_perturbed, "SHA-256 hashes should be different"
    
    phash_clean = phash(clean_img)
    phash_perturbed = phash(perturbed_img)
    
    # 64-bit phash representation
    assert len(phash_clean) == 64
    assert len(phash_perturbed) == 64
    
    dist = hamming_distance(phash_clean, phash_perturbed)
    assert dist <= 2, f"Hamming distance is {dist}, expected <= 2 for compression resilience"

def test_eip712_signing_and_recovery():
    """
    Requirement 3: Mock EIP-712 Signing & State Recovery
    Use eth_account to generate ephemeral test wallet, encode/sign Attestation struct, 
    and verify recovery.
    """
    # Generate an ephemeral test wallet (mock registrar)
    account = Account.create()
    registrar_address = account.address
    
    # Define an Attestation struct
    attestation = {
        "subject": "0x1234567890123456789012345678901234567890",
        "vectorRoot": "0x" + ("a" * 64),
        "timestamp": 1690000000
    }
    
    # Encode the struct (using encode_defunct for personal sign, or we could use structured data)
    # The prompt asks to verify with defunct_hash_message (now encode_defunct) and recover_message
    attestation_str = json.dumps(attestation, sort_keys=True)
    message = encode_defunct(text=attestation_str)
    
    # Sign the Attestation struct
    signed_message = Account.sign_message(message, private_key=account.key)
    
    # Verify with recover_message
    recovered_address = Account.recover_message(message, signature=signed_message.signature)
    
    assert recovered_address == registrar_address, "Recovered address must match the mock registrar"
