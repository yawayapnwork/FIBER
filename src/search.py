"""
F.I.B.E.R. Search Module
Reverse Visual Search using RapidAPI's Copyseeker API.
STRICT CONSTRAINT: Zero Google APIs (No Google Vision, Lens, SerpAPI).
"""

import os
from typing import Dict, Any, Optional, Union
import requests
from PIL import Image
import io

class CopyseekerSearchEngine:
    API_HOST = "copyseeker.p.rapidapi.com"
    API_URL = "https://copyseeker.p.rapidapi.com/by_image"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("RAPIDAPI_KEY")
        if not self.api_key:
            raise ValueError("RAPIDAPI_KEY environment variable or api_key parameter is required.")

    def search_by_image(self, image_input: Union[str, Image.Image]) -> Dict[str, Any]:
        """
        Perform reverse image search via Copyseeker RapidAPI.
        
        :param image_input: Path to image file or PIL Image object
        :return: JSON response payload from Copyseeker API
        """
        headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.API_HOST
        }

        if isinstance(image_input, str):
            with open(image_input, "rb") as f:
                files = {"file": (os.path.basename(image_input), f, "image/jpeg")}
                response = requests.post(self.API_URL, headers=headers, files=files)
        elif isinstance(image_input, Image.Image):
            buf = io.BytesIO()
            image_input.save(buf, format="JPEG")
            buf.seek(0)
            files = {"file": ("face_crop.jpg", buf, "image/jpeg")}
            response = requests.post(self.API_URL, headers=headers, files=files)
        else:
            raise ValueError("Input must be image path string or PIL Image.")

        if response.status_code != 200:
            return {
                "error": True,
                "status_code": response.status_code,
                "message": response.text
            }

        return response.json()
