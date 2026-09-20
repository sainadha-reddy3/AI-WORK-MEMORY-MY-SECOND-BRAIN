"""
Provider selection.

The only place in the codebase that decides which provider is used.
Everything else calls get_provider().
"""

from functools import lru_cache

from app.ai.base import AIProvider
from app.ai.mock_provider import MockProvider
from app.core.config import settings


@lru_cache(maxsize=1)
def get_provider() -> AIProvider:
    """
    Return the configured provider.

    Controlled by AI_PROVIDER in the environment. Unknown values fall
    back to the mock rather than crashing — a misconfigured provider
    should degrade visibly, not take the app down.
    """
    choice = (settings.ai_provider or "mock").lower()

    if choice == "mock":
        return MockProvider()

    # Ollama is added in Task 4.2.
    return MockProvider()