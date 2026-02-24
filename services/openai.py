import base64
from typing import Optional

from openai import OpenAI

from config import CHAT_GPT_API_KEY

_client: Optional[OpenAI] = None


def _get_client() -> Optional[OpenAI]:
    global _client
    if not CHAT_GPT_API_KEY:
        return None
    if _client is None:
        _client = OpenAI(api_key=CHAT_GPT_API_KEY)
    return _client


def chat(
    user_message: str,
    system_message: Optional[str] = None,
    model: str = "gpt-4o-mini",
) -> str:
    """
    Calls the OpenAI Chat Completions API and returns the assistant's reply.
    Returns an error message string if the API key is missing or the call fails.
    """
    client = _get_client()
    if not client:
        return "Chat is not configured (missing CHAT_GPT_API_KEY)."

    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
        )
        content = response.choices[0].message.content
        if not content:
            return "Sorry, I didn't get a reply."
        return content.strip()
    except Exception as e:
        return f"Sorry, something went wrong: {e!s}"


def chat_with_image(
    user_message: str,
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    system_message: Optional[str] = None,
    model: str = "gpt-4o-mini",
) -> str:
    """
    Calls the OpenAI Chat Completions API with an image (vision).
    user_message can be a caption from the user or a prompt like "What's in this image?"
    """
    client = _get_client()
    if not client:
        return "Chat is not configured (missing CHAT_GPT_API_KEY)."

    b64 = base64.standard_b64encode(image_bytes).decode("ascii")
    data_url = f"data:{mime_type};base64,{b64}"

    content = [
        {"type": "text", "text": user_message or "What's in this image? Describe it briefly."},
        {"type": "image_url", "image_url": {"url": data_url}},
    ]

    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": content})

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
        )
        msg_content = response.choices[0].message.content
        if not msg_content:
            return "Sorry, I couldn't understand the image."
        return msg_content.strip()
    except Exception as e:
        return f"Sorry, something went wrong: {e!s}"
