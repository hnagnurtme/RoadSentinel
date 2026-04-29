# ── Build args ───────────────────────────────────────────────────────────────
# WITH_AI=false  → lightweight API-only image (~150 MB) — used in CI/CD
# WITH_AI=true   → full AI image with torch/ultralytics (~2.8 GB)
ARG WITH_AI=false

# ── Stage 1: builder ─────────────────────────────────────────────────────────
FROM python:3.13-slim AS builder

ARG WITH_AI

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-api.txt requirements-ai.txt ./

# Always install API deps; conditionally add AI deps
RUN pip install --upgrade pip setuptools wheel \
    && pip install --prefix=/install -r requirements-api.txt \
    && if [ "$WITH_AI" = "true" ]; then \
         pip install --prefix=/install -r requirements-ai.txt; \
       fi

# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.13-slim AS runtime

ARG WITH_AI
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    # Expose whether AI is baked in (app reads _AI_AVAILABLE at import time)
    WITH_AI=${WITH_AI}

WORKDIR /app

# Minimal runtime system libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY . .

# Non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
