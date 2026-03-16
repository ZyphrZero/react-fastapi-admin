from pydantic import BaseModel

from fastapi import APIRouter, Header

from app.core.ctx import CTX_USER_ID
from app.core.dependency import DependAuth
from app.schemas.base import Success
from app.schemas.login import CredentialsSchema
from app.schemas.users import ProfileUpdate, UpdatePassword
from app.services import auth_service

router = APIRouter()


class RefreshTokenRequest(BaseModel):
    refresh_token: str


@router.post("/access_token", summary="获取token")
async def login_access_token(credentials: CredentialsSchema):
    return Success(data=await auth_service.login(credentials))


@router.post("/refresh_token", summary="刷新访问令牌")
async def refresh_token(request: RefreshTokenRequest):
    return Success(data=await auth_service.refresh_access_token(request.refresh_token))


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


@router.post("/update_password", summary="修改密码", dependencies=[DependAuth])
async def update_user_password(req_in: UpdatePassword):
    await auth_service.update_current_user_password(CTX_USER_ID.get(), req_in)
    return Success(msg="修改成功")


@router.post("/update_profile", summary="更新个人信息", dependencies=[DependAuth])
async def update_user_profile(req_in: ProfileUpdate):
    await auth_service.update_current_user_profile(CTX_USER_ID.get(), req_in)
    return Success(msg="个人信息更新成功")


@router.post("/logout", summary="用户注销", dependencies=[DependAuth])
async def logout(token: str = Header(..., description="token验证")):
    await auth_service.logout(token, CTX_USER_ID.get())
    return Success(msg="注销成功")
