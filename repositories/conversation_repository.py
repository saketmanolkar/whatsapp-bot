import logging
from datetime import datetime

from database import db
from models.conversation import ConversationMessage

CONVERSATIONS = db["conversations"]
CONVERSATIONS.create_index("sender")
logger = logging.getLogger(__name__)


def add_message(message: ConversationMessage) -> None:
    """Append one message to the conversations collection."""
    doc = message.model_dump()
    doc["created_at"] = datetime.utcnow()
    logger.info(f"Adding message: {doc}")
    CONVERSATIONS.insert_one(doc)

def get_messages(sender: str) -> list[ConversationMessage]:
    """Get latest 10 messages for a sender."""
    messages = CONVERSATIONS.find({"sender": sender}).sort("created_at", -1).limit(10)
    return [ConversationMessage(**message) for message in messages]
