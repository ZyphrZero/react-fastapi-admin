#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Celery 队列拓扑与 beat 调度测试

Author: bixuejun(bxjgood@163.com)
Date: 2026-09-24 15:14:00  # 北京时间 UTC+8
"""

from app.celery.celery_app import celery_app
from app.settings import settings


class TestQueueTopology:
    def test_default_queue_only(self) -> None:
        queue_names = {q.name for q in celery_app.conf.task_queues}
        assert queue_names == {"default"}

    def test_queues_follow_settings(self) -> None:
        assert settings.celery_queues == ["default"]
        assert settings.celery_queues[0] == "default"

    def test_cleanup_task_registered(self) -> None:
        assert celery_app.conf.task_routes == {"app.tasks.cleanup_tasks.*": {"queue": "default"}}
        schedule_tasks = {entry["task"] for entry in celery_app.conf.beat_schedule.values()}
        assert "app.tasks.cleanup_tasks.cleanup_tmp_objects" in schedule_tasks
        assert "app.tasks.cleanup_tasks.cleanup_tmp_objects" in celery_app.tasks

    def test_beat_lock_names_include_project_prefix(self) -> None:
        """beat 锁/调度文件名带项目前缀，避免多项目同机互抢。"""
        # app.celery.__init__ 再导出的 celery_app 实例会遮蔽同名子模块属性，须走 importlib 取真实模块
        import importlib

        celery_module = importlib.import_module("app.celery.celery_app")

        prefix = settings.PROJECT_NAME.lower().replace(" ", "-")
        assert celery_module._beat_lock_path.endswith("celery_beat.lock")
        assert prefix in celery_module._beat_lock_path.replace("\\", "/").split("/")[-1]
        assert prefix in celery_module._beat_schedule_path.replace("\\", "/").split("/")[-1]
