#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
lifespan 降级启动测试

- MINIO_ENABLED=true 且 MinIO 不可达（StorageUnavailableError）时应用降级启动而非崩溃
- MINIO_ENABLED=false（默认形态）时不做任何 MinIO 连接尝试
- 非存储异常仍向上传播

Author: bixuejun(bxjgood@163.com)
Date: 2026-09-27 12:00:00  # 北京时间 UTC+8
"""

import pytest
from fastapi import FastAPI

import app.application as application_module
import app.services.system_setting_service as system_setting_service_module
from app.application import lifespan
from app.settings import settings
from app.tests.modules.db_helpers import init_sqlite_memory_for_transactions, run_db_scenario
from app.utils.minio_utils import StorageUnavailableError

sss = system_setting_service_module


async def _noop_runtime_settings(*, app=None) -> None:
    """
    运行时设置初始化替身（no-op，签名对齐 initialize_runtime_settings）。

    Author: bixuejun(bxjgood@163.com)
    Date : 2026-09-27 12:00:00  # 北京时间 UTC+8
    """


class _FakeUnreachableStorage:
    """ensure_buckets 必抛 StorageUnavailableError 的存储替身。"""

    @staticmethod
    async def ensure_buckets() -> None:
        raise StorageUnavailableError("connection refused (test)")


class TestLifespanDegradedStart:
    """lifespan：MinIO 不可达降级启动；开关关闭零连接；非存储异常仍向上传播。"""

    def test_lifespan_starts_when_minio_unreachable(self, monkeypatch) -> None:
        """MINIO_ENABLED=true + ensure_buckets 抛 StorageUnavailableError → lifespan 正常进入与退出。"""

        async def scenario():
            # 复用测试库初始化：DatabaseRuntime.initialize 见 Tortoise 已 init 即幂等通过
            await init_sqlite_memory_for_transactions()

            monkeypatch.setattr(application_module, "get_storage", lambda: _FakeUnreachableStorage())
            monkeypatch.setattr(sss, "initialize_runtime_settings", _noop_runtime_settings)
            monkeypatch.setattr(settings, "CELERY_AUTOSTART", False)
            monkeypatch.setattr(settings, "MINIO_ENABLED", True)

            app = FastAPI()
            # 进入 lifespan 体即证明降级分支未中断启动；正常退出验证 finally 清理不抛
            async with lifespan(app):
                assert app.state.db_runtime is not None

        run_db_scenario(scenario())

    def test_minio_disabled_skips_connection(self, monkeypatch) -> None:
        """MINIO_ENABLED=False 时 get_storage 不被调用（零连接尝试）。"""

        async def scenario():
            await init_sqlite_memory_for_transactions()

            monkeypatch.setattr(application_module, "get_storage", lambda: pytest.fail("MINIO_ENABLED=false 不应触碰存储"))
            monkeypatch.setattr(sss, "initialize_runtime_settings", _noop_runtime_settings)
            monkeypatch.setattr(settings, "CELERY_AUTOSTART", False)
            monkeypatch.setattr(settings, "MINIO_ENABLED", False)

            app = FastAPI()
            async with lifespan(app):
                assert app.state.db_runtime is not None

        run_db_scenario(scenario())

    def test_lifespan_propagates_non_storage_errors(self, monkeypatch) -> None:
        """非存储异常（如运行时设置初始化失败）仍向上传播，降级不吞错误。"""

        async def scenario():
            await init_sqlite_memory_for_transactions()

            async def _boom_runtime_settings(*, app=None) -> None:
                raise RuntimeError("runtime settings broken (test)")

            monkeypatch.setattr(sss, "initialize_runtime_settings", _boom_runtime_settings)
            monkeypatch.setattr(settings, "CELERY_AUTOSTART", False)

            app = FastAPI()
            with pytest.raises(RuntimeError, match="runtime settings broken"):
                async with lifespan(app):
                    pass

        run_db_scenario(scenario())
