import json
import shutil
from pathlib import Path
from datetime import datetime

# CHANGE THIS to your actual Google Drive for desktop folder
DRIVE_FOLDER = Path(r"G:\My Drive\SocialPilot_AI")

POSTS_FOLDER = DRIVE_FOLDER / "posts"
IMAGES_FOLDER = DRIVE_FOLDER / "images"


def save_post_to_drive(post_data, image_path=None):
    try:
        POSTS_FOLDER.mkdir(parents=True, exist_ok=True)
        IMAGES_FOLDER.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

        image_name = None

        if image_path:
            source = Path(image_path)

            if source.exists() and source.is_file():
                image_name = f"post_{timestamp}{source.suffix}"
                destination = IMAGES_FOLDER / image_name
                shutil.copy2(source, destination)
            else:
                print("Drive storage: image file not found:", source)

        post_record = {
            "created_at": datetime.now().isoformat(),
            "product": post_data.get("product", ""),
            "topic": post_data.get("topic", ""),
            "goal": post_data.get("goal", ""),
            "platform": post_data.get("platform", "Instagram"),
            "caption": post_data.get("caption", ""),
            "hashtags": post_data.get("hashtags", []),
            "image_prompt": post_data.get("image_prompt", ""),
            "image_format": post_data.get("image_format", ""),
            "status": post_data.get("status", "GENERATED"),
            "scheduled_datetime": post_data.get(
                "scheduled_datetime"
            ),
            "published_at": post_data.get("published_at"),
            "image": image_name
        }

        json_path = POSTS_FOLDER / f"post_{timestamp}.json"

        with open(json_path, "w", encoding="utf-8") as file:
            json.dump(
                post_record,
                file,
                indent=4,
                ensure_ascii=False
            )

        print("Post saved to Drive folder:", json_path)

        return {
            "status": "SUCCESS",
            "message": "Post saved to Google Drive sync folder.",
            "file": str(json_path),
            "image": image_name
        }

    except Exception as error:
        print("Google Drive storage error:", str(error))

        return {
            "status": "ERROR",
            "message": str(error)
        }