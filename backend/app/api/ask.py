"""
Ask endpoint — questions about the user's recorded work history.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import AskRequest, AskResponse
from app.services import ask as ask_service

router = APIRouter(prefix="/ask", tags=["ask"])


@router.post("", response_model=AskResponse)
def ask_question(data: AskRequest, db: Session = Depends(get_db)):
    """
    Answer a question from recorded memories.

    Returns has_recorded_memory=False when nothing relevant exists,
    rather than producing a plausible answer with no basis.
    """
    return ask_service(db, data.question, data.include_general_knowledge)