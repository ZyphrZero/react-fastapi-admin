# Repository Guidelines

## Project Structure & Module Organization
`app/` contains the FastAPI backend. Keep HTTP routes in `app/api/v1/`, business logic in `app/controllers/`, ORM models in `app/models/`, schemas in `app/schemas/`, and framework setup in `app/core/` and `app/settings/`. Backend checks live in `app/tests/`.

`migrations/` stores committed Aerich schema history. Treat `migrations/models/*.py` as version-controlled application code, not disposable local artifacts.

`web/` contains the Vite + React frontend. Use `web/src/api/` for API clients, `web/src/components/` for reusable UI, `web/src/pages/` for routed screens, `web/src/router/` for navigation, and `web/src/utils/` or `web/src/hooks/` for shared code. Static files belong in `web/public/` or `web/src/assets/`. Entrypoints are `app/cli.py` for backend operations, `app/asgi.py` for the ASGI app, and `web/src/main.jsx` for the client.

## Build, Test, and Development Commands
Backend:
- `uv sync` installs Python dependencies, including `pytest`.
- `uv run python -m app bootstrap` applies committed migrations, seeds baseline data, and refreshes API metadata for a fresh environment.
- `uv run python -m app db upgrade` applies committed schema migrations only.
- `uv run python -m app serve` starts Granian/FastAPI on `http://localhost:9999`.

Frontend:
- `cd web && pnpm install` installs the UI dependencies.
- `cd web && pnpm dev` starts the Vite dev server.
- `cd web && pnpm build` creates the production bundle.
- `cd web && pnpm lint` runs ESLint.

Testing:
- `uv run python -m pytest app/tests` runs the backend test suite.
- `uv run python -m pytest app/tests/test_log_system.py` runs the log-system regression checks only.

## Coding Style & Naming Conventions
Python uses 4-space indentation and the repo is configured for Black, Ruff, and isort with a 120-character line length. Prefer `snake_case` for modules, functions, and variables. Keep route, controller, and schema names aligned by feature.

When changing Tortoise models in `app/models/`, generate and commit the matching Aerich migration in `migrations/models/` as part of the same change. Do not rely on local auto-created databases or uncommitted migration state.

React code uses ES modules, functional components, 2-space indentation, and no semicolons in existing files. Use `PascalCase` for components and page folders such as `UserManagement/`, `camelCase` for hooks and utilities, and `index.jsx` as the feature entry file when a folder groups related code.

## Testing Guidelines
Automated coverage is currently light: there is no configured frontend test runner or coverage threshold. Add backend tests under `app/tests/test_*.py`, keep them deterministic, and write them in `pytest`-compatible style so they run under `uv run python -m pytest app/tests`. For schema changes, verify the generated migration and run at least `uv run python -m app db upgrade` against a local database before opening a PR. For UI work, run at minimum `pnpm lint` and `pnpm build`.

## Commit & Pull Request Guidelines
Use English Conventional Commit messages with an emoji prefix. Preferred format is `<emoji> <type>(<scope>): <imperative summary>`, for example `🍒 feat(core): add bootstrap runtime`, `♻️ refactor(auth): simplify session flow`, and `📦 build(deps): update vite vendor split`.

Keep the `type` lowercase, make the `scope` short and lowercase when used, and write the summary in English imperative mood.

PRs should explain the change, note any migration or `.env` impact, link related issues, and include screenshots for UI updates. Review generated migrations before committing them, and prefer adding a new migration over rewriting migration history that may already have been applied elsewhere.

## Security & Configuration Tips
Copy `.env.example` to `.env` for local setup. Do not commit secrets, local database files, or temporary caches. Commit Aerich migration files, but keep local SQLite database artifacts such as `db.sqlite3` out of version control. The initial admin account is controlled by `INITIAL_ADMIN_USERNAME` and `INITIAL_ADMIN_PASSWORD`; if the password is left blank, first bootstrap generates a one-time password that should be rotated outside development.
