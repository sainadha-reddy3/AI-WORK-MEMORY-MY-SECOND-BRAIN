"""
Answering questions about recorded work history.

The central rule of this project lives here: the system answers from
the user's memories, or it says it cannot. It never fills the gap
with plausible-sounding invention.
"""

from sqlalchemy.orm import Session

from app.ai import get_provider
from app.services.search_service import hybrid_search

NO_MEMORY_MESSAGE = (
    "I don't have a recorded memory of this, so I don't want to guess."
)


def ask(db: Session, question: str, include_general: bool = True) -> dict:
    """
    Answer a question using only the user's recorded memories.

    When nothing relevant is found, the model is not consulted at
    all — there is nothing for it to summarise, and asking would
    invite invention.
    """
    provider = get_provider()
    hits = hybrid_search(db, question, limit=8)

    if not hits:
        general = None
        if include_general:
            general = (
                "I can explain this from general technical knowledge if "
                "that would help — just ask. It would not be based on "
                "anything you recorded."
            )

        return {
            "question": question,
            "has_recorded_memory": False,
            "answer": NO_MEMORY_MESSAGE,
            "general_knowledge": general,
            "sources": [],
            "provider": provider.name,
            "provider_available": provider.is_available(),
        }

    # Hand the provider plain dicts — it must not depend on ORM
    # objects, so any provider can be swapped in.
    memory_dicts = [
        {
            "id": str(h.memory.id),
            "occurred_on": str(h.memory.occurred_on),
            "title": h.memory.title,
            "content": h.memory.content,
            "confidence": h.memory.confidence,
            "topics": h.memory.topics,
        }
        for h in hits
    ]

    result = provider.answer_from_memories(question, memory_dicts)

    return {
        "question": question,
        "has_recorded_memory": True,
        "answer": result.answer,
        "general_knowledge": None,
        "sources": [h.memory for h in hits],
        "provider": provider.name,
        "provider_available": provider.is_available(),
    }