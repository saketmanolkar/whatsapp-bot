import os
import base64
import logging
import requests
from typing import Optional
from config import CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN
from enums import MessageType
from models.conversation import ConversationMessage
from repositories import add_message
from constants import SPOTIFY_PLAY_API_URL, SPOTIFY_SEARCH_API_URL, SPOTIFY_TOKEN_URL

logger = logging.getLogger(__name__)

def get_access_token():
    url = SPOTIFY_TOKEN_URL
    auth = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()

    data = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN
    }

    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    r = requests.post(url, data=data, headers=headers)
    r.raise_for_status()
    return r.json()["access_token"]


def spotify_search_track(access_token, query):
    url = SPOTIFY_SEARCH_API_URL
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"q": query, "type": "track", "limit": 1}

    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()
    items = r.json()["tracks"]["items"]
    return items[0]["uri"] if items else None


def spotify_search_track_info(access_token, query):
    """
    Search for a track and return first result as dict with uri, name, artists, or None.
    """
    url = SPOTIFY_SEARCH_API_URL
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"q": query, "type": "track", "limit": 1}

    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()
    items = r.json()["tracks"]["items"]
    if not items:
        return None
    t = items[0]
    return {
        "uri": t["uri"],
        "name": t["name"],
        "artists": [a["name"] for a in t.get("artists", [])],
    }


def _play_error_message(r) -> str:
    """Turn Spotify play API error into a short user-facing message."""
    try:
        data = r.json()
        msg = (data.get("error") or {}).get("message") or data.get("message") or r.text
    except Exception:
        msg = r.text or "Unknown error"
    if "active device" in msg.lower() or "no active device" in msg.lower():
        return "No active device found. Please open Spotify and select a device (e.g. your phone or computer), then try again."
    return msg


def spotify_play_uri(access_token, uri):
    url = SPOTIFY_PLAY_API_URL
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {"uris": [uri]}
    r = requests.put(url, headers=headers, json=payload)
    if r.status_code not in (200, 204):
        raise Exception(_play_error_message(r))
    logger.info("Song played: uri=%s", uri)

def agent_play_music(query: str, sender: Optional[str] = None) -> str:

    query = (query or "").strip()
    if not query:
        return "Please provide a song name, e.g. 'Holiday' or 'Holiday by Green Day'."
    try:
        token = get_access_token()
        track_uri = spotify_search_track(token, query)
        if not track_uri:
            return f"Could not find a track for: {query}"
        spotify_play_uri(token, track_uri)
        logger.info("Song played via agent: query=%s uri=%s sender=%s", query, track_uri, sender)
        data = ConversationMessage(
            sender=sender,
            sent_message=query,
            received_message=f"Now playing: {query}",
            message_type=MessageType.SPOTIFY_TOOL,
        )
        add_message(data)
        return f"Now playing: {query}"
    except Exception as e:
        return f"Could not play: {e!s}"