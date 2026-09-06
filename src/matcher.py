"""
F.I.B.E.R. Matcher Module
Pure Python facial vector embedding and cosine similarity matching using PyTorch and PIL.
STRICT CONSTRAINT: DO NOT import `cv2` or use OpenCV anywhere in this file.
"""

import io
import os
from typing import Any

import requests
import torch
import torch.nn.functional as F
from PIL import Image, ImageOps
from facenet_pytorch import MTCNN, InceptionResnetV1

# Global instances for performance (avoid reloading weights)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# MTCNN for face detection and alignment
mtcnn = MTCNN(
    keep_all=False,
    select_largest=True,
    device=device,
    post_process=False
)

# InceptionResnetV1 for 512-D embedding extraction
resnet = InceptionResnetV1(pretrained='vggface2').eval().to(device)


def extract_embedding(image: Image.Image) -> torch.Tensor:
    """
    Align face and extract a normalized 512-dimensional vector embedding.
    Raises ValueError if no valid human face is detected with >0.85 probability.
    
    :param image: PIL Image object
    :return: 512-D torch.Tensor embedding
    """
    # Fix EXIF rotation issues
    image = ImageOps.exif_transpose(image).convert("RGB")
    
    # MTCNN returns the cropped, aligned face tensor and the probability
    x_aligned, prob = mtcnn(image, return_prob=True)
    
    if x_aligned is None or prob is None or prob < 0.85:
        raise ValueError("No valid human face detected with confidence > 0.85")
        
    # x_aligned shape is (3, 160, 160). Add batch dimension to make it (1, 3, 160, 160)
    x_aligned = x_aligned.unsqueeze(0).to(device)
    
    # Normalize the pixel values as expected by facenet_pytorch (-1 to 1)
    # MTCNN with post_process=False returns [0, 255]. We scale to [-1, 1].
    x_aligned = (x_aligned - 127.5) / 128.0
    
    # Extract the 512-D embedding vector without tracking gradients
    with torch.no_grad():
        embedding = resnet(x_aligned)
        
    return embedding


def verify_candidate_match(input_img_path: str, candidate_image_url: str, threshold: float = 0.72) -> dict[str, Any]:
    """
    Compare a local input face image against a remote candidate image URL.
    
    :param input_img_path: Local path to the primary search face
    :param candidate_image_url: Remote URL to the candidate image match
    :param threshold: Cosine similarity threshold for a positive match
    :return: Dictionary containing match results and vector bytes
    """
    if not os.path.exists(input_img_path):
        raise ValueError(f"Input image path does not exist: {input_img_path}")
        
    # 1. Process local input image
    try:
        input_img = Image.open(input_img_path)
        input_embedding = extract_embedding(input_img)
    except ValueError as e:
        # If the input image fails detection, that's a fatal error for the search cycle
        raise ValueError(f"Failed to extract face from input image: {e}")
        
    # 2. Process remote candidate image
    try:
        # Stream into memory directly via requests without writing to disk
        resp = requests.get(candidate_image_url, stream=True, timeout=15)
        resp.raise_for_status()
        candidate_img = Image.open(io.BytesIO(resp.content))
        candidate_embedding = extract_embedding(candidate_img)
    except (requests.RequestException, ValueError, OSError) as e:
        # Gracefully reject candidate images that fail download or face detection
        return {
            "similarity_score": 0.0,
            "is_match": False,
            "candidate_vector_bytes": b"",
            "input_vector_bytes": input_embedding.cpu().numpy().tobytes(),
            "error": str(e)
        }
        
    # 3. Compute Cosine Similarity
    cosine_sim = F.cosine_similarity(input_embedding, candidate_embedding).item()
    
    # 4. Return formatted results
    return {
        "similarity_score": round(cosine_sim, 4),
        "is_match": bool(cosine_sim >= threshold),
        "candidate_vector_bytes": candidate_embedding.cpu().numpy().tobytes(),
        "input_vector_bytes": input_embedding.cpu().numpy().tobytes()
    }
