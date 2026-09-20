"""
The AI provider contract.

Every provider — mock, Ollama, or anything added later — implements
this interface. Nothing else in the application knows which provider
is in use, so swapping providers never touches application code.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class StructuredMemory:
    """
    The AI's interpretation of what the user described.

    This is category 3 in the project's source rules: AI organisation
    of user-provided information. It is never treated as fact on its
    own — `raw_input` always holds what the user actually said.
    """

    title: str
    content: str
    memory_type: str = "note"
    confidence: str = "confirmed"
    topics: list[str] = field(default_factory=list)
    project: str | None = None
    language: str = "en"

    # Phrases in the user's text that signalled uncertainty
    # ("I think", "not sure", "maybe"). Kept so the decision is
    # inspectable rather than mysterious.
    uncertainty_markers: list[str] = field(default_factory=list)


@dataclass
class MemoryAnswer:
    """
    An answer to a question about the user's history.

    The separation is the whole point: `answer` may only use the
    memories supplied. `general_knowledge` is clearly marked as
    coming from the model's training, not from the user's history.
    """

    answer: str
    # IDs of memories actually used. Empty means the system had
    # nothing recorded — and must say so.
    used_memory_ids: list[str] = field(default_factory=list)
    has_recorded_memory: bool = False
    general_knowledge: str | None = None


class AIProvider(ABC):
    """Interface all AI providers must implement."""

    name: str = "base"

    @abstractmethod
    def is_available(self) -> bool:
        """
        Can this provider be reached right now?

        Critical: when the answer is no, the system must say so
        rather than silently degrading into invented content.
        """

    @abstractmethod
    def structure_memory(self, text: str) -> StructuredMemory:
        """Turn a natural description into structured fields."""

    @abstractmethod
    def answer_from_memories(
        self, question: str, memories: list[dict]
    ) -> MemoryAnswer:
        """
        Answer using ONLY the supplied memories.

        If they don't contain the answer, say so. Never fill the gap
        from general knowledge while presenting it as the user's
        history.
        """

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Convert text to a vector for semantic search (Phase 5)."""