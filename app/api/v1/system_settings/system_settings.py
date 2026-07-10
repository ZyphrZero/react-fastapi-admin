from fastapi import APIRouter, Request
from pydantic import ValidationError as PydanticValidationError
from starlette.datastructures import UploadFile

from app.core.exceptions import AuthorizationError, ValidationError
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
from app.services.upload_service import upload_service

router = APIRouter()


APPLICATION_TEXT_FIELDS = (
    "app_title",
    "project_name",
    "app_description",
    "login_page_image_mode",
    "notification_position",
)
APPLICATION_NUMERIC_FIELDS = (
    "login_page_image_zoom",
    "login_page_image_position_x",
    "login_page_image_position_y",
    "notification_duration",
    "notification_visible_toasts",
)


def _build_application_settings(data: dict) -> ApplicationSettingsUpdate:
    try:
        return ApplicationSettingsUpdate.model_validate(data)
    except PydanticValidationError as exc:
        errors = exc.errors()
        message = errors[0].get("msg") if errors else "数据验证失败"
        raise ValidationError(str(message)) from exc


async def _application_settings_from_form(form) -> ApplicationSettingsUpdate:
    """Build application settings from multipart form-data, resolving the login-page image."""
    action = (str(form.get("login_page_image_action") or "keep")).strip().lower()
    login_page_image_url = (str(form.get("login_page_image_url") or "")).strip()

    if action == "replace":
        image_file = form.get("login_page_image_file")
        if not isinstance(image_file, UploadFile):
            raise ValidationError("请选择要上传的登录页图片")
        upload_result = await upload_service.upload_image(image_file)
        login_page_image_url = upload_result["url"]
    elif action == "remove":
        login_page_image_url = ""
    # action == "keep": keep the provided login_page_image_url

    data: dict = {"login_page_image_url": login_page_image_url}
    for field in APPLICATION_TEXT_FIELDS + APPLICATION_NUMERIC_FIELDS:
        value = form.get(field)
        if value is not None:
            data[field] = value
    debug_value = form.get("debug")
    if debug_value is not None:
        data["debug"] = debug_value

    return _build_application_settings(data)


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
    request: Request,
    current_user: CurrentUser,
):
    ensure_superuser(current_user)
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        payload = await _application_settings_from_form(form)
    else:
        payload = _build_application_settings(await request.json())
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
