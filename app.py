import os
import json
import re
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, render_template, jsonify, request

# =========================================================
# 1. CONFIGURATION
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static")
)

PRODUCTS_FILE = BASE_DIR / "data" / "products.json"
BRAND_FILE = BASE_DIR / "data" / "brand.json"

GENERATED_DIR = BASE_DIR / "static" / "generated"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

PUBLIC_BASE_URL = os.getenv(
    "PUBLIC_BASE_URL", ""
).strip().rstrip("/")

PUBLISH_MODE = os.getenv(
    "PUBLISH_MODE", "DEMO"
).strip().upper()

# =========================================================
# 2. IMPORT PROJECT MODULES
# =========================================================

from agents.planner import create_plan
from agents.validator_agent import validate_content
from agents.safety_agent import check_content_safety

from services.ai_image_generator import generate_ai_image

# Gemini caption generation
from services.image_captioner import generate_image_caption

from services.scheduler import (
    get_next_schedule,
    schedule_post,
    start_scheduler
)

from services.publisher import publish_post
from services.drive_storage import save_post_to_drive

# =========================================================
# 3. APPLICATION STATE
# =========================================================

current_post = None
post_status = "READY"

# =========================================================
# 4. JSON HELPERS
# =========================================================

def load_json_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as error:
        print(f"Could not load {file_path}: {error}")
        return {}


def load_products():
    data = load_json_file(PRODUCTS_FILE)

    if isinstance(data, dict):
        return data.get("products", [])

    return data if isinstance(data, list) else []


def load_brand():
    data = load_json_file(BRAND_FILE)
    return data if isinstance(data, dict) else {}


def normalize_hashtags(value):
    if isinstance(value, str):
        values = re.findall(r"#?[\w]+", value, flags=re.UNICODE)
    elif isinstance(value, list):
        values = value
    else:
        values = []

    result = []
    seen = set()

    for item in values:
        tag = str(item).strip()

        if not tag:
            continue

        tag = tag.lstrip("#").strip()

        if not tag:
            continue

        tag = "#" + tag
        key = tag.casefold()

        if key not in seen:
            seen.add(key)
            result.append(tag)

    return result


def sync_post_content(data):
    global current_post

    if not current_post:
        return

    if "caption" in data:
        current_post["caption"] = str(
            data.get("caption") or ""
        ).strip()

    if "hashtags" in data:
        current_post["hashtags"] = normalize_hashtags(
            data.get("hashtags")
        )


# =========================================================
# 5. IMAGE PATH HELPERS
# =========================================================

def normalize_image_path(image_path):
    if not image_path:
        return None

    image_path = str(image_path).strip()

    if image_path.startswith(("https://", "http://")):
        return image_path

    image_path = image_path.replace("\\", "/")

    if image_path.startswith("/static/"):
        return image_path

    if image_path.startswith("static/"):
        return "/" + image_path

    return "/static/" + image_path.lstrip("/")


def get_image_file_path(image_path):
    if not image_path:
        return None

    image_path = str(image_path).strip()

    if image_path.startswith(("https://", "http://")):
        return None

    image_path = image_path.replace("\\", "/").lstrip("/")

    if image_path.startswith("static/"):
        relative_path = image_path[len("static/"):]
    else:
        relative_path = image_path

    static_dir = (BASE_DIR / "static").resolve()
    image_file = (static_dir / relative_path).resolve()

    try:
        image_file.relative_to(static_dir)
    except ValueError:
        return None

    return image_file


def get_current_image_path():
    if not current_post:
        return None

    return (
        current_post.get("image_path")
        or current_post.get("image")
    )


def get_public_image_url(image_path):
    if not image_path:
        return None

    image_path = str(image_path).strip()

    if image_path.startswith("https://"):
        return image_path

    if image_path.startswith("http://"):
        return None

    if not PUBLIC_BASE_URL.startswith("https://"):
        print("PUBLIC_BASE_URL must be an HTTPS URL.")
        return None

    normalized_path = normalize_image_path(image_path)

    if not normalized_path:
        return None

    return PUBLIC_BASE_URL + normalized_path


