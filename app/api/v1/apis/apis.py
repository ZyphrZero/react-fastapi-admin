from fastapi import APIRouter, Query

from app.api.catalog import build_api_catalog_route_definitions
from app.schemas import Success, SuccessExtra
from app.schemas.apis import ApiUpdate
from app.services import api_admin_service

router = APIRouter()


@router.get("/list", summary="查看API列表")
async def list_api(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    path: str = Query(None, description="API路径"),
    summary: str = Query(None, description="API简介"),
    tags: str = Query(None, description="API模块"),
):
    return SuccessExtra(
        **(
            await api_admin_service.list_apis(
                page=page,
                page_size=page_size,
                path=path,
                summary=summary,
                tags=tags,
            )
        )
    )


@router.get("/get", summary="查看Api")
async def get_api(id: int = Query(..., description="Api")):
    return Success(data=await api_admin_service.get_api_detail(id))


@router.post("/update", summary="更新Api")
async def update_api(api_in: ApiUpdate):
    await api_admin_service.update_api(api_in)
    return Success(msg="更新成功")


@router.delete("/delete", summary="删除Api")
async def delete_api(api_id: int = Query(..., description="ApiID")):
    await api_admin_service.delete_api(api_id)
    return Success(msg="删除成功")


@router.post("/refresh", summary="刷新API列表")
async def refresh_api():
    await api_admin_service.refresh_api_catalog(build_api_catalog_route_definitions())
    return Success(msg="刷新成功")


@router.get("/tags", summary="获取所有API标签")
async def get_api_tags():
    return Success(data=await api_admin_service.get_api_tags())
