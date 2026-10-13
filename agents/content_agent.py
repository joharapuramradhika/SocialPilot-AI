
import re
import random

from services.image_captioner import generate_image_caption


def create_hashtags(description):
    """Create hashtags from the actual image description."""

    words = re.findall(r"[a-zA-Z]+", description.lower())

    stop_words = {
        "the", "and", "with", "for", "from", "this",
        "that", "are", "is", "has", "have", "image",
        "there", "which", "their", "into", "showing",
        "shows", "some", "what", "being", "about"
    }

    hashtags = []

    for word in words:
        if len(word) > 3 and word not in stop_words:
            tag = "#" + word.capitalize()

            if tag not in hashtags:
                hashtags.append(tag)

        if len(hashtags) == 5:
            break

    return hashtags


def generate_content(
    image_path,
    product="",
    topic="",
    brand=None,
    prompt=""
):
    brand = brand or {}

    try:
        # Get a description of the actual generated image
        result = generate_image_caption(image_path)

        if result.get("status") != "SUCCESS":
            return {
                "status": "ERROR",
                "caption": "",
                "hashtags": [],
                "message": "Could not describe the generated image."
            }

        description = result.get("description", "").strip()

        if not description:
            return {
                "status": "ERROR",
                "caption": "",
                "hashtags": [],
                "message": "Image description is empty."
            }

        # Use the image description, NOT the original prompt,
        # product or topic, to create the caption.
        caption = description.strip()

        # Clean up the description
        caption = caption[0].upper() + caption[1:]

        if caption[-1] not in ".!?":
            caption += "."

        # Add a varied, short social-media introduction
        introductions = [
            "A little inspiration for your day:",
            "Here's something worth a closer look:",
            "A moment to appreciate:",
            "Take a look at this:",
            "Bringing this idea to life:"
        ]

        caption = random.choice(introductions) + "\n\n" + caption

        brand_name = brand.get("name", "").strip()

        if brand_name:
            caption = f"{brand_name}\n\n{caption}"

        hashtags = create_hashtags(description)

        return {
            "status": "SUCCESS",
            "description": description,
            "caption": caption,
            "hashtags": hashtags,
            "message": "Caption generated from image description."
        }

    except Exception as e:
        print("Caption generation error:", str(e))

        return {
            "status": "ERROR",
            "caption": "",
            "hashtags": [],
            "message": "Caption generation failed."
        }