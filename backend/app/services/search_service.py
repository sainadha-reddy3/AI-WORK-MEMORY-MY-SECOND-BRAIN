"""
Hybrid search — keyword and semantic, merged.

Keyword search is precise but literal; semantic search understands
meaning but is fuzzy. Running both and fusing the results gives
precision and recall together.

Critical rule: if nothing clears the relevance threshold, we return
nothing. Returning the least-bad match would let the system answer
questions it has no real memory of — which is exactly the failure
this project exists to prevent.
"""

from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.ai import get_provider
from app.models import Memory, MemoryEmbedding
from app.services.embedding_service import _fit_dimensions

# Below this similarity, a semantic match is treated as noise.
# Deliberately conservative — a wrong memory is worse than none.
MIN_SEMANTIC_SIMILARITY = 0.35

# Reciprocal Rank Fusion constant. 60 is the value from the original
# paper and works well in practice.
RRF_K = 60


@dataclass
class SearchHit:
    memory: Memory
    score: float
    matched_by: list[str]  # "keyword", "semantic", or both


def keyword_search(db: Session, query: str, limit: int = 20) -> list[Memory]:
    """Literal text matching across title, content and topics."""
    q = query.strip()
    if not q:
        return []

    pattern = f"%{q}%"
    stmt = (
        select(Memory)
        .options(selectinload(Memory.evidence))
        .where(
            or_(
                Memory.title.ilike(pattern),
                Memory.content.ilike(pattern),
                Memory.topics.any(q.lower()),
            )
        )
        .order_by(Memory.occurred_on.desc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def semantic_search(
    db: Session, query: str, limit: int = 20
) -> list[tuple[Memory, float]]:
    """
    Meaning-based search using pgvector.

    Returns (memory, similarity) pairs, best first. Anything below
    MIN_SEMANTIC_SIMILARITY is dropped rather than returned weakly.
    """
    provider = get_provider()

    try:
        raw = provider.embed(query)
    except Exception:
        return []

    if not raw:
        return []

    vector = _fit_dimensions(raw)

    # <=> is pgvector's cosine distance operator. Lower is closer,
    # so we convert to a similarity where higher is better.
    distance = MemoryEmbedding.vector.cosine_distance(vector)

    stmt = (
        select(Memory, distance.label("distance"))
        .join(MemoryEmbedding, MemoryEmbedding.memory_id == Memory.id)
        .where(MemoryEmbedding.model == provider.name)
        .options(selectinload(Memory.evidence))
        .order_by(distance)
        .limit(limit)
    )

    results = []
    for memory, dist in db.execute(stmt).all():
        similarity = 1.0 - float(dist)
        if similarity >= MIN_SEMANTIC_SIMILARITY:
            results.append((memory, similarity))

    return results


def hybrid_search(db: Session, query: str, limit: int = 10) -> list[SearchHit]:
    """
    Run both searches and fuse the rankings.

    Reciprocal Rank Fusion: each result scores 1/(k + rank) in each
    list it appears in, and the scores add. A memory ranked highly by
    both methods beats one ranked highly by only one — without
    needing the two scoring systems to be comparable.
    """
    keyword_results = keyword_search(db, query, limit=limit * 2)
    semantic_results = semantic_search(db, query, limit=limit * 2)

    scores: dict = {}
    matched: dict = {}
    memories: dict = {}

    for rank, memory in enumerate(keyword_results, start=1):
        key = str(memory.id)
        scores[key] = scores.get(key, 0.0) + 1.0 / (RRF_K + rank)
        matched.setdefault(key, []).append("keyword")
        memories[key] = memory

    for rank, (memory, _sim) in enumerate(semantic_results, start=1):
        key = str(memory.id)
        scores[key] = scores.get(key, 0.0) + 1.0 / (RRF_K + rank)
        matched.setdefault(key, []).append("semantic")
        memories[key] = memory

    hits = [
        SearchHit(memory=memories[k], score=v, matched_by=matched[k])
        for k, v in scores.items()
    ]
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:limit]