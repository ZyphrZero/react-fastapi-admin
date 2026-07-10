from fastapi import APIRouter, Cookie, File, Request, Response, UploadFile
from pydantic import ValidationError as PydanticValidationError
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.core.dependency import AuthControl, CurrentUser
from app.core.exceptions import AuthenticationError, ValidationError
from app.schemas.base import Success
from app.schemas.login import CredentialsSchema
from app.schemas.users import ProfileUpdate, UpdatePassword
from app.settings import settings
from app.services import auth_service
from app.services.upload_service import upload_service
from app.utils.password import get_password_policy

router = APIRouter()


def set_refresh_token_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        value=refresh_token,
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=settings.refresh_token_cookie_secure,
        samesite=settings.REFRESH_TOKEN_COOKIE_SAMESITE,
        path="/api",
    )


def clear_refresh_token_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        path="/api",
    )


def build_public_token_payload(payload: dict) -> dict:
    return {key: value for key, value in payload.items() if key != "refresh_token"}


@router.post("/access_token", summary="获取token")
async def login_access_token(credentials: CredentialsSchema, request: Request, response: Response):
    client_ip = AuthControl.get_client_ip(request)
    await AuthControl.enforce_rate_limit(f"login:{client_ip}:{credentials.username}")
    payload = await auth_service.login(credentials)
    set_refresh_token_cookie(response, payload["refresh_token"])
    return Success(data=build_public_token_payload(payload))


@router.post("/refresh_token", summary="刷新访问令牌")
async def refresh_token(
    raw_request: Request,
    response: Response,
    refresh_token_cookie: str | None = Cookie(default=None, alias=settings.REFRESH_TOKEN_COOKIE_NAME),
):
    client_ip = AuthControl.get_client_ip(raw_request)
    await AuthControl.enforce_rate_limit(f"refresh:{client_ip}")
    if not refresh_token_cookie:
        raise AuthenticationError("缺少刷新令牌")

    payload = await auth_service.refresh_access_token(refresh_token_cookie)
    set_refresh_token_cookie(response, payload["refresh_token"])
    return Success(data=build_public_token_payload(payload))


@router.get("/app_meta", summary="查看应用元信息", openapi_extra={"skip_api_catalog": True})
async def get_app_meta():
    return Success(
        data={
            "app_title": settings.APP_TITLE,
            "project_name": settings.PROJECT_NAME,
            "app_description": settings.APP_DESCRIPTION,
            "login_page_image_url": settings.LOGIN_PAGE_IMAGE_URL,
            "login_page_image_mode": settings.LOGIN_PAGE_IMAGE_MODE,
            "login_page_image_zoom": settings.LOGIN_PAGE_IMAGE_ZOOM,
            "login_page_image_position_x": settings.LOGIN_PAGE_IMAGE_POSITION_X,
            "login_page_image_position_y": settings.LOGIN_PAGE_IMAGE_POSITION_Y,
            "notification_position": settings.NOTIFICATION_POSITION,
            "notification_duration": settings.NOTIFICATION_DURATION,
            "notification_visible_toasts": settings.NOTIFICATION_VISIBLE_TOASTS,
        }
    )


@router.get("/userinfo", summary="查看用户信息")
async def get_userinfo(current_user: CurrentUser):
    return Success(data=await auth_service.get_current_user_info(current_user))


@router.get("/usermenu", summary="查看用户菜单")
async def get_user_menu(current_user: CurrentUser):
    return Success(data=await auth_service.get_current_user_menu(current_user))


@router.get("/userapi", summary="查看用户API")
async def get_user_api(current_user: CurrentUser):
    return Success(data=await auth_service.get_current_user_api_permissions(current_user))


@router.get("/overview", summary="查看管理台概览")
async def get_overview(_current_user: CurrentUser):
    return Success(data=await auth_service.get_platform_overview())


@router.get("/password_policy", summary="查看密码策略")
async def get_runtime_password_policy(_current_user: CurrentUser):
    return Success(data=get_password_policy())


@router.post("/update_password", summary="修改密码")
async def update_user_password(req_in: UpdatePassword, current_user: CurrentUser):
    await auth_service.update_current_user_password(current_user, req_in)
    return Success(msg="修改成功")


def _form_str_or_none(form, key: str) -> str | None:
    """Read a text field from multipart form data, treating blanks as None."""
    value = form.get(key)
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed or None


def _build_profile_update(data: dict) -> ProfileUpdate:
    try:
        return ProfileUpdate.model_validate(data)
    except PydanticValidationError as exc:
        errors = exc.errors()
        message = errors[0].get("msg") if errors else "数据验证失败"
        raise ValidationError(str(message)) from exc


@router.post("/update_profile", summary="更新个人信息")
async def update_user_profile(request: Request, current_user: CurrentUser):
    """Update the current user's profile.

    Accepts either JSON (avatar handled via the `avatar` URL) or multipart form-data
    (avatar handled via `avatar_mode` + `avatar_file`, matching the deferred-upload flow).
    """
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        profile_data: dict = {
            "nickname": _form_str_or_none(form, "nickname"),
            "email": _form_str_or_none(form, "email"),
            "phone": _form_str_or_none(form, "phone"),
        }
        avatar_mode = (str(form.get("avatar_mode") or "keep")).strip().lower()
        if avatar_mode == "replace":
            avatar_file = form.get("avatar_file")
            if not isinstance(avatar_file, StarletteUploadFile):
                raise ValidationError("请选择要上传的头像文件")
            upload_result = await upload_service.upload_avatar(avatar_file)
            profile_data["avatar"] = upload_result["url"]
        elif avatar_mode == "remove":
            profile_data["avatar"] = ""
        # avatar_mode == "keep": leave avatar untouched
        payload = _build_profile_update(profile_data)
    else:
        payload = _build_profile_update(await request.json())

    await auth_service.update_current_user_profile(current_user, payload)
    return Success(msg="个人信息更新成功")


@router.post("/upload_avatar", summary="上传头像")
async def upload_avatar(_current_user: CurrentUser, file: UploadFile = File(...)):
    return Success(data=await upload_service.upload_avatar(file))


@router.post("/logout", summary="用户注销")
async def logout(response: Response, current_user: CurrentUser):
    await auth_service.logout(current_user)
    clear_refresh_token_cookie(response)
    return Success(msg="注销成功")
