# Voice-CRM 后端（CPU 版，适用于 docker compose 全栈部署）
FROM python:3.11-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    libsndfile1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# 先装 CPU 版 PyTorch，减小镜像体积
RUN pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r requirements.txt

COPY agent/ agent/
COPY alembic/ alembic/
COPY alembic.ini .
COPY config.example.yaml .
COPY main_server/ main_server/
COPY scripts/ scripts/
COPY run.py .

RUN mkdir -p main_server/data/knowledge main_server/data/models \
    main_server/data/sqlite main_server/data/chroma main_server/data/logs

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/health || exit 1

CMD ["uvicorn", "main_server.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
