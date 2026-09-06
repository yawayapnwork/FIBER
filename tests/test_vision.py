"""
Unit tests for src/vision.py module.
"""

import os
import unittest
from PIL import Image
from src.vision import extract_face, FaceDetector

class TestVisionModule(unittest.TestCase):
    def setUp(self):
        self.sample_img_path = "test_vision_input.jpg"
        self.output_crop_path = "test_vision_output.jpg"
        # Create a simple synthetic image
        img = Image.new("RGB", (200, 200), color=(180, 180, 180))
        img.save(self.sample_img_path)

    def tearDown(self):
        if os.path.exists(self.sample_img_path):
            os.remove(self.sample_img_path)
        if os.path.exists(self.output_crop_path):
            os.remove(self.output_crop_path)

    def test_extract_face_no_face_raises_value_error(self):
        # A blank synthetic image should raise ValueError("No valid human face detected")
        with self.assertRaises(ValueError) as ctx:
            extract_face(self.sample_img_path, output_path=self.output_crop_path)
        self.assertIn("No valid human face detected", str(ctx.exception))

    def test_extract_face_invalid_file_raises_value_error(self):
        with self.assertRaises(ValueError):
            extract_face("non_existent_file.jpg", output_path=self.output_crop_path)

    def test_face_detector_init(self):
        detector = FaceDetector()
        self.assertIsNotNone(detector.mtcnn)

if __name__ == "__main__":
    unittest.main()
