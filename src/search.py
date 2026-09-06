"""
F.I.B.E.R. Search Module
Reverse Visual Search using RapidAPI's Copyseeker API.

STRICT CONSTRAINT: Zero Google APIs (No Google Vision, Lens, SerpAPI).
"""

import io
import os
import time
from typing import Any
from urllib.parse import urlparse

import requests
from PIL import Image


class CopyseekerAPIError(Exception):
    """Base exception for Copyseeker API errors."""

class CopyseekerTimeoutError(CopyseekerAPIError):
    """Raised when Copyseeker API request times out."""

class CopyseekerRateLimitError(CopyseekerAPIError):
    """Raised when RapidAPI rate limit is exceeded (HTTP 429)."""

class NoMatchesFoundError(CopyseekerAPIError):
    """Raised when reverse visual search yields no matching URLs."""

SOCIAL_DOMAINS = [
    "twitter.com",
    "x.com",
    "instagram.com",
    "linkedin.com",
    "reddit.com",
    "facebook.com",
    "tiktok.com"
]

class CopyseekerSearchEngine:
    API_HOST = "copyseeker.p.rapidapi.com"
    API_URL_FILE = "https://copyseeker.p.rapidapi.com/by_image"
    API_URL_LINK = "https://copyseeker.p.rapidapi.com/by_url"

    def __init__(self, api_key: str | None = None, timeout: int = 15):
        self.api_key = api_key or os.getenv("RAPIDAPI_KEY")
        if not self.api_key:
            raise ValueError("RAPIDAPI_KEY environment variable or api_key parameter is required.")
        self.timeout = timeout

    def search(self, image_input: str | Image.Image) -> dict[str, Any]:
        """
        Perform reverse image search via RapidAPI Copyseeker API.
        
        :param image_input: Image file path, web URL string, or PIL Image object
        :return: Standardized dictionary containing source_url, page_title, matched_image_url, discovered_at
        """
        headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.API_HOST
        }

        try:
            if isinstance(image_input, str) and image_input.startswith(("http://", "https://")):
                # Search by image URL
                response = requests.post(
                    self.API_URL_LINK,
                    headers=headers,
                    json={"url": image_input},
                    timeout=self.timeout
                )
            elif isinstance(image_input, str):
                if not os.path.exists(image_input):
                    raise ValueError(f"Image file does not exist: {image_input}")
                with open(image_input, "rb") as f:
                    files = {"file": (os.path.basename(image_input), f, "image/jpeg")}
                    response = requests.post(
                        self.API_URL_FILE,
                        headers=headers,
                        files=files,
                        timeout=self.timeout
                    )
            elif isinstance(image_input, Image.Image):
                buf = io.BytesIO()
                image_input.convert("RGB").save(buf, format="JPEG")
                buf.seek(0)
                files = {"file": ("face_crop.jpg", buf, "image/jpeg")}
                response = requests.post(
                    self.API_URL_FILE,
                    headers=headers,
                    files=files,
                    timeout=self.timeout
                )
            else:
                raise ValueError("Input must be image file path, image URL string, or PIL Image object.")
        except requests.exceptions.Timeout as e:
            raise CopyseekerTimeoutError(f"Request to Copyseeker API timed out after {self.timeout}s.") from e
        except requests.exceptions.RequestException as e:
            raise CopyseekerAPIError(f"Network error querying Copyseeker API: {e}") from e

        if response.status_code == 429:
            raise CopyseekerRateLimitError("RapidAPI Copyseeker rate limit exceeded (HTTP 429).")
        elif response.status_code != 200:
            raise CopyseekerAPIError(f"Copyseeker API error (HTTP {response.status_code}): {response.text}")

        try:
            data = response.json()
        except Exception as e:
            raise CopyseekerAPIError(f"Failed to parse API response JSON: {e}") from e

        return self._process_search_results(data)

    def _process_search_results(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """
        Parse raw Copyseeker API results, prioritize social domains, and fallback to highest-ranking match.
        """
        matches: list[dict[str, Any]] = []

        # Extract items from common Copyseeker response formats
        raw_matches = (
            raw_data.get("visual_matches") or
            raw_data.get("pages_with_matching_images") or
            raw_data.get("results") or
            raw_data.get("similar_images") or
            []
        )

        for item in raw_matches:
            if isinstance(item, dict):
                url = item.get("url") or item.get("page_url") or item.get("link") or ""
                title = item.get("title") or item.get("page_title") or item.get("source") or "Visual Match"
                matched_img = item.get("matched_image_url") or item.get("image_url") or item.get("thumbnail") or url

                if url:
                    matches.append({
                        "source_url": url,
                        "page_title": title,
                        "matched_image_url": matched_img
                    })

        if not matches:
            raise NoMatchesFoundError("No matching visual results discovered for the provided image.")

        # Check for social domain match
        selected_match = None
        for m in matches:
            domain = urlparse(m["source_url"]).netloc.lower()
            if any(soc in domain for soc in SOCIAL_DOMAINS):
                selected_match = m
                break

        # Fallback to highest-ranking web match if no social domain found
        if not selected_match:
            selected_match = matches[0]

        return {
            "source_url": selected_match["source_url"],
            "page_title": selected_match["page_title"],
            "matched_image_url": selected_match["matched_image_url"],
            "discovered_at": int(time.time())
        }

def perform_reverse_search(
    image_input: str | Image.Image,
    api_key: str | None = None
) -> dict[str, Any]:
    """Helper function to perform reverse visual search."""
    engine = CopyseekerSearchEngine(api_key=api_key)
    return engine.search(image_input)
