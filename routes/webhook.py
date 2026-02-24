from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from config import VERIFY_TOKEN
from services.whatsapp import get_media, send_whatsapp_text
from services.openai import chat as openai_chat, chat_with_image

router = APIRouter()


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
    print("Incoming webhook payload:", payload)

    try:
        change = payload["entry"][0]["changes"][0]["value"]

        if "messages" not in change:
            return {"status": "ignored"}

        msg = change["messages"][0]
        sender = msg["from"]
        msg_type = msg.get("type", "text")

        if msg_type == "text":
            text = (msg.get("text") or {}).get("body") or ""
            reply_text = openai_chat(text)
            
        elif msg_type == "image":
            image_obj = msg.get("image") or {}
            media_id = image_obj.get("id")
            caption = image_obj.get("caption") or ""
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
                    )
        else:
            reply_text = f"I can only handle text and images for now (got {msg_type})."

        send_whatsapp_text(to=sender, body=reply_text)

    except Exception as e:
        print("Error parsing webhook:", e)

    return {"status": "ok"}