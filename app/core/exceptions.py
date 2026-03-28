from typing import Optional, Dict, Any
from fastapi import HTTPException, Request, status
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


# Exception handler mapping.
exception_handlers = {
    HTTPException: http_exception_handler,
    StarletteHTTPException: starlette_exception_handler,
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
