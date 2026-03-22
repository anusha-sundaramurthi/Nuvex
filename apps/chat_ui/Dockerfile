FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Copy workspace root files for dependency resolution
COPY pyproject.toml uv.lock ./

# Copy package files and source
COPY apps/chat_ui ./apps/chat_ui

ENV UV_COMPILE_BYTECODE=1

# Install dependencies without cache mount (Railway compatible)
RUN uv sync --frozen --no-dev --package chat_ui

ENV PYTHONOPTIMIZE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/apps/chat_ui/src:$PYTHONPATH"

RUN addgroup --system app && \
    adduser --system --ingroup app app && \
    chown -R app:app /app

USER app

EXPOSE 8501

WORKDIR /app/apps/chat_ui/src

CMD ["streamlit", "run", "chat_ui/app.py", "--server.port=8501", "--server.address=0.0.0.0"]