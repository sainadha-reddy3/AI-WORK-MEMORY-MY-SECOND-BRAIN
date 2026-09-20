"""
Application settings.

Every environment variable the app needs is read here and nowhere
else. That way there is a single place to look when something is
misconfigured, and no secret is ever hardcoded in the codebase.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Read from the DATABASE_URL environment variable.
    database_url: str

    environment: str = "development"

    class Config:
        case_sensitive = False


# Created once, imported everywhere.
settings = Settings()