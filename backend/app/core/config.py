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
    # Multilingual: understands Telugu and Hindi as well as English.
    # Must also be pre-downloaded in the Dockerfile.
    embedding_model: str = "intfloat/multilingual-e5-small"

    # Below this similarity a semantic match is treated as noise.
    # Depends on the embedding model — re-tune it whenever the model
    # changes. A wrong memory is worse than no memory.
    semantic_threshold: float = 0.82

    # --- File storage -----------------------------------------
    # Where original files live: "local" (a folder) or "s3" (any
    # S3-compatible service — Neon now, Floci in the lab, AWS later).
    storage_backend: str = "local"

    # Used when storage_backend is "local". Mounted from ./storage,
    # which is gitignored — personal files never enter Git.
    storage_dir: str = "/app/storage"

    # Used when storage_backend is "s3".
    s3_endpoint: str = ""
    s3_bucket: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_region: str = "us-east-1"

    # --- OCR --------------------------------------------------
    # Tesseract languages. "eng" is fastest and most accurate for
    # screenshots; use "eng+tel+hin" for printed Telugu/Hindi.
    ocr_langs: str = "eng"

    # --- Voice ------------------------------------------------
    # Whisper model for speech-to-text. Must also be pre-downloaded in
    # the Dockerfile.
    whisper_model: str = "small"

    class Config:
        case_sensitive = False


# Created once, imported everywhere.
settings = Settings()