# =========================================================
# 6. GOOGLE DRIVE STORAGE
# =========================================================

def save_current_post_to_drive(status=None):
    """
    Save the current post and its actual image file
    to the Google Drive for desktop sync folder.
    """

    global current_post, post_status

    if not current_post:
        print("Drive save skipped: No current post.")
        return {
            "status": "ERROR",
            "message": "No current post available."
        }

    # Create a snapshot so status changes are saved.
    post_data = dict(current_post)

    post_data["status"] = status or post_status

    # Get the actual Windows image file path.
    image_path = get_current_image_path()
    image_file = get_image_file_path(image_path)

    if image_file and image_file.is_file():
        actual_image_path = str(image_file)
    else:
        actual_image_path = None

        print(
            "Drive save: Image file not found:",
            image_file
        )

    # Save the JSON post and copy the image to Drive.
    result = save_post_to_drive(
        post_data,
        image_path=actual_image_path
    )

    print("Drive save result:", result)

    return result


# =========================================================
# 7. VALIDATION AND SAFETY
# =========================================================

def validate_current_post():
    if not current_post:
        return {
            "status": "FAIL",
            "problems": ["No post has been generated."]
        }

    products = load_products()
    brand = load_brand()

    content = dict(current_post)
    content.setdefault("caption", "")
    content.setdefault("product", "")
    content.setdefault("topic", "")

    try:
        return validate_content(content, products, brand)
    except Exception as error:
        print("Content validation error:", error)

        return {
            "status": "FAIL",
            "problems": [
                "Content validation could not be completed."
            ]
        }


def run_image_safety_check():
    if not current_post:
        return {
            "status": "REVIEW_REQUIRED",
            "reasons": ["No current post."]
        }

    image_file = get_image_file_path(
        get_current_image_path()
    )

    if not image_file or not image_file.is_file():
        return {
            "status": "REVIEW_REQUIRED",
            "reasons": ["Generated image is missing."]
        }

    try:
        return check_content_safety(
            str(image_file),
            current_post.get("caption", "")
        )
    except Exception as error:
        print("Image safety error:", error)

        return {
            "status": "REVIEW_REQUIRED",
            "reasons": [
                "The safety check could not be completed."
            ]
        }


def get_creative_preview():
    if not current_post:
        return {}

    return {
        "image": normalize_image_path(
            get_current_image_path()
        ),
        "prompt": current_post.get("image_prompt", ""),
        "format": current_post.get("image_format", "4:5"),
        "width": current_post.get("image_width", 512),
        "height": current_post.get("image_height", 640)
    }


def create_initial_post():
    products = load_products()

    if not products:
        raise ValueError(
            "No approved products found in data/products.json"
        )

    plan = create_plan(products)

    return {
        "product": plan.get("product", ""),
        "topic": plan.get("topic", ""),
        "goal": plan.get("goal", ""),
        "platform": plan.get("platform", "Instagram"),

        "caption": "",
        "hashtags": [],

        "image": None,
        "image_path": None,
        "image_url": None,

        "image_description": "",
        "image_caption": "",
        "image_hashtags": [],

        "image_prompt": "",
        "image_format": "4:5",
        "image_width": 512,
        "image_height": 640
    }
    
    # =========================================================
# 8. HOME PAGE
# =========================================================

@app.route("/")
def home():
    global current_post, post_status

    try:
        if current_post is None:
            current_post = create_initial_post()
            post_status = "READY"

        return render_template(
            "dashboard.html",
            content=current_post,
            validation=validate_current_post(),
            creative=get_creative_preview(),
            schedule=get_next_schedule(),
            post_status=post_status,
            publish_mode=PUBLISH_MODE
        )

    except Exception as error:
        print("Dashboard error:", error)

        return (
            "Unable to load dashboard. "
            "Check the Flask terminal for details.",
            500
        )


