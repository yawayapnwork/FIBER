"""
Unit tests for src/search.py module.
"""

import unittest
from unittest.mock import patch, MagicMock
from PIL import Image
from src.search import CopyseekerSearchEngine

class TestCopyseekerSearchEngine(unittest.TestCase):
    def test_missing_api_key_raises_error(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ValueError):
                CopyseekerSearchEngine(api_key=None)

    @patch("src.search.requests.post")
    def test_search_by_pil_image(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "similar_images": [
                {"url": "https://example.com/match1.jpg", "score": 0.95}
            ]
        }
        mock_post.return_value = mock_response

        engine = CopyseekerSearchEngine(api_key="test_rapidapi_key")
        test_img = Image.new("RGB", (50, 50), color="blue")
        res = engine.search_by_image(test_img)

        self.assertNotIn("error", res)
        self.assertIn("similar_images", res)
        self.assertEqual(len(res["similar_images"]), 1)

if __name__ == "__main__":
    unittest.main()
