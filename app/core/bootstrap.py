from __future__ import annotations

import asyncio
from pathlib import Path

from aerich import Command
from tortoise.context import require_context

from app.controllers.api import api_controller
from app.controllers.user import UserCreate, user_controller
from app.models.admin import Role, User
from app.settings import settings
from app.utils.log_control import logger


async def ensure_database_connection() -> None:
    """确保当前执行流已经显式绑定数据库上下文。"""
    context = require_context()
    if not context.inited:
        raise RuntimeError("数据库上下文未初始化")


async def bootstrap_database() -> None:
    """
    初始化数据库连接，并按配置选择是否应用现有迁移。

    框架启动阶段只做安全的表初始化与迁移升级，不在运行时生成迁移文件。
    """
    await ensure_database_connection()

    if not settings.AUTO_BOOTSTRAP:
        logger.info("已关闭启动数据库自举，仅保留连接初始化")
        return

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

    if not settings.should_run_migrations_on_startup:
        logger.info("已跳过启动迁移升级，当前为显式迁移模式")
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
    if await user_controller.model.exists():
        return None

    if settings.is_production and settings.INITIAL_ADMIN_PASSWORD == "123456":
        logger.warning("生产环境仍在使用默认管理员密码，请尽快通过环境变量覆盖 INITIAL_ADMIN_PASSWORD")

    admin_user = await user_controller.create_user(
        UserCreate(
            username=settings.INITIAL_ADMIN_USERNAME,
            email=settings.INITIAL_ADMIN_EMAIL,
            nickname=settings.INITIAL_ADMIN_NICKNAME,
            phone=None,
            password=settings.INITIAL_ADMIN_PASSWORD,
            is_active=True,
            is_superuser=True,
        )
    )
    logger.info(f"已初始化管理员账户: {admin_user.username}")
    return admin_user


async def init_roles() -> tuple[Role | None, Role | None]:
    if await Role.exists():
        return None, None

    admin_role = await Role.create(name="管理员", desc="管理员角色")
    user_role = await Role.create(name="普通用户", desc="普通用户角色")
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


async def refresh_api_metadata() -> None:
    has_api_metadata = await api_controller.model.exists()
    if has_api_metadata and not settings.should_refresh_api_metadata_on_startup:
        return

    if settings.should_refresh_api_metadata_on_startup or not has_api_metadata:
        await api_controller.refresh_api()
        logger.info("已刷新 API 元数据")


async def seed_base_data() -> None:
    if not settings.should_seed_base_data_on_startup:
        logger.info("已跳过基础数据初始化")
        return

    await init_roles()
    await init_superuser()
    await init_user_roles()


async def bootstrap_application() -> None:
    await bootstrap_database()
    await seed_base_data()
    await refresh_api_metadata()