# =========================================================
# 9. REGENERATE POST PLAN
# =========================================================

@app.route("/regenerate", methods=["POST"])
def regenerate():
    global current_post, post_status

    try:
        current_post = create_initial_post()
        post_status = "READY"

        # Save the new post plan to Google Drive.
        save_current_post_to_drive("GENERATED")

        return jsonify({
            "status": "SUCCESS",
            "message": "New content plan created.",
            "content": current_post,
            "validation": validate_current_post(),
            "post_status": post_status
        })

    except Exception as error:
        print("Regeneration error:", error)

        return jsonify({
            "status": "ERROR",
            "message": str(error)
        }), 500


# =========================================================
# 10. GENERATE IMAGE AND CAPTION
# =========================================================

@app.route("/generate-creative", methods=["POST"])
def generate_creative():
    global current_post, post_status

    try:
        if current_post is None:
            current_post = create_initial_post()

        data = request.get_json(silent=True) or {}

        prompt = (
            data.get("prompt")
            or current_post.get("image_prompt")
            or (
                "Create a professional, attractive social media "
                "creative about "
                + current_post.get("topic", "the approved topic")
            )
        )

        image_format = (
            data.get("image_format")
            or data.get("format")
            or "4:5"
        )

        dimensions = {
            "1:1": (512, 512),
            "4:5": (512, 640),
            "9:16": (512, 896),
            "16:9": (896, 512)
        }

        if image_format not in dimensions:
            return jsonify({
                "status": "ERROR",
                "message": "Please select a valid image format."
            }), 400

        width, height = dimensions[image_format]

        # Generate the image.
        result = generate_ai_image(
            prompt=prompt,
            image_format=image_format
        )

        if not isinstance(result, dict):
            return jsonify({
                "status": "ERROR",
                "message": "Image generator returned an invalid result."
            }), 500

        if result.get("status") != "SUCCESS":
            return jsonify({
                "status": "ERROR",
                "message": result.get(
                    "message", "Image generation failed."
                )
            }), 500

        generated_image = (
            result.get("image_path")
            or result.get("image")
        )

        if not generated_image:
            return jsonify({
                "status": "ERROR",
                "message": "Image path was not returned."
            }), 500

        image_path = normalize_image_path(generated_image)
        image_file = get_image_file_path(image_path)

        if not image_file or not image_file.is_file():
            return jsonify({
                "status": "ERROR",
                "message": "Generated image file could not be found."
            }), 500

        current_post.update({
            "image": image_path,
            "image_path": image_path,
            "image_url": None,
            "image_prompt": prompt,
            "image_format": image_format,
            "image_width": width,
            "image_height": height
        })

        # -------------------------------------------------
        # Generate caption and hashtags using Gemini
        # -------------------------------------------------

        caption_result = generate_image_caption(
            str(image_file),
            prompt
        )

        if not isinstance(caption_result, dict):
            return jsonify({
                "status": "ERROR",
                "message": "Caption generator returned an invalid result."
            }), 500

        if caption_result.get("status") != "SUCCESS":
            current_post["caption"] = ""
            current_post["hashtags"] = []
            post_status = "READY"

            # Save the generated image even if caption generation fails.
            save_current_post_to_drive("READY")

            return jsonify({
                "status": "ERROR",
                "message": caption_result.get(
                    "message",
                    "Image generated, but caption generation failed."
                ),
                "image": image_path,
                "post_status": post_status
            }), 500

        caption = str(
            caption_result.get("caption", "")
        ).strip()

        hashtags = normalize_hashtags(
            caption_result.get("hashtags", [])
        )

        if not caption:
            return jsonify({
                "status": "ERROR",
                "message": "The generated caption is empty.",
                "image": image_path
            }), 500

        current_post["caption"] = caption
        current_post["hashtags"] = hashtags
        current_post["image_caption"] = caption
        current_post["image_hashtags"] = hashtags

        current_post["image_description"] = (
            caption_result.get("description", "")
        )

        # Validate the generated content.
        validation = validate_current_post()

        post_status = (
            "READY"
            if validation.get("status") == "PASS"
            else "REJECTED"
        )

        # Save image and post to Google Drive.
        save_current_post_to_drive(post_status)

        return jsonify({
            "status": "SUCCESS",
            "message": "Image and caption generated successfully.",
            "image": image_path,
            "image_url": image_path,
            "image_path": image_path,
            "caption": caption,
            "hashtags": hashtags,
            "caption_status": "SUCCESS",
            "validation": validation,
            "format": image_format,
            "image_format": image_format,
            "width": width,
            "height": height,
            "post_status": post_status
        })

    except Exception as error:
        print("Creative generation error:", error)

        return jsonify({
            "status": "ERROR",
            "message": str(error)
        }), 500
        
        # =========================================================
