import json
import re
from datetime import datetime
from typing import Any

from fastapi import FastAPI
from fastapi.responses import Response
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from app.models.admin import AuditLog
from app.repositories.api_repository import ApiRepository

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
    """Explicitly bind `TortoiseContext` for each request."""

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
        self.max_body_size = 1024 * 1024  # 1 MB response-body size limit.
        # Compile regular expressions up front for better performance.
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
        """Return request arguments with optimized parsing logic."""
        args = {}

        try:
            # Collect query parameters.
            for key, value in request.query_params.items():
                args[key] = value

            # Collect the request body.
            if request.method in ["POST", "PUT", "PATCH"]:
                try:
                    body_bytes = await request.body()
                    if not body_bytes:
                        return args

                    content_type = request.headers.get("content-type", "").lower()

                    # Handle each content type separately.
                    if "application/json" in content_type:
                        body_str = body_bytes.decode("utf-8", errors="replace")
                        try:
                            body = json.loads(body_str)
                            if isinstance(body, dict):
                                for k, v in body.items():
                                    if hasattr(v, "filename"):  # File upload payload.
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
                            # For file uploads, record only file metadata instead of the whole file object.
                            form = await request.form()
                            for k, v in form.items():
                                # Persist only file metadata for uploaded files.
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
                        # For other content types, keep only a limited raw preview.
                        args["raw_body"] = body_bytes.decode("utf-8", errors="replace")[:1000]
                except Exception as e:
                    args["parse_error"] = str(e)[:200]
        except Exception as e:
            args["middleware_error"] = str(e)[:200]

        return args

    async def get_response_body(self, request: Request, response: Response) -> Any:
        """Return the response body while handling large payloads efficiently."""
        # Check Content-Length to avoid processing oversized responses.
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
            # Read the response body.
            if hasattr(response, "body"):
                body = response.body
            else:
                return {"truncated": True, "message": "Streaming response skipped"}

            if isinstance(body, bytes) and len(body) > self.max_body_size:
                return {"truncated": True, "message": "Response too large to log"}

            # Parse the response body.
            return await self.lenient_json(body)
        except Exception as e:
            return {"error": f"Response parsing error: {str(e)[:200]}"}

    async def lenient_json(self, v: Any) -> Any:
        """Parse JSON leniently while reducing unnecessary async overhead."""
        if v is None:
            return {}

        # Handle byte strings.
        if isinstance(v, bytes):
            try:
                v = v.decode("utf-8", errors="replace")
            except Exception:
                return {"raw_content": "Binary content"}

        # Handle regular strings.
        if isinstance(v, str):
            if not v or v.isspace():
                return {}

            try:
                # Parse small strings inline without extra async overhead.
                if len(v) < 10000:  # Handle payloads smaller than 10 KB inline.
                    return json.loads(v)

                # Parse large strings in a worker thread.
                import asyncio

                result = await asyncio.to_thread(json.loads, v)
                return result
            except (ValueError, TypeError, json.JSONDecodeError):
                # If parsing fails, return a truncated raw preview.
                preview = str(v)[:100] + ("..." if len(str(v)) > 100 else "")
                return {"raw_content": preview}

        # Return non-string values as-is.
        return v

    async def get_request_log(self, request: Request, response: Response) -> dict:
        """Build audit-log data from the request and response with optimized route matching."""
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

        # Set the operation type.
        operation_map = {"GET": "查询", "POST": "创建", "PUT": "更新", "DELETE": "删除"}
        data["operation_type"] = operation_map.get(request.method, "其他")

        # Set the log level.
        if 200 <= response.status_code < 300:
            data["log_level"] = "info"
        elif 300 <= response.status_code < 400:
            data["log_level"] = "warning"
        else:
            data["log_level"] = "error"

        # Resolve route metadata.
        app: FastAPI = request.app
        for route in app.routes:
            if (
                isinstance(route, APIRoute)
                and route.path_regex.match(request.url.path)
                and request.method in route.methods
            ):
                data["module"] = ",".join(route.tags)
                data["summary"] = ApiRepository.require_route_summary(route)
                break

        # Attach user information when available.
        user_obj = getattr(request.state, "current_user", None)
        if user_obj:
            data["user_id"] = user_obj.id
            data["username"] = user_obj.username

        return data

    async def should_skip_log(self, request: Request) -> bool:
        """Return whether audit logging should be skipped for the request."""
        # Check the request method.
        if request.method not in self.methods:
            return True

        # Check excluded paths.
        path = request.url.path
        for pattern in self.exclude_paths_regex:
            if pattern.search(path):
                return True

        return False

    async def before_request(self, request: Request):
        """Handle request preprocessing."""
        # Skip request-argument collection when logging is not needed.
        if await self.should_skip_log(request):
            request.state.skip_audit_log = True
            return

        request_args = await self.get_request_args(request)
        request.state.request_args = request_args

    def safe_serialize(self, obj: Any) -> Any:
        """
        Safely serialize an object so complex values can be converted to JSON.

        Args:
            obj: Object to serialize.

        Returns:
            A JSON-safe representation of the object.
        """
        if obj is None:
            return None

        # Handle primitive types.
        if isinstance(obj, (str, int, float, bool)):
            return obj

        # Handle lists.
        if isinstance(obj, list):
            return [self.safe_serialize(item) for item in obj]

        # Handle dictionaries.
        if isinstance(obj, dict):
            return {k: self.safe_serialize(v) for k, v in obj.items()}

        # Handle other complex objects.
        try:
            # Try to serialize the object via `__dict__`.
            if hasattr(obj, "__dict__"):
                return {"_type": obj.__class__.__name__, **self.safe_serialize(obj.__dict__)}

            # Fall back to the string representation.
            return str(obj)
        except Exception:
            # Return the object type name when serialization fails completely.
            return f"<Non-serializable object: {obj.__class__.__name__}>"

    async def after_request(self, request: Request, response: Response, process_time: int):
        """Handle post-response processing."""
        # Check whether logging should be skipped.
        if getattr(request.state, "skip_audit_log", False):
            return response

        data = await self.get_request_log(request=request, response=response)
        data["response_time"] = process_time

        # Attach request arguments.
        request_args = getattr(request.state, "request_args", {}) or {}
        # Ensure request arguments can be serialized to JSON.
        data["request_args"] = self.redact_sensitive_data(self.safe_serialize(request_args))

        # Attach the response body.
        response_body = await self.get_response_body(request, response)
        # Ensure the response body can be serialized to JSON.
        data["response_body"] = self.redact_sensitive_data(self.safe_serialize(response_body))

        # Defer the database write to a background task.
        await BgTasks.add_task(AuditLog.create, **data)

        return response

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Handle request dispatch."""
        start_time = datetime.now()
        await self.before_request(request)
        response = await call_next(request)
        end_time = datetime.now()
        process_time = int((end_time.timestamp() - start_time.timestamp()) * 1000)
        await self.after_request(request, response, process_time)
        return response
