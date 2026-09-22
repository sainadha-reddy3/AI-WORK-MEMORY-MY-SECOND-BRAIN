"""
Local embedding provider.

Runs all-MiniLM-L6-v2 inside this container. No network calls, no
external service, no per-session setup — which is what makes the
whole application portable: clone, docker compose up, and search
works on any machine.

Text structuring still falls back to the rule-based mock. This
provider exists to make embeddings reliable, not to replace an LLM.
"""

from functools import lru_cache

from app.ai.base import AIProvider, MemoryAnswer, StructuredMemory
from app.ai.mock_provider import MockProvider

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# all-MiniLM-L6-v2 produces 384-dimensional vectors.
LOCAL_EMBEDDING_DIM = 384


@lru_cache(maxsize=1)
def _load_model():
    """
    Load the model once and keep it in memory.

    First call takes a second or two; every call after is instant.
    """
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODEL_NAME)


class LocalProvider(AIProvider):
    name = "local"

    def __init__(self) -> None:
        # Structuring stays rule-based. A small embedding model is
        # excellent at similarity and useless at following JSON
        # instructions, so we don't pretend otherwise.
        self._rules = MockProvider()

    def is_available(self) -> bool:
        try:
            _load_model()
            return True
        except Exception:
            return False

    def structure_memory(self, text: str) -> StructuredMemory:
        return self._rules.structure_memory(text)

    def answer_from_memories(
        self, question: str, memories: list[dict]
    ) -> MemoryAnswer:
        return self._rules.answer_from_memories(question, memories)

    def embed(self, text: str) -> list[float]:
        """Real semantic embedding — the reason this provider exists."""
        model = _load_model()
        vector = model.encode(text, normalize_embeddings=True)
        return vector.tolist()