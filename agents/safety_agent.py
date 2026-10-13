
import os
import re


# Basic list of suspicious phrases.
# You can add more phrases as needed.
BLOCKED_TERMS = [
    "steal password",
    "steal credentials",
    "hack someone's account",
    "send your password",
    "phishing",
    "malware",
    "ransomware",
    "fake giveaway",
    "guaranteed money",
    "get rich instantly"
]


def check_content_safety(image_path, caption):
    """
    Basic rule-based safety check for SocialPilot AI.

    Returns:
        APPROVED, BLOCKED, or REVIEW_REQUIRED
    """

    reasons = []

    # 1. Check whether the generated image exists
    if not image_path or not os.path.isfile(image_path):
        return {
            "status": "REVIEW_REQUIRED",
            "reasons": ["Generated image is missing."]
        }

    # 2. Check caption for suspicious phrases
    text = (caption or "").lower()

    for term in BLOCKED_TERMS:
        if term in text:
            reasons.append(
                f"Suspicious phrase detected: {term}"
            )

    # 3. Check for suspicious links
    urls = re.findall(
        r"https?://\S+|www\.\S+",
        text
    )

    for url in urls:
        if any(
            word in url.lower()
            for word in ["login", "password", "verify-account"]
        ):
            reasons.append(
                "Potentially suspicious link detected."
            )
            break

    # 4. Return the safety decision
    if reasons:
        return {
            "status": "BLOCKED",
            "reasons": reasons
        }

    return {
        "status": "APPROVED",
        "reasons": []
    }