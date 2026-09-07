"""
Passive Liveness Detection Analyzer
Implements High-Frequency Fourier Texture Checks and Chrominance Divergence Analysis
to prevent static photo and screen spoofing attacks.
"""

import numpy as np
from PIL import Image

def verify_liveness(face_image: Image.Image) -> dict:
    """
    Perform passive liveness heuristics on a cropped facial image.
    
    :param face_image: PIL Image of the cropped face
    :return: dict containing liveness score, boolean flag, and metric details
    """
    # 1. Texture Entropy Check (2D FFT)
    # Convert to grayscale array
    gray_img = face_image.convert("L")
    gray_arr = np.array(gray_img, dtype=np.float64)
    
    # Compute 2D Fast Fourier Transform
    f = np.fft.fft2(gray_arr)
    fshift = np.fft.fftshift(f)
    magnitude_spectrum = np.abs(fshift) ** 2
    
    # Calculate energy ratio: high frequency / total
    rows, cols = gray_arr.shape
    crow, ccol = rows // 2, cols // 2
    # Radius for low frequency (inner 15% of the shortest dimension)
    r = int(min(rows, cols) * 0.15) 
    
    y, x = np.ogrid[-crow:rows-crow, -ccol:cols-ccol]
    mask = x*x + y*y <= r*r
    
    low_energy = np.sum(magnitude_spectrum[mask])
    total_energy = np.sum(magnitude_spectrum)
    
    # Avoid division by zero
    if total_energy == 0:
        total_energy = 1e-8
        
    high_energy = total_energy - low_energy
    texture_entropy = float(high_energy / total_energy)
    
    # 2. Chrominance Divergence Analysis (Specular / Color checking)
    # Ensure image is RGB
    rgb_img = face_image.convert("RGB")
    rgb_arr = np.array(rgb_img, dtype=np.float32)
    
    r_ch = rgb_arr[:, :, 0]
    g_ch = rgb_arr[:, :, 1]
    b_ch = rgb_arr[:, :, 2]
    
    # Mean absolute difference between color channels
    rg_diff = np.abs(r_ch - g_ch).mean()
    gb_diff = np.abs(g_ch - b_ch).mean()
    rb_diff = np.abs(r_ch - b_ch).mean()
    
    chrominance_divergence = float((rg_diff + gb_diff + rb_diff) / 3.0)
    
    # Dynamic range clipping check (screens often have pure black or clipped highlights)
    clipped_pixels = np.sum((rgb_arr >= 250) | (rgb_arr <= 5))
    clipping_ratio = float(clipped_pixels / rgb_arr.size)
    
    # 3. Compute Liveness Score
    # Start with a perfect score and apply penalties based on heuristics
    score = 1.0
    
    # A printed photo is typically very blurry (low high-frequency texture)
    # Real faces typically have texture_entropy around 0.0025 - 0.0050
    if texture_entropy < 0.001:
        score -= 0.4
    
    # A screen often emits moire patterns which cause distinct high frequency spikes
    if texture_entropy > 0.02:
        score -= 0.3
        
    # Printed paper often lacks the deep variance of human skin / subsurface scattering
    if chrominance_divergence < 5.0:
        score -= 0.3
        
    # Glare from a screen glass causes clipped highlights
    if clipping_ratio > 0.1:
        score -= 0.2
        
    # Clamp score
    score = max(0.0, min(1.0, score))
    is_live = score >= 0.70
    
    return {
        "liveness_score": round(score, 4),
        "is_live": is_live,
        "checks": {
            "texture_entropy": round(texture_entropy, 4),
            "chrominance_divergence": round(chrominance_divergence, 4),
            "clipping_ratio": round(clipping_ratio, 4)
        }
    }
