import asyncio
import logging
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, SystemMessage

from config import get_settings
from agent.llm_factory import create_llm, supports_tool_calling
from agent.tools import get_tools_for_user
from agent.prompts import get_system_prompt
import db.repository as repo

logger = logging.getLogger(__name__)
settings = get_settings()
AGENT_TIMEOUT = 60  # seconds


async def run_agent(user_id: int, user_message: str) -> str:
    user_profile = await repo.get_user(user_id)
    system_prompt = get_system_prompt(user_profile)
    llm = create_llm()
    tools = get_tools_for_user(user_id)

    if not supports_tool_calling():
        logger.warning(f"Model {settings.LLM_MODEL} may not support tool calling.")
        result = await llm.ainvoke(
            [SystemMessage(content=system_prompt),
             HumanMessage(content=user_message)]
        )
        return result.content

    # No checkpointer — each message is independent; all state lives in the DB.
    # A persistent checkpointer caused broken-state loops when previous runs were
    # interrupted (timeout/crash), making the agent hit the recursion limit.
    agent = create_react_agent(
        llm,
        tools,
        prompt=system_prompt,
    )

    config = {"recursion_limit": 25}

    try:
        result = await asyncio.wait_for(
            agent.ainvoke(
                {"messages": [HumanMessage(content=user_message)]},
                config=config,
            ),
            timeout=AGENT_TIMEOUT,
        )
        response = result["messages"][-1].content
        # LangGraph returns this English string when recursion_limit is hit
        if not response or "Sorry, need more steps" in response:
            raise RuntimeError("Agent hit recursion limit")
        return response

    except asyncio.TimeoutError:
        logger.error(f"Agent timed out for user {user_id} after {AGENT_TIMEOUT}s")
        raise
    except Exception as e:
        logger.error(f"Agent error for user {user_id}: {e}", exc_info=True)
        raise
