from typing import Dict, Optional, Set
import time

import jwt
from fastapi import Depends, Header, Request, Query

from app.core.ctx import CTX_USER_ID
from app.core.exceptions import AuthenticationError, AuthorizationError, RateLimitError
from app.models import User
from app.repositories import user_repository
from app.settings import settings
from app.utils.jwt_utils import decode_token


class AuthControl:
    """身份验证控制器"""

    # 用于存储用户请求频率限制
    _rate_limit_data: Dict[str, Dict[str, int]] = {}

    # 从配置文件加载IP白名单
    _ip_whitelist: Set[str] = set(settings.ip_whitelist)

    @classmethod
    async def initialize(cls):
        """初始化身份验证控制器"""
        # 加载白名单
        cls._ip_whitelist = set(settings.ip_whitelist)
        # 清空过期数据
        cls._clear_expired_data()

    @classmethod
    def _clear_expired_data(cls):
        """清理过期的频率限制数据"""
        current_time = int(time.time())
        expired_keys = []

        for key, data in cls._rate_limit_data.items():
            if current_time - data["timestamp"] > settings.RATE_LIMIT_WINDOW_SECONDS * 2:
                expired_keys.append(key)

        for key in expired_keys:
            cls._rate_limit_data.pop(key, None)

    @classmethod
    def enforce_rate_limit(cls, key: str) -> None:
        """
        检查请求频率限制
        :param key: 限流键
        """
        if not settings.RATE_LIMIT_ENABLED:
            return

        current_time = int(time.time())
        max_requests = settings.RATE_LIMIT_MAX_REQUESTS
        time_window = settings.RATE_LIMIT_WINDOW_SECONDS

        if key not in cls._rate_limit_data:
            cls._rate_limit_data[key] = {"count": 1, "timestamp": current_time}
            return

        data = cls._rate_limit_data[key]
        if current_time - data["timestamp"] > time_window:
            cls._rate_limit_data[key] = {"count": 1, "timestamp": current_time}
            return

        data["count"] += 1
        if data["count"] > max_requests:
            raise RateLimitError("请求过于频繁，请稍后再试")

    @classmethod
    def check_ip_whitelist(cls, client_ip: str) -> bool:
        """检查IP是否在白名单中，如果白名单为空则不检查"""
        if not cls._ip_whitelist:
            return True
        return client_ip in cls._ip_whitelist

    @classmethod
    def _get_client_ip(cls, request: Optional[Request]) -> str:
        """获取客户端IP地址"""
        if not request or not request.client:
            return "0.0.0.0"
        return request.client.host

    @classmethod
    def get_client_ip(cls, request: Optional[Request]) -> str:
        return cls._get_client_ip(request)

    @classmethod
    def extract_bearer_token(cls, authorization: str) -> str:
        if not authorization:
            raise AuthenticationError("缺少 Authorization 请求头")

        scheme, _, credentials = authorization.partition(" ")
        if scheme.lower() != "bearer" or not credentials:
            raise AuthenticationError("Authorization 请求头格式必须为 Bearer <token>")

        return credentials.strip()

    @classmethod
    def _validate_access_token(cls, token: str) -> dict:
        """
        验证JWT token并返回用户ID
        :param token: JWT token
        :return: 解码后的载荷
        :raises AuthenticationError: 当token无效时抛出异常
        """
        try:
            decode_data = decode_token(token, expected_type="access")
            if not decode_data.get("user_id"):
                raise AuthenticationError("Token中缺少用户标识")
            if decode_data.get("session_version") is None:
                raise AuthenticationError("Token中缺少会话版本")
            return decode_data

        # 按照异常的具体程度排序，先处理具体异常，再处理通用异常
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("登录已过期")
        except jwt.InvalidAlgorithmError:
            raise AuthenticationError("无效的签名算法")
        except jwt.InvalidAudienceError:
            raise AuthenticationError("无效的Token受众")
        except jwt.InvalidIssuerError:
            raise AuthenticationError("无效的Token签发者")
        except jwt.InvalidTokenError:
            raise AuthenticationError("无效的Token")

    @classmethod
    async def is_authed(
        cls, request: Request, authorization: str = Header(..., description="Bearer access token")
    ) -> Optional["User"]:
        """
        身份验证主方法
        :param authorization: Bearer token
        :param request: 请求对象
        :return: 用户对象
        """
        try:
            client_ip = cls._get_client_ip(request)
            if not cls.check_ip_whitelist(client_ip):
                raise AuthorizationError("IP地址未授权访问")

            token = cls.extract_bearer_token(authorization)
            payload = cls._validate_access_token(token)
            user_id = int(payload["user_id"])
            session_version = int(payload["session_version"])

            user = await user_repository.get(user_id)
            if not user:
                raise AuthenticationError("用户不存在或已被删除")
            if not user.is_active:
                raise AuthorizationError("用户已被禁用")
            if user.session_version != session_version:
                raise AuthenticationError("登录状态已失效，请重新登录")

            cls.enforce_rate_limit(f"{client_ip}:{user_id}")
            CTX_USER_ID.set(int(user_id))
            request.state.current_user = user
            return user

        except (AuthenticationError, AuthorizationError, RateLimitError):
            raise
        except Exception as e:
            raise AuthenticationError(f"认证失败: {repr(e)}")


class PermissionControl:
    """简化的权限控制器 - 只检查超级用户权限"""

    @classmethod
    async def has_permission(cls, request: Request, current_user: User = Depends(AuthControl.is_authed)) -> None:
        """
        简化的权限检查 - 只允许超级用户访问
        :param request: 请求对象
        :param current_user: 当前用户
        """
        # 超级用户跳过权限检查
        if current_user.is_superuser:
            return

        # 非超级用户禁止访问需要权限的资源
        method = request.method
        path = request.url.path
        raise AuthorizationError(f"权限不足 - 方法:{method} 路径:{path}")

    @classmethod
    async def check_permission_by_code(cls, current_user: User, permission_code: str) -> bool:
        """简化的权限代码检查 - 只检查超级用户"""
        return current_user.is_superuser


async def get_page_params(
    page: int = Query(1, description="页码", ge=1),
    page_size: int = Query(10, description="每页数量", ge=1, le=100),
) -> Dict[str, int]:
    """
    页码参数依赖，用于分页查询
    :param page: 页码，从1开始
    :param page_size: 每页数量，最大100
    :return: 分页参数字典
    """
    return {"page": page, "page_size": page_size}


# 依赖注入快捷方式
DependAuth = Depends(AuthControl.is_authed)
DependPermisson = Depends(PermissionControl.has_permission)
