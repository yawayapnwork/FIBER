"""
Unit tests for src/vision.py module.
"""

import unittest
from PIL import Image
from src.vision import FaceDetector

class TestFaceDetector(unittest.TestCase):
    def test_pil_to_bytes(self):
        img = Image.new("RGB", (64, 64), color="green")
        raw_bytes = FaceDetector.pil_to_bytes(img)
        self.assertIsInstance(raw_bytes, bytes)
        self.assertGreater(len(raw_bytes), 0)

    def test_detector_invalid_input(self):
        detector = FaceDetector()
        with self.assertRaises(ValueError):
            detector.detect_and_crop(12345)

if __name__ == "__main__":
    unittest.main()
