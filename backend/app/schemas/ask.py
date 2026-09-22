"""
Schemas for asking questions about recorded history.

The response deliberately separates recorded memory from general
knowledge. Blending them into one paragraph would make it impossible
to tell what the user actually did from what the model merely knows.
"""

from pydantic import BaseModel, Field

from app.schemas.memory import MemoryRead


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)

    # When true, general knowledge may be included alongside — but
    # never merged into — the memory-based answer.
    include_general_knowledge: bool = True


class AskResponse(BaseModel):
    question: str

    # True only when recorded memories were found and used.
    has_recorded_memory: bool

    # Answer derived strictly from the user's memories.
    answer: str

    # Clearly separated general knowledge, when offered.
    general_knowledge: str | None = None

    # The memories this answer rests on, so it can be audited.
    sources: list[MemoryRead] = Field(default_factory=list)

    provider: str
    provider_available: bool