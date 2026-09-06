"""
F.I.B.E.R. Vision Module
Pure Python facial identification pipeline using Pillow (PIL) and facenet-pytorch (MTCNN).

STRICT CONSTRAINT: DO NOT import `cv2` or use OpenCV anywhere in this file or project.
"""

import os
import sys
from typing import Any

import torch
from facenet_pytorch import MTCNN
from PIL import Image, ImageOps


class FaceDetector:
    def __init__(self, device: str | None = None, thresholds: list[float] | None = None):
        """Initialize MTCNN face detector using PyTorch and PIL."""
        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device

        if thresholds is None:
            thresholds = [0.6, 0.7, 0.85]

        # Initialize MTCNN without any OpenCV dependence
        self.mtcnn = MTCNN(
            keep_all=True,
            select_largest=False,
            device=self.device,
            thresholds=thresholds,
            post_process=False
        )


def _detect_and_select_face(img: Image.Image, detector: FaceDetector, min_conf: float):
    boxes, probs = detector.mtcnn.detect(img)
    if boxes is None or probs is None or len(boxes) == 0:
        return None

    valid_faces: list[tuple[list[float], float, float]] = []
    for box, prob in zip(boxes, probs):
        if prob is not None and prob >= min_conf:
            l, t, r, b = box
            area = max(0.0, r - l) * max(0.0, b - t)
            valid_faces.append((box, prob, area))

    if not valid_faces:
        return None

    valid_faces.sort(key=lambda x: x[2], reverse=True)
    return valid_faces[0]


def extract_face_info(
    image_path: str,
    output_path: str = "cropped_face.jpg",
    padding: int = 15,
    min_confidence: float = 0.85,
    device: str | None = None
) -> dict[str, Any]:
    """
    Detect faces, select the largest valid human face, apply padding,
    crop using Pillow, save high-quality JPEG, and return detailed face metrics dictionary.
    Includes adaptive, progressive fallback for extreme occlusion and yaw angles.

    :param image_path: Input image file path
    :param output_path: Destination file path for face crop
    :param padding: Padding pixels to add around face bounding box
    :param min_confidence: Minimum MTCNN detection probability score (default: 0.85)
    :param device: PyTorch device ('cpu' or 'cuda')
    :return: Dictionary containing output_path, box, width, height, aspect_ratio, confidence, profile_recovered
    :raises ValueError: If image path is invalid or no valid face is detected after all passes
    """
    if not os.path.exists(image_path):
        raise ValueError(f"Input image path does not exist: {image_path}")

    try:
        orig_img = Image.open(image_path)
        orig_img = ImageOps.exif_transpose(orig_img).convert("RGB")
    except Exception as e:
        raise ValueError(f"Failed to open image file '{image_path}': {e}")

    # 1. Primary Pass
    primary_detector = FaceDetector(device=device, thresholds=[0.6, 0.7, 0.85])
    best_face = _detect_and_select_face(orig_img, primary_detector, min_confidence)
    
    img_to_crop = orig_img
    profile_recovered = False

    # 2. Fallback Pass (Test-Time Augmentation & Multi-Scale)
    if best_face is None:
        fallback_detector = FaceDetector(device=device, thresholds=[0.5, 0.6, 0.70])
        
        # a. Contrast & Histogram Equalization
        auto_img = ImageOps.autocontrast(orig_img)
        
        # b. Multi-Scale Resizing
        scales = [1.25, 0.8]
        for scale in scales:
            new_size = (int(auto_img.width * scale), int(auto_img.height * scale))
            scaled_img = auto_img.resize(new_size, Image.Resampling.LANCZOS)
            
            # c. Relaxed Profile Threshold (0.70 min_confidence instead of 0.85)
            face = _detect_and_select_face(scaled_img, fallback_detector, 0.70)
            if face is not None:
                box, prob, area = face
                l, t, r, b = box
                w = r - l
                h = b - t
                
                # Strict Safety Anchor
                if w >= 60 and h >= 60:
                    best_face = face
                    img_to_crop = scaled_img
                    profile_recovered = True
                    break
                    
        if best_face is None:
            raise ValueError("No human face detected even after multi-scale adaptive recovery.")

    # We now have the best box on img_to_crop
    best_box, best_prob, _ = best_face
    width, height = img_to_crop.size

    # Add padding pixels around coordinates while bounding within image dimensions
    left = max(0, int(best_box[0] - padding))
    top = max(0, int(best_box[1] - padding))
    right = min(width, int(best_box[2] + padding))
    bottom = min(height, int(best_box[3] + padding))

    crop_w = right - left
    crop_h = bottom - top

    if crop_w <= 0 or crop_h <= 0:
        raise ValueError("No human face detected even after multi-scale adaptive recovery (invalid dimensions).")

    # Crop face region using Pillow, save as high-quality JPEG
    cropped_face = img_to_crop.crop((left, top, right, bottom))

    out_dir = os.path.dirname(os.path.abspath(output_path))
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    cropped_face.save(output_path, format="JPEG", quality=95)
    
    aspect_ratio = round(crop_w / crop_h, 2) if crop_h > 0 else 1.0

    return {
        "output_path": output_path,
        "box": [left, top, right, bottom],
        "width": crop_w,
        "height": crop_h,
        "aspect_ratio": aspect_ratio,
        "confidence": float(best_prob),
        "profile_recovered": profile_recovered
    }


def extract_face(
    image_path: str,
    output_path: str = "cropped_face.jpg",
    padding: int = 15,
    min_confidence: float = 0.85,
    device: str | None = None
) -> str:
    """Wrapper returning output_path string."""
    res = extract_face_info(image_path, output_path, padding, min_confidence, device)
    return res["output_path"]


if __name__ == "__main__":
    print("[F.I.B.E.R. Vision] Running standalone adaptive face extraction test...")

    sample_img_path = "sample_test.jpg"
    out_crop_path = "output_cropped_face.jpg"

    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        sample_img = Image.new("RGB", (300, 300), color=(220, 220, 220))
        sample_img.save(sample_img_path)
        input_file = sample_img_path

    try:
        info = extract_face_info(input_file, output_path=out_crop_path, padding=15)
        print(f"[+] Face extraction succeeded: {info}")
    except ValueError as err:
        print(f"[!] Expected result / face detection error: {err}")
    finally:
        if os.path.exists(sample_img_path) and len(sys.argv) <= 1:
            os.remove(sample_img_path)
        if os.path.exists(out_crop_path):
            os.remove(out_crop_path)
