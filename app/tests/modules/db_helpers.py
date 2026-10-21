#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试公共 DB helper：独立事件循环执行场景 + Tortoise 状态彻底复位

Author: bixuejun(bxjgood@163.com)
Date: 2026-09-26 13:52:00  # 北京时间 UTC+8
"""

import asyncio

from tortoise import Tortoise
from tortoise.backends.base.executor import EXECUTOR_CACHE
from tortoise.connection import connections

from app.settings import settings
from app.utils import redis_utils as redis_utils_module

# 模型注册点（业务项目追加自身 modules 到此列表）
MODEL_MODULES = ["app.models"]


async def reset_tortoise() -> None:
    """
    彻底复位 Tortoise 连接状态

    Tortoise.close_connections() 不会重置 _inited；残留 True 会让后续未 init Tortoise 的
    纯 mock 单测（如 test_role_admin_service）里的 managed_transaction 尝试连接配置数据库而报错，
    因此必须显式复位。

    另外两处进程级状态必须一并清除：
    1. EXECUTOR_CACHE 以 (connection_name, schema, table) 为键缓存 INSERT SQL（含 paramstyle
       占位符）。MySQL 场景与 init_sqlite_memory_for_transactions 共用 settings.DB_CONNECTION
       别名，若不清缓存，MySQL 生成的 %s 占位 SQL 会被 SQLite 场景复用而报 near "%"；
    2. connections._db_config 只 update 不清键，残留别名会把惰性连接指回错误引擎。

    Author  ：bixuejun(bxjgood@163.com)
    Date    ：2026-09-26 13:52:00  # 北京时间 UTC+8
    """
    if Tortoise._inited:
        await Tortoise.close_connections()
        Tortoise._inited = False
    EXECUTOR_CACHE.clear()
    connections._db_config = None


async def init_sqlite_memory() -> None:
    """
    以 SQLite 内存库初始化 Tortoise 并建表（单元契约测试用，不依赖外部数据库）

    use_tz/timezone 与 settings.tortoise_orm 生产配置保持一致（本地 +08 naive 存储），
    避免时间过滤（created_at__gte 等）因存储时区错位而失真。

    Author  ：bixuejun(bxjgood@163.com)
    Date    ：2026-09-26 13:52:00  # 北京时间 UTC+8
    """
    await reset_tortoise()
    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"models": MODEL_MODULES},
        use_tz=False,
        timezone="Asia/Shanghai",
    )
    await Tortoise.generate_schemas()


async def init_sqlite_memory_for_transactions() -> None:
    """
    以 SQLite 内存库注册到 settings.DB_CONNECTION 连接别名并建表（事务类单元测试用）

    managed_transaction()/in_transaction() 按 settings.DB_CONNECTION 取连接；
    init_sqlite_memory 注册的是 default 别名，走事务的 Service 单测须用本函数，
    否则事务开启时按别名找不到连接。SQLite 无行锁语义，并发裁决断言仍须集成测试。

    Author  ：bixuejun(bxjgood@163.com)
    Date    ：2026-09-26 17:30:00  # 北京时间 UTC+8
    """
    await reset_tortoise()
    await Tortoise.init(
        config={
            "connections": {settings.DB_CONNECTION: "sqlite://:memory:"},
            "apps": {"models": {"models": MODEL_MODULES, "default_connection": settings.DB_CONNECTION}},
        },
        use_tz=False,
        timezone="Asia/Shanghai",
    )
    await Tortoise.generate_schemas()


async def init_from_settings() -> None:
    """
    以 settings.tortoise_orm 初始化 Tortoise（集成契约测试用，连接 .env 声明的真实数据库）

    Author  ：bixuejun(bxjgood@163.com)
    Date    ：2026-09-26 13:52:00  # 北京时间 UTC+8
    """
    await reset_tortoise()
    await Tortoise.init(config=settings.tortoise_orm)


def run_db_scenario(coro):
    """
    独立事件循环执行测试场景；场景结束彻底复位 Tortoise 并恢复事件循环策略（Windows Proactor）

    Tortoise.init 会经 aerich（config 注册了 aerich.models）在 Windows 上把全局策略改为
    Selector，破坏同进程后续子进程创建；场景结束恢复原策略。
    场景开始时重置全局 Redis 单例：CustomRedisClient 连接绑定创建时的事件循环，
    跨 asyncio.run 场景复用会操作已关闭循环的连接（写失败被吞/TTL 误报 -2）。

    Author  ：bixuejun(bxjgood@163.com)
    Date    ：2026-09-26 13:52:00  # 北京时间 UTC+8

    Args:
        coro: 待执行的测试场景协程

    Returns:
        Any: 场景协程的返回值
    """

    async def wrapper():
        try:
            redis_utils_module._common_redis_client = None
            return await coro
        finally:
            await reset_tortoise()

    policy = asyncio.get_event_loop_policy()
    try:
        return asyncio.run(wrapper())
    finally:
        asyncio.set_event_loop_policy(policy)


def get_model(name: str):
    """
    取已注册的模型类（Tortoise apps 注册表）

    Author  ：bixuejun(bxjgood@163.com)
    Date    ：2026-09-26 13:52:00  # 北京时间 UTC+8

    Args:
        name: 模型类名

    Returns:
        type: 模型类
    """
    return Tortoise.apps["models"][name]
