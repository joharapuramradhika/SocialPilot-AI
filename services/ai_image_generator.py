import os
import base64
from pathlib import Path
from dotenv import load_dotenv
from google import genai

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY is missing from .env")

client = genai.Client(api_key=API_KEY)

MODEL_NAME = "gemini-3.1-flash-image"

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "static" / "generated"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_PATH = OUTPUT_DIR / "latest_post.png"


def generate_ai_image(prompt, image_format="4:5"):
    try:
        aspect_ratio = (
            image_format
            if image_format in [
                "1:1", "4:5", "5:4", "3:2",
                "2:3", "3:4", "4:3", "9:16",
                "16:9", "21:9"
            ]
            else "1:1"
        )

        full_prompt = f"""
        Generate a professional social media advertisement image.

        Subject:
        {prompt}

        Requirements:
        - High-quality, professional marketing visual.
        - Attractive composition and realistic lighting.
        - Suitable for Instagram and Facebook.
        - No unwanted text, logos, or watermarks.
        - Do not add misleading product claims.
        """

        interaction = client.interactions.create(
            model=MODEL_NAME,
            input=full_prompt,
            response_format={
                "type": "image",
                "mime_type": "image/png",
                "aspect_ratio": aspect_ratio,
                "image_size": "1K"
            }
        )

        image_data = interaction.output_image

        if not image_data or not image_data.data:
            return {
                "status": "FAILED",
                "message": "Gemini did not return an image."
            }

        image_bytes = base64.b64decode(image_data.data)

        with open(OUTPUT_PATH, "wb") as f:
            f.write(image_bytes)

        return {
            "status": "SUCCESS",
            "image_path": str(OUTPUT_PATH),
            "image": "/static/generated/latest_post.png",
            "message": "Image generated successfully using Gemini."
        }

    except Exception as e:
        print("Gemini image generation error:", str(e))

        return {
            "status": "FAILED",
            "message": str(e)
        }