import os
import re
import threading
import requests

from dotenv import load_dotenv

load_dotenv()

publish_lock = threading.Lock()

GRAPH_API_VERSION = "v23.0"
GRAPH_API_BASE = f"https://graph.instagram.com/{GRAPH_API_VERSION}"


def build_instagram_caption(content):
    """
    Combine the caption and hashtags into one Instagram caption.

    Instagram Graph API accepts hashtags as part of the caption
    text, not as a separate hashtags parameter.
    """

    caption = str(content.get("caption") or "").strip()

    hashtags = content.get("hashtags", [])

    # Support hashtags as either a list or a string.
    if isinstance(hashtags, str):
        hashtags = hashtags.replace(",", " ").split()

    if not isinstance(hashtags, list):
        hashtags = []

    cleaned_hashtags = []

    for hashtag in hashtags:
        hashtag = str(hashtag).strip()

        if not hashtag:
            continue

        # Add # if the user entered a tag without it.
        if not hashtag.startswith("#"):
            hashtag = "#" + hashtag

        # Avoid duplicate tags in the hashtags list.
        if hashtag.lower() not in [
            tag.lower() for tag in cleaned_hashtags
        ]:
            cleaned_hashtags.append(hashtag)

    # Find hashtags already included in the caption.
    existing_tags = set(
        re.findall(r"(?<!\w)#[\w]+", caption, flags=re.UNICODE)
    )

    existing_tags = {
        tag.lower() for tag in existing_tags
    }

    # Append only hashtags that are not already in the caption.
    hashtags_to_add = [
        tag for tag in cleaned_hashtags
        if tag.lower() not in existing_tags
    ]

    if hashtags_to_add:
        caption = (
            caption + "\n\n" + " ".join(hashtags_to_add)
        ).strip()

    return caption


def publish_demo(content):
    """Simulate publishing without posting to Instagram."""

    caption = build_instagram_caption(content)

    print("\n--- DEMO PUBLISHING ---")
    print("Caption with hashtags:")
    print(caption)

    return {
        "status": "SUCCESS",
        "message": "Post published successfully in demo mode.",
        "caption": caption
    }


def publish_to_instagram(content):
    """Publish an image and caption to Instagram using Instagram Login."""

    print("\n--- LIVE INSTAGRAM PUBLISHING ---")

    access_token = os.getenv("META_ACCESS_TOKEN")
    instagram_account_id = os.getenv("INSTAGRAM_ACCOUNT_ID")

    if not access_token or not instagram_account_id:
        return {
            "status": "ERROR",
            "message": "Instagram access token or account ID is missing from .env"
        }

    image_url = content.get("image_url")

    # Combine the caption and hashtags before sending to Instagram.
    caption = build_instagram_caption(content)

    if not image_url:
        return {
            "status": "ERROR",
            "message": "No image URL available."
        }

    if not image_url.startswith("https://"):
        return {
            "status": "ERROR",
            "message": "Image URL must be a publicly accessible HTTPS URL."
        }

    create_url = (
        f"{GRAPH_API_BASE}/"
        f"{instagram_account_id}/media"
    )

    publish_url = (
        f"{GRAPH_API_BASE}/"
        f"{instagram_account_id}/media_publish"
    )

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    print("Creating Instagram media container...")
    print("Instagram Account ID configured:", bool(instagram_account_id))
    print("Access token configured:", bool(access_token))
    print("Image URL:", image_url)
    print("Caption with hashtags:", caption)

    try:
        # Step 1: Create the Instagram media container.
        create_response = requests.post(
            create_url,
            headers=headers,
            data={
                "image_url": image_url,
                "caption": caption
            },
            timeout=60
        )

        print(
            "Instagram create-container HTTP status:",
            create_response.status_code
        )

        try:
            create_result = create_response.json()
        except ValueError:
            create_result = {
                "error": {
                    "message": create_response.text
                }
            }

        if create_response.status_code not in (200, 201):
            print(
                "Instagram create-container error:",
                create_result
            )

            return {
                "status": "ERROR",
                "message": "Instagram media container creation failed.",
                "details": create_result
            }

        creation_id = create_result.get("id")

        if not creation_id:
            return {
                "status": "ERROR",
                "message": "Instagram did not return a media container ID.",
                "details": create_result
            }

        print("Media container created:", creation_id)

        # Step 2: Publish the media container.
        print("Publishing Instagram media...")

        publish_response = requests.post(
            publish_url,
            headers=headers,
            data={
                "creation_id": creation_id
            },
            timeout=60
        )

        print(
            "Instagram publish HTTP status:",
            publish_response.status_code
        )

        try:
            publish_result = publish_response.json()
        except ValueError:
            publish_result = {
                "error": {
                    "message": publish_response.text
                }
            }

        if publish_response.status_code not in (200, 201):
            print(
                "Instagram publish error:",
                publish_result
            )

            return {
                "status": "ERROR",
                "message": "Instagram media publishing failed.",
                "details": publish_result
            }

        media_id = publish_result.get("id")

        print("Instagram post published successfully!")
        print("Instagram Media ID:", media_id)

        return {
            "status": "SUCCESS",
            "message": "Instagram post published successfully.",
            "media_id": media_id,
            "caption": caption
        }

    except requests.exceptions.Timeout:
        print("Instagram API request timed out.")

        return {
            "status": "ERROR",
            "message": "Instagram API request timed out."
        }

    except requests.exceptions.RequestException as error:
        print("Instagram request exception:", str(error))

        return {
            "status": "ERROR",
            "message": str(error)
        }


def publish_post(content):
    """Choose live or demo publishing based on PUBLISH_MODE."""

    if not publish_lock.acquire(blocking=False):
        return {
            "status": "ERROR",
            "message": "Another publishing operation is already running."
        }

    try:
        publish_mode = os.getenv(
            "PUBLISH_MODE", "DEMO"
        ).strip().upper()

        print("\nPUBLISH_POST FUNCTION CALLED")
        print("PUBLISH_MODE:", publish_mode)

        if publish_mode == "LIVE":
            return publish_to_instagram(content)

        return publish_demo(content)

    finally:
        publish_lock.release()