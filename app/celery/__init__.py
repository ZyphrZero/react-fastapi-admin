#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Celery 异步任务模块

提供 Celery 应用实例与内嵌 worker/beat 启停入口。

Author: bixuejun(bxjgood@163.com)
Date: 2026-09-22 09:45  # 北京时间 UTC+8
"""
from .celery_app import celery_app, start_celery_beat, start_celery_worker, stop_celery_beat, stop_celery_worker

__all__ = [
    "celery_app",
    "start_celery_worker",
    "stop_celery_worker",
    "start_celery_beat",
    "stop_celery_beat",
]
