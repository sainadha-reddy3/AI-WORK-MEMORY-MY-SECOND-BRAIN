"""
Schemas for topic-centric history.

The response carries `uncertain_count` deliberately: a topic history
built largely on hedged memories should say so, rather than reading
as a confident narrative.
"""

from datetime import date

from pydantic import BaseModel, Field

from app.schemas.memory import MemoryRead


class TopicSummary(BaseModel):
    """One topic in a list."""

    topic: str
    count: int
    last_seen: date


class RelatedTopic(BaseModel):
    topic: str
    shared_memories: int


class TopicHistory(BaseModel):
    topic: str
    total: int

    first_seen: date | None = None
    last_seen: date | None = None

    # How many of these memories the user was unsure about.
    uncertain_count: int = 0

    # Every memory on this topic, newest first.
    timeline: list[MemoryRead] = Field(default_factory=list)

    # The same memories grouped by kind, so the history reads as a
    # narrative: incidents, mistakes, solutions, learnings.
    by_type: dict[str, list[MemoryRead]] = Field(default_factory=dict)

    # Topics that co-occur with this one in the user's own tags.
    related_topics: list[RelatedTopic] = Field(default_factory=list)