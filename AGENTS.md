# Repository Guidelines

## Project Structure & Module Organization
`app/` contains the FastAPI backend. Keep HTTP routes in `app/api/v1/`, business logic in `app/controllers/`, ORM models in `app/models/`, schemas in `app/schemas/`, and framework setup in `app/core/` and `app/settings/`. Backend checks live in `app/tests/`.

`web/` contains the Vite + React frontend. Use `web/src/api/` for API clients, `web/src/components/` for reusable UI, `web/src/pages/` for routed screens, `web/src/router/` for navigation, and `web/src/utils/` or `web/src/hooks/` for shared code. Static files belong in `web/public/` or `web/src/assets/`. Entrypoints are `app/cli.py` for backend operations, `app/asgi.py` for the ASGI app, and `web/src/main.jsx` for the client.

## Build, Test, and Development Commands
Backend:
- `uv sync` installs Python dependencies, including `pytest`.
- `python -m app serve` starts Granian/FastAPI on `http://localhost:9999`.
- `python -m app db upgrade` applies committed schema migrations.

Frontend:
- `cd web && pnpm install` installs the UI dependencies.
- `cd web && pnpm dev` starts the Vite dev server.
- `cd web && pnpm build` creates the production bundle.
- `cd web && pnpm lint` runs ESLint.

Testing:
- `uv run pytest app/tests` runs the backend test suite.
- `uv run pytest app/tests/test_log_system.py` runs the log-system regression checks only.

## Coding Style & Naming Conventions
Python uses 4-space indentation and the repo is configured for Black, Ruff, and isort with a 120-character line length. Prefer `snake_case` for modules, functions, and variables. Keep route, controller, and schema names aligned by feature.

React code uses ES modules, functional components, 2-space indentation, and no semicolons in existing files. Use `PascalCase` for components and page folders such as `UserManagement/`, `camelCase` for hooks and utilities, and `index.jsx` as the feature entry file when a folder groups related code.

## Testing Guidelines
Automated coverage is currently light: there is no configured frontend test runner or coverage threshold. Add backend tests under `app/tests/test_*.py`, keep them deterministic, and write them in `pytest`-compatible style so they run under `uv run pytest app/tests`. For UI work, run at minimum `pnpm lint` and `pnpm build` before opening a PR.

## Commit & Pull Request Guidelines
Use English Conventional Commit messages with an emoji prefix. Preferred format is `<emoji> <type>(<scope>): <imperative summary>`, for example `🍒 feat(core): add bootstrap runtime`, `♻️ refactor(auth): simplify session flow`, and `📦 build(deps): update vite vendor split`.

Keep the `type` lowercase, make the `scope` short and lowercase when used, and write the summary in English imperative mood.

PRs should explain the change, note any migration or `.env` impact, link related issues, and include screenshots for UI updates. Review generated migrations before committing them.

## Security & Configuration Tips
Copy `.env.example` to `.env` for local setup. Do not commit secrets, local database files, or temporary caches. The seeded admin account (`admin` / `Admin123!@#`) is for local bootstrap only and should be changed outside development.
