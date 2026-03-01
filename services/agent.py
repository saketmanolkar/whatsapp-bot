from typing import Optional

import logging
from config import CHAT_GPT_API_KEY, OPENAI_MODEL
from langchain_openai import ChatOpenAI
from langchain.agents import Tool, AgentType, initialize_agent

from .openai import chat as openai_chat 
from .spotify import agent_play_music

_agent = None
_current_sender: list = [None]
_last_tool_output: list = [None]  # full output from the last tool (executor may truncate observation)


logger = logging.getLogger(__name__)


def _get_llm() -> ChatOpenAI:
    if not CHAT_GPT_API_KEY:
        raise RuntimeError("Missing CHAT_GPT_API_KEY for LangChain agent")
    return ChatOpenAI(
        model=OPENAI_MODEL,
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
        sender = _current_sender[0]
        out = openai_chat(query, sender=sender)
        _last_tool_output[0] = out
        logger.info("general_questions: stored output len=%s preview=%s", len(out), (out[:80] + "...") if len(out) > 80 else out)
        return out

    def play_music(query: str) -> str:
        """
        Use when the user wants to play a song on Spotify.
        Input must be the song name only, e.g. "Holiday" or "Holiday by Green Day".
        """
        sender = _current_sender[0]
        out = agent_play_music(query, sender=sender)
        _last_tool_output[0] = out
        return out

    tools = [
        Tool(
            name="general_questions",
            func=general_questions,
            description=(
                "MANDATORY: You MUST call this tool for every user message unless they ask to play a song. "
                "Do NOT respond without calling a tool. Use general_questions for: thanks, hi, bye, okay, "
                "any question, listing past messages, summarizing the conversation, chitchat, advice, "
                "or any other text. This tool has conversation history. Input = the user's message exactly."
            ),
        ),
        Tool(
            name="play_music",
            func=play_music,
            description=(
                "Use ONLY when the user explicitly wants to play a song or music on Spotify (e.g. 'play X', 'play me X'). "
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
            agent_kwargs={
                "prefix": (
                    "You must always use one of the tools. Never give a final answer without calling a tool first. "
                    "For any user message (thanks, hi, bye, questions, list messages, etc.) use the general_questions tool. "
                    "Only use play_music when the user clearly asks to play a song on Spotify.\n\n"
                ),
            },
            agent_executor_kwargs={
                "max_iterations": 8,
                "handle_parsing_errors": True,
                "return_intermediate_steps": True,
            },
        )
    return _agent


def ask_agent(message: str, sender: Optional[str] = None) -> str:
    """
    Call the agent (it only picks which tool to use). We return the tool's output
    verbatim — the agent does not rephrase or shorten it.
    """
    _current_sender[0] = sender
    try:
        agent = get_agent()
        try:
            result = agent.invoke({"input": message})
        except Exception as invoke_error:
            # Agent may throw output parsing error when the LLM reply isn't valid ReAct (e.g. after tool error).
            # If we have the tool's output (e.g. "no active device"), return it so the user sees the real error.
            err_msg = str(invoke_error)
            if _last_tool_output[0] is not None:
                out = _last_tool_output[0]
                _last_tool_output[0] = None
                logger.info("ask_agent: output parsing (or other) error, returning stored tool output: %s", err_msg[:80])
                return out
            if "Could not parse LLM output:" in err_msg or "output parsing" in err_msg.lower():
                # Try to extract the quoted LLM output so user still gets a readable message
                if "`" in err_msg:
                    start = err_msg.find("`") + 1
                    end = err_msg.find("`", start)
                    if end > start:
                        return err_msg[start:end].strip()
                return "Something went wrong while handling your request. Please try again."
            raise

        if not isinstance(result, dict):
            logger.info("ask_agent: result not dict, returning str(result)")
            return str(result)

        steps = result.get("intermediate_steps", [])
        agent_output = result.get("output", "")
        stored_output = _last_tool_output[0]

        logger.info(
            "ask_agent: len(steps)=%s, len(agent_output)=%s, stored_output is None=%s, len(stored_output)=%s",
            len(steps),
            len(agent_output or ""),
            stored_output is None,
            len(stored_output) if stored_output else 0,
        )

        if stored_output is not None:
            _last_tool_output[0] = None
            preview = (stored_output[:60] + "...") if len(stored_output) > 60 else stored_output
            logger.info("ask_agent: returning STORED tool output (len=%s) preview=%r", len(stored_output), preview)
            return stored_output

        if agent_output and ("iteration limit" in agent_output.lower() or "time limit" in agent_output.lower()):
            return "That took a bit long. Try asking something shorter or more specific."
        preview = (agent_output or "")[:60] + "..." if len(agent_output or "") > 60 else (agent_output or "")
        logger.info("ask_agent: returning AGENT output (len=%s) preview=%r", len(agent_output or ""), preview)
        return agent_output or str(result)
    finally:
        _current_sender[0] = None
        _last_tool_output[0] = None