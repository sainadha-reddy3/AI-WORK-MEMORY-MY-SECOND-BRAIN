"""
AI Work Memory — backend entry point.

This file creates the FastAPI application and defines the first
two endpoints. Everything else in the backend will eventually be
wired into the `app` object created here.
"""

from fastapi import FastAPI

app = FastAPI(
    title="AI Work Memory",
    description="Personal long-term work memory system.",
    version="0.1.0",
)


@app.get("/")
def read_root():
    """A friendly hello, so we can confirm the server is reachable."""
    return {
        "app": "AI Work Memory — My Second Brain",
        "status": "running",
        "phase": 1,
    }


@app.get("/health")
def health_check():
    """
    A health endpoint. Later, Docker and the frontend will call this
    to check whether the backend is alive before doing real work.
    """
    return {"status": "ok"}