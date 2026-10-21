from typing import Optional, Dict, Any
from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.schemas.base import ApiResponse
from app.utils.log_control import logger
import traceback


class SettingNotFound(Exception):
    """Configuration file not found."""

    pass


class CustomHTTPException(HTTPException):
    """Custom HTTP exception supporting extra error data."""

    def __init__(
        self,
        status_code: int,
        detail: Optional[str] = None,
        headers: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.data = data


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    HTTP exception handler that returns a unified response shape.
    """
    status_code = exc.status_code
    detail = exc.detail
    data = getattr(exc, "data", None)

    # Record exception details.
    logger.warning(f"HTTP exception - status_code: {status_code}, detail: {detail}, path: {request.url.path}")

    # Return the appropriate response by status code.
    if status_code == 401:
        return ApiResponse.unauthorized(msg=detail, data=data)
    elif status_code == 403:
        return ApiResponse.forbidden(msg=detail, data=data)
    elif status_code == 404:
        return ApiResponse.not_found(msg=detail, data=data)
    elif status_code == 422:
        return ApiResponse.validation_error(msg=detail, data=data)
    elif status_code == 429:
        return ApiResponse.fail(msg=detail, code=429, data=data)
    elif 400 <= status_code < 500:
        return ApiResponse.fail(msg=detail, code=status_code, data=data)
    else:
        return ApiResponse.error(msg=detail, code=status_code, data=data)


async def starlette_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Starlette HTTP exception handler.
    """
    return await http_exception_handler(request, HTTPException(status_code=exc.status_code, detail=exc.detail))


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for uncaught exceptions.
    """
    # Record the full exception details.
    logger.error(f"Unhandled exception: {type(exc).__name__}: {str(exc)}")
    logger.error(f"Request path: {request.url.path}")
    logger.error(f"Exception traceback:\n{traceback.format_exc()}")

    # Return a unified error response.
    return ApiResponse.error(msg="服务器内部错误", data=None)


# 请求参数校验错误的字段名中文映射（未映射字段原样展示；业务项目可按需补充条目）
VALIDATION_FIELD_LABELS = {}

# 校验错误类型的中文描述
VALIDATION_TYPE_MESSAGES = {
    "string_pattern_mismatch": "格式不正确",
    "string_too_short": "长度不足",
    "string_too_long": "长度超限",
    "missing": "为必填项，不能为空",
    "value_error": "取值无效",
    "int_parsing": "应为数字",
    "bool_parsing": "应为布尔值",
    "json_invalid": "应为合法 JSON",
}


def _validation_message(errors: list) -> str:
    """把 Pydantic 校验错误列表转为用户可读中文提示（哪个参数、什么问题）。

    Author  ：bixuejun(bxjgood@163.com)
    Date    ：2026-10-12 20:35:00  # 北京时间 UTC+8

    Args:
        errors: FastAPI RequestValidationError.errors() 列表

    Returns:
        中文提示（多错误以；拼接，最多 3 条）
    """
    parts: list[str] = []
    for err in errors[:3]:
        field_path = ".".join(str(loc) for loc in err.get("loc", []) if str(loc) != "body")
        label = VALIDATION_FIELD_LABELS.get(field_path, field_path or "请求参数")
        reason = VALIDATION_TYPE_MESSAGES.get(err.get("type"), "不正确")
        parts.append(f"「{label}」{reason}")
    return "请求参数有误：" + "；".join(parts) + "。请检查后重试"


async def validation_exception_handler(request: Request, exc) -> JSONResponse:
    """
    请求参数校验失败（422）统一转中文可读提示（替代 FastAPI 原始 detail 数组）。

    Author  ：bixuejun(bxjgood@163.com)
    Date    ：2026-10-12 20:35:00  # 北京时间 UTC+8

    Args:
        request: 请求
        exc: RequestValidationError

    Returns:
        统一业务错误响应（code=422）
    """
    message = _validation_message(exc.errors())
    logger.warning(f"Validation error - path: {request.url.path}, message: {message}")
    return ApiResponse.fail(msg=message, code=422, data=None)


# Exception handler mapping.
exception_handlers = {
    HTTPException: http_exception_handler,
    StarletteHTTPException: starlette_exception_handler,
    RequestValidationError: validation_exception_handler,
    Exception: global_exception_handler,
}


# Authentication-related exceptions.
class AuthenticationError(CustomHTTPException):
    """Authentication error."""

    def __init__(self, detail: str = "认证失败", data: Optional[Dict[str, Any]] = None):
        super().__init__(status_code=401, detail=detail, data=data)


class AuthorizationError(CustomHTTPException):
    """Authorization error."""

    def __init__(self, detail: str = "权限不足", data: Optional[Dict[str, Any]] = None):
        super().__init__(status_code=403, detail=detail, data=data)


class RateLimitError(CustomHTTPException):
    """Rate-limit error."""

    def __init__(self, detail: str = "请求过于频繁", data: Optional[Dict[str, Any]] = None):
        super().__init__(status_code=429, detail=detail, data=data)


class ValidationError(CustomHTTPException):
    """Validation error."""

    def __init__(self, detail: str = "数据验证失败", data: Optional[Dict[str, Any]] = None):
        super().__init__(status_code=422, detail=detail, data=data)


# CRUD-related exceptions.
class RecordNotFoundError(CustomHTTPException):
    """Record not found error."""

    def __init__(self, detail: str = "记录不存在", data: Optional[Dict[str, Any]] = None):
        super().__init__(status_code=404, detail=detail, data=data)


class RecordAlreadyExistsError(CustomHTTPException):
    """Record already exists error."""

    def __init__(self, detail: str = "记录已存在", data: Optional[Dict[str, Any]] = None):
        super().__init__(status_code=409, detail=detail, data=data)


class InvalidParameterError(CustomHTTPException):
    """Invalid parameter error."""

    def __init__(self, detail: str = "参数无效", data: Optional[Dict[str, Any]] = None):
        super().__init__(status_code=400, detail=detail, data=data)
