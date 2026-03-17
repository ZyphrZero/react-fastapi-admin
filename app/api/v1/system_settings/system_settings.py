from fastapi import APIRouter, Depends

from app.core.exceptions import AuthorizationError
from app.core.dependency import AuthControl
from app.models import User
from app.schemas.base import Success
from app.schemas.system_settings import StorageSettingsUpdate
from app.services import system_setting_service

router = APIRouter()


def ensure_superuser(current_user: User) -> None:
    if not current_user.is_superuser:
        raise AuthorizationError("只有超级管理员才能访问系统设置")


@router.get("/storage", summary="查看存储设置", openapi_extra={"skip_api_catalog": True})
async def get_storage_settings(current_user: User = Depends(AuthControl.is_authed)):
    ensure_superuser(current_user)
    return Success(data=await system_setting_service.get_storage_settings())


@router.post("/storage", summary="更新存储设置", openapi_extra={"skip_api_catalog": True})
async def update_storage_settings(
    payload: StorageSettingsUpdate,
    current_user: User = Depends(AuthControl.is_authed),
):
    ensure_superuser(current_user)
    data = await system_setting_service.update_storage_settings(payload)
    return Success(data=data, msg="存储设置已更新")
