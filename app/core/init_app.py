from fastapi import FastAPI
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.exceptions import exception_handlers
from app.settings.config import settings
from app.utils.log_control import AccessLogMiddleware

from .middlewares import BackGroundTaskMiddleware, DatabaseContextMiddleware, HttpAuditLogMiddleware


def make_middlewares() -> list[Middleware]:
    middleware = [
        Middleware(DatabaseContextMiddleware),
        Middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
            allow_methods=settings.CORS_ALLOW_METHODS,
            allow_headers=settings.CORS_ALLOW_HEADERS,
        ),
        Middleware(BackGroundTaskMiddleware),
    ]

    if settings.LOG_ENABLE_ACCESS_LOG:
        middleware.append(
            Middleware(
                AccessLogMiddleware,
                skip_paths=["/docs", "/redoc", "/openapi.json", "/favicon.ico", "/static/", "/health"],
            )
        )

    middleware.append(
        Middleware(
            HttpAuditLogMiddleware,
            methods=["GET", "POST", "PUT", "DELETE"],
            exclude_paths=[
                "/health",
                "/docs",
                "/openapi.json",
                "/static/",
                "/api/v1/auditlog/list",
                "/api/v1/auditlog/detail",
                "/api/v1/auditlog/delete",
                "/api/v1/auditlog/batch_delete",
                "/api/v1/auditlog/clear",
                "/api/v1/auditlog/export",
                "/api/v1/auditlog/download",
                "/api/v1/auditlog/statistics",
            ],
        )
    )

    return middleware


def register_exceptions(app: FastAPI) -> None:
    """注册异常处理器。"""
    for exception_type, handler in exception_handlers.items():
        app.add_exception_handler(exception_type, handler)


def register_routers(app: FastAPI, prefix: str = "/api") -> None:
    """注册所有 API 路由。"""
    app.include_router(api_router, prefix=prefix)
