from __future__ import annotations

import asyncio
from typing import TypedDict

from tortoise.expressions import Q

from app.models.admin import Role, User
from app.repositories.base import BaseRepository
from app.schemas.roles import RoleCreate, RoleUpdate


class PermissionBundle(TypedDict):
    menu_paths: list[str]
    api_ids: list[int]


class RoleRepository(BaseRepository[Role, RoleCreate, RoleUpdate]):
    def __init__(self) -> None:
        super().__init__(model=Role)

    async def exists_any(self) -> bool:
        return await self.model.exists()

    async def get_by_name(self, name: str) -> Role | None:
        return await self.model.filter(name=name).first()

    async def exists_by_name(self, name: str, *, exclude_id: int | None = None) -> bool:
        query = self.model.filter(name=name)
        if exclude_id is not None:
            query = query.exclude(id=exclude_id)
        return await query.exists()

    async def list_roles(self, *, page: int, page_size: int, search: Q) -> tuple[int, list[dict]]:
        total, role_objects = await self.list(page=page, page_size=page_size, search=search, order=["id"])
        role_data = await asyncio.gather(*(role.to_dict() for role in role_objects))
        user_counts = await asyncio.gather(*(User.filter(roles=role.id).count() for role in role_objects))

        for item, user_count in zip(role_data, user_counts):
            item["user_count"] = user_count
            item["menu_count"] = len(item.get("menu_paths") or [])
            item["api_count"] = len(item.get("api_ids") or [])

        return total, role_data

    async def list_permissions_for_user(self, user_id: int) -> PermissionBundle:
        permission_rows = await self.model.filter(user_roles__id=user_id).all().values("menu_paths", "api_ids")
        menu_paths: set[str] = set()
        api_ids: set[int] = set()

        for row in permission_rows:
            menu_paths.update(row.get("menu_paths") or [])
            api_ids.update(int(api_id) for api_id in (row.get("api_ids") or []))

        return {
            "menu_paths": sorted(menu_paths),
            "api_ids": sorted(api_ids),
        }


role_repository = RoleRepository()
