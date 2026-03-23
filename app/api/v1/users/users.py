from fastapi import APIRouter, Query

from app.core.ctx import CTX_USER_ID
from app.schemas.base import Success, SuccessExtra
from app.schemas.users import ResetPasswordRequest, UserCreate, UserUpdate
from app.services import user_admin_service

router = APIRouter()


@router.get("/list", summary="查看用户列表")
async def list_user(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    username: str = Query("", description="用户名称，用于搜索"),
    nickname: str = Query("", description="昵称，用于搜索"),
    email: str = Query("", description="邮箱地址"),
):
    result = await user_admin_service.list_users(
        page=page,
        page_size=page_size,
        username=username,
        nickname=nickname,
        email=email,
    )
    return SuccessExtra(**result)


@router.get("/get", summary="查看用户")
async def get_user(user_id: int = Query(..., description="用户ID")):
    return Success(data=await user_admin_service.get_user_detail(user_id))


@router.post("/create", summary="创建用户")
async def create_user(user_in: UserCreate):
    await user_admin_service.create_user(user_in, current_user_id=CTX_USER_ID.get())
    return Success(msg="创建成功")


@router.post("/update", summary="更新用户")
async def update_user(user_in: UserUpdate):
    await user_admin_service.update_user(user_in, current_user_id=CTX_USER_ID.get())
    return Success(msg="更新成功")


@router.delete("/delete", summary="删除用户")
async def delete_user(user_id: int = Query(..., description="用户ID")):
    await user_admin_service.delete_user(user_id=user_id, current_user_id=CTX_USER_ID.get())
    return Success(msg="删除成功")


@router.post("/reset_password", summary="重置密码")
async def reset_password(payload: ResetPasswordRequest):
    await user_admin_service.reset_user_password(payload, current_user_id=CTX_USER_ID.get())
    return Success(msg="密码更新成功")
