"""
Pydantic models for the conversations collection.
"""
from datetime import datetime
from pydantic import BaseModel, Field
from enums import MessageType


class ConversationMessage(BaseModel):
    """A single message as stored or returned from the DB."""

    sender: str = None
    sent_message: str
    received_message: str
    message_type: MessageType
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True
