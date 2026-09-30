"""
Answering questions about recorded work history.

The central rule of this project lives here: the system answers from
the user's memories, or it says it cannot. It never fills the gap
with plausible-sounding invention.

Time expressions ("yesterday", "last week") become explicit date
filters. A filtered search never silently widens its range — if
nothing matches in the period asked about, the answer says so.
"""

import re

from sqlalchemy.orm import Session

from app.ai import get_provider
from app.models import Memory
from app.services.dates import parse_date_range
from app.services.memory_service import list_memories
from app.services.search_service import STOPWORDS, hybrid_search

NO_MEMORY_MESSAGE = "I don't have a recorded memory of this, so I don't want to guess."

# Words that ask for "everything" rather than naming a topic — including
# common romanised Telugu and Hindi, for mixed-language questions.
FILLER = STOPWORDS | {
    "explain", "please", "everything", "anything", "happened", "list",
    "summarise", "summarize", "recap", "things", "stuff", "all",
    "nenu", "emi", "em", "enti", "chesanu", "chesa", "cheppu", "naku",
    "maine", "kya", "kiya", "mujhe", "batao", "main",
}


def _topic_terms(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9][a-z0-9.\-_]*", text.lower())
    return [w for w in words if w not in FILLER and len(w) > 1]


def _date_filter_dict(dr) -> dict | None:
    if dr is None:
        return None
    return {"label": dr.label, "since": dr.since, "until": dr.until}


def _no_memory(question, provider, message, include_general, dr) -> dict:
    general = None
    if include_general and dr is None:
        general = (
            "I can explain this from general technical knowledge if that "
            "would help — just ask. It would not be based on anything you recorded."
        )
    return {
        "question": question,
        "has_recorded_memory": False,
        "answer": message,
        "general_knowledge": general,
        "sources": [],
        "provider": provider.name,
        "provider_available": provider.is_available(),
        "date_filter": _date_filter_dict(dr),
    }


def _answer(question, provider, memories: list[Memory], dr) -> dict:
    # Hand the provider plain dicts — it must not depend on ORM objects,
    # so any provider can be swapped in.
    memory_dicts = [
        {
            "id": str(m.id),
            "occurred_on": str(m.occurred_on),
            "title": m.title,
            "content": m.content,
            "confidence": m.confidence,
            "topics": m.topics,
        }
        for m in memories
    ]
    result = provider.answer_from_memories(question, memory_dicts)
    return {
        "question": question,
        "has_recorded_memory": True,
        "answer": result.answer,
        "general_knowledge": None,
        "sources": memories,
        "provider": provider.name,
        "provider_available": provider.is_available(),
        "date_filter": _date_filter_dict(dr),
    }


def ask(db: Session, question: str, include_general: bool = True) -> dict:
    """Answer a question using only the user's recorded memories."""
    provider = get_provider()
    dr = parse_date_range(question)

    if dr is not None:
        # Only a time, no topic: "What did I do yesterday?" → everything then.
        if not _topic_terms(dr.remaining):
            memories = list_memories(db, since=dr.since, until=dr.until, limit=50)
            if not memories:
                return _no_memory(
                    question, provider,
                    f"I don't have any recorded memories from {dr.label}.",
                    include_general, dr,
                )
            return _answer(question, provider, memories, dr)

        # A topic and a time: search, then keep only what's inside the range.
        hits = hybrid_search(db, dr.remaining, limit=20)
        in_range = [h.memory for h in hits if dr.since <= h.memory.occurred_on <= dr.until]

        if not in_range:
            message = f"I don't have a recorded memory about that from {dr.label}."
            if hits:
                n = len(hits)
                message += (
                    f" You do have {n} related {'memory' if n == 1 else 'memories'} "
                    "from other dates — ask again without the date to see them."
                )
            return _no_memory(question, provider, message, include_general, dr)

        return _answer(question, provider, in_range[:8], dr)

    hits = hybrid_search(db, question, limit=8)
    if not hits:
        # The model is not consulted at all — there is nothing for it to
        # summarise, and asking would invite invention.
        return _no_memory(question, provider, NO_MEMORY_MESSAGE, include_general, None)

    return _answer(question, provider, [h.memory for h in hits], None)