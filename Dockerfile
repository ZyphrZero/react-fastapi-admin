FROM node:20-alpine AS frontend-builder

WORKDIR /build/web

COPY web/package.json web/pnpm-lock.yaml ./

RUN corepack enable \
    && pnpm install --frozen-lockfile

COPY web ./

RUN pnpm build

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ENV=prod \
    HOST=0.0.0.0 \
    PORT=9999

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
COPY migrations ./migrations
COPY web/package.json ./web/package.json

RUN python -m pip install --upgrade pip \
    && python -m pip install .

COPY --from=frontend-builder /build/web/dist ./web/dist

RUN mkdir -p /app/storage /app/app/logs

EXPOSE 9999

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9999/health', timeout=3)"

CMD ["python", "-m", "app", "serve"]
