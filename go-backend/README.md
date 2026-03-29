# Go Backend Migration

This directory contains the Go replacement for the current FastAPI backend.

Current scope:

- Gin HTTP server on `/api/v1`
- Shared config loading from the repository `.env`
- Go-native schema migrations, seed flow, and API catalog sync
- JWT access/refresh token support
- Migrated modules: `base`, `users`, `roles`, `apis`, `system_settings`, `auditlog`

Recommended migration defaults used in this branch:

- Router: `gin`
- Persistence: `gorm`
- Logging: `slog` + `lumberjack`
- CLI: `cobra`
- Toolchain: `go1.26.1`

Entrypoints:

```bash
cd go-backend
C:\Program Files\Go\bin\go.exe run ./cmd/migrate
C:\Program Files\Go\bin\go.exe run ./cmd/seed
C:\Program Files\Go\bin\go.exe run ./cmd/catalog-sync
C:\Program Files\Go\bin\go.exe run ./cmd/server
```

Recommended workflow for a fresh Go-only environment:

```bash
cd go-backend
C:\Program Files\Go\bin\go.exe run ./cmd/migrate
C:\Program Files\Go\bin\go.exe run ./cmd/seed
C:\Program Files\Go\bin\go.exe run ./cmd/server
```

Notes:

- `cmd/migrate` applies schema by default; use `-status` or `-down -steps N` for inspection or rollback
- `seed` creates default roles, the bootstrap admin, and baseline permissions
- `catalog sync` refreshes API metadata without needing the Python backend
