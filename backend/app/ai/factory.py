"""
Provider selection.

The only place in the codebase that decides which provider is used.
Everything else calls get_provider().
"""

from functools import lru_cache

from app.ai.base import AIProvider
from app.ai.mock_provider import MockProvider
from app.ai.ollama_provider import OllamaProvider
from app.core.config import settings


@lru_cache(maxsize=1)
def get_provider() -> AIProvider:
    """
    Return the configured provider.

    Unknown values fall back to the mock rather than crashing — a
    misconfigured provider should degrade visibly, not take the
    application down.
    """
    choice = (settings.ai_provider or "mock").lower()

    if choice == "ollama":
        return OllamaProvider()

    return MockProvider()