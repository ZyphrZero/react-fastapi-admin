from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from tortoise import Tortoise
from tortoise.transactions import in_transaction

from app.settings.config import settings


@asynccontextmanager
async def managed_transaction() -> AsyncIterator[None]:
    """
    Enable a transaction when a database context exists.

    Unit tests often use repository mocks and do not initialize Tortoise.
    In that case this degrades to a no-op so pure business tests are not forced to depend on the database.
    """
    if not getattr(Tortoise, "_inited", False):
        yield
        return

    # 项目 tortoise 配置恒同时注册 sqlite/mysql 双引擎条目（config.tortoise_orm），
    # in_transaction() 不带连接名时遇多连接抛 ParamsError，这里显式绑定配置声明的默认连接
    async with in_transaction(connection_name=settings.DB_CONNECTION):
        yield
