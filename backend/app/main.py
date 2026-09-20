"""
AI Work Memory — backend entry point.
"""

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db

app = FastAPI(
    title="AI Work Memory",
    description="Personal long-term work memory system.",
    version="0.1.0",
)


@app.get("/")
def read_root():
    return {
        "app": "AI Work Memory — My Second Brain",
        "status": "running",
        "phase": 2,
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/health/db")
def database_health(db: Session = Depends(get_db)):
    """
    Confirms the backend can actually reach PostgreSQL.

    Depends(get_db) is FastAPI's dependency injection: it runs
    get_db(), hands us the session, and closes it afterwards.
    """
    try:
        version = db.execute(text("SELECT version()")).scalar()
        return {"database": "connected", "version": version}
    except Exception as exc:
        # Never let a database failure look like success.
        return {"database": "unreachable", "error": str(exc)}