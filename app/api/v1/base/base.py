from fastapi import APIRouter, Cookie, File, Request, Response, UploadFile

from app.controllers.upload import upload_controller
from app.core.ctx import CTX_USER_ID
from app.core.dependency import AuthControl, DependAuth
from app.core.exceptions import AuthenticationError
from app.schemas.base import Success
from app.schemas.login import CredentialsSchema
from app.schemas.users import ProfileUpdate, UpdatePassword
from app.settings import settings
from app.services import auth_service
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
        }
    )


@router.get("/userinfo", summary="查看用户信息", dependencies=[DependAuth])
async def get_userinfo():
    return Success(data=await auth_service.get_current_user_info(CTX_USER_ID.get()))


@router.get("/usermenu", summary="查看用户菜单", dependencies=[DependAuth])
async def get_user_menu():
    return Success(data=await auth_service.get_current_user_menu(CTX_USER_ID.get()))


@router.get("/userapi", summary="查看用户API", dependencies=[DependAuth])
async def get_user_api():
    return Success(data=await auth_service.get_current_user_api_permissions(CTX_USER_ID.get()))


@router.get("/overview", summary="查看管理台概览", dependencies=[DependAuth])
async def get_overview():
    return Success(data=await auth_service.get_platform_overview())


@router.get("/password_policy", summary="查看密码策略", dependencies=[DependAuth])
async def get_runtime_password_policy():
    return Success(data=get_password_policy())


@router.post("/update_password", summary="修改密码", dependencies=[DependAuth])
async def update_user_password(req_in: UpdatePassword):
    await auth_service.update_current_user_password(CTX_USER_ID.get(), req_in)
    return Success(msg="修改成功")


@router.post("/update_profile", summary="更新个人信息", dependencies=[DependAuth])
async def update_user_profile(req_in: ProfileUpdate):
    await auth_service.update_current_user_profile(CTX_USER_ID.get(), req_in)
    return Success(msg="个人信息更新成功")


@router.post("/upload_avatar", summary="上传头像", dependencies=[DependAuth])
async def upload_avatar(file: UploadFile = File(...)):
    return Success(data=await upload_controller.upload_avatar(file))


@router.post("/logout", summary="用户注销", dependencies=[DependAuth])
async def logout(response: Response):
    await auth_service.logout(CTX_USER_ID.get())
    clear_refresh_token_cookie(response)
    return Success(msg="注销成功")
