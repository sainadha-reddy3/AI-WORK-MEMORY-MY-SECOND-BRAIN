"""
Topic endpoints — the user's history organised by subject.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import TopicHistory, TopicSummary
from app.services import get_topic_history, list_all_topics

router = APIRouter(prefix="/topics", tags=["topics"])


@router.get("", response_model=list[TopicSummary])
def list_topics(db: Session = Depends(get_db)):
    """Every topic recorded, most frequent first."""
    return list_all_topics(db)


@router.get("/{topic}", response_model=TopicHistory)
def topic_history(topic: str, db: Session = Depends(get_db)):
    """
    Everything recorded about one topic.

    Returns an empty history rather than 404 when the topic is
    unknown: "you have never recorded this" is a real answer, and
    the UI should show it as one.
    """
    return get_topic_history(db, topic)