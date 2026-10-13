import os
import requests
from dotenv import load_dotenv

load_dotenv()

GRAPH_API_VERSION = "v23.0"


def get_access_token():
    return os.getenv("META_ACCESS_TOKEN")


def get_instagram_account_id():
    return os.getenv("INSTAGRAM_ACCOUNT_ID")


def test_access_token():
    """
    Test whether the configured Instagram access token
    can be used to access the configured Instagram account.
    """

    access_token = get_access_token()
    instagram_account_id = get_instagram_account_id()

    if not access_token:
        return {
            "status": "ERROR",
            "message": "META_ACCESS_TOKEN is not configured."
        }

    if not instagram_account_id:
        return {
            "status": "ERROR",
            "message": "INSTAGRAM_ACCOUNT_ID is not configured."
        }

    url = (
        f"https://graph.instagram.com/"
        f"{GRAPH_API_VERSION}/{instagram_account_id}"
    )

    params = {
        "fields": "id,username",
        "access_token": access_token
    }

    try:
        response = requests.get(url, params=params, timeout=30)

        if response.ok:
            return {
                "status": "SUCCESS",
                "data": response.json()
            }

        return {
            "status": "ERROR",
            "http_status": response.status_code,
            "message": response.text
        }

    except requests.RequestException as error:
        return {
            "status": "ERROR",
            "message": str(error)
        }