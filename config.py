from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Literal


class Settings(BaseSettings):
    TELEGRAM_TOKEN: str
    WEBHOOK_URL: str

    # ── LLM Provider ─────────────────────────────────────────────────────
    LLM_PROVIDER: Literal[
        "openrouter",   # Claude/GPT/Llama via OpenRouter
        "openai",       # GPT direct
        "anthropic",    # Claude direct
        "ollama",       # Local model
    ] = "openrouter"

    # OpenRouter / OpenAI
    OPENROUTER_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # Anthropic
    ANTHROPIC_API_KEY: str = ""

    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Model name
    LLM_MODEL: str = "meta-llama/llama-3.3-70b-instruct"

    # DB paths (Railway volume at /app/data)
    DB_PATH: str = "/app/data/nutrition.db"
    CHECKPOINT_DB_PATH: str = "/app/data/checkpoints.db"

    DEBUG: bool = False

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Recommended models per provider
RECOMMENDED_MODELS = {
    "openrouter": {
        "balanced": "meta-llama/llama-3.3-70b-instruct",   # free + powerful
        "premium":  "anthropic/claude-sonnet-4-5",
        "fast":     "google/gemma-3-27b-it:free",
    },
    "openai": {
        "balanced": "gpt-4o-mini",
        "premium":  "gpt-4o",
    },
    "anthropic": {
        "balanced": "claude-haiku-4-5-20251001",
        "premium":  "claude-sonnet-4-5-20251001",
    },
    "ollama": {
        "balanced": "llama3.2",
        "premium":  "llama3.3:70b",
        "hebrew":   "aya-expanse",
    },
}
