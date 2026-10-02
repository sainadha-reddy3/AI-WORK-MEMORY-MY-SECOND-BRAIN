FROM python:3.12-slim

WORKDIR /app

# ---- Layer 0: system packages (almost never change) ----
# Tesseract OCR with English, Telugu and Hindi language data.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      tesseract-ocr tesseract-ocr-eng tesseract-ocr-tel tesseract-ocr-hin \
 && rm -rf /var/lib/apt/lists/*

# ---- Layer 1: heavy ML dependencies (rarely change) ----
# CPU-only PyTorch: there is no GPU here, and the default build pulls
# several GB of CUDA libraries that would never be used.
COPY requirements-ml.txt .
RUN pip install --no-cache-dir torch==2.4.1 --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r requirements-ml.txt

# Previous English-only embedding model, kept so this layer stays
# cached. Safe to remove in a later clean-up.
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# ---- Layer 1b: speech-to-text (rarely changes) ----
COPY requirements-voice.txt .
RUN pip install --no-cache-dir -r requirements-voice.txt
RUN python -c "from faster_whisper import WhisperModel; \
    WhisperModel('small', device='cpu', compute_type='int8')"

# ---- Layer 1c: multilingual embeddings ----
# Understands Telugu and Hindi as well as English, so a question in one
# language can find a memory written in another. Baked in so search
# works offline on any machine.
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('intfloat/multilingual-e5-small')"

# ---- Layer 2: application dependencies (change often) ----
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]