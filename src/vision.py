"""
F.I.B.E.R. Vision Module
Pure Python facial identification pipeline using Pillow (PIL) and facenet-pytorch (MTCNN).
STRICT CONSTRAINT: No OpenCV (cv2) or libGL dependencies.
"""

from typing import List, Optional, Dict, Any, Union
from PIL import Image
import torch
from facenet_pytorch import MTCNN
import io

class FaceDetector:
    def __init__(self, keep_all: bool = True, device: Optional[str] = None):
        """
        Initialize MTCNN face detector with PyTorch and PIL.
        """
        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device
            
        # Initialize MTCNN without cv2 dependence
        self.mtcnn = MTCNN(
            keep_all=keep_all,
            select_largest=False,
            device=self.device,
            post_process=False
        )

    def detect_and_crop(
        self, image_input: Union[str, Image.Image]
    ) -> List[Dict[str, Any]]:
        """
        Detect faces in an image and return facial bounding boxes, confidence scores,
        and cropped PIL Image objects.
        
        :param image_input: Path string or PIL Image object
        :return: List of dicts containing 'box', 'prob', and 'crop_pil'
        """
        if isinstance(image_input, str):
            img = Image.open(image_input).convert('RGB')
        elif isinstance(image_input, Image.Image):
            img = image_input.convert('RGB')
        else:
            raise ValueError("Input must be a file path string or PIL Image object.")

        # Detect boxes and probabilities using MTCNN
        boxes, probs = self.mtcnn.detect(img)
        
        results = []
        if boxes is not None and len(boxes) > 0:
            for box, prob in zip(boxes, probs):
                if prob is None or prob < 0.85:
                    continue
                
                # Box coordinates: [left, top, right, bottom]
                left, top, right, bottom = [int(coord) for coord in box]
                
                # Clamp coordinates to image boundaries
                width, height = img.size
                left = max(0, left)
                top = max(0, top)
                right = min(width, right)
                bottom = min(height, bottom)

                if right <= left or bottom <= top:
                    continue

                # Crop face using PIL crop (no cv2)
                cropped_img = img.crop((left, top, right, bottom))

                results.append({
                    "box": [left, top, right, bottom],
                    "prob": float(prob),
                    "crop_pil": cropped_img
                })

        return results

    @staticmethod
    def pil_to_bytes(img: Image.Image, format: str = "JPEG") -> bytes:
        """Convert a PIL Image to raw bytes."""
        buffer = io.BytesIO()
        img.save(buffer, format=format)
        return buffer.getvalue()
