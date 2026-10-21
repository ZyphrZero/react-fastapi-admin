#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Celery 任务注册中心

任务模块、路由与周期调度在此登记（骨架默认为空，业务项目按需追加）。

新增任务模块时在 TASK_MODULES 登记模块路径，并按需补充 TASK_ROUTES 或 BEAT_SCHEDULE：
- TASK_MODULES：填写 Python 模块完整路径，celery_app 会立即导入使 @celery_app.task 注册；
  只写路由或计划不会自动导入任务模块。
- TASK_ROUTES：键须匹配 @celery_app.task(name=...) 声明的任务名（支持末尾 * 通配符）；
  值中的 queue 必须是 settings.CELERY_QUEUES 启用的队列，未配置路由的任务走 default。
- BEAT_SCHEDULE：每个键是唯一计划标识；task 须为已注册任务的完整名。部署时只运行一个
  beat 实例，避免同一周期任务被重复投递。

Author: bixuejun(bxjgood@163.com)
Date: 2026-09-27 10:03:11  # 北京时间 UTC+8
"""

from celery.schedules import crontab

# 任务模块注册清单：填写 Python 模块完整路径，不写任务函数名或通配符。
# 新增 app/tasks/xxx_tasks.py 后，在此加入 "app.tasks.xxx_tasks"；
# celery_app.py 会立即导入这些模块，使其中的 @celery_app.task 在后端进程和独立 worker 中注册。
# 只写 TASK_ROUTES 或 BEAT_SCHEDULE 不会自动导入任务模块。
TASK_MODULES = (
    "app.tasks.cleanup_tasks",
)

# 任务路由：键必须匹配 @celery_app.task(name=...) 声明的任务名，支持末尾 * 通配符；
# 值中的 queue 必须是 settings.CELERY_QUEUES 启用的队列，未配置路由的任务走 default。
# 新任务需要专用队列时在此补路由，并同步确认部署的 worker 正在消费该队列。
# 可先登记尚未实现的任务路由；路由配置本身不会注册任务。
TASK_ROUTES = {
    "app.tasks.cleanup_tasks.*": {"queue": "default"},
}

# 周期计划：每个键是唯一的计划标识；task 必须填写已注册任务的完整任务名。
# schedule 可填秒数（例如 60.0 表示每 60 秒）或 crontab（例如每日 03:30）。
# 新增计划时，先将任务模块加入 TASK_MODULES，再添加本条目；如需指定队列，同时补 TASK_ROUTES。
# 部署时只运行一个 beat 实例，避免同一周期任务被重复投递。
BEAT_SCHEDULE = {
    "cleanup-tmp-objects": {
        "task": "app.tasks.cleanup_tasks.cleanup_tmp_objects",
        "schedule": crontab(hour=3, minute=30),
    },
}
