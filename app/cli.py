from __future__ import annotations

import argparse
import asyncio
from collections.abc import Awaitable, Callable, Sequence

from granian import Granian

from app.core.bootstrap import bootstrap_database, refresh_api_metadata, seed_base_data, sync_default_role_permissions
from app.core.db_runtime import DatabaseRuntime
from app.settings import settings
from app.settings.reload_config import RELOAD_CONFIG
from app.utils.log_control import init_logging, logger


AsyncOperation = Callable[[], Awaitable[None]]


async def run_with_database_context(operation: AsyncOperation) -> None:
    runtime = DatabaseRuntime()
    await runtime.initialize()

    try:
        async with runtime.activate():
            await operation()
    finally:
        await runtime.close()


def serve() -> None:
    Granian(
        "app.asgi:app",
        interface="asgi",
        address=settings.HOST,
        port=settings.PORT,
        reload=settings.server_reload_enabled,
        **RELOAD_CONFIG,
    ).serve()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Project operations entrypoint")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("serve", help="Start the ASGI service")

    db_parser = subparsers.add_parser("db", help="Database and metadata operations")
    db_subparsers = db_parser.add_subparsers(dest="db_command", required=True)
    db_subparsers.add_parser("upgrade", help="Apply committed database migrations")
    db_subparsers.add_parser("seed", help="Seed default roles, admin user, and baseline permissions")
    db_subparsers.add_parser("sync", help="Sync API catalog from declared application routes")

    subparsers.add_parser("bootstrap", help="Apply migrations, seed baseline data, and refresh API catalog")
    return parser


async def seed_application_data() -> None:
    await seed_base_data()
    await sync_default_role_permissions()


async def bootstrap_application_data() -> None:
    await seed_base_data()
    await refresh_api_metadata()
    await sync_default_role_permissions()


async def execute_async_command(args: argparse.Namespace) -> int:
    init_logging()
    command_label = args.command if args.command != "db" else f"db {args.db_command}"

    try:
        if args.command == "db" and args.db_command == "upgrade":
            await bootstrap_database()
        elif args.command == "db" and args.db_command == "seed":
            await run_with_database_context(seed_application_data)
        elif args.command == "db" and args.db_command == "sync":
            await run_with_database_context(refresh_api_metadata)
        elif args.command == "bootstrap":
            await bootstrap_database()
            await run_with_database_context(bootstrap_application_data)
        else:
            raise ValueError(f"不支持的命令: {command_label}")
    except Exception:
        logger.exception(f"运维命令执行失败: {command_label}")
        return 1

    logger.info(f"运维命令执行完成: {command_label}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "serve":
        serve()
        return 0

    return asyncio.run(execute_async_command(args))


__all__ = ["build_parser", "main", "serve"]
