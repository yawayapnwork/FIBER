"""
Unit tests for src/search.py module.
"""

import unittest
from unittest.mock import patch, MagicMock
from PIL import Image
import requests
from src.search import (
    CopyseekerSearchEngine,
    CopyseekerRateLimitError,
    CopyseekerTimeoutError,
    NoMatchesFoundError,
    perform_reverse_search
)

class TestCopyseekerSearchEngine(unittest.TestCase):
    def test_missing_api_key_raises_error(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ValueError):
                CopyseekerSearchEngine(api_key=None)

    @patch("src.search.requests.post")
    def test_search_prioritizes_social_domain(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "visual_matches": [
                {"url": "https://generic-blog.com/photo.jpg", "title": "Generic Blog"},
                {"url": "https://twitter.com/user/status/123", "title": "Twitter Post"},
                {"url": "https://instagram.com/p/abc", "title": "Instagram Post"}
            ]
        }
        mock_post.return_value = mock_response

        engine = CopyseekerSearchEngine(api_key="test_key")
        test_img = Image.new("RGB", (50, 50), color="blue")
        res = engine.search(test_img)

        self.assertEqual(res["source_url"], "https://twitter.com/user/status/123")
        self.assertEqual(res["page_title"], "Twitter Post")
        self.assertIn("discovered_at", res)

    @patch("src.search.requests.post")
    def test_search_fallback_to_highest_rank(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "visual_matches": [
                {"url": "https://news-outlet.com/article1", "title": "News Title 1"},
                {"url": "https://another-blog.org/page", "title": "Blog Page"}
            ]
        }
        mock_post.return_value = mock_response

        engine = CopyseekerSearchEngine(api_key="test_key")
        test_img = Image.new("RGB", (50, 50), color="green")
        res = engine.search(test_img)

        self.assertEqual(res["source_url"], "https://news-outlet.com/article1")
        self.assertEqual(res["page_title"], "News Title 1")

    @patch("src.search.requests.post")
    def test_rate_limit_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_post.return_value = mock_response

        engine = CopyseekerSearchEngine(api_key="test_key")
        test_img = Image.new("RGB", (10, 10))
        with self.assertRaises(CopyseekerRateLimitError):
            engine.search(test_img)

    @patch("src.search.requests.post")
    def test_timeout_error(self, mock_post):
        mock_post.side_effect = requests.exceptions.Timeout("Timed out")
        engine = CopyseekerSearchEngine(api_key="test_key")
        test_img = Image.new("RGB", (10, 10))
        with self.assertRaises(CopyseekerTimeoutError):
            engine.search(test_img)

    @patch("src.search.requests.post")
    def test_no_matches_found_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"visual_matches": []}
        mock_post.return_value = mock_response

        engine = CopyseekerSearchEngine(api_key="test_key")
        test_img = Image.new("RGB", (10, 10))
        with self.assertRaises(NoMatchesFoundError):
            engine.search(test_img)

if __name__ == "__main__":
    unittest.main()
