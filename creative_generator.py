
from pathlib import Path

from services.ai_image_generator import generate_ai_image


# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "static" / "generated"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def generate_creative(content):

    # Get content information
    product = content.get("product", "AI Solutions")
    topic = content.get(
        "topic",
        "AI-powered business innovation"
    )
    call_to_action = content.get(
        "call_to_action",
        "Learn more"
    )

    # Use custom image prompt if provided
    prompt = content.get("image_prompt")

    if not prompt:
        prompt = f"""
        Create a professional Instagram promotional creative.

        Product or brand: {product}

        Topic: {topic}

        Call to action: {call_to_action}

        Design requirements:
        - Visually attractive and professional
        - Suitable for business social media
        - Use a clean, modern layout
        - Use readable, minimal text
        - Make the image relevant to the product
        - Avoid watermarks and blurry elements
        """

    # Get image format
    image_format = content.get(
        "image_format",
        "4:5"
    )

    # Generate image using Gemini
    result = generate_ai_image(
        prompt,
        image_format
    )

    if result.get("status") != "SUCCESS":
        return {
            "status": "ERROR",
            "message": result.get(
                "message",
                "Image generation failed."
            )
        }

    # Use the generated image path
    image_filename = str(
        OUTPUT_DIR / "latest_post.png"
    )

    # Create HTML preview
    html_filename = str(
        OUTPUT_DIR / "latest_post.html"
    )

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Social Media Creative</title>

        <style>
            body {
                margin: 0;
                background: #f5f5f5;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
            }

            img {
                width: 100%;
                max-width: 600px;
                height: auto;
                border-radius: 20px;
                box-shadow: 0 10px 30px
                    rgba(0,0,0,0.15);
            }
        </style>
    </head>

    <body>
        <img
            src="/static/generated/latest_post.png"
            alt="Gemini Generated Social Media Creative"
        >
    </body>
    </html>
    """

    with open(
        html_filename,
        "w",
        encoding="utf-8"
    ) as file:
        file.write(html)

    return {
        "status": "SUCCESS",
        "image": image_filename,
        "html": html_filename
    }