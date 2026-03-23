from fastapi import APIRouter, Request

from app.core.exceptions import AuthorizationError
from app.core.dependency import CurrentUser
from app.models import User
from app.schemas.base import Success
from app.schemas.system_settings import (
    ApplicationSettingsUpdate,
    LoggingSettingsUpdate,
    SecuritySettingsUpdate,
    StorageSettingsUpdate,
)
from app.services import system_setting_service

router = APIRouter()


def ensure_superuser(current_user: User) -> None:
    if not current_user.is_superuser:
        raise AuthorizationError("只有超级管理员才能访问系统设置")


@router.get("/storage", summary="查看存储设置", openapi_extra={"skip_api_catalog": True})
async def get_storage_settings(current_user: CurrentUser):
    ensure_superuser(current_user)
    return Success(data=await system_setting_service.get_storage_settings())


@router.get("/application", summary="查看基础设置", openapi_extra={"skip_api_catalog": True})
async def get_application_settings(current_user: CurrentUser):
    ensure_superuser(current_user)
    return Success(data=await system_setting_service.get_application_settings())


@router.post("/application", summary="更新基础设置", openapi_extra={"skip_api_catalog": True})
async def update_application_settings(
    payload: ApplicationSettingsUpdate,
    request: Request,
    current_user: CurrentUser,
):
    ensure_superuser(current_user)
    data = await system_setting_service.update_application_settings(payload, app=request.app)
    return Success(data=data, msg="基础设置已更新")


@router.get("/security", summary="查看安全设置", openapi_extra={"skip_api_catalog": True})
async def get_security_settings(current_user: CurrentUser):
    ensure_superuser(current_user)
    return Success(data=await system_setting_service.get_security_settings())


@router.get("/logging", summary="查看日志设置", openapi_extra={"skip_api_catalog": True})
async def get_logging_settings(current_user: CurrentUser):
    ensure_superuser(current_user)
    return Success(data=await system_setting_service.get_logging_settings())


@router.post("/security", summary="更新安全设置", openapi_extra={"skip_api_catalog": True})
async def update_security_settings(
    payload: SecuritySettingsUpdate,
    request: Request,
    current_user: CurrentUser,
):
    ensure_superuser(current_user)
    data = await system_setting_service.update_security_settings(payload, app=request.app)
    return Success(data=data, msg="安全设置已更新")


@router.post("/logging", summary="更新日志设置", openapi_extra={"skip_api_catalog": True})
async def update_logging_settings(
    payload: LoggingSettingsUpdate,
    request: Request,
    current_user: CurrentUser,
):
    ensure_superuser(current_user)
    data = await system_setting_service.update_logging_settings(payload, app=request.app)
    return Success(data=data, msg="日志设置已更新")


@router.post("/storage", summary="更新存储设置", openapi_extra={"skip_api_catalog": True})
async def update_storage_settings(
    payload: StorageSettingsUpdate,
    current_user: CurrentUser,
):
    ensure_superuser(current_user)
    data = await system_setting_service.update_storage_settings(payload)
    return Success(data=data, msg="存储设置已更新")
