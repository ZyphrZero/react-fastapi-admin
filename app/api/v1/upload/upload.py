from typing import List, Optional

from fastapi import APIRouter, File, Query, UploadFile

from app.core.dependency import CurrentUser
from app.schemas.base import Success
from app.schemas.upload import BatchFileUploadResp, FileDeleteResp, FileListResp, FileUploadResp
from app.services.upload_service import upload_service

router = APIRouter()


@router.post("/image", summary="上传图片", response_model=FileUploadResp)
async def upload_image(_current_user: CurrentUser, file: UploadFile = File(...)):
    """
    上传单个图片文件到对象存储或本地存储

    根据系统配置选择上传目标:
    - 当系统设置选择对象存储时，上传到对象存储
    - 否则上传到本地存储

    Args:
        file: 上传的图片文件
        current_user: 当前用户

    Returns:
        FileUploadResp: 包含上传后的图片URL的响应
    """
    file_info = await upload_service.upload_image(file)
    return Success(data=file_info)


@router.post("/files", summary="批量上传文件", response_model=BatchFileUploadResp)
async def upload_files(_current_user: CurrentUser, files: List[UploadFile] = File(...)):
    """
    批量上传文件到对象存储或本地存储

    根据系统配置选择上传目标:
    - 当系统设置选择对象存储时，上传到对象存储
    - 否则上传到本地存储

    Args:
        files: 上传的文件列表
        current_user: 当前用户

    Returns:
        BatchFileUploadResp: 包含上传后的文件URL列表的响应
    """
    result = await upload_service.upload_files(files)
    return Success(data=result)


@router.get("/list", summary="获取对象存储文件列表", response_model=FileListResp)
async def list_files(
    _current_user: CurrentUser,
    prefix: Optional[str] = Query(None, description="路径前缀，例如 image/"),
    max_keys: int = Query(100, description="最大返回数量", gt=0, le=1000),
):
    """
    获取对象存储中的文件列表

    Args:
        prefix: 路径前缀，例如 image/
        max_keys: 最大返回数量
        current_user: 当前用户

    Returns:
        FileListResp: 包含文件列表的响应
    """
    result = await upload_service.list_files(prefix, max_keys)
    return Success(data=result)


@router.delete("/delete", summary="删除文件", response_model=FileDeleteResp)
async def delete_file(
    _current_user: CurrentUser,
    file_key: str = Query(..., description="文件的对象存储键值或本地路径"),
):
    """
    删除对象存储或本地存储中的文件

    Args:
        file_key: 文件的对象存储键值或本地存储路径
        current_user: 当前用户

    Returns:
        FileDeleteResp: 包含删除结果的响应
    """
    result = await upload_service.delete_file(file_key)
    return Success(data=result)


@router.post("/set-public-acl", summary="批量设置文件ACL为公共读")
async def set_public_acl(
    current_user: CurrentUser,
    prefix: Optional[str] = Query(None, description="路径前缀，例如 image/"),
):
    """
    批量设置指定前缀下的文件ACL为公共读

    Args:
        prefix: 路径前缀，例如 image/
        current_user: 当前用户

    Returns:
        Dict: 包含处理结果的响应
    """
    result = await upload_service.set_public_acl(prefix, actor=current_user)
    return Success(data=result)
