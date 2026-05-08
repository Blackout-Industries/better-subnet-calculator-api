# syntax=docker/dockerfile:1.7

# ---- deps: resolve and install third-party deps into /app/.venv ----
FROM python:3.12-slim AS deps
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
WORKDIR /app
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
COPY pyproject.toml uv.lock* ./
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    uv sync --frozen --no-install-project --no-dev

# ---- dev: source-mounted, hot-reload uvicorn ----
FROM deps AS dev
WORKDIR /app
ENV PATH=/app/.venv/bin:$PATH
COPY . .
EXPOSE 8000
CMD ["uvicorn", "subnet_api.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "src"]

# ---- test: install project + dev deps, run pytest as part of build ----
FROM deps AS test
WORKDIR /app
ENV PATH=/app/.venv/bin:$PATH
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    uv sync --frozen --extra dev
RUN python -m pytest

# ---- build: production install (no dev), source assembled for runtime copy ----
FROM deps AS build
WORKDIR /app
ENV PATH=/app/.venv/bin:$PATH
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    uv sync --frozen --no-dev

# ---- runtime: minimal image, non-root, healthcheck, uvicorn on 8000 ----
FROM python:3.12-slim AS runtime
WORKDIR /app
ENV PATH=/app/.venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd --system --gid 10001 app \
 && useradd  --system --uid 10001 --gid app --home-dir /app --shell /usr/sbin/nologin app
COPY --from=build --chown=app:app /app/.venv /app/.venv
COPY --from=build --chown=app:app /app/src /app/src
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/healthz >/dev/null || exit 1
CMD ["uvicorn", "subnet_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
