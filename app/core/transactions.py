from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from tortoise.context import require_context
from tortoise.transactions import in_transaction


@asynccontextmanager
async def managed_transaction() -> AsyncIterator[None]:
    """
    在存在数据库上下文时启用事务。

    单元测试中大量使用仓库 mock，不会初始化 TortoiseContext；
    这种情况下退化为 no-op，避免把纯业务测试强行绑定到数据库。
    """
    try:
        require_context()
    except RuntimeError:
        yield
        return

    async with in_transaction():
        yield
