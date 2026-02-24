from typing import Optional

import logging
from config import CHAT_GPT_API_KEY
from langchain_openai import ChatOpenAI
from langchain.agents import Tool, AgentType, initialize_agent

from .openai import chat as openai_chat  # reuse your existing chat function
from .spotify import get_access_token, spotify_search_track, spotify_play_uri

_agent = None  # cache the agent so it’s not rebuilt every request


logger = logging.getLogger(__name__)


def _get_llm() -> ChatOpenAI:
    if not CHAT_GPT_API_KEY:
        raise RuntimeError("Missing CHAT_GPT_API_KEY for LangChain agent")
    return ChatOpenAI(
        model="gpt-4o-mini",  # same model you already use
        temperature=0.2,
        api_key=CHAT_GPT_API_KEY,
    )


def _get_tools() -> list[Tool]:
    # This is your single tool: general_questions
    def general_questions(query: str) -> str:
        """
        Use this for general questions, small talk, and
        any natural-language question that doesn't require
        a specific external API.
        """
        # Delegate actual answering to your existing OpenAI helper
        return openai_chat(query)

    def play_music(query: str) -> str:
        """
        Use when the user wants to play a song on Spotify.
        Input must be the song name only, e.g. "Holiday" or "Holiday by Green Day".
        """
        query = (query or "").strip()
        if not query:
            return "Please provide a song name, e.g. 'Holiday' or 'Holiday by Green Day'."
        try:
            token = get_access_token()
            track_uri = spotify_search_track(token, query)
            if not track_uri:
                return f"Could not find a track for: {query}"
            spotify_play_uri(token, track_uri)
            logger.info("Song played via agent: query=%s uri=%s", query, track_uri)
            return f"Now playing: {query}"
        except Exception as e:
            return f"Could not play: {e}"

    tools = [
        Tool(
            name="general_questions",
            func=general_questions,
            description=(
                "Use this for answering general questions, chitchat, "
                "and everyday natural-language queries from the user."
            ),
        ),
        Tool(
            name="play_music",
            func=play_music,
            description=(
                "Use this when the user wants to play a song or music on Spotify. "
                "Input must be the song name only, e.g. 'Holiday' or 'Holiday by Green Day'. "
                "Do not include words like 'play' or 'play me'—extract just the song (and optionally artist)."
            ),
        ),
    ]
    return tools


def get_agent():
    """
    Build (once) and return a LangChain agent that knows about our tools.
    """
    global _agent
    if _agent is None:
        llm = _get_llm()
        tools = _get_tools()

        # ZERO_SHOT_REACT_DESCRIPTION = classic ReAct-style agent:
        # LLM thinks, decides which tool to call based on descriptions.
        _agent = initialize_agent(
            tools=tools,
            llm=llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=False,
        )
    return _agent


def ask_agent(message: str) -> str:
    """
    High-level helper: call the agent and always get back a string answer.
    """
    agent = get_agent()
    result = agent.invoke({"input": message})
    # LangChain agents usually return dicts with "output"
    if isinstance(result, dict) and "output" in result:
        return result["output"]
    return str(result)