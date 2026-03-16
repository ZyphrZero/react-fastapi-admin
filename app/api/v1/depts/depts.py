from fastapi import APIRouter, Query

from app.schemas import Success
from app.schemas.depts import DeptCreate, DeptUpdate
from app.services import dept_admin_service

router = APIRouter()


@router.get("/list", summary="查看部门列表")
async def list_dept(name: str = Query(None, description="部门名称")):
    return Success(data=await dept_admin_service.list_dept_tree(name))


@router.get("/get", summary="查看部门")
async def get_dept(id: int = Query(..., description="部门ID")):
    return Success(data=await dept_admin_service.get_dept_detail(id))


@router.post("/create", summary="创建部门")
async def create_dept(dept_in: DeptCreate):
    return Success(msg="Created Successfully", data={"id": await dept_admin_service.create_dept(dept_in)})


@router.post("/update", summary="更新部门")
async def update_dept(dept_in: DeptUpdate):
    return Success(msg="Update Successfully", data={"id": await dept_admin_service.update_dept(dept_in)})


@router.delete("/delete", summary="删除部门")
async def delete_dept(
    dept_id: int = Query(..., description="部门ID"),
    cascade: bool = Query(True, description="是否级联删除子部门"),
):
    await dept_admin_service.delete_dept(dept_id=dept_id, cascade=cascade)
    return Success(msg="Deleted Success")
