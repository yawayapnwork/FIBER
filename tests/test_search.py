"""
QA & Automation Unit Tests for src/search.py
Using pytest and unittest.mock.
"""

import pytest
from unittest.mock import patch, MagicMock
from PIL import Image
import requests
from src.search import (
    CopyseekerSearchEngine,
    CopyseekerRateLimitError,
    CopyseekerTimeoutError,
    NoMatchesFoundError,
    CopyseekerAPIError
)

class TestSearchModule:
    @patch("src.search.requests.post")
    def test_domain_prioritization_social_over_generic(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "visual_matches": [
                {"url": "https://random-forum.com/thread/1", "title": "Random Forum"},
                {"url": "https://twitter.com/target_user/status/987654321", "title": "Twitter Match"},
                {"url": "https://generic-news.com/article", "title": "News Article"}
            ]
        }
        mock_post.return_value = mock_resp

        engine = CopyseekerSearchEngine(api_key="mock_rapidapi_key")
        test_img = Image.new("RGB", (50, 50), color="blue")
        result = engine.search(test_img)

        assert result["source_url"] == "https://twitter.com/target_user/status/987654321"
        assert result["page_title"] == "Twitter Match"
        assert "discovered_at" in result

    @patch("src.search.requests.post")
    def test_fallback_to_highest_rank_web_match(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "visual_matches": [
                {"url": "https://primary-news-portal.com/photo", "title": "Primary News"},
                {"url": "https://secondary-blog.org/item", "title": "Secondary Blog"}
            ]
        }
        mock_post.return_value = mock_resp

        engine = CopyseekerSearchEngine(api_key="mock_rapidapi_key")
        test_img = Image.new("RGB", (50, 50), color="green")
        result = engine.search(test_img)

        assert result["source_url"] == "https://primary-news-portal.com/photo"
        assert result["page_title"] == "Primary News"

    @patch("src.search.requests.post")
    def test_empty_response_raises_no_matches_found(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"visual_matches": []}
        mock_post.return_value = mock_resp

        engine = CopyseekerSearchEngine(api_key="mock_rapidapi_key")
        test_img = Image.new("RGB", (50, 50))
        with pytest.raises(NoMatchesFoundError):
            engine.search(test_img)

    @patch("src.search.requests.post")
    def test_rate_limit_429_raises_custom_exception(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_post.return_value = mock_resp

        engine = CopyseekerSearchEngine(api_key="mock_rapidapi_key")
        test_img = Image.new("RGB", (50, 50))
        with pytest.raises(CopyseekerRateLimitError):
            engine.search(test_img)

    @patch("src.search.requests.post")
    def test_timeout_raises_custom_exception(self, mock_post):
        mock_post.side_effect = requests.exceptions.Timeout("Connection timed out")
        engine = CopyseekerSearchEngine(api_key="mock_rapidapi_key")
        test_img = Image.new("RGB", (50, 50))
        with pytest.raises(CopyseekerTimeoutError):
            engine.search(test_img)
