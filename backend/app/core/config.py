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

    # Your local timezone. Decides what "today" and "yesterday" mean,
    # and which day a memory is dated. The server clock runs on UTC.
    timezone: str = "Asia/Kolkata"

    # --- AI provider ------------------------------------------
    # Which provider to use: "local", "ollama" or "mock".
    # Kept in config so switching providers never means a code change.
    ai_provider: str = "local"

    # Used only when ai_provider is "ollama".
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    ollama_embed_model: str = "nomic-embed-text"

    # --- Embeddings & search ----------------------------------
    # Multilingual: understands Telugu and Hindi as well as English,
    # so a question in one language can find a memory in another.
    # Must also be pre-downloaded in the Dockerfile.
    embedding_model: str = "intfloat/multilingual-e5-small"

    # Below this similarity a semantic match is treated as noise.
    # Depends on the embedding model — re-tune it whenever the model
    # changes. A wrong memory is worse than no memory.
    semantic_threshold: float = 0.82
    # --- File storage -----------------------------------------
    # Where original files (screenshots, documents, notebook photos,
    # voice recordings) are kept. Mounted from ./storage on the host,
    # which is gitignored — personal files never enter Git.
    storage_dir: str = "/app/storage"

    # --- OCR --------------------------------------------------
    # Tesseract languages. "eng" is fastest and most accurate for
    # screenshots; use "eng+tel+hin" for printed Telugu/Hindi.
    ocr_langs: str = "eng"

    # --- Voice ------------------------------------------------
    # Whisper model for speech-to-text. "small" handles Telugu and
    # Hindi far better than "base". Must also be pre-downloaded in
    # the Dockerfile.
    whisper_model: str = "small"

    class Config:
        case_sensitive = False


# Created once, imported everywhere.
settings = Settings()