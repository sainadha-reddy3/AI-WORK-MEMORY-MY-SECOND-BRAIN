"""
Local embedding provider.

Runs a multilingual embedding model inside this container. No network
calls, no external service, no per-session setup — which is what makes
the whole application portable: clone, docker compose up, and search
works on any machine.

Text structuring still falls back to the rule-based mock. This
provider exists to make embeddings reliable, not to replace an LLM.
"""

from functools import lru_cache

from app.ai.base import AIProvider, MemoryAnswer, StructuredMemory
from app.ai.mock_provider import MockProvider
from app.core.config import settings

MODEL_NAME = settings.embedding_model

# Stored with every vector, so vectors from different models are never
# compared with each other by mistake.
EMBEDDING_ID = f"local:{MODEL_NAME.split('/')[-1]}"


@lru_cache(maxsize=1)
def _load_model():
    """Load the model once and keep it in memory."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODEL_NAME)


class LocalProvider(AIProvider):
    name = "local"
    embedding_id = EMBEDDING_ID

    def __init__(self) -> None:
        # Structuring stays rule-based. An embedding model is excellent
        # at similarity and useless at following instructions, so we
        # don't pretend otherwise.
        self._rules = MockProvider()

    def is_available(self) -> bool:
        try:
            _load_model()
            return True
        except Exception:
            return False

    def structure_memory(self, text: str) -> StructuredMemory:
        return self._rules.structure_memory(text)

    def answer_from_memories(self, question: str, memories: list[dict]) -> MemoryAnswer:
        return self._rules.answer_from_memories(question, memories)

    def embed(self, text: str) -> list[float]:
        """Real semantic embedding — the reason this provider exists."""
        # E5 models expect a prefix. "query: " is the recommended choice
        # when the same function embeds both questions and memories.
        if "e5" in MODEL_NAME.lower():
            text = f"query: {text}"
        vector = _load_model().encode(text, normalize_embeddings=True)
        return vector.tolist()