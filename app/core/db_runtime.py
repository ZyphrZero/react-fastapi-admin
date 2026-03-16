from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from tortoise.context import TortoiseContext
from tortoise.context import _current_context

from app.settings import settings


class DatabaseRuntime:
    """
    管理应用级 TortoiseContext，并在请求/任务边界显式绑定上下文。

    这里不使用 global fallback，而是把数据库上下文作为运行时基础设施显式管理。
    """

    def __init__(self) -> None:
        self._context: TortoiseContext | None = None

    @property
    def context(self) -> TortoiseContext:
        if self._context is None or not self._context.inited:
            raise RuntimeError("数据库运行时尚未初始化")
        return self._context

    async def initialize(self) -> TortoiseContext:
        if self._context is not None and self._context.inited:
            return self._context

        context = TortoiseContext()
        token = _current_context.set(context)
        try:
            await context.init(config=settings.tortoise_orm)
        except Exception:
            await context.close_connections()
            raise
        finally:
            _current_context.reset(token)

        self._context = context
        return context

    @asynccontextmanager
    async def activate(self) -> AsyncIterator[TortoiseContext]:
        token = _current_context.set(self.context)
        try:
            yield self.context
        finally:
            _current_context.reset(token)

    async def close(self) -> None:
        if self._context is None:
            return

        await self._context.close_connections()
        self._context = None
