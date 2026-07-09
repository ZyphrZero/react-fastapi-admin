from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from tortoise import Tortoise
from tortoise.transactions import in_transaction


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

    async with in_transaction():
        yield
