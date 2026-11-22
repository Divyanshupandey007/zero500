# syntax=docker/dockerfile:1
# Stage 1: builder — install runtime deps into an isolated venv/wheelhouse.
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VENV_PATH=/opt/venv

WORKDIR /app

# System deps needed to build psycopg/pgvector wheels.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create and populate a venv so the final image can copy just the runtime.
RUN python -m venv ${VENV_PATH}
ENV PATH="${VENV_PATH}/bin:${PATH}"

COPY backend/requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Stage 2: final — slim runtime image, non-root user, uvicorn entrypoint.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}" \
    VENV_PATH=/opt/venv

WORKDIR /app

# Only the runtime libraries from the builder stage.
COPY --from=builder ${VENV_PATH} ${VENV_PATH}

# Application code.
COPY backend/ ./

# Non-root user for the runtime.
RUN useradd --create-home --shell /bin/bash zero500 && \
    chown -R zero500:zero500 /app
USER zero500

# Configuration + secrets are read from the environment at runtime.
ENV DATABASE_URL="" \
    GEMINI_API_KEY="" \
    GEMINI_MODEL="gemini-3.5-flash" \
    EMBEDDING_MODEL="gemini-embedding-001" \
    EMBEDDING_DIMENSIONS="768" \
    ALLOWED_ORIGINS="http://localhost:4200,http://127.0.0.1:4200" \
    PORT="8000"

EXPOSE ${PORT}

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
