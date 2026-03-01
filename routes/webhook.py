import time
from collections import deque

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from config import VERIFY_TOKEN
from services.whatsapp import get_media, send_whatsapp_text
from services.openai import chat_with_image
from services.agent import ask_agent

router = APIRouter()

# Dedupe duplicate webhook deliveries (Meta sometimes sends the same message many times)
_PROCESSED_MESSAGE_IDS: set = set()
_PROCESSED_IDS_DEQUE: deque = deque()
# Fallback when message_id is missing: same sender+body within this many seconds = duplicate
_RECENT_SENDER_BODY: dict[str, float] = {}
_DEDUPE_WINDOW_SEC = 30

# Ignore echo: if incoming text exactly matches what we just sent to this user, skip (stops bot replying to itself)
_LAST_SENT_BY_SENDER: dict[str, tuple[str, float]] = {}
_ECHO_WINDOW_SEC = 60


def _already_processed(message_id: str) -> bool:
    """Return True if we already handled this message_id (duplicate). Otherwise register it and return False."""
    if message_id in _PROCESSED_MESSAGE_IDS:
        return True
    if len(_PROCESSED_IDS_DEQUE) >= 500:
        _PROCESSED_MESSAGE_IDS.discard(_PROCESSED_IDS_DEQUE.popleft())
    _PROCESSED_IDS_DEQUE.append(message_id)
    _PROCESSED_MESSAGE_IDS.add(message_id)
    return False


def _is_echo_of_our_reply(sender: str, incoming_text: str) -> bool:
    """True if this incoming text is exactly what we last sent to this sender (within _ECHO_WINDOW_SEC)."""
    if not incoming_text:
        return False
    now = time.time()
    if sender not in _LAST_SENT_BY_SENDER:
        return False
    sent_body, sent_at = _LAST_SENT_BY_SENDER[sender]
    if now - sent_at > _ECHO_WINDOW_SEC:
        return False
    return sent_body.strip() == incoming_text.strip()


def _record_sent_reply(sender: str, body: str) -> None:
    """Call after sending a reply so we can ignore echo."""
    _LAST_SENT_BY_SENDER[sender] = (body, time.time())


def _already_processed_recent(sender: str, msg_type: str, body: str) -> bool:
    """Return True if we handled this exact (sender, type, body) in the last _DEDUPE_WINDOW_SEC seconds."""
    key = f"{sender}|{msg_type}|{body}"
    now = time.time()
    # Prune old entries
    for k in list(_RECENT_SENDER_BODY):
        if now - _RECENT_SENDER_BODY[k] > _DEDUPE_WINDOW_SEC + 10:
            del _RECENT_SENDER_BODY[k]
    if key in _RECENT_SENDER_BODY and now - _RECENT_SENDER_BODY[key] < _DEDUPE_WINDOW_SEC:
        return True
    _RECENT_SENDER_BODY[key] = now
    return False


@router.get("/webhook")
async def webhook_verify(request: Request):
    """
    Meta calls this during "Verify and save".
    You must return hub.challenge if verify_token matches.
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN and challenge:
        return PlainTextResponse(challenge)

    return PlainTextResponse("Verification failed", status_code=403)


@router.post("/webhook")
async def webhook_receive(request: Request):
    """
    Meta calls this when messages arrive.
    We parse the message and reply.
    """
    payload = await request.json()
    #print("Incoming webhook payload:", payload)

    try:
        change = payload["entry"][0]["changes"][0]["value"]

        if "messages" not in change:
            return {"status": "ignored"}

        msg = change["messages"][0]
        message_id = msg.get("id")
        if message_id and _already_processed(message_id):
            return {"status": "ignored_duplicate"}

        sender = msg["from"]
        msg_type = msg.get("type", "text")

        if msg_type == "text":
            text = (msg.get("text") or {}).get("body") or ""
            if _is_echo_of_our_reply(sender, text):
                return {"status": "ignored_echo"}
            if _already_processed_recent(sender, msg_type, text):
                return {"status": "ignored_duplicate"}
            reply_text = ask_agent(text, sender)
            
        elif msg_type == "image":
            image_obj = msg.get("image") or {}
            media_id = image_obj.get("id")
            caption = image_obj.get("caption") or ""
            if _already_processed_recent(sender, msg_type, media_id or ""):
                return {"status": "ignored_duplicate"}
            if not media_id:
                reply_text = "I couldn't get the image."
            else:
                media = get_media(media_id)
                if not media:
                    reply_text = "I couldn't download the image."
                else:
                    image_bytes, mime_type = media
                    reply_text = chat_with_image(
                        user_message=caption or "What's in this image? Describe it briefly.",
                        image_bytes=image_bytes,
                        mime_type=mime_type,
                        sender=sender,
                    )
        else:
            reply_text = f"I can only handle text and images for now (got {msg_type})."

        send_whatsapp_text(to=sender, body=reply_text)
        _record_sent_reply(sender, reply_text)

    except Exception as e:
        print("Error parsing webhook:", e)

    return {"status": "ok"}