FROM python:3.12-slim

WORKDIR /app

# ---- Layer 1: heavy ML dependencies (rarely change) ----
# CPU-only PyTorch: there is no GPU here, and the default build pulls
# several GB of CUDA libraries that would never be used.
COPY requirements-ml.txt .
RUN pip install --no-cache-dir torch==2.4.1 --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r requirements-ml.txt

# Bake the embedding model into the image so the app works offline
# and needs no setup on a new machine.
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# ---- Layer 2: application dependencies (change often) ----
# Kept separate so adding a small library doesn't reinstall PyTorch.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]