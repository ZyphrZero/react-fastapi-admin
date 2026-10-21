#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
from typing import Any, Optional, List, Dict
from contextlib import asynccontextmanager

from redis import asyncio as aioredis
from loguru import logger

from app.settings import settings

"""
Redis 工具类模块
提供 Redis 的基本操作封装，支持传入不同的 Redis 配置信息实现多环境隔离。
主要功能：
- 自动连接管理（无需手动 connect/close）
- String、Hash、List 等数据类型的完整操作
- 自动序列化/反序列化 JSON 数据
- 键名前缀支持
- 异常处理和日志记录
- 全局单例客户端支持
- 兼容 Python 3.11+ 环境，使用 redis 包替代 aioredis

Author: bixuejun(bxjgood@163.com)
Date: 2025-10-28 12:16:58
"""


class CustomRedisClient:
    """
    Redis 客户端封装类
    支持传入不同的 Redis 配置信息
    """

    def __init__(self, config: dict):
        """
        初始化 Redis 客户端

        Author  ：bixuejun(bxjgood@163.com)
        Date    ：2025-10-28 12:16:58
        Args:
            config: Redis 配置字典，包含以下字段：
                - host: Redis 主机地址
                - port: Redis 端口
                - db: Redis 数据库索引
                - password: Redis 密码（可选）
                - prefix: Redis 键前缀（可选）

        Returns:
            None
        """
        self.host = config.get("host", "localhost")
        self.port = config.get("port", 6379)
        self.db = config.get("db", 0)
        self.password = config.get("password", "")
        self.prefix = config.get("prefix", "")
        self._redis: Optional[aioredis.Redis] = None

    async def connect(self):
        """
        连接到 Redis 服务器
        首次调用时建立连接，后续调用会复用已有连接

        Author  ：bixuejun(bxjgood@163.com)
        Date    ：2025-10-28 12:16:58
        Args:
            无

        Returns:
            None

        Raises:
            Exception: Redis 连接失败时抛出异常
        """
        if self._redis is None:
            try:
                # 使用 redis.asyncio 创建连接
                # socket 超时（秒）：不可达端口必须快速失败——无超时的连接在 Windows/IPv6
                # 回退路径上可挂数秒，令依赖 Redis 的调用方（如认证缓存降级）被拖慢
                self._redis = aioredis.Redis(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    password=self.password if self.password else None,
                    decode_responses=True,
                    encoding="utf-8",
                    socket_connect_timeout=2,
                    socket_timeout=2,
                )
                # 测试连接
                await self._redis.ping()
                logger.info(f"Redis 连接成功: {self.host}:{self.port}/{self.db}")
            except Exception as e:
                logger.error(f"Redis 连接失败: {e}")
                raise

    async def close(self):
        """
        关闭 Redis 连接
        释放连接资源，通常在应用退出时调用

        Author  ：bixuejun(bxjgood@163.com)
        Date    ：2025-10-28 12:16:58
        Args:
            无

        Returns:
            None
        """
        if self._redis:
            await self._redis.aclose()
            self._redis = None
            logger.info("Redis 连接已关闭")

    def _get_key(self, key: str) -> str:
        """
        获取带前缀的键名
        内部方法，用于自动添加配置的键前缀

        Author  ：bixuejun(bxjgood@163.com)
        Date    ：2025-10-28 12:16:58
        Args:
            key: 原始键名

        Returns:
            str: 带前缀的完整键名
        """
        if self.prefix:
            return f"{self.prefix}:{key}"
        return key

    async def set(self, key: str, value: Any, expire: Optional[int] = None, serialize: bool = True) -> bool:
        """
        设置键值
        支持自动序列化复杂对象为 JSON，支持设置过期时间

        Author  ：bixuejun(bxjgood@163.com)
        Date    ：2025-10-28 12:16:58
        Args:
            key: 键名
            value: 值，支持字符串、字典、列表等类型
            expire: 过期时间（秒），None 表示不过期
            serialize: 是否序列化为 JSON，默认 True

        Returns:
            bool: 是否设置成功
        """
        if not self._redis:
            await self.connect()

        try:
            full_key = self._get_key(key)
            if serialize and not isinstance(value, (str, bytes)):
                value = json.dumps(value, ensure_ascii=False)

            if expire:
                await self._redis.setex(full_key, expire, value)
            else:
                await self._redis.set(full_key, value)
            return True
        except Exception as e:
            logger.error(f"Redis SET 操作失败: key={key}, error={e}")
            return False

    async def set_nx(self, key: str, value: Any, expire: Optional[int] = None, serialize: bool = True) -> bool:
        """
        SET NX：仅当键不存在时写入（原子占位，防并发首写互相覆盖）

        Author  ：bixuejun(bxjgood@163.com)
        Date    ：2026-09-26 19:05:00  # 北京时间 UTC+8
        Args:
            key: 键名
            value: 值，支持字符串、字典、列表等类型
            expire: 过期时间（秒），None 表示不过期
            serialize: 是否序列化为 JSON，默认 True

        Returns:
            bool: 是否实际写入（键已存在时 False）
        """
        if not self._redis:
            await self.connect()

        try:
            full_key = self._get_key(key)
            if serialize and not isinstance(value, (str, bytes)):
                value = json.dumps(value, ensure_ascii=False)

            if expire:
                result = await self._redis.set(full_key, value, nx=True, ex=expire)
            else:
                result = await self._redis.set(full_key, value, nx=True)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis SETNX 操作失败: key={key}, error={e}")
            return False

    async def eval_script(self, script: str, keys: List[str], args: Optional[List[Any]] = None) -> Any:
        """
        执行 Lua 脚本（EVAL 原生封装，键名自动叠加前缀；供 compare-token 续期等原子操作）

        Author  ：bixuejun(bxjgood@163.com)
        Date    ：2026-09-26 19:05:00  # 北京时间 UTC+8
        Args:
            script: Lua 脚本源码
            keys: KEYS 列表（原始键名，内部补前缀）
            args: ARGV 列表，默认空

        Returns:
            Any: 脚本返回值；执行失败时返回 None（调用方按失败语义兜底）
        """
        if not self._redis:
            await self.connect()

        try:
            full_keys = [self._get_key(key) for key in keys]
            return await self._redis.eval(script, len(full_keys), *full_keys, *(args or []))
        except Exception as e:
            logger.error(f"Redis EVAL 操作失败: script={script[:60]}..., error={e}")
            return None

    async def get(self, key: str, default: Any = None, deserialize: bool = True) -> Any:
        """
        获取键值
        支持自动反序列化 JSON 数据为 Python 对象

        Author  ：bixuejun(bxjgood@163.com)
        Date    ：2025-10-28 12:16:58
        Args:
            key: 键名
            default: 键不存在时返回的默认值
            deserialize: 是否反序列化 JSON，默认 True

        Returns:
            Any: 键对应的值，不存在时返回 default
        """
        if not self._redis:
            await self.connect()

        try:
            full_key = self._get_key(key)
            value = await self._redis.get(full_key)

            if value is None:
                return default

            if deserialize and isinstance(value, (str, bytes)):
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            return value
        except Exception as e:
            logger.error(f"Redis GET 操作失败: key={key}, error={e}")
            return default

    async def delete(self, *keys: str) -> int:
        """
        删除一个或多个键

        Author  ：bixuejun(bxjgood@163.com)
        Date    ：2025-10-28 12:16:58
        Args:
            *keys: 可变参数，一个或多个键名

        Returns:
            int: 实际删除的键数量
        """
        if not self._redis:
            await self.connect()

        try:
            full_keys = [self._get_key(key) for key in keys]
            count = await self._redis.delete(*full_keys)
            return count
        except Exception as e:
            logger.error(f"Redis DELETE 操作失败: keys={keys}, error={e}")
            return 0

    async def exists(self, *keys: str) -> int:
        """
        检查键是否存在

        Author  ：bixuejun(bxjgood@163.com)
        Date    ：2025-10-28 12:16:58
        Args:
            *keys: 可变参数，一个或多个键名

        Returns:
            int: 存在的键数量
        """
        if not self._redis:
            await self.connect()

        try:
            full_keys = [self._get_key(key) for key in keys]
            count = await self._redis.exists(*full_keys)
            return count
        except Exception as e:
            logger.error(f"Redis EXISTS 操作失败: keys={keys}, error={e}")
            return 0

    async def expire(self, key: str, seconds: int) -> bool:
        """
        设置键的过期时间

        Author  ：bixuejun(bxjgood@163.com)
        Date    ：2025-10-28 12:16:58
        Args:
            key: 键名
            seconds: 过期时间（秒）

        Returns:
            bool: 是否设置成功
        """
        if not self._redis:
            await self.connect()

        try:
            full_key = self._get_key(key)
            result = await self._redis.expire(full_key, seconds)
            return result
        except Exception as e:
            logger.error(f"Redis EXPIRE 操作失败: key={key}, error={e}")
            return False

    async def ttl(self, key: str) -> int:
        """
        获取键的剩余过期时间

        Author  ：bixuejun(bxjgood@163.com)
        Date    ：2025-10-28 12:16:58
        Args:
            key: 键名

        Returns:
            int: 剩余过期时间（秒），-1 表示永不过期，-2 表示键不存在
        """
        if not self._redis:
            await self.connect()

        try:
            full_key = self._get_key(key)
            ttl_value = await self._redis.ttl(full_key)
            return ttl_value
        except Exception as e:
            logger.error(f"Redis TTL 操作失败: key={key}, error={e}")
            return -2

    async def incr(self, key: str, amount: int = 1) -> int:
        """
        将键的值增加指定数量
        用于计数器等场景

        Author  ：bixuejun(bxjgood@163.com)
        Date    ：2025-10-28 12:16:58
        Args:
            key: 键名
            amount: 增加的数量，默认为 1

        Returns:
            int: 增加后的值
        """
        if not self._redis:
            await self.connect()

        try:
            full_key = self._get_key(key)
            if amount == 1:
                result = await self._redis.incr(full_key)
            else:
                result = await self._redis.incrby(full_key, amount)
            return result
        except Exception as e:
            logger.error(f"Redis INCR 操作失败: key={key}, error={e}")
            return 0

    async def decr(self, key: str, amount: int = 1) -> int:
        """
        将键的值减少指定数量
        用于计数器等场景

        Author  ：bixuejun(bxjgood@163.com)
        Date    ：2025-10-28 12:16:58
        Args:
            key: 键名
            amount: 减少的数量，默认为 1

        Returns:
            int: 减少后的值
        """
        if not self._redis:
            await self.connect()

        try:
            full_key = self._get_key(key)
            if amount == 1:
                result = await self._redis.decr(full_key)
            else:
                result = await self._redis.decrby(full_key, amount)
            return result
        except Exception as e:
            logger.error(f"Redis DECR 操作失败: key={key}, error={e}")
            return 0

    async def hset(
        self,
        name: str,
        key: Optional[str] = None,
        value: Optional[Any] = None,
        mapping: Optional[Dict] = None,
        serialize: bool = True,
    ) -> int:
        """
        设置哈希表字段
        支持单个字段设置和批量字段设置两种方式

        Author  ：bixuejun(bxjgood@163.com)
        Date    ：2025-10-28 12:16:58
        Args:
            name: 哈希表名
            key: 字段名（单个字段模式）
            value: 字段值（单个字段模式）
            mapping: 字典形式的多个字段（批量模式）
            serialize: 是否序列化为 JSON，默认 True

        Returns:
            int: 新增的字段数量
        """
        if not self._redis:
            await self.connect()

        try:
            full_name = self._get_key(name)

            if mapping:
                if serialize:
                    mapping = {
                        k: json.dumps(v, ensure_ascii=False) if not isinstance(v, (str, bytes)) else v
                        for k, v in mapping.items()
                    }
                result = await self._redis.hmset(full_name, mapping)
                return len(mapping) if result else 0
            elif key is not None and value is not None:
                if serialize and not isinstance(value, (str, bytes)):
                    value = json.dumps(value, ensure_ascii=False)
                result = await self._redis.hset(full_name, key, value)
                return result
            else:
                raise ValueError("必须提供 key 和 value 或 mapping 参数")
        except Exception as e:
            logger.error(f"Redis HSET 操作失败: name={name}, error={e}")
            return 0

    async def hget(self, name: str, key: str, default: Any = None, deserialize: bool = True) -> Any:
        """
        获取哈希表字段值

        Author  ：bixuejun(bxjgood@163.com)
        Date    ：2025-10-28 12:16:58
        Args:
            name: 哈希表名
            key: 字段名
            default: 字段不存在时返回的默认值
            deserialize: 是否反序列化 JSON，默认 True

        Returns:
            Any: 字段值，不存在时返回 default
        """
        if not self._redis:
            await self.connect()

        try:
            full_name = self._get_key(name)
            value = await self._redis.hget(full_name, key)

            if value is None:
                return default

            if deserialize and isinstance(value, (str, bytes)):
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            return value
        except Exception as e:
            logger.error(f"Redis HGET 操作失败: name={name}, key={key}, error={e}")
            return default

    async def hgetall(self, name: str, deserialize: bool = True) -> Dict:
        """
        获取哈希表所有字段

        Author  ：bixuejun(bxjgood@163.com)
        Date    ：2025-10-28 12:16:58
        Args:
            name: 哈希表名
            deserialize: 是否反序列化 JSON，默认 True

        Returns:
            Dict: 包含所有字段和值的字典
        """
        if not self._redis:
            await self.connect()

        try:
            full_name = self._get_key(name)
            data = await self._redis.hgetall(full_name)

            if deserialize:
                result = {}
                for k, v in data.items():
                    try:
                        result[k] = json.loads(v)
                    except (json.JSONDecodeError, TypeError):
                        result[k] = v
                return result
            return data
        except Exception as e:
            logger.error(f"Redis HGETALL 操作失败: name={name}, error={e}")
            return {}

    async def hdel(self, name: str, *keys: str) -> int:
        """
        删除哈希表字段

        Author  ：bixuejun(bxjgood@163.com)
        Date    ：2025-10-28 12:16:58
        Args:
            name: 哈希表名
            *keys: 可变参数，一个或多个字段名

        Returns:
            int: 实际删除的字段数量
        """
        if not self._redis:
            await self.connect()

        try:
            full_name = self._get_key(name)
            count = await self._redis.hdel(full_name, *keys)
            return count
        except Exception as e:
            logger.error(f"Redis HDEL 操作失败: name={name}, keys={keys}, error={e}")
            return 0

    async def lpush(self, key: str, *values: Any, serialize: bool = True) -> int:
        """
        从列表左侧推入元素
        支持一次推入多个元素

        Author  ：bixuejun(bxjgood@163.com)
        Date    ：2025-10-28 12:16:58
        Args:
            key: 列表键名
            *values: 可变参数，一个或多个值
            serialize: 是否序列化为 JSON，默认 True

        Returns:
            int: 推入后的列表长度
        """
        if not self._redis:
            await self.connect()

        try:
            full_key = self._get_key(key)
            if serialize:
                values = [json.dumps(v, ensure_ascii=False) if not isinstance(v, (str, bytes)) else v for v in values]
            length = await self._redis.lpush(full_key, *values)
            return length
        except Exception as e:
            logger.error(f"Redis LPUSH 操作失败: key={key}, error={e}")
            return 0

    async def rpush(self, key: str, *values: Any, serialize: bool = True) -> int:
        """
        从列表右侧推入元素
        支持一次推入多个元素

        Author  ：bixuejun(bxjgood@163.com)
        Date    ：2025-10-28 12:16:58
        Args:
            key: 列表键名
            *values: 可变参数，一个或多个值
            serialize: 是否序列化为 JSON，默认 True

        Returns:
            int: 推入后的列表长度
        """
        if not self._redis:
            await self.connect()

        try:
            full_key = self._get_key(key)
            if serialize:
                values = [json.dumps(v, ensure_ascii=False) if not isinstance(v, (str, bytes)) else v for v in values]
            length = await self._redis.rpush(full_key, *values)
            return length
        except Exception as e:
            logger.error(f"Redis RPUSH 操作失败: key={key}, error={e}")
            return 0

    async def lpop(self, key: str, deserialize: bool = True) -> Any:
        """
        从列表左侧弹出元素

        Author  ：bixuejun(bxjgood@163.com)
        Date    ：2025-10-28 12:16:58
        Args:
            key: 列表键名
            deserialize: 是否反序列化 JSON，默认 True

        Returns:
            Any: 弹出的元素，列表为空时返回 None
        """
        if not self._redis:
            await self.connect()

        try:
            full_key = self._get_key(key)
            value = await self._redis.lpop(full_key)

            if value is None:
                return None

            if deserialize and isinstance(value, (str, bytes)):
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            return value
        except Exception as e:
            logger.error(f"Redis LPOP 操作失败: key={key}, error={e}")
            return None

    async def rpop(self, key: str, deserialize: bool = True) -> Any:
        """
        从列表右侧弹出元素

        Author  ：bixuejun(bxjgood@163.com)
        Date    ：2025-10-28 12:16:58
        Args:
            key: 列表键名
            deserialize: 是否反序列化 JSON，默认 True

        Returns:
            Any: 弹出的元素，列表为空时返回 None
        """
        if not self._redis:
            await self.connect()

        try:
            full_key = self._get_key(key)
            value = await self._redis.rpop(full_key)

            if value is None:
                return None

            if deserialize and isinstance(value, (str, bytes)):
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            return value
        except Exception as e:
            logger.error(f"Redis RPOP 操作失败: key={key}, error={e}")
            return None

    async def lrange(self, key: str, start: int = 0, end: int = -1, deserialize: bool = True) -> List:
        """
        获取列表指定范围的元素

        Author  ：bixuejun(bxjgood@163.com)
        Date    ：2025-10-28 12:16:58
        Args:
            key: 列表键名
            start: 起始索引，默认为 0
            end: 结束索引，-1 表示到末尾，默认为 -1
            deserialize: 是否反序列化 JSON，默认 True

        Returns:
            List: 元素列表
        """
        if not self._redis:
            await self.connect()

        try:
            full_key = self._get_key(key)
            values = await self._redis.lrange(full_key, start, end)

            if deserialize:
                result = []
                for v in values:
                    try:
                        result.append(json.loads(v))
                    except (json.JSONDecodeError, TypeError):
                        result.append(v)
                return result
            return values
        except Exception as e:
            logger.error(f"Redis LRANGE 操作失败: key={key}, error={e}")
            return []

    async def llen(self, key: str) -> int:
        """
        获取列表长度

        Author  ：bixuejun(bxjgood@163.com)
        Date    ：2025-10-28 12:16:58
        Args:
            key: 列表键名

        Returns:
            int: 列表长度
        """
        if not self._redis:
            await self.connect()

        try:
            full_key = self._get_key(key)
            length = await self._redis.llen(full_key)
            return length
        except Exception as e:
            logger.error(f"Redis LLEN 操作失败: key={key}, error={e}")
            return 0

    async def keys(self, pattern: str = "*") -> List[str]:
        """
        获取匹配的键列表
        支持通配符模式匹配

        Author  ：bixuejun(bxjgood@163.com)
        Date    ：2025-10-28 12:16:58
        Args:
            pattern: 匹配模式，默认为 "*"（所有键）

        Returns:
            List[str]: 匹配的键列表
        """
        if not self._redis:
            await self.connect()

        try:
            full_pattern = self._get_key(pattern)
            keys = await self._redis.keys(full_pattern)
            # 移除前缀
            if self.prefix:
                prefix_len = len(self.prefix) + 1
                return [key[prefix_len:] for key in keys]
            return keys
        except Exception as e:
            logger.error(f"Redis KEYS 操作失败: pattern={pattern}, error={e}")
            return []

    async def flushdb(self) -> bool:
        """
        清空当前数据库
        警告：此操作会删除当前数据库的所有数据，请谨慎使用

        Author  ：bixuejun(bxjgood@163.com)
        Date    ：2025-10-28 12:16:58
        Args:
            无

        Returns:
            bool: 是否成功
        """
        if not self._redis:
            await self.connect()

        try:
            await self._redis.flushdb()
            logger.warning(f"Redis 数据库 {self.db} 已清空")
            return True
        except Exception as e:
            logger.error(f"Redis FLUSHDB 操作失败: error={e}")
            return False


# 全局 Redis 客户端实例（需要时可以初始化）
_common_redis_client: Optional[CustomRedisClient] = None


def get_common_redis_client(config: dict = settings.common_redis_config) -> CustomRedisClient:
    """
    获取通用的 Redis 客户端实例
    单例模式，全局共享同一个客户端实例

    Author  ：bixuejun(bxjgood@163.com)
    Date    ：2025-10-28 12:16:58
    Args:
        config: Redis 配置字典

    Returns:
        CustomRedisClient: Redis 客户端实例
    """
    global _common_redis_client
    if _common_redis_client is None:
        _common_redis_client = CustomRedisClient(config)
    return _common_redis_client


@asynccontextmanager
async def redis_context(config: dict):
    """
    Redis 客户端上下文管理器
    自动管理连接的建立和关闭，适用于临时操作

    Author  ：bixuejun(bxjgood@163.com)
    Date    ：2025-10-28 15:30:00
    Args:
        config: Redis 配置字典

    Returns:
        AsyncGenerator[CustomRedisClient, None]: Redis 客户端实例生成器
    """
    client = CustomRedisClient(config)
    try:
        await client.connect()
        yield client
    finally:
        await client.close()
