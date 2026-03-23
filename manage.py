#!/usr/bin/env python

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Awaitable, Callable

from app import create_app
from app.core.bootstrap import (
    bootstrap_application,
    bootstrap_database,
    refresh_api_metadata,
    seed_base_data,
    sync_default_role_permissions,
)
from app.core.db_runtime import DatabaseRuntime
from app.utils.log_control import init_logging, logger


AsyncCommand = Callable[[], Awaitable[None]]


async def run_command(command: AsyncCommand) -> None:
    init_logging()
    runtime = DatabaseRuntime()
    await runtime.initialize()

    try:
        async with runtime.activate():
            await command()
    finally:
        await runtime.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Project operations entrypoint")
    subparsers = parser.add_subparsers(dest="command", required=True)

    bootstrap_parser = subparsers.add_parser("bootstrap", help="Initialize database, seed base data, and sync API catalog")
    bootstrap_parser.add_argument(
        "--skip-migrations",
        action="store_true",
        help="Skip migration upgrade and only ensure database initialization",
    )

    migrate_parser = subparsers.add_parser("migrate", help="Initialize database and apply migrations")
    migrate_parser.add_argument(
        "--init-only",
        action="store_true",
        help="Only ensure database initialization without applying migration upgrade",
    )

    subparsers.add_parser("seed", help="Seed roles, bootstrap admin user, and default permissions")
    subparsers.add_parser("refresh-api", help="Refresh API catalog from the current application routes")
    return parser


async def main_async() -> int:
    parser = build_parser()
    args = parser.parse_args()

    app = create_app()

    command_map: dict[str, AsyncCommand] = {
        "bootstrap": lambda: bootstrap_application(
            app.routes
        )
        if not args.skip_migrations
        else _bootstrap_without_migrations(app.routes),
        "migrate": lambda: bootstrap_database(run_migrations=not args.init_only),
        "seed": _seed_only,
        "refresh-api": lambda: refresh_api_metadata(app.routes),
    }

    try:
        await run_command(command_map[args.command])
    except Exception:
        logger.exception(f"运维命令执行失败: {args.command}")
        return 1

    logger.info(f"运维命令执行完成: {args.command}")
    return 0


async def _bootstrap_without_migrations(routes: list[object]) -> None:
    await bootstrap_database(run_migrations=False)
    await seed_base_data()
    await refresh_api_metadata(routes)
    await sync_default_role_permissions()


async def _seed_only() -> None:
    await seed_base_data()
    await sync_default_role_permissions()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main_async()))
