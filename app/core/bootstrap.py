from __future__ import annotations

import asyncio
import sys
from collections.abc import Iterable
from pathlib import Path

from aerich import Command
from tortoise.context import require_context

from app.core.navigation import get_default_role_menu_paths
from app.repositories import role_repository, user_repository
from app.models.admin import Api, Role, User
from app.services.api_admin_service import api_admin_service
from app.settings import settings
from app.utils.log_control import logger
from app.utils.password import generate_bootstrap_admin_password, get_password_hash, validate_password_strength


async def ensure_database_connection() -> None:
    """确保当前执行流已经显式绑定数据库上下文。"""
    context = require_context()
    if not context.inited:
        raise RuntimeError("数据库上下文未初始化")


async def bootstrap_database(*, run_migrations: bool = True) -> None:
    """
    初始化数据库连接，并按显式命令选择是否应用现有迁移。

    该函数由显式运维命令调用，不再由 Web 服务启动隐式触发。
    """
    await ensure_database_connection()

    command = Command(tortoise_config=settings.tortoise_orm)
    migrations_dir = Path(settings.BASE_DIR) / "migrations" / "models"
    has_migration_files = migrations_dir.exists() and any(migrations_dir.glob("*.py"))

    if not has_migration_files:
        try:
            await asyncio.shield(command.init_db(safe=True))
            logger.info("已初始化数据库结构与初始迁移")
        except FileExistsError as exc:
            logger.warning(f"检测到已存在的迁移文件，跳过初始化: {exc}")
            has_migration_files = True
        except Exception as exc:
            logger.error(f"数据库初始化失败: {exc}")
            return

    if not run_migrations:
        logger.info("已跳过迁移升级，仅完成数据库初始化检查")
        return

    if not has_migration_files:
        logger.info("当前没有可升级的迁移文件")
        return

    try:
        await command.init()
        upgraded = await asyncio.shield(command.upgrade(run_in_transaction=True))
        if upgraded:
            logger.info(f"已应用数据库迁移: {upgraded}")
        else:
            logger.info("数据库迁移已是最新状态")
    except FileNotFoundError:
        logger.warning("迁移文件不存在，已跳过自动升级")
    except Exception as exc:
        logger.error(f"数据库升级失败: {exc}")


async def init_superuser() -> User | None:
    if await user_repository.exists_any():
        return None

    initial_password = settings.INITIAL_ADMIN_PASSWORD.strip()
    generated_password: str | None = None

    if initial_password:
        is_valid, message = validate_password_strength(initial_password)
        if not is_valid:
            raise RuntimeError(f"INITIAL_ADMIN_PASSWORD 不符合密码策略: {message}")
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

    logger.info(f"已初始化管理员账户: {admin_user.username}")
    if generated_password is not None:
        emit_bootstrap_admin_password(admin_user.username, generated_password)
    return admin_user


def emit_bootstrap_admin_password(username: str, password: str) -> None:
    logger.warning("首次引导已自动生成超级管理员密码，请从当前启动控制台复制该一次性密码并立即修改。")
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
    logger.info("已初始化默认角色")
    return admin_role, user_role


async def init_user_roles() -> None:
    """确保超级管理员持有默认管理员角色。"""
    admin_role = await Role.filter(name="管理员").first()
    if not admin_role:
        logger.warning("未找到管理员角色，跳过角色分配")
        return

    admin_user = await User.filter(username=settings.INITIAL_ADMIN_USERNAME, is_superuser=True).first()
    if not admin_user:
        logger.warning("未找到超级管理员用户，跳过角色分配")
        return

    user_roles = await admin_user.roles.all()
    admin_role_assigned = any(role.name == "管理员" for role in user_roles)
    if admin_role_assigned:
        return

    await admin_user.roles.add(admin_role)
    logger.info("已为超级管理员分配管理员角色")


async def refresh_api_metadata(routes: Iterable[object]) -> None:
    await api_admin_service.refresh_api_catalog(routes)
    logger.info("已刷新 API 元数据")


async def sync_default_role_permissions() -> None:
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
            logger.info(f"已初始化角色默认权限: {role_name}")


async def seed_base_data() -> None:
    await init_roles()
    await init_superuser()
    await init_user_roles()


async def bootstrap_application(routes: Iterable[object]) -> None:
    await bootstrap_database()
    await seed_base_data()
    await refresh_api_metadata(routes)
    await sync_default_role_permissions()
