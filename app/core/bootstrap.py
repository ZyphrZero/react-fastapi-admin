from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from aerich import Command
from tortoise.context import require_context

from app.api.catalog import build_api_catalog_route_definitions
from app.core.navigation import get_default_role_menu_paths
from app.repositories import role_repository, user_repository
from app.models.admin import Api, Role, User
from app.services.api_admin_service import api_admin_service
from app.settings import settings
from app.utils.log_control import logger
from app.utils.password import generate_bootstrap_admin_password, get_password_hash, validate_password_strength


async def ensure_database_connection() -> None:
    """Ensure the current execution flow is explicitly bound to a database context."""
    context = require_context()
    if not context.inited:
        raise RuntimeError("Database context is not initialized")


async def bootstrap_database() -> None:
    """
    Apply committed database migrations.
    """
    migrations_dir = Path(settings.BASE_DIR) / "migrations" / "models"
    has_migration_files = migrations_dir.exists() and any(migrations_dir.glob("*.py"))
    if not has_migration_files:
        raise FileNotFoundError(f"Migration directory does not exist or is empty: {migrations_dir}")

    command = Command(tortoise_config=settings.tortoise_orm)
    try:
        await command.init()
        upgraded = await asyncio.shield(command.upgrade(run_in_transaction=True))
        if upgraded:
            logger.info(f"Applied database migrations: {upgraded}")
        else:
            logger.info("Database migrations are already up to date")
    finally:
        await command.close()


async def init_superuser() -> User | None:
    if await user_repository.exists_any():
        return None

    initial_password = settings.INITIAL_ADMIN_PASSWORD.strip()
    generated_password: str | None = None

    if initial_password:
        is_valid, message = validate_password_strength(initial_password)
        if not is_valid:
            raise RuntimeError(f"INITIAL_ADMIN_PASSWORD does not satisfy the password policy: {message}")
    else:
        initial_password = generate_bootstrap_admin_password()
        generated_password = initial_password

    admin_user, created = await User.get_or_create(
        username=settings.INITIAL_ADMIN_USERNAME,
        defaults={
            "email": settings.INITIAL_ADMIN_EMAIL,
            "nickname": settings.INITIAL_ADMIN_NICKNAME,
            "phone": None,
            "password": get_password_hash(initial_password),
            "is_active": True,
            "is_superuser": True,
        },
    )
    if not created:
        return None

    logger.info(f"Initialized admin account: {admin_user.username}")
    if generated_password is not None:
        emit_bootstrap_admin_password(admin_user.username, generated_password)
    return admin_user


def emit_bootstrap_admin_password(username: str, password: str) -> None:
    logger.warning(
        "A bootstrap superuser password was generated automatically. Copy this one-time password from the current "
        "startup console and rotate it immediately."
    )
    print(
        "\n".join(
            [
                "",
                "================ INITIAL ADMIN PASSWORD ================",
                f"username: {username}",
                f"password: {password}",
                "This password is shown only during first bootstrap.",
                "Rotate it immediately after the first login.",
                "========================================================",
                "",
            ]
        ),
        file=sys.stderr,
        flush=True,
    )


async def init_roles() -> tuple[Role | None, Role | None]:
    if await role_repository.exists_any():
        return None, None

    admin_role = await Role.create(
        name="管理员",
        desc="管理员角色",
        menu_paths=get_default_role_menu_paths("管理员"),
        api_ids=[],
    )
    user_role = await Role.create(
        name="普通用户",
        desc="普通用户角色",
        menu_paths=get_default_role_menu_paths("普通用户"),
        api_ids=[],
    )
    logger.info("Initialized default roles")
    return admin_role, user_role


async def init_user_roles() -> None:
    """Ensure the superuser has the default administrator role."""
    admin_role = await Role.filter(name="管理员").first()
    if not admin_role:
        logger.warning("Administrator role not found; skipping role assignment")
        return

    admin_user = await User.filter(username=settings.INITIAL_ADMIN_USERNAME, is_superuser=True).first()
    if not admin_user:
        logger.warning("Superuser not found; skipping role assignment")
        return

    user_roles = await admin_user.roles.all()
    admin_role_assigned = any(role.name == "管理员" for role in user_roles)
    if admin_role_assigned:
        return

    await admin_user.roles.add(admin_role)
    logger.info("Assigned administrator role to superuser")


async def refresh_api_metadata() -> None:
    await ensure_database_connection()
    await api_admin_service.refresh_api_catalog(build_api_catalog_route_definitions())
    logger.info("API metadata refreshed")


async def sync_default_role_permissions() -> None:
    await ensure_database_connection()
    built_in_roles = {
        "管理员": await Role.filter(name="管理员").first(),
        "普通用户": await Role.filter(name="普通用户").first(),
    }
    all_api_ids = list(await Api.all().values_list("id", flat=True))

    for role_name, role in built_in_roles.items():
        if not role:
            continue

        updated_fields: list[str] = []
        current_menu_paths = list(role.menu_paths or [])
        current_api_ids = [int(api_id) for api_id in (role.api_ids or [])]

        if not current_menu_paths:
            role.menu_paths = get_default_role_menu_paths(role_name)
            updated_fields.append("menu_paths")

        if role_name == "管理员" and not current_api_ids:
            role.api_ids = all_api_ids
            updated_fields.append("api_ids")

        if role_name == "普通用户" and role.api_ids is None:
            role.api_ids = []
            updated_fields.append("api_ids")

        if updated_fields:
            updated_fields.append("updated_at")
            await role.save(update_fields=updated_fields)
            logger.info(f"Initialized default role permissions: {role_name}")


async def seed_base_data() -> None:
    await ensure_database_connection()
    await init_roles()
    await init_superuser()
    await init_user_roles()
