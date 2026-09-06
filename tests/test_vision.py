"""
QA & Automation Unit Tests for src/vision.py
Using pytest and unittest.mock.
"""

import os
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image

import src.vision
from src.vision import extract_face


class TestVisionPipeline:
    @pytest.fixture(autouse=True)
    def setup_teardown(self, tmp_path):
        self.tmp_dir = tmp_path
        self.sample_input = str(self.tmp_dir / "sample_face_input.jpg")
        self.crop_output = str(self.tmp_dir / "cropped_output.jpg")

        # Create a sample input image
        img = Image.new("RGB", (200, 200), color=(200, 200, 200))
        img.save(self.sample_input)
        yield
        # Teardown
        if os.path.exists(self.sample_input):
            os.remove(self.sample_input)
        if os.path.exists(self.crop_output):
            os.remove(self.crop_output)

    @patch("src.vision.MTCNN")
    def test_extract_face_success_with_padding(self, mock_mtcnn_cls):
        # Mock MTCNN detect to return a valid face bounding box [l, t, r, b] and 0.95 prob
        mock_mtcnn_inst = MagicMock()
        mock_mtcnn_inst.detect.return_value = (
            np.array([[30.0, 30.0, 120.0, 120.0]]),
            np.array([0.95])
        )
        mock_mtcnn_cls.return_value = mock_mtcnn_inst

        out_path = extract_face(
            image_path=self.sample_input,
            output_path=self.crop_output,
            padding=15
        )

        assert os.path.exists(out_path)
        assert out_path == self.crop_output

        # Verify output is a valid JPEG created via Pillow
        crop_img = Image.open(out_path)
        assert crop_img.format == "JPEG"
        assert crop_img.size[0] > 0 and crop_img.size[1] > 0

    @patch("src.vision.MTCNN")
    def test_extract_face_low_confidence_raises_error(self, mock_mtcnn_cls):
        # Mock MTCNN returning 0.50 probability score (< 0.85 threshold)
        mock_mtcnn_inst = MagicMock()
        mock_mtcnn_inst.detect.return_value = (
            np.array([[30.0, 30.0, 120.0, 120.0]]),
            np.array([0.50])
        )
        mock_mtcnn_cls.return_value = mock_mtcnn_inst

        with pytest.raises(ValueError, match="No valid human face detected"):
            extract_face(
                image_path=self.sample_input,
                output_path=self.crop_output
            )

    @patch("src.vision.MTCNN")
    def test_extract_face_no_boxes_raises_error(self, mock_mtcnn_cls):
        mock_mtcnn_inst = MagicMock()
        mock_mtcnn_inst.detect.return_value = (None, None)
        mock_mtcnn_cls.return_value = mock_mtcnn_inst

        with pytest.raises(ValueError, match="No valid human face detected"):
            extract_face(
                image_path=self.sample_input,
                output_path=self.crop_output
            )

    def test_opencv_not_imported_in_vision_module(self):
        # Verify OpenCV (cv2) is not imported or used anywhere in src/vision.py
        assert not hasattr(src.vision, "cv2")
        with open(src.vision.__file__, "r", encoding="utf-8") as f:
            code_content = f.read()
        assert "import cv2" not in code_content
        assert "from cv2" not in code_content
        assert "cv2." not in code_content
