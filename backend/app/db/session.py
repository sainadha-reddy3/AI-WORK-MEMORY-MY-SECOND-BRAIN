"""
Database connection setup.

The engine is created once when the application starts.
Each incoming request gets its own short-lived Session, which is
always closed afterwards — even if the request fails.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

# SQLAlchemy needs the "+psycopg" suffix to know which driver to use.
DATABASE_URL = settings.database_url.replace(
    "postgresql://", "postgresql+psycopg://", 1
)

engine = create_engine(
    DATABASE_URL,
    # Checks a connection is still alive before using it, so a
    # restarted database doesn't leave the app holding dead sockets.
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """All database table classes will inherit from this."""
    pass


def get_db():
    """
    FastAPI dependency. Opens a session, gives it to the endpoint,
    and guarantees it is closed when the request finishes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()