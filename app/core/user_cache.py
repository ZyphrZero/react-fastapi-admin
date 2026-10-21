#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
认证用户 Redis 缓存

REDIS_ENABLED=true 时，is_authed 的用户信息按 AUTH_USER_CACHE_TTL 缓存于 Redis
（键 auth:user:{id}，载荷不含口令散列），避免每请求实时查库；用户状态变更处
（登出/改密/资料更新/管理端变更）调用 invalidate_user_cache 立即失效。
Redis 故障一律降级回数据库，绝不阻断认证。

Author: bixuejun(bxjgood@163.com)
Date: 2026-10-19 22:30:00  # 北京时间 UTC+8
"""

from datetime import datetime
from typing import Optional

from tortoise.fields.relational import (
    BackwardFKRelation,
    ForeignKeyFieldInstance,
    ManyToManyFieldInstance,
)

from app.models.admin import User
from app.repositories import user_repository
from app.settings import settings
from app.utils.log_control import logger
from app.utils.redis_utils import get_common_redis_client

# 键带 v1 版本号：载荷格式演进时换版本即可让旧缓存自然失效
_CACHE_KEY_TEMPLATE = "auth:user:v1:{user_id}"

# 载荷必须包含的核心键（残缺/异源载荷按未命中处理）
_REQUIRED_PAYLOAD_KEYS = ("id", "username", "is_active", "is_superuser", "session_version")

_field_names_cache: Optional[list[str]] = None


def _cache_key(user_id: int) -> str:
    """构造缓存键（客户端侧自动叠加 REDIS_PREFIX 前缀）。"""
    return _CACHE_KEY_TEMPLATE.format(user_id=user_id)


def _cache_field_names() -> list[str]:
    """
    参与缓存的 User 字段清单（DB 数据字段，排除关系字段；惰性计算一次）

    从 fields_map 推导而非 db_native_fields/db_default_fields——后两者在 Tortoise.init
    前为空清单，纯 mock 单测场景（未 init）首用即会算出空列表、写入残缺载荷。

    Returns:
        list[str]: 字段名列表（含口令列，写入前会被置 None）
    """
    global _field_names_cache
    if _field_names_cache is None:
        relational = (ForeignKeyFieldInstance, ManyToManyFieldInstance, BackwardFKRelation)
        _field_names_cache = [
            name for name, field in User._meta.fields_map.items() if not isinstance(field, relational)
        ]
    return _field_names_cache


def _to_json_value(value: object) -> object:
    """datetime → ISO 字符串（反序列化由 _init_from_db 的字段转换器还原）。"""
    if isinstance(value, datetime):
        return value.isoformat()
    return value


async def get_cached_user(user_id: int) -> Optional[User]:
    """
    读缓存用户（REDIS_ENABLED=false 或任何 Redis/反序列化异常 → None，回退数据库）

    Args:
        user_id: 用户 ID

    Returns:
        Optional[User]: 缓存命中的用户实例（password 为 None）；未命中返回 None
    """
    if not settings.REDIS_ENABLED:
        return None
    try:
        payload = await get_common_redis_client().get(_cache_key(user_id))
    except Exception as exc:
        logger.warning(f"认证用户缓存读取失败，回退数据库: {exc}")
        return None
    if not isinstance(payload, dict):
        return None
    if not all(key in payload for key in _REQUIRED_PAYLOAD_KEYS):
        # 残缺/异源载荷按未命中处理，回库重建
        logger.warning(f"认证用户缓存载荷残缺（缺核心键），按未命中处理: user_id={user_id}")
        return None
    try:
        return User._init_from_db(**payload)
    except Exception as exc:
        logger.warning(f"认证用户缓存反序列化失败，回退数据库: {exc}")
        return None


async def cache_user(user: User) -> None:
    """
    写缓存用户（载荷不含口令散列；TTL=AUTH_USER_CACHE_TTL；异常吞掉不阻断认证）

    Args:
        user: 待缓存的用户实例

    Returns:
        None
    """
    if not settings.REDIS_ENABLED or user is None:
        return
    try:
        payload = {name: _to_json_value(getattr(user, name, None)) for name in _cache_field_names()}
        payload["password"] = None
        await get_common_redis_client().set(_cache_key(user.id), payload, expire=settings.AUTH_USER_CACHE_TTL)
    except Exception as exc:
        logger.warning(f"认证用户缓存写入失败（忽略）: {exc}")


async def invalidate_user_cache(user_id: int) -> None:
    """
    立即失效缓存用户（登出/改密/禁用/删除等状态变更后调用；异常吞掉）

    Args:
        user_id: 用户 ID

    Returns:
        None
    """
    if not settings.REDIS_ENABLED:
        return
    try:
        await get_common_redis_client().delete(_cache_key(user_id))
    except Exception as exc:
        logger.warning(f"认证用户缓存失效失败（忽略）: {exc}")


async def load_authed_user(user_id: int) -> Optional[User]:
    """
    认证取用户：缓存命中直接返回；未命中查库并回填缓存

    Args:
        user_id: 令牌内的用户 ID

    Returns:
        Optional[User]: 用户实例（缓存实例 password 为 None）；不存在返回 None
    """
    user = await get_cached_user(user_id)
    if user is not None:
        return user
    user = await user_repository.get(user_id)
    if user is not None:
        await cache_user(user)
    return user
