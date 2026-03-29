FROM node:20-alpine AS frontend-builder

WORKDIR /build/web

COPY web/package.json web/pnpm-lock.yaml ./

RUN corepack enable \
    && pnpm install --frozen-lockfile

COPY web ./

RUN pnpm build

FROM golang:1.26 AS backend-builder

WORKDIR /build

COPY go.mod go.sum ./

RUN go mod download

COPY app ./app
COPY .env.example ./.env.example

RUN CGO_ENABLED=1 GOOS=linux GOARCH=amd64 go build -trimpath -ldflags "-s -w" -o /out/react-go-admin ./app

FROM debian:bookworm-slim

ENV APP_ENV=prod \
    TZ=Asia/Shanghai \
    HOST=0.0.0.0 \
    PORT=9999

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY --from=backend-builder /out/react-go-admin /app/react-go-admin
COPY --from=frontend-builder /build/web/dist ./web/dist
COPY .env.example ./.env.example

RUN mkdir -p /app/storage /app/logs

EXPOSE 9999

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=5 \
  CMD curl -fsS http://127.0.0.1:9999/health >/dev/null || exit 1

ENTRYPOINT ["/app/react-go-admin"]
