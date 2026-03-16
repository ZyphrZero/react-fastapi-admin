from __future__ import annotations

from tortoise.expressions import Q

from app.core.navigation import (
    find_unknown_menu_paths,
    get_assignable_menu_tree,
    normalize_menu_paths,
)
from app.core.exceptions import ValidationError
from app.repositories import api_repository, role_repository
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
        data = await role.to_dict()
        data["menu_paths"] = sorted(data.get("menu_paths") or [])
        data["api_ids"] = sorted(int(api_id) for api_id in (data.get("api_ids") or []))
        data["menu_count"] = len(data["menu_paths"])
        data["api_count"] = len(data["api_ids"])
        return data

    async def get_permission_options(self) -> dict:
        api_items = await api_repository.list_all_for_permissions()
        api_groups: dict[str, list[dict]] = {}

        for api_item in api_items:
            tag_name = api_item.get("tags") or "未分类"
            api_groups.setdefault(tag_name, []).append(api_item)

        grouped_options = [
            {"tag": tag, "items": items}
            for tag, items in sorted(api_groups.items(), key=lambda item: item[0])
        ]

        return {
            "menu_tree": get_assignable_menu_tree(),
            "api_groups": grouped_options,
        }

    async def _normalize_role_permissions(
        self,
        *,
        menu_paths: list[str] | None,
        api_ids: list[int] | None,
    ) -> tuple[list[str], list[int]]:
        next_menu_paths = list(menu_paths or [])
        unknown_menu_paths = find_unknown_menu_paths(next_menu_paths)
        if unknown_menu_paths:
            raise ValidationError(f"菜单权限不存在: {', '.join(unknown_menu_paths)}")

        normalized_menu_paths = normalize_menu_paths(next_menu_paths)
        normalized_api_ids = sorted({int(api_id) for api_id in (api_ids or [])})

        if normalized_api_ids:
            existing_api_ids = set(await api_repository.model.filter(id__in=normalized_api_ids).values_list("id", flat=True))
            missing_api_ids = [str(api_id) for api_id in normalized_api_ids if api_id not in existing_api_ids]
            if missing_api_ids:
                raise ValidationError(f"API权限不存在: {', '.join(missing_api_ids)}")

        return normalized_menu_paths, normalized_api_ids

    async def create_role(self, role_in: RoleCreate) -> None:
        if await role_repository.exists_by_name(role_in.name):
            raise ValidationError("该角色名称已存在")
        menu_paths, api_ids = await self._normalize_role_permissions(
            menu_paths=role_in.menu_paths,
            api_ids=role_in.api_ids,
        )
        await role_repository.create(
            {
                "name": role_in.name,
                "desc": role_in.desc,
                "menu_paths": menu_paths,
                "api_ids": api_ids,
            }
        )

    async def update_role(self, role_in: RoleUpdate) -> None:
        await role_repository.get_or_raise(role_in.id, "角色不存在")
        if role_in.name and await role_repository.exists_by_name(role_in.name, exclude_id=role_in.id):
            raise ValidationError("该角色名称已存在")

        update_data = role_in.model_dump(exclude_unset=True, exclude={"id"})
        if "menu_paths" in update_data or "api_ids" in update_data:
            current_role = await role_repository.get_or_raise(role_in.id, "角色不存在")
            menu_paths, api_ids = await self._normalize_role_permissions(
                menu_paths=update_data.get("menu_paths", current_role.menu_paths),
                api_ids=update_data.get("api_ids", current_role.api_ids),
            )
            update_data["menu_paths"] = menu_paths
            update_data["api_ids"] = api_ids

        await role_repository.update(role_in.id, update_data)

    async def delete_role(self, role_id: int) -> None:
        await role_repository.get_or_raise(role_id, "角色不存在")
        await role_repository.remove(role_id)


role_admin_service = RoleAdminService()