# 11. APPROVE POST
# =========================================================

@app.route("/approve", methods=["POST"])
def approve():
    global post_status

    if not current_post:
        return jsonify({
            "status": "ERROR",
            "message": "No post is available."
        }), 400

    data = request.get_json(silent=True) or {}
    sync_post_content(data)

    if not current_post.get("caption", "").strip():
        return jsonify({
            "status": "ERROR",
            "message": "Please enter a caption before approval."
        }), 400

    validation = validate_current_post()

    if validation.get("status") != "PASS":
        return jsonify({
            "status": "ERROR",
            "message": "Content validation failed.",
            "validation": validation
        }), 400

    image_file = get_image_file_path(
        get_current_image_path()
    )

    if not image_file or not image_file.is_file():
        return jsonify({
            "status": "ERROR",
            "message": "Generate an image before approval."
        }), 400

    safety = run_image_safety_check()

    if safety.get("status") != "APPROVED":
        return jsonify({
            "status": "ERROR",
            "message": "Safety check did not approve this post.",
            "safety": safety
        }), 400

    post_status = "APPROVED"

    # Save approved post to Drive.
    save_current_post_to_drive(post_status)

    return jsonify({
        "status": "SUCCESS",
        "message": "Post approved successfully.",
        "post_status": post_status
    })


# =========================================================
# 12. REJECT POST
# =========================================================

@app.route("/reject", methods=["POST"])
def reject():
    global post_status

    post_status = "REJECTED"

    # Save rejection status to Drive.
    save_current_post_to_drive(post_status)

    return jsonify({
        "status": "SUCCESS",
        "message": "Post rejected.",
        "post_status": post_status
    })


# =========================================================
# 13. SCHEDULE POST
# =========================================================

@app.route("/schedule", methods=["POST"])
def schedule():
    global post_status

    if not current_post:
        return jsonify({
            "status": "ERROR",
            "message": "No post is available."
        }), 400

    data = request.get_json(silent=True) or {}

    sync_post_content(data)

    if post_status != "APPROVED":
        return jsonify({
            "status": "ERROR",
            "message": "Approve the post before scheduling."
        }), 400

    validation = validate_current_post()

    if validation.get("status") != "PASS":
        return jsonify({
            "status": "ERROR",
            "message": "Content validation failed.",
            "validation": validation
        }), 400

    safety = run_image_safety_check()

    if safety.get("status") != "APPROVED":
        return jsonify({
            "status": "ERROR",
            "message": "Safety check failed.",
            "safety": safety
        }), 400

    scheduled_time = (
        data.get("scheduled_datetime")
        or data.get("datetime")
        or data.get("schedule_time")
    )

    if not scheduled_time:
        return jsonify({
            "status": "ERROR",
            "message": "Please provide a schedule date and time."
        }), 400

    try:
        parsed_time = datetime.fromisoformat(scheduled_time)

        if parsed_time <= datetime.now():
            return jsonify({
                "status": "ERROR",
                "message": "Schedule time must be in the future."
            }), 400

    except (ValueError, TypeError):
        return jsonify({
            "status": "ERROR",
            "message": "Invalid schedule date/time."
        }), 400

    result = schedule_post(current_post, parsed_time)

    if result.get("status") != "SUCCESS":
        return jsonify(result), 400

    post_status = "SCHEDULED"

    current_post["scheduled_datetime"] = parsed_time.isoformat()

    # Save scheduled post and date to Drive.
    save_current_post_to_drive(post_status)

    return jsonify({
        "status": "SUCCESS",
        "message": "Post scheduled successfully.",
        "post": result.get("post"),
        "post_status": post_status
    })
    
    # =========================================================
