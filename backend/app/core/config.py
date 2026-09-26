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

    # --- AI provider ------------------------------------------
    # Which provider to use: "local", "ollama" or "mock".
    # Kept in config so switching providers never means a code change.
    ai_provider: str = "local"

    # Used only when ai_provider is "ollama".
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    ollama_embed_model: str = "nomic-embed-text"

    # --- File storage -----------------------------------------
    # Where original files (screenshots, documents, notebook photos)
    # are kept. Mounted from ./storage on the host, which is
    # gitignored — personal files never enter Git.
    storage_dir: str = "/app/storage"

    class Config:
        case_sensitive = False


# Created once, imported everywhere.
settings = Settings()