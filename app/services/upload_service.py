from __future__ import annotations

from fastapi import HTTPException, UploadFile, status

from app.controllers.upload import upload_controller
from app.models import User


class UploadService:
    async def upload_image(self, file: UploadFile) -> dict:
        return await upload_controller.upload_image(file)

    async def upload_files(self, files: list[UploadFile]) -> list[dict]:
        return await upload_controller.upload_files(files)

    async def list_files(self, prefix: str | None = None, max_keys: int = 100) -> list[dict]:
        return await upload_controller.list_files(prefix, max_keys)

    async def delete_file(self, file_key: str) -> bool:
        return await upload_controller.delete_file(file_key)

    async def upload_avatar(self, file: UploadFile) -> dict:
        return await upload_controller.upload_avatar(file)

    async def set_public_acl(self, prefix: str | None, *, actor: User) -> dict:
        if not actor.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员才能执行此操作",
            )
        return await upload_controller.set_public_acl(prefix)


upload_service = UploadService()
