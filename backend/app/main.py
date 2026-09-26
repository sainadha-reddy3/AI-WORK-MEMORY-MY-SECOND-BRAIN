"""
AI Work Memory — backend entry point.
"""

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.ask import router as ask_router
from app.api.memories import router as memories_router
from app.api.topics import router as topics_router
from app.db.session import get_db

app = FastAPI(
    title="AI Work Memory",
    description="Personal long-term work memory system.",
    version="0.1.0",
)

# The frontend runs on a different port, so the browser treats it as
# a different origin and blocks requests unless we allow them.
# Wide open in development; tightened in Phase 17.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(memories_router)
app.include_router(ask_router)
app.include_router(topics_router)


@app.get("/")
def read_root():
    return {
        "app": "AI Work Memory — My Second Brain",
        "status": "running",
        "phase": 6,
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/health/db")
def database_health(db: Session = Depends(get_db)):
    try:
        version = db.execute(text("SELECT version()")).scalar()
        return {"database": "connected", "version": version}
    except Exception as exc:
        return {"database": "unreachable", "error": str(exc)}