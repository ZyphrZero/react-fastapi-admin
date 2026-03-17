from fastapi import APIRouter

from .system_settings import router

system_settings_router = APIRouter()
system_settings_router.include_router(router, tags=["系统设置"])

__all__ = ["system_settings_router"]
