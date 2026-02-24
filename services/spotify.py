import os
import base64
import logging
import requests
from fastapi import HTTPException
from config import CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN

logger = logging.getLogger(__name__)

def get_access_token():
    url = "https://accounts.spotify.com/api/token"
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
    url = "https://api.spotify.com/v1/search"
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
    url = "https://api.spotify.com/v1/search"
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


def spotify_play_uri(access_token, uri):
    url = "https://api.spotify.com/v1/me/player/play"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {"uris": [uri]}
    r = requests.put(url, headers=headers, json=payload)
    if r.status_code not in (200, 204):
        raise Exception(r.text)
    logger.info("Song played: uri=%s", uri)