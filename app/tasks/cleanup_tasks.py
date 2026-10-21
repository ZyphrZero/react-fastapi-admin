#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
清理类周期任务（app-tmp 临时对象回收，作为脚手架示例任务）

Author: bixuejun(bxjgood@163.com)
Date: 2026-09-24 15:15:00  # 北京时间 UTC+8
"""

from datetime import datetime, timedelta, timezone

from app.celery.celery_app import celery_app
from app.settings import settings
from app.utils.celery_task_utils import run_async_task
from app.utils.log_control import logger
from app.utils.minio_utils import StorageBucket, get_storage


async def _cleanup_tmp_objects_async() -> int:
    """
    扫描 app-tmp 桶，删除超过 TMP_RETAIN_HOURS 的对象（幂等，可重入）

    Author  ：bixuejun(bxjgood@163.com)
    Date    ：2026-09-24 15:15:00  # 北京时间 UTC+8

    Returns:
        int: 本次删除的对象数
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.TMP_RETAIN_HOURS)
    storage = get_storage()
    removed = 0
    async for object_key in storage.list_objects(StorageBucket.TMP, prefix=""):
        stat = await storage.stat_object(StorageBucket.TMP, object_key)
        last_modified = stat.last_modified  # MinIO 返回 aware datetime（UTC）
        if last_modified < cutoff:
            await storage.remove_object(StorageBucket.TMP, object_key)
            removed += 1
            logger.info(f"app-tmp 回收: {object_key}（last_modified={last_modified.isoformat()}）")
    if removed:
        logger.info(f"app-tmp 回收完成，共删除 {removed} 个超期对象")
    return removed


@celery_app.task(name="app.tasks.cleanup_tasks.cleanup_tmp_objects")
def cleanup_tmp_objects() -> int:
    """
    [Celery 任务] 每日 03:30 回收 app-tmp 超期临时对象（beat 调度）

    Author  ：bixuejun(bxjgood@163.com)
    Date    ：2026-09-24 15:15:00  # 北京时间 UTC+8

    Returns:
        int: 删除的对象数
    """
    return run_async_task(_cleanup_tmp_objects_async())
