"""
Login, logout, and "am I logged in?".

Single user: there is one password, stored only as a hash in .env.
"""

import time

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.security import SESSION_COOKIE, is_valid_session, make_session_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

MAX_FAILURES = 5
LOCKOUT_SECONDS = 300
_failures: list[float] = []  # timestamps of recent wrong attempts


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=200)


@router.post("/login")
def login(data: LoginRequest, response: Response):
    if not settings.auth_password_hash or not settings.session_secret:
        raise HTTPException(
            status_code=503,
            detail="Login isn't set up yet. Run: docker exec -it awm-backend python -m app.tools.set_password",
        )

    now = time.time()
    _failures[:] = [t for t in _failures if now - t < LOCKOUT_SECONDS]
    if len(_failures) >= MAX_FAILURES:
        raise HTTPException(status_code=429, detail="Too many wrong attempts. Wait 5 minutes and try again.")

    if not verify_password(data.password, settings.auth_password_hash):
        _failures.append(now)
        time.sleep(0.5)  # slow down guessing a little more
        raise HTTPException(status_code=401, detail="Wrong password.")

    _failures.clear()
    response.set_cookie(
        SESSION_COOKIE,
        make_session_token(settings.session_secret, settings.session_days),
        max_age=settings.session_days * 86400,
        httponly=True,       # JavaScript can't read it
        samesite="lax",      # other sites can't make your browser send it
        secure=settings.cookie_secure,  # HTTPS-only when deployed
        path="/",
    )
    return {"authenticated": True}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"authenticated": False}


@router.get("/me")
def me(request: Request):
    return {"authenticated": is_valid_session(request.cookies.get(SESSION_COOKIE), settings.session_secret)}