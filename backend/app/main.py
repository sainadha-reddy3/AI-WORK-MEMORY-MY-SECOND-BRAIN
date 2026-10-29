"""
AI Work Memory — backend entry point.
"""

import threading

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.ask import router as ask_router
from app.api.attachments import router as attachments_router
from app.api.auth import router as auth_router
from app.api.memories import router as memories_router
from app.api.topics import router as topics_router
from app.api.voice import router as voice_router
from app.core.config import settings
from app.core.security import SESSION_COOKIE, is_valid_session
from app.db.session import get_db

app = FastAPI(
    title="AI Work Memory",
    description="Personal long-term work memory system.",
    version="0.1.0",
)

# The frontend reaches the backend through the Next.js proxy (same
# origin), so this mainly matters for direct API testing.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Everything requires login except these.
PUBLIC_PATHS = {"/", "/health", "/health/db", "/auth/login", "/auth/logout", "/auth/me"}


@app.middleware("http")
async def require_login(request: Request, call_next):
    """Refuse every request without a valid session cookie."""
    if request.method == "OPTIONS" or request.url.path in PUBLIC_PATHS:
        return await call_next(request)
    if not is_valid_session(request.cookies.get(SESSION_COOKIE), settings.session_secret):
        return JSONResponse({"detail": "Not logged in."}, status_code=401)
    return await call_next(request)


app.include_router(auth_router)
app.include_router(memories_router)
app.include_router(ask_router)
app.include_router(topics_router)
app.include_router(attachments_router)
app.include_router(voice_router)


@app.on_event("startup")
def warm_models() -> None:
    """Load the heavy models in the background so the first request doesn't wait."""

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
    return {"app": "AI Work Memory — My Second Brain", "status": "running", "phase": 17}


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