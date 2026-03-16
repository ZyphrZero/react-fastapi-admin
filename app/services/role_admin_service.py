from __future__ import annotations

from tortoise.expressions import Q

from app.core.exceptions import ValidationError
from app.repositories import role_repository
from app.schemas.roles import RoleCreate, RoleUpdate


class RoleAdminService:
    def build_search_query(self, role_name: str = "") -> Q:
        return Q(name__contains=role_name) if role_name else Q()

    async def list_roles(self, *, page: int, page_size: int, role_name: str = "") -> dict:
        total, data = await role_repository.list_roles(
            page=page,
            page_size=page_size,
            search=self.build_search_query(role_name),
        )
        return {"data": data, "total": total, "page": page, "page_size": page_size}

    async def get_role_detail(self, role_id: int) -> dict:
        role = await role_repository.get_or_raise(role_id, "角色不存在")
        return await role.to_dict()

    async def create_role(self, role_in: RoleCreate) -> None:
        if await role_repository.exists_by_name(role_in.name):
            raise ValidationError("该角色名称已存在")
        await role_repository.create(role_in)

    async def update_role(self, role_in: RoleUpdate) -> None:
        await role_repository.get_or_raise(role_in.id, "角色不存在")
        if role_in.name and await role_repository.exists_by_name(role_in.name, exclude_id=role_in.id):
            raise ValidationError("该角色名称已存在")
        await role_repository.update(role_in.id, role_in)

    async def delete_role(self, role_id: int) -> None:
        await role_repository.get_or_raise(role_id, "角色不存在")
        await role_repository.remove(role_id)


role_admin_service = RoleAdminService()
