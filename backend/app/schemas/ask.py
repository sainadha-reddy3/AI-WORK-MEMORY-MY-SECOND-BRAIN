"""
Schemas for asking questions about recorded history.

The response deliberately separates recorded memory from general
knowledge, and states any date range that was applied — so the user
always knows exactly what was searched.
"""

from datetime import date

from pydantic import BaseModel, Field

from app.schemas.memory import MemoryRead


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    include_general_knowledge: bool = True


class DateFilter(BaseModel):
    label: str
    since: date
    until: date


class AskResponse(BaseModel):
    question: str
    has_recorded_memory: bool
    answer: str
    general_knowledge: str | None = None
    sources: list[MemoryRead] = Field(default_factory=list)
    provider: str
    provider_available: bool
    # Set when the question mentioned a time ("yesterday", "last week"…).
    date_filter: DateFilter | None = None