import os
import json
import time
import threading

from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv


# =========================================================
# CONFIGURATION
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
SCHEDULE_FILE = DATA_DIR / "scheduled_posts.json"

PUBLIC_BASE_URL = os.getenv(
    "PUBLIC_BASE_URL", ""
).strip().rstrip("/")

CHECK_INTERVAL = 10

# Prevent simultaneous scheduler executions
scheduler_lock = threading.Lock()

# Prevent simultaneous JSON file access
file_lock = threading.Lock()

# Scheduler thread management
scheduler_thread = None
scheduler_running = False


# =========================================================
# 1. LOAD SCHEDULED POSTS
# =========================================================

def load_scheduled_posts():
    """Load scheduled posts from JSON."""

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with file_lock:

        if not SCHEDULE_FILE.exists():

            with open(
                SCHEDULE_FILE,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump([], file, indent=4)

        try:

            with open(
                SCHEDULE_FILE,
                "r",
                encoding="utf-8"
            ) as file:

                posts = json.load(file)

            if not isinstance(posts, list):

                print("ERROR: JSON must contain a list.")

                return []

            return posts

        except (json.JSONDecodeError, OSError) as error:

            print(
                "Error loading scheduled posts:",
                error
            )

            return []


# =========================================================
# 2. SAVE SCHEDULED POSTS
# =========================================================

def save_scheduled_posts(posts):
    """Safely save scheduled posts to JSON."""

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    temp_file = SCHEDULE_FILE.with_suffix(".tmp")

    with file_lock:

        try:

            with open(
                temp_file,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    posts,
                    file,
                    indent=4,
                    ensure_ascii=False
                )

            os.replace(
                temp_file,
                SCHEDULE_FILE
            )

        except OSError as error:

            print(
                "Error saving scheduled posts:",
                error
            )

            raise


# =========================================================
# 3. GET NEXT SCHEDULE
# =========================================================

def get_next_schedule():
    """Return the next upcoming scheduled date and time."""

    posts = load_scheduled_posts()

    now = datetime.now()

    scheduled_times = []

    for post in posts:

        if post.get("status") != "SCHEDULED":
            continue

        try:

            scheduled_time = datetime.fromisoformat(
                post["scheduled_datetime"]
            )

            if scheduled_time > now:

                scheduled_times.append(
                    scheduled_time
                )

        except (ValueError, TypeError, KeyError):

            continue

    if not scheduled_times:
        return None

    next_time = min(scheduled_times)

    return next_time.strftime(
        "%Y-%m-%d %H:%M"
    )


# =========================================================
# 4. SCHEDULE A NEW POST
# =========================================================

def schedule_post(content, scheduled_time):
    """
    Save a new post in scheduled_posts.json.

    Stores:
        - Caption
        - Hashtags
        - Image path
        - Product and topic
        - Scheduled date and time
        - Publishing status

    Compatible with:
        schedule_post(current_post, scheduled_datetime)
    """

    if isinstance(scheduled_time, datetime):

        scheduled_datetime = scheduled_time.isoformat(
            timespec="minutes"
        )

    else:

        scheduled_datetime = str(
            scheduled_time
        ).strip()

        try:

            parsed_time = datetime.fromisoformat(
                scheduled_datetime
            )

            scheduled_datetime = parsed_time.isoformat(
                timespec="minutes"
            )

        except ValueError:

            return {
                "status": "ERROR",
                "message": "Invalid scheduled date/time."
            }

    # Get the caption entered or generated in the dashboard.
    caption = str(
        content.get("caption") or ""
    ).strip()

    # Preserve hashtags as a separate list.
    hashtags = content.get("hashtags", [])

    if isinstance(hashtags, str):

        hashtags = hashtags.replace(
            ",", " "
        ).split()

    if not isinstance(hashtags, list):
        hashtags = []

    cleaned_hashtags = []

    for hashtag in hashtags:

        hashtag = str(hashtag).strip()

        if not hashtag:
            continue

        if not hashtag.startswith("#"):
            hashtag = "#" + hashtag

        if hashtag.lower() not in [
            existing.lower()
            for existing in cleaned_hashtags
        ]:

            cleaned_hashtags.append(hashtag)

    # Get the image path.
    image_path = (
        content.get("image_url")
        or content.get("image")
        or content.get("image_path")
        or "static/generated/latest_post.png"
    )

    posts = load_scheduled_posts()

    try:

        new_id = max(
            (
                int(post.get("id", 0))
                for post in posts
            ),
            default=0
        ) + 1

    except (ValueError, TypeError):

        new_id = len(posts) + 1

    # Save the full content, including hashtags.
    new_post = {
        "id": new_id,

        "product": content.get(
            "product", ""
        ),

        "topic": content.get(
            "topic", ""
        ),

        "caption": caption,

        "hashtags": cleaned_hashtags,

        "image": image_path,

        "scheduled_datetime": scheduled_datetime,

        "status": "SCHEDULED",

        "created_at": datetime.now().isoformat()
    }

    posts.append(new_post)

    save_scheduled_posts(posts)

    print(
        f"Post {new_id} scheduled for "
        f"{scheduled_datetime}"
    )

    print("Caption saved:", caption)

    print(
        "Hashtags saved:",
        cleaned_hashtags
    )

    return {
        "status": "SUCCESS",
        "post": new_post
    }


# =========================================================
# 5. CREATE PUBLIC IMAGE URL
# =========================================================

def get_public_image_url(image_path):
    """Convert local image path to public HTTPS URL."""

    if not image_path:
        return None

    image_path = str(
        image_path
    ).strip()

    if image_path.startswith("https://"):
        return image_path

    if image_path.startswith("http://"):
        return None

    if not PUBLIC_BASE_URL:

        print(
            "ERROR: PUBLIC_BASE_URL missing in .env"
        )

        return None

    image_path = image_path.replace(
        "\\", "/"
    ).lstrip("/")

    return (
        f"{PUBLIC_BASE_URL}/{image_path}"
    )


# =========================================================
# 6. PROCESS SCHEDULED POSTS
# =========================================================

def process_scheduled_posts():
    """
    Publish posts whose scheduled time has arrived.

    Only posts with status SCHEDULED are processed.

    Caption and hashtags are passed separately to
    publisher.py, which combines them for Instagram.
    """

    # Prevent two scheduler executions at the same time.
    if not scheduler_lock.acquire(blocking=False):

        print(
            "Scheduler is already processing posts."
        )

        return

    try:

        from services.publisher import publish_post

        now = datetime.now()

        posts = load_scheduled_posts()

        for post in posts:

            # Ignore posts that are not scheduled.
            if post.get("status") != "SCHEDULED":
                continue

            try:

                scheduled_time = datetime.fromisoformat(
                    post["scheduled_datetime"]
                )

            except (
                ValueError,
                TypeError,
                KeyError
            ) as error:

                print(
                    f"Invalid date for post "
                    f"{post.get('id')}: {error}"
                )

                continue

            # Wait until the scheduled time.
            if scheduled_time > now:
                continue

            post_id = post.get("id")

            print(
                f"\nPost {post_id} "
                "is due for publishing."
            )

            # Save PROCESSING before calling Instagram.
            post["status"] = "PROCESSING"

            save_scheduled_posts(posts)

            # Generate the public image URL.
            image_url = get_public_image_url(
                post.get("image")
            )

            if not image_url:

                post["status"] = "FAILED"

                post["error"] = (
                    "Public image URL missing. "
                    "Check PUBLIC_BASE_URL in .env."
                )

                save_scheduled_posts(posts)

                print(
                    f"Post {post_id} failed: "
                    "image URL missing."
                )

                continue

            # Prepare the publisher payload.
            # IMPORTANT: Include hashtags separately.
            content = {
                "caption": post.get(
                    "caption", ""
                ),

                "hashtags": post.get(
                    "hashtags", []
                ),

                "image_url": image_url
            }

            try:

                print(
                    f"Publishing post {post_id} "
                    "to Instagram..."
                )

                print(
                    "Scheduled caption:",
                    content["caption"]
                )

                print(
                    "Scheduled hashtags:",
                    content["hashtags"]
                )

                result = publish_post(
                    content
                )

                if (
                    isinstance(result, dict)
                    and result.get("status") == "SUCCESS"
                ):

                    post["status"] = "PUBLISHED"

                    post["published_at"] = (
                        datetime.now().isoformat()
                    )

                    post["media_id"] = result.get(
                        "media_id"
                    )

                    # Save the actual caption sent to Instagram.
                    post["published_caption"] = result.get(
                        "caption",
                        content["caption"]
                    )

                    post.pop("error", None)

                    print(
                        f"Post {post_id} "
                        "published successfully."
                    )

                else:

                    post["status"] = "FAILED"

                    if isinstance(result, dict):

                        post["error"] = (
                            result.get("message")
                            or result.get("error")
                            or str(result)
                        )

                    else:

                        post["error"] = str(
                            result
                        )

                    print(
                        f"Post {post_id} failed: "
                        f"{post['error']}"
                    )

            except Exception as error:

                post["status"] = "FAILED"

                post["error"] = str(error)

                print(
                    f"Publishing error for post "
                    f"{post_id}: {error}"
                )

            finally:

                # Save the final publishing status.
                save_scheduled_posts(posts)

    finally:

        scheduler_lock.release()


# =========================================================
# 7. BACKGROUND SCHEDULER LOOP
# =========================================================

def scheduler_loop():
    """Check for due posts every CHECK_INTERVAL seconds."""

    global scheduler_running

    print(
        "SocialPilot AI scheduler started."
    )

    while scheduler_running:

        try:

            process_scheduled_posts()

        except Exception as error:

            print(
                "Scheduler error:",
                error
            )

        time.sleep(
            CHECK_INTERVAL
        )

    print(
        "SocialPilot AI scheduler stopped."
    )


# =========================================================
# 8. START SCHEDULER
# =========================================================

def start_scheduler():
    """Start only one scheduler thread."""

    global scheduler_thread
    global scheduler_running

    if (
        scheduler_thread is not None
        and scheduler_thread.is_alive()
    ):

        print(
            "Scheduler is already running."
        )

        return

    scheduler_running = True

    scheduler_thread = threading.Thread(
        target=scheduler_loop,
        daemon=True,
        name="SocialPilotScheduler"
    )

    scheduler_thread.start()


# =========================================================
# 9. STOP SCHEDULER
# =========================================================

def stop_scheduler():
    """Stop the background scheduler."""

    global scheduler_running

    scheduler_running = False

    print(
        "Scheduler stop requested."
    )