# 14. PUBLISH POST
# =========================================================

@app.route("/publish", methods=["POST"])
def publish():
    global post_status

    if not current_post:
        return jsonify({
            "status": "ERROR",
            "message": "No post is available."
        }), 400

    data = request.get_json(silent=True) or {}

    sync_post_content(data)

    if post_status not in ("APPROVED", "SCHEDULED"):
        return jsonify({
            "status": "ERROR",
            "message": "Approve the post before publishing."
        }), 400

    if not current_post.get("caption", "").strip():
        return jsonify({
            "status": "ERROR",
            "message": "Please enter a caption before publishing."
        }), 400

    validation = validate_current_post()

    if validation.get("status") != "PASS":
        return jsonify({
            "status": "ERROR",
            "message": "Content validation failed.",
            "validation": validation
        }), 400

    safety = run_image_safety_check()

    if safety.get("status") != "APPROVED":
        return jsonify({
            "status": "ERROR",
            "message": "Safety check failed.",
            "safety": safety
        }), 400

    image_path = get_current_image_path()
    image_file = get_image_file_path(image_path)

    if not image_file or not image_file.is_file():
        return jsonify({
            "status": "ERROR",
            "message": "Generated image is missing."
        }), 400

    publish_content = dict(current_post)

    publish_content["caption"] = current_post.get("caption", "")
    publish_content["hashtags"] = normalize_hashtags(
        current_post.get("hashtags", [])
    )

    if PUBLISH_MODE == "LIVE":
        image_url = get_public_image_url(image_path)

        if not image_url:
            return jsonify({
                "status": "ERROR",
                "message": (
                    "Public HTTPS image URL is unavailable. "
                    "Check PUBLIC_BASE_URL."
                )
            }), 400

        publish_content["image_url"] = image_url

    else:
        publish_content["image_url"] = normalize_image_path(
            image_path
        )

    result = publish_post(publish_content)

    if (
        isinstance(result, dict)
        and result.get("status") == "SUCCESS"
    ):
        post_status = "PUBLISHED"

        current_post["published_at"] = datetime.now().isoformat()

        # Save published status and timestamp to Drive.
        save_current_post_to_drive(post_status)

        return jsonify({
            "status": "SUCCESS",
            "message": result.get(
                "message", "Post published successfully."
            ),
            "media_id": result.get("media_id"),
            "post_status": post_status
        })

    return jsonify({
        "status": "ERROR",
        "message": (
            result.get("message", "Publishing failed.")
            if isinstance(result, dict)
            else str(result)
        ),
        "details": (
            result.get("details", {})
            if isinstance(result, dict)
            else {}
        )
    }), 500


# =========================================================
# 15. INSTAGRAM CALLBACK
# =========================================================

@app.route("/instagram/callback")
def instagram_callback():
    code = request.args.get("code")
    error = request.args.get("error")

    if error:
        return jsonify({
            "status": "ERROR",
            "message": error
        })

    if code:
        return jsonify({
            "status": "SUCCESS",
            "message": "Instagram authorization callback received."
        })

    return jsonify({
        "status": "ERROR",
        "message": "No authorization code received."
    })


# =========================================================
# 16. RUN APPLICATION
# =========================================================

if __name__ == "__main__":
    start_scheduler()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        use_reloader=False
    )