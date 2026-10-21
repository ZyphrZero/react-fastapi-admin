#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
认证用户 Redis 缓存测试（REDIS_ENABLED 门控、TTL、失效钩子、回退语义）

Author: bixuejun(bxjgood@163.com)
Date: 2026-10-19 22:30:00  # 北京时间 UTC+8
"""

import asyncio
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.core import user_cache
from app.models.admin import User
from app.tests.modules.db_helpers import init_sqlite_memory_for_transactions, run_db_scenario


class _FakeRedis:
    """内存版 Redis 客户端替身（键值 dict，get/set/delete）。"""

    def __init__(self):
        self.store = {}
        self.get_calls = 0
        self.set_calls = 0

    async def get(self, key, default=None, deserialize=True):
        self.get_calls += 1
        return self.store.get(key, default)

    async def set(self, key, value, expire=None, serialize=True):
        self.set_calls += 1
        self.store[key] = value
        return True

    async def delete(self, *keys):
        removed = 0
        for key in keys:
            if self.store.pop(key, None) is not None:
                removed += 1
        return removed


def _fake_user(**overrides) -> User:
    values = dict(
        id=7,
        username="alice",
        nickname="Alice",
        avatar=None,
        email="a@x.com",
        phone=None,
        password="hashed-secret",
        is_active=True,
        is_superuser=False,
        last_login=datetime(2026, 10, 19, 21, 0, 0),
        session_version=3,
        refresh_token_jti="jti-x",
        created_at=datetime(2026, 10, 1, 8, 0, 0),
        updated_at=datetime(2026, 10, 1, 8, 0, 0),
    )
    values.update(overrides)
    return User._init_from_db(**values)


def _enabled(fake: _FakeRedis):
    """REDIS_ENABLED=true + 假 Redis 客户端注入的上下文组合。"""
    from contextlib import ExitStack

    stack = ExitStack()
    stack.enter_context(patch.object(user_cache.settings, "REDIS_ENABLED", True))
    stack.enter_context(patch.object(user_cache.settings, "AUTH_USER_CACHE_TTL", 600))
    stack.enter_context(patch.object(user_cache, "get_common_redis_client", lambda: fake))
    return stack


class TestUserCacheRoundtrip:
    def test_roundtrip_rehydrates_user_without_password(self) -> None:
        async def scenario():
            await init_sqlite_memory_for_transactions()
            fake = _FakeRedis()
            with _enabled(fake):
                await user_cache.cache_user(_fake_user())
                cached = await user_cache.get_cached_user(7)
            assert cached is not None
            assert cached.username == "alice"
            assert cached.session_version == 3
            assert cached.is_active is True
            assert isinstance(cached.last_login, datetime)
            assert cached.password is None  # 缓存载荷不含口令散列

        run_db_scenario(scenario())

    def test_field_names_resolve_without_tortoise_init(self) -> None:
        """Tortoise 未 init 时（纯 mock 单测场景）字段清单也必须完整，防止残缺载荷入缓存。"""

        async def scenario():
            from tortoise import Tortoise

            if Tortoise._inited:
                await Tortoise.close_connections()
                Tortoise._inited = False
            user_cache._field_names_cache = None  # 重置惰性缓存复现首用时序

            fake = _FakeRedis()
            with _enabled(fake):
                await user_cache.cache_user(_fake_user())
            payload = fake.store.get("auth:user:v1:7")
            assert payload is not None, "缓存未写入"
            for required in ("id", "username", "is_active", "is_superuser", "session_version"):
                assert required in payload, f"残缺载荷缺 {required}"

        run_db_scenario(scenario())

    def test_cache_write_passes_ttl(self) -> None:
        async def scenario():
            await init_sqlite_memory_for_transactions()
            fake = _FakeRedis()
            with _enabled(fake):
                await user_cache.cache_user(_fake_user())
            assert fake.set_calls == 1
            # TTL 经 AUTH_USER_CACHE_TTL 传入（默认 600 秒 = 10 分钟）

        run_db_scenario(scenario())


class TestLoadAuthedUser:
    def test_second_load_hits_cache_not_db(self) -> None:
        async def scenario():
            await init_sqlite_memory_for_transactions()
            fake = _FakeRedis()
            repo_get = AsyncMock(side_effect=lambda uid: _fake_user(id=uid))
            with _enabled(fake), patch.object(user_cache.user_repository, "get", new=repo_get):
                first = await user_cache.load_authed_user(7)
                second = await user_cache.load_authed_user(7)
            assert first is not None and second is not None
            assert repo_get.await_count == 1  # 第二次走缓存

        run_db_scenario(scenario())

    def test_disabled_skips_cache_entirely(self) -> None:
        async def scenario():
            await init_sqlite_memory_for_transactions()
            fake = _FakeRedis()
            repo_get = AsyncMock(side_effect=lambda uid: _fake_user(id=uid))
            with (
                patch.object(user_cache.settings, "REDIS_ENABLED", False),
                patch.object(user_cache, "get_common_redis_client", lambda: fake),
                patch.object(user_cache.user_repository, "get", new=repo_get),
            ):
                await user_cache.load_authed_user(7)
                await user_cache.load_authed_user(7)
            assert repo_get.await_count == 2
            assert fake.get_calls == 0  # 关闭时不触碰 Redis

        run_db_scenario(scenario())

    def test_redis_error_falls_back_to_db(self) -> None:
        class _BrokenRedis(_FakeRedis):
            async def get(self, key, default=None, deserialize=True):
                raise ConnectionError("redis down (test)")

        async def scenario():
            await init_sqlite_memory_for_transactions()
            broken = _BrokenRedis()
            repo_get = AsyncMock(side_effect=lambda uid: _fake_user(id=uid))
            with _enabled(broken), patch.object(user_cache.user_repository, "get", new=repo_get):
                user = await user_cache.load_authed_user(7)
            assert user is not None  # 缓存故障不阻断认证
            assert repo_get.await_count == 1

        run_db_scenario(scenario())

    def test_invalidate_forces_next_load_from_db(self) -> None:
        async def scenario():
            await init_sqlite_memory_for_transactions()
            fake = _FakeRedis()
            repo_get = AsyncMock(side_effect=lambda uid: _fake_user(id=uid))
            with _enabled(fake), patch.object(user_cache.user_repository, "get", new=repo_get):
                await user_cache.load_authed_user(7)
                await user_cache.invalidate_user_cache(7)
                await user_cache.load_authed_user(7)
            assert repo_get.await_count == 2

        run_db_scenario(scenario())


class TestInvalidationHooks:
    def test_logout_invalidates_cache(self) -> None:
        from app.services import auth_service

        user = SimpleNamespace(id=7, session_version=2, refresh_token_jti="j", save=AsyncMock())
        with patch("app.services.auth_service.invalidate_user_cache", new=AsyncMock()) as invalidate:
            asyncio.run(auth_service.logout(user))
        invalidate.assert_awaited_once_with(7)
        user.save.assert_awaited_once()

    def test_update_user_invalidates_cache(self) -> None:
        from app.schemas.users import UserUpdate
        from app.services import user_admin_service

        existing = SimpleNamespace(id=7, is_superuser=False, is_active=True)
        with (
            patch("app.services.user_admin_service.user_repository.get", new=AsyncMock(return_value=existing)),
            patch("app.services.user_admin_service.user_repository.get_by_email", new=AsyncMock(return_value=None)),
            patch("app.services.user_admin_service.user_repository.get_by_username", new=AsyncMock(return_value=None)),
            patch("app.services.user_admin_service.user_repository.update", new=AsyncMock(return_value=existing)),
            patch(
                "app.services.user_admin_service.admin_permission_service.ensure_can_update_user",
                new=AsyncMock(),
            ),
            patch(
                "app.services.user_admin_service.invalidate_user_cache",
                new=AsyncMock(),
            ) as invalidate,
        ):
            asyncio.run(
                user_admin_service.update_user(
                    UserUpdate(id=7, nickname="新昵称"), actor=SimpleNamespace(id=1, is_superuser=True)
                )
            )
        invalidate.assert_awaited_once_with(7)
