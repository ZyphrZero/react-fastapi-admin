#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Celery任务工具模块

提供Celery异步任务的通用工具函数，包括事件循环隔离、数据库连接管理等

Author: bixuejun(bxjgood@163.com)
Date: 2026-01-29 15:03:08
"""

import asyncio
from typing import Any, Coroutine

from tortoise import Tortoise

from app.settings.config import settings
from app.utils.log_control import logger
from app.utils.redis_utils import _common_redis_client


async def _cleanup_redis_connections():
    """
    清理 Redis 连接，防止事件循环冲突

    关闭所有全局 Redis 客户端的连接，确保：
    1. 不持有对即将关闭的事件循环的引用
    2. 下次任务执行时创建新连接

    Author  ：bixuejun(bxjgood@163.com)
    Date    ：2026-02-11 10:10:00
    """
    # 清理全局 Redis 客户端单例
    try:
        if _common_redis_client is not None:
            await _common_redis_client.close()
            logger.debug("全局 Common Redis 客户端已关闭")
    except Exception as e:
        logger.debug(f"清理全局 Common Redis 客户端失败: {e}")


def run_async_task(coro: Coroutine) -> Any:
    """
    运行异步任务的辅助函数

    为每个 Celery 任务创建完全独立的事件循环和数据库连接，
    避免循环复用导致的 Future 冲突和数据库连接冲突。

    关键改进：
    1. 每个任务独立初始化 Tortoise ORM
    2. 每个任务使用独立的数据库连接
    3. 避免并发任务的数据库连接冲突
    4. 使用 asyncio.run() 简化事件循环管理
    5. 确保 Redis 连接在任务完成后正确关闭，避免事件循环冲突

    适用场景：
    - 所有需要在 Celery 任务中执行异步代码的场景
    - 特别是需要长时间轮询、数据库操作的任务

    Author  ：bixuejun(bxjgood@163.com)
    Date    ：2026-01-27 16:40:00

    Args:
        coro: 异步协程对象

    Returns:
        异步任务的执行结果

    Raises:
        Exception: 任务执行异常时会抛出

    Examples:
        >>> @celery_task()
        >>> def my_celery_task(arg1: str) -> None:
        >>>     run_async_task(_my_async_function(arg1))
        >>>
        >>> async def _my_async_function(arg1: str) -> None:
        >>>     # 执行异步操作
        >>>     pass
    """
    async def run_with_db():
        """
        执行协程并管理数据库连接

        为当前任务初始化独立的数据库连接
        """
        await Tortoise.init(
            config=settings.tortoise_orm,
            _create_db=False  # 不创建数据库，只连接
        )

        try:
            # 执行实际的协程
            return await coro
        finally:
            # 关闭数据库连接
            try:
                await Tortoise.close_connections()
            except Exception as e:
                logger.debug(f"关闭数据库连接时异常（可忽略）: {e}")

            # ========== 关键修复：确保 Redis 连接也正确关闭 ==========
            # 防止 Redis 客户端持有对已关闭事件循环的引用
            try:
                await _cleanup_redis_connections()
            except Exception as e:
                logger.debug(f"清理 Redis 连接时异常（可忽略）: {e}")

    try:
        # 使用 asyncio.run() 管理事件循环生命周期
        return asyncio.run(run_with_db())
    except Exception as e:
        logger.error(f"任务执行异常: {str(e)}", exc_info=True)
        raise
