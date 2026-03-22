FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Copy workspace root files for dependency resolution
COPY pyproject.toml uv.lock ./

# Copy package files and source
COPY apps/api ./apps/api

ENV UV_COMPILE_BYTECODE=1

# Install dependencies without cache mount (Railway compatible)
RUN uv sync --frozen --no-dev --package api

ENV PYTHONOPTIMIZE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/apps/api/src:$PYTHONPATH"

RUN addgroup --system app && \
    adduser --system --ingroup app app && \
    chown -R app:app /app

USER app

EXPOSE 8000

WORKDIR /app/apps/api/src

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]