"""
LLM Factory — returns a ready LLM instance based on configuration.
All providers return a BaseChatModel compatible with LangGraph.
Switching provider = change env var only, no code changes needed.
"""
from langchain_core.language_models import BaseChatModel
from config import get_settings

settings = get_settings()


def create_llm() -> BaseChatModel:
    provider = settings.LLM_PROVIDER
    model = settings.LLM_MODEL

    if provider == "openrouter":
        return _openrouter_llm(model)
    elif provider == "openai":
        return _openai_llm(model)
    elif provider == "anthropic":
        return _anthropic_llm(model)
    elif provider == "ollama":
        return _ollama_llm(model)
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider}")


def _openrouter_llm(model: str) -> BaseChatModel:
    """
    OpenRouter — gateway to all models.
    Supports Claude, GPT, Llama, Gemma, Mistral via a single API.
    """
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.OPENROUTER_API_KEY,
        model=model,
        temperature=0.3,
        max_tokens=1024,
        default_headers={
            "HTTP-Referer": "https://nutrition-bot.app",
            "X-Title": "NutritionBot",
        },
    )


def _openai_llm(model: str) -> BaseChatModel:
    """Direct GPT"""
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        api_key=settings.OPENAI_API_KEY,
        model=model,
        temperature=0.3,
        max_tokens=1024,
    )


def _anthropic_llm(model: str) -> BaseChatModel:
    """Claude direct via Anthropic API"""
    from langchain_anthropic import ChatAnthropic
    return ChatAnthropic(
        api_key=settings.ANTHROPIC_API_KEY,
        model=model,
        temperature=0.3,
        max_tokens=1024,
    )


def _ollama_llm(model: str) -> BaseChatModel:
    """
    Ollama — local models.
    Requires: ollama pull llama3.2 (or any other model)
    For remote production: point OLLAMA_BASE_URL to a remote Ollama server.
    """
    from langchain_ollama import ChatOllama
    return ChatOllama(
        base_url=settings.OLLAMA_BASE_URL,
        model=model,
        temperature=0.3,
        num_predict=1024,
    )


# ─── Tool Compatibility ───────────────────────────────────────────────────────

OLLAMA_TOOL_CAPABLE_MODELS = {
    "llama3.2", "llama3.3", "llama3.1",
    "mistral", "mistral-nemo",
    "qwen2.5", "qwen2.5-coder",
    "command-r", "firefunction-v2",
}


def supports_tool_calling() -> bool:
    if settings.LLM_PROVIDER != "ollama":
        return True
    base_model = settings.LLM_MODEL.split(":")[0].lower()
    return any(m in base_model for m in OLLAMA_TOOL_CAPABLE_MODELS)
