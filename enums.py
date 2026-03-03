"""
App-wide enums. Import from here or from submodules if we split later.
"""
from enum import Enum


class MessageType(str, Enum):
    """Type of conversation message."""

    GENERAL_TOOL = "general_tool"
    IMAGE = "image"
    SPOTIFY_TOOL = "spotify_tool"
    WEATHER_TOOL = "weather_tool"

class OpenaiPayloadType(str, Enum):
    """Type of payload for OpenAI chat."""

    GENERAL = "general"
    WEATHER = "weather"
