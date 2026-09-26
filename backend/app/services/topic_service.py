"""
Topic-centric history.

Search answers "where is X?". This answers "what is my relationship
with X?" — the whole arc of a topic across time, grouped by the kind
of memory each entry is.

Everything here is derived from recorded data. Related topics come
from co-occurrence in the user's own tags, not from a model's
opinion about what relates to what.
"""

from collections import Counter, defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Memory

# The order sections appear in a topic history. Chosen to read as a
# narrative: what happened, what went wrong, what fixed it, what was
# learned.
TYPE_ORDER = [
    "incident",
    "mistake",
    "solution",
    "learning",
    "code",
    "meeting",
    "note",
]


def get_topic_history(db: Session, topic: str) -> dict:
    """
    Everything recorded about one topic.

    Returns an empty history rather than raising when the topic has
    no memories — "you have never recorded this" is a valid and
    useful answer, not an error.
    """
    key = topic.strip().lower()

    stmt = (
        select(Memory)
        .where(Memory.topics.any(key))
        .options(selectinload(Memory.evidence))
        .order_by(Memory.occurred_on.desc(), Memory.created_at.desc())
    )
    memories = list(db.execute(stmt).scalars().all())

    if not memories:
        return {
            "topic": key,
            "total": 0,
            "first_seen": None,
            "last_seen": None,
            "uncertain_count": 0,
            "timeline": [],
            "by_type": {},
            "related_topics": [],
        }

    # Group by memory type, preserving date order within each group.
    grouped: dict[str, list[Memory]] = defaultdict(list)
    for m in memories:
        grouped[m.memory_type].append(m)

    by_type = {
        t: grouped[t] for t in TYPE_ORDER if t in grouped
    }
    # Any type not in TYPE_ORDER still gets included.
    for t, items in grouped.items():
        if t not in by_type:
            by_type[t] = items

    # Related topics: which tags appear alongside this one, and how
    # often. Derived from the user's own tagging, not inferred.
    counter: Counter = Counter()
    for m in memories:
        for t in m.topics:
            if t != key:
                counter[t] += 1

    dates = [m.occurred_on for m in memories]

    return {
        "topic": key,
        "total": len(memories),
        "first_seen": min(dates),
        "last_seen": max(dates),
        # How much of this history is unconfirmed. Surfaced so the
        # user can see when a topic's story rests on hedged memories.
        "uncertain_count": sum(
            1 for m in memories if m.confidence == "uncertain"
        ),
        "timeline": memories,
        "by_type": by_type,
        "related_topics": [
            {"topic": t, "shared_memories": n}
            for t, n in counter.most_common(10)
        ],
    }


def list_all_topics(db: Session) -> list[dict]:
    """
    Every topic the user has recorded, with counts.

    Backs the left panel and any topic browser.
    """
    memories = db.execute(select(Memory)).scalars().all()

    counter: Counter = Counter()
    last_seen: dict = {}

    for m in memories:
        for t in m.topics:
            counter[t] += 1
            if t not in last_seen or m.occurred_on > last_seen[t]:
                last_seen[t] = m.occurred_on

    return [
        {"topic": t, "count": n, "last_seen": last_seen[t]}
        for t, n in counter.most_common()
    ]