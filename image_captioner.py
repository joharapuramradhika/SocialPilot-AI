import os
import json
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

MODEL_NAME = "gemini-3.5-flash-lite"


def generate_image_caption(image_path, user_prompt=""):

    try:
        if not user_prompt or not user_prompt.strip():
            return {
                "status": "ERROR",
                "description": "",
                "caption": "",
                "hashtags": [],
                "message": "Please enter a prompt."
            }

        prompt = f"""
You are a professional social media copywriter.

User's prompt:
{user_prompt}

Write ONE original, engaging social media caption
that follows the user's prompt exactly.

Requirements:
- Follow the requested topic, tone, and purpose.
- Generate a natural, professional caption.
- Do not provide multiple caption options.
- Do not use a fixed template or keyword categories.
- Do not invent facts or claims.
- Generate 5 relevant hashtags.

Return ONLY valid JSON:

{{
  "caption": "Your caption",
  "hashtags": ["#Tag1", "#Tag2", "#Tag3", "#Tag4", "#Tag5"]
}}
"""

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )

        response_text = response.text.strip()

        # Remove markdown code fences if present
        if response_text.startswith("```"):
            response_text = response_text.replace(
                "```json", ""
            ).replace("```", "").strip()

        result = json.loads(response_text)

        caption = result.get("caption", "").strip()
        hashtags = result.get("hashtags", [])

        if not caption:
            raise ValueError("Gemini returned an empty caption.")

        print("Gemini caption generated:")
        print(caption)

        return {
            "status": "SUCCESS",
            "description": caption,
            "caption": caption,
            "hashtags": hashtags,
            "message": "Caption generated successfully."
        }

    except Exception as e:

        print("GEMINI CAPTION ERROR:", repr(e))

        return {
            "status": "ERROR",
            "description": "",
            "caption": "",
            "hashtags": [],
            "message": str(e)
        }