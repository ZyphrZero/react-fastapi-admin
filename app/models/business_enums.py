#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
跨模块共用业务枚举

Author: bixuejun(bxjgood@163.com)
Date: 2026-09-24 23:37:20  # 北京时间 UTC+8
"""

from app.models.enums import StrEnum




class TaskStatus(StrEnum):
    """任务状态（task_run ）。"""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"






