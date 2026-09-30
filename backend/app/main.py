"""
AI Work Memory — backend entry point.
"""

import threading

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.ask import router as ask_router
from app.api.attachments import router as attachments_router
from app.api.memories import router as memories_router
from app.api.topics import router as topics_router
from app.api.voice import router as voice_router
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
app.include_router(attachments_router)
app.include_router(voice_router)


@app.on_event("startup")
def warm_models() -> None:
    """
    Load the heavy models in the background as soon as the server starts,
    so the first voice note or search doesn't wait for them. Runs in a
    thread so startup itself isn't delayed; failures are harmless — the
    model simply loads on first use instead.
    """

    def _warm() -> None:
        try:
            from app.services.voice_service import _model

            _model()
        except Exception:
            pass
        try:
            from app.ai import get_provider

            get_provider().embed("warm up")
        except Exception:
            pass

    threading.Thread(target=_warm, daemon=True).start()


@app.get("/")
def read_root():
    return {
        "app": "AI Work Memory — My Second Brain",
        "status": "running",
        "phase": 9,
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