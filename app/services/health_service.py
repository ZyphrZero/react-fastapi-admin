#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
依赖健康探测服务（db / redis / minio 三项探测、开关感知与聚合）

Author: bixuejun(bxjgood@163.com)
Date: 2026-09-26 09:42:00  # 北京时间 UTC+8
"""

import asyncio

from tortoise import Tortoise

from app.settings import settings
from app.utils.log_control import logger
from app.utils.minio_utils import minio_client
from app.utils.redis_utils import get_common_redis_client

# MinIO 探测超时（秒）：list_buckets 走同步 SDK 经 to_thread 包装，无超时会在 TCP 黑洞下
# 使 gather 永久等待、/health/deps 挂起
_MINIO_PROBE_TIMEOUT_SECONDS = 15


async def check_db() -> bool:
    """
    SELECT 1 探测数据库连接（连接名 = settings.DB_CONNECTION，与 tortoise_orm 注册一致）

    Author  ：bixuejun(bxjgood@163.com)
    Date    ：2026-09-26 09:42:00  # 北京时间 UTC+8

    Returns:
        bool: 连接与查询正常为 True
    """
    try:
        conn = Tortoise.get_connection(settings.DB_CONNECTION)
        await conn.execute_query("SELECT 1")
        return True
    except Exception as e:
        logger.warning(f"health/deps db 探测失败: {e}")
        return False


async def check_redis() -> bool:
    """
    PING 探测 Redis 连接

    Author  ：bixuejun(bxjgood@163.com)
    Date    ：2026-09-26 09:42:00  # 北京时间 UTC+8

    Returns:
        bool: 连接与 PING 正常为 True
    """
    try:
        client = get_common_redis_client()
        if client._redis is None:
            await client.connect()
        return bool(await client._redis.ping())
    except Exception as e:
        logger.warning(f"health/deps redis 探测失败: {e}")
        return False


async def check_minio() -> bool:
    """
    列举桶探测 MinIO 可达性（wait_for 超时防 TCP 黑洞挂起）

    Author  ：bixuejun(bxjgood@163.com)
    Date    ：2026-09-26 09:42:00  # 北京时间 UTC+8

    Returns:
        bool: 可达且能列举桶为 True
    """
    try:
        buckets = await asyncio.wait_for(
            asyncio.to_thread(minio_client._client.list_buckets),
            timeout=_MINIO_PROBE_TIMEOUT_SECONDS,
        )
        return bool(buckets)
    except Exception as e:
        logger.warning(f"health/deps minio 探测失败: {e}")
        return False


async def collect_deps_health() -> dict:
    """
    汇总三项依赖健康（开关关闭的项报 skip 不算失败；任一已启用项 err 由端点转 503）

    Author  ：bixuejun(bxjgood@163.com)
    Date    ：2026-09-26 09:42:00  # 北京时间 UTC+8

    Returns:
        dict: {"db": "ok"|"err", "redis": "ok"|"err"|"skip", "minio": "ok"|"err"|"skip"}
    """
    db_ok, redis_ok, minio_ok = await asyncio.gather(
        check_db(),
        check_redis() if settings.REDIS_ENABLED else _probe_skipped(),
        check_minio() if settings.MINIO_ENABLED else _probe_skipped(),
    )
    return {
        "db": "ok" if db_ok else "err",
        "redis": ("ok" if redis_ok else "err") if settings.REDIS_ENABLED else "skip",
        "minio": ("ok" if minio_ok else "err") if settings.MINIO_ENABLED else "skip",
    }


async def _probe_skipped() -> bool:
    """被开关关闭的探测占位（gather 形状对齐，结果被 skip 覆盖）。"""
    return False
