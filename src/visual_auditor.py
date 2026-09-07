import os
import numpy as np
from PIL import Image

def generate_tamper_delta(original_img_path: str, candidate_img_path: str, output_delta_path: str, threshold: float = 30.0) -> dict:
    """
    Compares two images using raw RGB Euclidean distances and outputs a vivid magenta delta mask
    for visually auditing physical tampering.
    """
    img1 = Image.open(original_img_path).convert("RGB")
    img2 = Image.open(candidate_img_path).convert("RGB")
    
    # Force resize candidate to original bounds for pixel-perfect comparison
    if img1.size != img2.size:
        img2 = img2.resize(img1.size, Image.Resampling.LANCZOS)
        
    arr1 = np.array(img1, dtype=np.float32)
    arr2 = np.array(img2, dtype=np.float32)
    
    # Calculate absolute per-pixel Euclidean distance across RGB channels
    diff = arr1 - arr2
    sq_diff = np.square(diff)
    euclidean_dist = np.sqrt(np.sum(sq_diff, axis=2))
    
    # Identify tampered pixels
    tampered_mask = euclidean_dist > threshold
    tampered_pixel_count = np.sum(tampered_mask)
    total_pixels = tampered_mask.size
    
    tamper_percentage = (tampered_pixel_count / total_pixels) * 100.0
    structural_parity_score = 100.0 - tamper_percentage
    
    # Bounding Box Calculation
    y_indices, x_indices = np.where(tampered_mask)
    if len(y_indices) > 0:
        min_x, max_x = int(np.min(x_indices)), int(np.max(x_indices))
        min_y, max_y = int(np.min(y_indices)), int(np.max(y_indices))
        bounding_box = (min_x, min_y, max_x, max_y)
    else:
        bounding_box = None
        
    # Apply amplification mask
    # 1. Convert original image to desaturated grayscale background
    grayscale = np.mean(arr1, axis=2, keepdims=True)
    # Dim the background slightly to make magenta pop more
    grayscale = grayscale * 0.6
    base_img = np.repeat(grayscale, 3, axis=2).astype(np.uint8)
    
    # 2. Highlight tampered regions in vivid magenta
    base_img[tampered_mask] = [255, 0, 255]
    
    # Ensure directory exists and save the output delta image
    os.makedirs(os.path.dirname(os.path.abspath(output_delta_path)), exist_ok=True)
    out_pil = Image.fromarray(base_img)
    out_pil.save(output_delta_path)
    
    return {
        "tamper_percentage": round(tamper_percentage, 4),
        "structural_parity_score": round(structural_parity_score, 4),
        "bounding_box": bounding_box,
        "delta_path": output_delta_path
    }
