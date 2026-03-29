# Repository Guidelines

## Project Structure
- Backend entrypoint: `app/main.go`
- Backend implementation: `app/internal/`
- Frontend implementation: `web/`
- Deployment assets: `deploy/`

Backend package layout:
- `app/internal/http/router/`: Gin route wiring and middleware
- `app/internal/modules/`: feature modules (`users`, `roles`, `apis`, `auditlog`, `upload`, `systemsettings`, `base`)
- `app/internal/platform/`: infrastructure adapters (database, auth, logger, password, response)
- `app/internal/config/`: environment config loading
- `app/internal/migrate/`, `app/internal/seed/`, `app/internal/catalog/`: startup migration/seed/catalog flows

Frontend layout:
- `web/src/api/`: API clients
- `web/src/components/`: reusable components
- `web/src/pages/`: routed pages
- `web/src/router/`: route config
- `web/src/utils/`, `web/src/hooks/`: shared utilities and hooks

## Build, Run, and Test
Backend:
- `go mod download`: install backend dependencies
- `go run ./app`: start backend on `http://localhost:9999`
- `go test ./...`: run backend tests

Startup behavior:
- migration + baseline seed run automatically on startup
- set `DISABLE_AUTO_MIGRATE=true` to disable startup bootstrap

Frontend:
- `cd web && pnpm install`
- `cd web && pnpm dev`
- `cd web && pnpm build`
- `cd web && pnpm lint`

## Coding Conventions
Go:
- Run `gofmt` on edited Go files
- Keep executable wiring in `app/main.go`
- Keep domain logic inside `app/internal/*`
- Use lowercase package names and idiomatic Go naming

React:
- Keep existing 2-space indentation and semicolon-free style
- Use `PascalCase` for components/pages
- Use `camelCase` for hooks/utilities

## Testing Guidelines
- Keep tests deterministic and colocated as `*_test.go`
- Before PR, run:
  1. `go test ./...`
  2. `go run ./app` (verify startup bootstrap and health endpoint)
- For UI changes, run `pnpm lint` and `pnpm build` in `web/`

## Commit and PR Guidelines
- Conventional Commit with emoji prefix:
  - `<emoji> <type>(<scope>): <imperative summary>`
  - Example: `🍒 feat(core): simplify startup bootstrap flow`
- PR should include:
  - behavior changes
  - `.env` changes
  - migration/seed impact
  - screenshots for UI changes

## Security and Config
- Copy `.env.example` to `.env` for local setup
- Do not commit secrets or local runtime artifacts (`db.sqlite3`, logs, storage cache)
- Initial admin is controlled by `INITIAL_ADMIN_USERNAME` and `INITIAL_ADMIN_PASSWORD`
- If `INITIAL_ADMIN_PASSWORD` is empty, startup bootstrap generates and logs a one-time password
