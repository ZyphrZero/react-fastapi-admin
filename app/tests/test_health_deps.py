#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
/health/deps 端点测试（db/redis/minio 三项探测、开关感知 skip 与 503 语义）

Author: bixuejun(bxjgood@163.com)
Date: 2026-09-26 09:40:00  # 北京时间 UTC+8
"""

import asyncio
from contextlib import ExitStack
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.base import base as base_api
from app.core.exceptions import exception_handlers
from app.services import health_service


def _make_client() -> TestClient:
    app = FastAPI()
    # 注册脚手架统一异常处理器，复现生产响应包形状（CustomHTTPException → {code,msg,data}）
    for exc_type, handler in exception_handlers.items():
        app.add_exception_handler(exc_type, handler)
    app.include_router(base_api.router, prefix="/api/v1/base")
    return TestClient(app)


async def _ok() -> bool:
    return True


async def _bad() -> bool:
    return False


def _patch_probes(db=_ok, redis=None, minio=None):
    """统一 patch 三个探测函数（redis/minio 可单独覆盖）。"""
    from contextlib import ExitStack

    stack = ExitStack()
    stack.enter_context(patch.object(health_service, "check_db", new=db))
    stack.enter_context(patch.object(health_service, "check_redis", new=redis or _ok))
    stack.enter_context(patch.object(health_service, "check_minio", new=minio or _ok))
    stack.enter_context(patch.object(health_service.settings, "REDIS_ENABLED", True))
    stack.enter_context(patch.object(health_service.settings, "MINIO_ENABLED", True))
    return stack


class TestHealthDeps:
    def test_all_ok_returns_200(self) -> None:
        with _patch_probes():
            response = _make_client().get("/api/v1/base/health/deps")
        assert response.status_code == 200
        assert response.json()["data"] == {"db": "ok", "redis": "ok", "minio": "ok"}

    def test_any_failure_returns_503(self) -> None:
        with _patch_probes(redis=_bad):
            response = _make_client().get("/api/v1/base/health/deps")
        assert response.status_code == 503
        assert response.json()["data"]["redis"] == "err"

    def test_disabled_report_skip(self) -> None:
        """REDIS_ENABLED/MINIO_ENABLED 关闭时：探测函数不执行，值报 skip 且端点 200。"""
        with _patch_probes() as stack:
            redis_probe = stack.enter_context(patch.object(health_service, "check_redis"))
            stack.enter_context(patch.object(health_service.settings, "REDIS_ENABLED", False))
            stack.enter_context(patch.object(health_service.settings, "MINIO_ENABLED", False))
            deps = asyncio.run(health_service.collect_deps_health())
        redis_probe.assert_not_called()
        assert deps == {"db": "ok", "redis": "skip", "minio": "skip"}

        with _patch_probes() as stack:
            stack.enter_context(patch.object(health_service.settings, "REDIS_ENABLED", False))
            stack.enter_context(patch.object(health_service.settings, "MINIO_ENABLED", False))
            response = _make_client().get("/api/v1/base/health/deps")
        assert response.status_code == 200
        assert response.json()["data"] == {"db": "ok", "redis": "skip", "minio": "skip"}
