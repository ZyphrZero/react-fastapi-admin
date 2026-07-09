from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from tortoise import Tortoise, connections

from app.settings import settings


class DatabaseRuntime:
    """
    Manage the application-level Tortoise lifecycle.
    """

    def __init__(self) -> None:
        self._initialized = False

    @property
    def initialized(self) -> bool:
        return self._initialized and bool(getattr(Tortoise, "_inited", False))

    def ensure_initialized(self) -> None:
        if not self.initialized:
            raise RuntimeError("数据库运行时尚未初始化")

    async def initialize(self) -> None:
        if self.initialized:
            return

        if getattr(Tortoise, "_inited", False):
            self._initialized = True
            return

        try:
            await Tortoise.init(config=settings.tortoise_orm)
        except Exception:
            await connections.close_all(discard=True)
            Tortoise._inited = False
            raise

        self._initialized = True

    @asynccontextmanager
    async def activate(self) -> AsyncIterator[None]:
        self.ensure_initialized()
        yield

    async def close(self) -> None:
        if not self._initialized and not getattr(Tortoise, "_inited", False):
            return

        await connections.close_all(discard=True)
        Tortoise._inited = False
        self._initialized = False
