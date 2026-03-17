import json
import re
from datetime import datetime
from typing import Any, AsyncGenerator

from fastapi import FastAPI
from fastapi.responses import Response
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from app.models.admin import AuditLog

from .bgtask import BgTasks


class SimpleBaseMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)

        response = await self.before_request(request) or self.app
        await response(request.scope, request.receive, send)
        await self.after_request(request)

    async def before_request(self, request: Request):
        return self.app

    async def after_request(self, request: Request):
        return None


class BackGroundTaskMiddleware(SimpleBaseMiddleware):
    async def before_request(self, request):
        await BgTasks.init_bg_tasks_obj()

    async def after_request(self, request):
        await BgTasks.execute_tasks()


class DatabaseContextMiddleware(BaseHTTPMiddleware):
    """为每个请求显式绑定 TortoiseContext。"""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        db_runtime = getattr(request.app.state, "db_runtime", None)
        if db_runtime is None:
            return await call_next(request)

        async with db_runtime.activate():
            return await call_next(request)


class HttpAuditLogMiddleware(BaseHTTPMiddleware):
    sensitive_keys = {
        "password",
        "old_password",
        "new_password",
        "confirm_password",
        "access_token",
        "refresh_token",
        "token",
        "authorization",
        "secret_key",
    }

    def __init__(self, app, methods: list[str], exclude_paths: list[str]):
        super().__init__(app)
        self.methods = methods
        self.exclude_paths = exclude_paths
        self.max_body_size = 1024 * 1024  # 1MB 响应体大小限制
        # 编译正则表达式提高性能
        self.exclude_paths_regex = [re.compile(path, re.I) for path in exclude_paths]

    def redact_sensitive_data(self, value: Any) -> Any:
        if isinstance(value, dict):
            redacted = {}
            for key, item in value.items():
                if isinstance(key, str) and key.lower() in self.sensitive_keys:
                    redacted[key] = "***REDACTED***"
                else:
                    redacted[key] = self.redact_sensitive_data(item)
            return redacted

        if isinstance(value, list):
            return [self.redact_sensitive_data(item) for item in value]

        return value

    async def get_request_args(self, request: Request) -> dict:
        """获取请求参数，优化处理逻辑"""
        args = {}

        try:
            # 获取查询参数
            for key, value in request.query_params.items():
                args[key] = value

            # 获取请求体
            if request.method in ["POST", "PUT", "PATCH"]:
                try:
                    body_bytes = await request.body()
                    if not body_bytes:
                        return args

                    content_type = request.headers.get("content-type", "").lower()

                    # 针对不同内容类型分别处理
                    if "application/json" in content_type:
                        body_str = body_bytes.decode("utf-8", errors="replace")
                        try:
                            body = json.loads(body_str)
                            if isinstance(body, dict):
                                for k, v in body.items():
                                    if hasattr(v, "filename"):  # 文件上传行为
                                        args[k] = v.filename
                                    elif isinstance(v, list) and v and hasattr(v[0], "filename"):
                                        args[k] = [file.filename for file in v]
                                    else:
                                        args[k] = v
                            else:
                                args["body"] = body
                        except json.JSONDecodeError:
                            args["raw_body"] = body_str[:1000]
                    elif "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
                        try:
                            # 对于含有文件上传的请求，只记录文件名称和大小，而不是整个文件对象
                            form = await request.form()
                            for k, v in form.items():
                                # 如果是文件对象，只保存文件信息
                                if hasattr(v, "filename") and hasattr(v, "size"):
                                    args[k] = {
                                        "filename": getattr(v, "filename", "unknown"),
                                        "content_type": getattr(v, "content_type", "unknown"),
                                        "size": getattr(v, "size", 0),
                                    }
                                else:
                                    args[k] = str(v)
                        except Exception as e:
                            args["form_parse_error"] = str(e)[:200]
                    else:
                        # 其他内容类型，存储有限的原始内容
                        args["raw_body"] = body_bytes.decode("utf-8", errors="replace")[:1000]
                except Exception as e:
                    args["parse_error"] = str(e)[:200]
        except Exception as e:
            args["middleware_error"] = str(e)[:200]

        return args

    async def get_response_body(self, request: Request, response: Response) -> Any:
        """获取响应体内容，优化大型响应体处理"""
        # 检查Content-Length以避免处理过大的响应
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) > self.max_body_size:
            return {"truncated": True, "message": "Response too large to log"}

        content_type = (response.headers.get("content-type") or "").lower()
        if content_type.startswith(("image/", "audio/", "video/", "font/")):
            return {"truncated": True, "message": f"Binary response skipped: {content_type}"}
        if any(
            marker in content_type
            for marker in (
                "application/octet-stream",
                "application/pdf",
                "application/zip",
                "application/vnd",
                "multipart/",
            )
        ):
            return {"truncated": True, "message": f"Binary response skipped: {content_type}"}

        try:
            # 获取响应体
            if hasattr(response, "body"):
                body = response.body
            else:
                # 收集响应体片段
                body_chunks = []
                async for chunk in response.body_iterator:
                    if not isinstance(chunk, bytes):
                        chunk = chunk.encode(response.charset)
                    body_chunks.append(chunk)

                # 重建响应迭代器
                response.body_iterator = self._async_iter(body_chunks)
                body = b"".join(body_chunks)

            # 解析响应体
            return await self.lenient_json(body)
        except Exception as e:
            return {"error": f"Response parsing error: {str(e)[:200]}"}

    async def lenient_json(self, v: Any) -> Any:
        """优化的JSON解析方法，减少异步操作开销"""
        if v is None:
            return {}

        # 处理字节类型
        if isinstance(v, bytes):
            try:
                v = v.decode("utf-8", errors="replace")
            except Exception:
                return {"raw_content": "Binary content"}

        # 处理字符串类型
        if isinstance(v, str):
            if not v or v.isspace():
                return {}

            try:
                # 对于小型字符串，直接解析而不使用异步
                if len(v) < 10000:  # 10KB以下直接处理
                    return json.loads(v)

                # 大型字符串使用异步处理
                import asyncio

                result = await asyncio.to_thread(json.loads, v)
                return result
            except (ValueError, TypeError, json.JSONDecodeError):
                # 解析失败则返回截断的原始内容
                preview = str(v)[:100] + ("..." if len(str(v)) > 100 else "")
                return {"raw_content": preview}

        # 非字符串类型直接返回
        return v

    async def _async_iter(self, items: list[bytes]) -> AsyncGenerator[bytes, None]:
        for item in items:
            yield item

    async def get_request_log(self, request: Request, response: Response) -> dict:
        """根据request和response对象获取对应的日志记录数据，优化路由匹配逻辑"""
        data = {
            "path": request.url.path,
            "status": response.status_code,
            "method": request.method,
            "module": "",
            "summary": "",
            "user_id": 0,
            "username": "",
            "ip_address": request.client.host if request.client else "",
            "user_agent": request.headers.get("user-agent", ""),
        }

        # 设置操作类型
        operation_map = {"GET": "查询", "POST": "创建", "PUT": "更新", "DELETE": "删除"}
        data["operation_type"] = operation_map.get(request.method, "其他")

        # 设置日志级别
        if 200 <= response.status_code < 300:
            data["log_level"] = "info"
        elif 300 <= response.status_code < 400:
            data["log_level"] = "warning"
        else:
            data["log_level"] = "error"

        # 路由信息
        app: FastAPI = request.app
        for route in app.routes:
            if (
                isinstance(route, APIRoute)
                and route.path_regex.match(request.url.path)
                and request.method in route.methods
            ):
                data["module"] = ",".join(route.tags)
                data["summary"] = route.summary
                break

        # 获取用户信息
        user_obj = getattr(request.state, "current_user", None)
        if user_obj:
            data["user_id"] = user_obj.id
            data["username"] = user_obj.username

        return data

    async def should_skip_log(self, request: Request) -> bool:
        """判断是否应该跳过日志记录"""
        # 检查请求方法
        if request.method not in self.methods:
            return True

        # 检查排除路径
        path = request.url.path
        for pattern in self.exclude_paths_regex:
            if pattern.search(path):
                return True

        return False

    async def before_request(self, request: Request):
        """请求前处理"""
        # 如果不需要记录日志，就不获取请求参数
        if await self.should_skip_log(request):
            request.state.skip_audit_log = True
            return

        request_args = await self.get_request_args(request)
        request.state.request_args = request_args

    def safe_serialize(self, obj: Any) -> Any:
        """
        安全地序列化对象，确保复杂对象可以被JSON序列化

        Args:
            obj: 要序列化的对象

        Returns:
            转换后可以安全序列化的对象
        """
        if obj is None:
            return None

        # 处理基本类型
        if isinstance(obj, (str, int, float, bool)):
            return obj

        # 处理列表
        if isinstance(obj, list):
            return [self.safe_serialize(item) for item in obj]

        # 处理字典
        if isinstance(obj, dict):
            return {k: self.safe_serialize(v) for k, v in obj.items()}

        # 处理其他复杂对象
        try:
            # 尝试将对象转换为字典
            if hasattr(obj, "__dict__"):
                return {"_type": obj.__class__.__name__, **self.safe_serialize(obj.__dict__)}

            # 尝试将对象转换为字符串
            return str(obj)
        except Exception:
            # 如果无法序列化，返回对象类型名称
            return f"<Non-serializable object: {obj.__class__.__name__}>"

    async def after_request(self, request: Request, response: Response, process_time: int):
        """请求后处理"""
        # 检查是否需要跳过日志记录
        if getattr(request.state, "skip_audit_log", False):
            return response

        data = await self.get_request_log(request=request, response=response)
        data["response_time"] = process_time

        # 添加请求参数
        request_args = getattr(request.state, "request_args", {}) or {}
        # 确保请求参数可以序列化为JSON
        data["request_args"] = self.redact_sensitive_data(self.safe_serialize(request_args))

        # 添加响应体
        response_body = await self.get_response_body(request, response)
        # 确保响应体可以序列化为JSON
        data["response_body"] = self.redact_sensitive_data(self.safe_serialize(response_body))

        # 将数据库操作添加到后台任务
        await BgTasks.add_task(AuditLog.create, **data)

        return response

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """请求调度处理"""
        start_time = datetime.now()
        await self.before_request(request)
        response = await call_next(request)
        end_time = datetime.now()
        process_time = int((end_time.timestamp() - start_time.timestamp()) * 1000)
        await self.after_request(request, response, process_time)
        return response
