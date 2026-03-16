from fastapi import APIRouter, Query

from app.schemas.base import Success, SuccessExtra
from app.schemas.roles import RoleCreate, RoleUpdate
from app.services import role_admin_service

router = APIRouter()


@router.get("/list", summary="查看角色列表")
async def list_role(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    role_name: str = Query("", description="角色名称，用于查询"),
):
    return SuccessExtra(**(await role_admin_service.list_roles(page=page, page_size=page_size, role_name=role_name)))


@router.get("/get", summary="查看角色")
async def get_role(role_id: int = Query(..., description="角色ID")):
    return Success(data=await role_admin_service.get_role_detail(role_id))


@router.post("/create", summary="创建角色")
async def create_role(role_in: RoleCreate):
    await role_admin_service.create_role(role_in)
    return Success(msg="创建成功")


@router.post("/update", summary="更新角色")
async def update_role(role_in: RoleUpdate):
    await role_admin_service.update_role(role_in)
    return Success(msg="更新成功")


@router.delete("/delete", summary="删除角色")
async def delete_role(role_id: int = Query(..., description="角色ID")):
    await role_admin_service.delete_role(role_id)
    return Success(msg="删除成功")
