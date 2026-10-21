#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
事务上下文连接名绑定测试（A2 回归钉）

项目 tortoise 配置恒同时注册 sqlite/mysql 双引擎条目（settings.tortoise_orm），
in_transaction() 不带连接名时遇多连接抛 ParamsError——managed_transaction 必须显式
绑定配置声明的默认连接。

Author: bixuejun(bxjgood@163.com)
Date: 2026-10-19 21:10:33  # 北京时间 UTC+8
"""

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import MagicMock, patch

from app.core.transactions import managed_transaction
from app.settings import settings


class TestTransactionConnectionBinding:
    def test_transactional_binds_default_connection(self) -> None:
        captured = {}

        @asynccontextmanager
        async def fake_in_transaction(**kwargs):
            captured.update(kwargs)
            yield

        tortoise_stub = MagicMock()
        tortoise_stub._inited = True

        with (
            patch("app.core.transactions.in_transaction", side_effect=lambda **kw: fake_in_transaction(**kw)),
            patch("app.core.transactions.Tortoise", tortoise_stub),
        ):

            async def run() -> None:
                async with managed_transaction():
                    pass

            asyncio.run(run())

        assert captured.get("connection_name") == settings.DB_CONNECTION

    def test_transactional_noop_without_tortoise(self) -> None:
        """Tortoise 未初始化时降级为 no-op，不触碰 in_transaction。"""
        tortoise_stub = MagicMock()
        tortoise_stub._inited = False

        with (
            patch("app.core.transactions.in_transaction") as in_tx_mock,
            patch("app.core.transactions.Tortoise", tortoise_stub),
        ):

            async def run() -> None:
                async with managed_transaction():
                    pass

            asyncio.run(run())

        in_tx_mock.assert_not_called()
