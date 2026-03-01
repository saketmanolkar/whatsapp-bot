import base64
from typing import Optional
from openai import OpenAI
from enums import MessageType
from config import CHAT_GPT_API_KEY, OPENAI_MODEL
from models.conversation import ConversationMessage
from repositories import add_message, get_messages
from prompts.openai_prompts import chat_system_message, image_description_system_message

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
    model: Optional[str] = None,
    sender: Optional[str] = None,
) -> str:
    """
    Calls the OpenAI Chat Completions API and returns the assistant's reply.
    Returns an error message string if the API key is missing or the call fails.
    """
    client = _get_client()
    if not client:
        return "Chat is not configured (missing CHAT_GPT_API_KEY)."
    model = model or OPENAI_MODEL

    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    else:
        messages.append({"role": "system", "content": chat_system_message()})

    sender_messages = get_messages(sender) if sender else []
    for msg in reversed(sender_messages):
        messages.append({"role": "user", "content": msg.sent_message})
        messages.append({"role": "assistant", "content": msg.received_message})

    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
        )
        content = response.choices[0].message.content
        if not content:
            return "Sorry, I didn't get a reply."
        
        data = ConversationMessage(
            sender=sender,
            sent_message=user_message,
            received_message=content.strip(),
            message_type=MessageType.GENERAL_TOOL,
        )
        add_message(data)
        return content.strip()
    except Exception as e:
        return f"Sorry, something went wrong: {e!s}"


def chat_with_image(
    user_message: str,
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    system_message: Optional[str] = None,
    model: Optional[str] = None,
    sender: Optional[str] = None,
) -> str:
    """
    Calls the OpenAI Chat Completions API with an image (vision).
    user_message can be a caption from the user or a prompt like "What's in this image?"
    """
    client = _get_client()
    if not client:
        return "Chat is not configured (missing CHAT_GPT_API_KEY)."
    model = model or OPENAI_MODEL

    b64 = base64.standard_b64encode(image_bytes).decode("ascii")
    data_url = f"data:{mime_type};base64,{b64}"

    content = [
        {"type": "text", "text": user_message or "What's in this image? Describe it briefly."},
        {"type": "image_url", "image_url": {"url": data_url}},
    ]

    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    else:
        messages.append({"role": "system", "content": image_description_system_message()})
    
    messages.append({"role": "user", "content": content})

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
        )
        msg_content = response.choices[0].message.content
        if not msg_content:
            return "Sorry, I couldn't understand the image."
        data = ConversationMessage(
            sender=sender,
            sent_message=user_message,
            received_message=msg_content.strip(),
            message_type=MessageType.IMAGE,
        )
        add_message(data)
        return msg_content.strip()
    except Exception as e:
        return f"Sorry, something went wrong: {e!s}"
