from fastapi import APIRouter, Cookie, File, Request, Response, UploadFile

from app.core.dependency import AuthControl, CurrentUser
from app.core.exceptions import AuthenticationError
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


@router.post("/update_profile", summary="更新个人信息")
async def update_user_profile(req_in: ProfileUpdate, current_user: CurrentUser):
    await auth_service.update_current_user_profile(current_user, req_in)
    return Success(msg="个人信息更新成功")


@router.post("/upload_avatar", summary="上传头像")
async def upload_avatar(_current_user: CurrentUser, file: UploadFile = File(...)):
    return Success(data=await upload_service.upload_avatar(file))


@router.post("/logout", summary="用户注销")
async def logout(response: Response, current_user: CurrentUser):
    await auth_service.logout(current_user)
    clear_refresh_token_cookie(response)
    return Success(msg="注销成功")
