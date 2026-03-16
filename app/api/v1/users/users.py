import logging

from fastapi import APIRouter, Body, Query
from tortoise.expressions import Q

from app.controllers.dept import dept_controller
from app.controllers.user import user_controller
from app.core.ctx import CTX_USER_ID
from app.core.dependency import DependAuth
from app.core.exceptions import AuthenticationError, ValidationError
from app.schemas.base import Fail, Success, SuccessExtra
from app.schemas.users import *

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/list", summary="查看用户列表")
async def list_user(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    username: str = Query("", description="用户名称，用于搜索"),
    nickname: str = Query("", description="昵称，用于搜索"),
    email: str = Query("", description="邮箱地址"),
    dept_id: int = Query(None, description="部门ID"),
):
    """
    获取用户列表

    Args:
        page: 页码
        page_size: 每页数量
        username: 用户名称搜索
        nickname: 昵称搜索
        email: 邮箱地址搜索
        dept_id: 部门ID搜索

    Returns:
        用户列表和分页信息
    """
    q = Q()
    if username:
        q &= Q(username__contains=username)
    if nickname:
        q &= Q(nickname__contains=nickname)
    if email:
        q &= Q(email__contains=email)
    if dept_id is not None:
        q &= Q(dept_id=dept_id)

    total, user_objs = await user_controller.list(page=page, page_size=page_size, search=q)
    data = [await obj.to_dict(m2m=True, exclude_fields=["password"]) for obj in user_objs]

    for item in data:
        dept_id = item.pop("dept_id", None)
        if dept_id:
            dept_obj = await dept_controller.get(id=dept_id)
            item["dept"] = await dept_obj.to_dict() if dept_obj else {}
        else:
            item["dept"] = {}

    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.get("/get", summary="查看用户")
async def get_user(
    user_id: int = Query(..., description="用户ID"),
):
    """
    获取指定用户信息

    Args:
        user_id: 用户ID

    Returns:
        用户信息

    Raises:
        AuthenticationError: 当用户不存在时抛出
    """
    user_obj = await user_controller.get(id=user_id)
    if not user_obj:
        raise AuthenticationError("用户不存在")

    user_dict = await user_obj.to_dict(exclude_fields=["password"])
    return Success(data=user_dict)


@router.post("/create", summary="创建用户")
async def create_user(
    user_in: UserCreate,
):
    """
    创建新用户

    Args:
        user_in: 用户创建信息

    Returns:
        创建结果

    Raises:
        ValidationError: 当用户邮箱或用户名已存在时抛出
    """
    # 检查邮箱唯一性
    if user_in.email:
        existing_email_user = await user_controller.get_by_email(user_in.email)
        if existing_email_user:
            raise ValidationError("该邮箱地址已被使用")

    # 检查用户名唯一性
    existing_username_user = await user_controller.get_by_username(user_in.username)
    if existing_username_user:
        raise ValidationError("该用户名已被使用")

    # 使用create_dict方法获取创建数据
    create_data = user_in.create_dict()
    
    # 创建用户（user_controller.create_user会处理密码加密）
    new_user = await user_controller.create_user(obj_in=user_in)
    if not new_user:
        raise ValidationError("用户创建失败")

    # 处理角色关联
    if user_in.role_ids:
        await user_controller.update_roles(new_user, user_in.role_ids)

    return Success(msg="创建成功")


@router.post("/update", summary="更新用户")
async def update_user(
    user_in: UserUpdate,
):
    """
    更新用户信息

    Args:
        user_in: 用户更新信息

    Returns:
        更新结果

    Raises:
        AuthenticationError: 当用户不存在时抛出
        ValidationError: 当邮箱已被其他用户使用时抛出
    """
    # 检查用户是否存在
    existing_user = await user_controller.get(id=user_in.id)
    if not existing_user:
        raise AuthenticationError("用户不存在")

    # 检查邮箱唯一性（如果更新了邮箱）
    if user_in.email:
        email_user = await user_controller.get_by_email(user_in.email)
        if email_user and email_user.id != user_in.id:
            raise ValidationError("该邮箱地址已被其他用户使用")

    # 使用update_dict方法获取要更新的数据，排除role_ids
    update_data = user_in.update_dict()
    
    # 如果有密码更新，需要加密
    if "password" in update_data and update_data["password"]:
        is_valid, message = await user_controller.validate_password(update_data["password"])
        if not is_valid:
            raise ValidationError(f"密码强度不足: {message}")
        from app.utils.password import get_password_hash
        update_data["password"] = get_password_hash(update_data["password"])
    
    # 更新用户基本信息
    if update_data:  # 只有在有数据需要更新时才调用update
        user = await user_controller.update(id=user_in.id, obj_in=update_data)
        if not user:
            raise AuthenticationError("用户更新失败")
    else:
        user = existing_user

    # 处理角色关联（支持设置为空数组来清空角色）
    if user_in.role_ids is not None:  # 使用 is not None 来区分None和空数组
        await user_controller.update_roles(user, user_in.role_ids)

    return Success(msg="更新成功")


@router.delete("/delete", summary="删除用户", dependencies=[DependAuth])
async def delete_user(
    user_id: int = Query(..., description="用户ID"),
):
    """
    删除指定用户

    Args:
        user_id: 用户ID

    Returns:
        删除结果

    Raises:
        ValidationError: 当用户尝试删除自己的账户时抛出
        AuthenticationError: 当用户不存在时抛出
    """
    # 获取当前用户ID
    current_user_id = CTX_USER_ID.get()

    # 检查用户是否尝试删除自己的账户
    if current_user_id == user_id:
        raise ValidationError("不能删除自己的账户")

    # 检查要删除的用户是否存在
    user_to_delete = await user_controller.get(id=user_id)
    if not user_to_delete:
        raise AuthenticationError("要删除的用户不存在")

    # 额外的安全检查：防止删除超级管理员账户（如果有需要）
    if user_to_delete.is_superuser:
        # 检查是否还有其他超级管理员
        superuser_count = await user_controller.model.filter(is_superuser=True).count()
        if superuser_count <= 1:
            raise ValidationError("不能删除最后一个超级管理员账户")

    await user_controller.remove(id=user_id)
    return Success(msg="删除成功")


@router.post("/reset_password", summary="重置密码")
async def reset_password(user_id: int = Body(..., description="用户ID", embed=True)):
    """
    重置用户密码

    Args:
        user_id: 用户ID

    Returns:
        重置结果
    """
    await user_controller.reset_password(user_id)
    return Success(msg="密码已重置为123456")
