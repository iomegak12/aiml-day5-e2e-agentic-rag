# syntax=docker/dockerfile:1
# NetCore Agentic RAG API - multi-stage, slim, non-root. Builds with Docker or Podman:
#   docker build -f Containerfile -t localhost/netcore-rag-api:0.10.0 .
#   podman build -f Containerfile --format docker -t localhost/netcore-rag-api:0.10.0 .   (keeps HEALTHCHECK)

# ---------- 1. builder: resolve and install dependencies with uv ----------
FROM docker.io/library/python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.9.16 /uv /bin/uv
# binutils (strip) is needed only in this stage
RUN apt-get update && apt-get install -y --no-install-recommends binutils && rm -rf /var/lib/apt/lists/*

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app
COPY pyproject.toml uv.lock ./
# runtime dependencies only (no dev / kb groups), from the lock file
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-default-groups --no-install-project
# slim the venv: drop bundled test suites and type stubs, strip debug symbols from native libraries
RUN find /app/.venv/lib/python3.12/site-packages -mindepth 2 -type d -name tests -prune -exec rm -rf {} + \
    && find /app/.venv -name "*.pyi" -delete \
    && find /app/.venv -type f -name "*.so*" -exec strip --strip-debug {} + 2>/dev/null; \
    du -sh /app/.venv

# ---------- 2. runtime: python slim + the venv + the code ----------
FROM docker.io/library/python:3.12-slim AS runtime

ENV PATH=/app/.venv/bin:$PATH \
    PYTHONPATH=/app/scripts:/app/api \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    API_PORT=8080

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /app --shell /usr/sbin/nologin app

WORKDIR /app
COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app scripts/ /app/scripts/
COPY --chown=app:app api/ /app/api/
RUN mkdir -p /app/logs && chown app:app /app/logs

USER app
EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3)"]

# apply DB migrations, then serve (single worker: agent runs use threads; see TROUBLESHOOTING for scaling)
CMD ["sh", "-c", "alembic -c api/alembic.ini upgrade head && exec uvicorn app.main:create_app --factory --app-dir api --host 0.0.0.0 --port 8080 --proxy-headers --no-access-log"]
