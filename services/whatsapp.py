from typing import Optional, Tuple

import requests
from config import WHATSAPP_TOKEN, PHONE_NUMBER_ID, GRAPH_VERSION


def get_media(media_id: str) -> Optional[Tuple[bytes, str]]:
    """
    Fetches media (e.g. image) by WhatsApp media ID.
    Returns (bytes, mime_type) or None on failure.
    """
    if not WHATSAPP_TOKEN:
        return None
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    meta_resp = requests.get(
        f"https://graph.facebook.com/{GRAPH_VERSION}/{media_id}",
        headers=headers,
        timeout=15,
    )
    if meta_resp.status_code != 200:
        print("Get media URL failed:", meta_resp.status_code, meta_resp.text)
        return None
    data = meta_resp.json()
    url = data.get("url")
    mime_type = data.get("mime_type", "image/jpeg")
    if not url:
        return None
    download_resp = requests.get(url, headers=headers, timeout=30)
    if download_resp.status_code != 200:
        print("Download media failed:", download_resp.status_code)
        return None
    return (download_resp.content, mime_type)


def send_whatsapp_text(to: str, body: str) -> None:
    """
    Sends a text message using WhatsApp Cloud API.
    """
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        print("Missing WHATSAPP_TOKEN or PHONE_NUMBER_ID in .env")
        return

    url = f"https://graph.facebook.com/{GRAPH_VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }

    resp = requests.post(url, headers=headers, json=data, timeout=20)
    print("Send message status:", resp.status_code, resp.text)
