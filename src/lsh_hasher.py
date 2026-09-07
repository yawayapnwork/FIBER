import numpy as np
import torch

def get_projection_matrix(input_dim: int = 512, hash_size: int = 64, seed: int = 42) -> np.ndarray:
    """
    Generate a deterministic random projection matrix.
    """
    rng = np.random.RandomState(seed)
    # Generate random hyperplanes from standard normal distribution
    matrix = rng.randn(input_dim, hash_size)
    return matrix

# Cache the projection matrix so we don't re-generate it on every call
PROJECTION_MATRIX = get_projection_matrix()

def compute_simhash(vector: torch.Tensor) -> int:
    """
    Computes a 64-bit SimHash from a 512-D embedding tensor using random projection.
    
    :param vector: A PyTorch tensor of shape (1, 512) or (512,)
    :return: 64-bit integer mask
    """
    vec_np = vector.detach().cpu().numpy().flatten()
    
    if len(vec_np) != 512:
        raise ValueError(f"Expected 512-dimensional vector, got {len(vec_np)}")
    
    # Project vector onto hyperplanes
    projections = np.dot(vec_np, PROJECTION_MATRIX)
    
    # Map positive to 1, else 0
    bits = (projections > 0).astype(int)
    
    # Convert bits array to 64-bit integer
    hash_value = 0
    for bit in bits:
        hash_value = (hash_value << 1) | int(bit)
        
    return hash_value

def compute_simhash_distance(hash_a: int, hash_b: int) -> int:
    """
    Compute the Hamming distance between two 64-bit SimHashes.
    
    :param hash_a: First 64-bit integer hash
    :param hash_b: Second 64-bit integer hash
    :return: Number of differing bits
    """
    xor_val = hash_a ^ hash_b
    return bin(xor_val).count('1')
