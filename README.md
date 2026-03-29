# React Go Admin

一个基于 Go + Gin + GORM + React + Vite 的后台管理系统。

## Overview
- Backend: Go 1.26+, Gin, GORM, slog
- Frontend: React 19, Vite 8, shadcn/ui
- Database: SQLite (default), MySQL, PostgreSQL
- Runtime model: backend starts from `app/main.go`, and startup can auto-run migration + seed

## Project Layout

```text
.
├── app/
│   ├── main.go
│   └── internal/
│       ├── catalog/
│       ├── config/
│       ├── core/
│       ├── http/router/
│       ├── migrate/
│       ├── modules/
│       ├── platform/
│       └── seed/
├── web/
├── deploy/
├── go.mod
└── .env.example
```

## Local Development

### 1) Prerequisites
- Go 1.26+
- Node.js 18.8+
- pnpm

### 2) Environment

```bash
cp .env.example .env
```

PowerShell:

```powershell
Copy-Item .env.example .env
```

### 3) Start Backend

```bash
go mod download
go run ./app
```

Default startup behavior:
- auto-apply schema migration
- auto-seed baseline data (roles/admin/default permissions/API catalog)

Disable startup bootstrap:

```bash
DISABLE_AUTO_MIGRATE=true go run ./app
```

PowerShell:

```powershell
$env:DISABLE_AUTO_MIGRATE = "true"
go run ./app
```

### 4) Start Frontend

```bash
cd web
pnpm install
pnpm dev
```

## Endpoints
- API: `http://127.0.0.1:9999`
- Health: `http://127.0.0.1:9999/health`
- Frontend dev: `http://127.0.0.1:5173`

## Testing

Backend:

```bash
go test ./...
```

Frontend:

```bash
cd web
pnpm lint
pnpm build
```

## Docker Deployment

Deployment files:
- `deploy/.env.example`
- `deploy/docker-compose.yml`
- `deploy/install.sh`

Quick start:

```bash
cd deploy
cp .env.example .env
chmod +x install.sh
./install.sh install
```

Useful commands:

```bash
./install.sh upgrade
./install.sh status
./install.sh logs
./install.sh down
```

## License
[MIT](./LICENSE)
