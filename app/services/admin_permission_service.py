from __future__ import annotations

from dataclasses import dataclass

from app.core.exceptions import AuthorizationError
from app.models.admin import Role, User
from app.repositories import role_repository


@dataclass(frozen=True, slots=True)
class PermissionScope:
    menu_paths: frozenset[str]
    api_ids: frozenset[int]

    @classmethod
    def from_bundle(cls, *, menu_paths: list[str] | None = None, api_ids: list[int] | None = None) -> "PermissionScope":
        return cls(
            menu_paths=frozenset(menu_paths or []),
            api_ids=frozenset(int(api_id) for api_id in (api_ids or [])),
        )

    def includes(self, other: "PermissionScope") -> bool:
        return other.menu_paths.issubset(self.menu_paths) and other.api_ids.issubset(self.api_ids)

    def strictly_includes(self, other: "PermissionScope") -> bool:
        return self.includes(other) and self != other


class AdminPermissionService:
    async def get_user_scope(self, user: User) -> PermissionScope:
        if user.is_superuser:
            return PermissionScope.from_bundle(menu_paths=["*"], api_ids=[-1])

        permission_bundle = await role_repository.list_permissions_for_user(user.id)
        return PermissionScope.from_bundle(
            menu_paths=permission_bundle["menu_paths"],
            api_ids=permission_bundle["api_ids"],
        )

    async def get_scope_for_role_ids(self, role_ids: list[int] | None) -> PermissionScope:
        permission_bundle = await role_repository.list_permissions_for_role_ids(list(role_ids or []))
        return PermissionScope.from_bundle(
            menu_paths=permission_bundle["menu_paths"],
            api_ids=permission_bundle["api_ids"],
        )

    def get_scope_for_role(self, role: Role) -> PermissionScope:
        return PermissionScope.from_bundle(menu_paths=list(role.menu_paths or []), api_ids=list(role.api_ids or []))

    async def ensure_can_manage_user(self, *, actor: User, target: User, action: str) -> None:
        if actor.is_superuser:
            return
        if target.is_superuser:
            raise AuthorizationError("不能操作超级管理员账户")

        actor_scope = await self.get_user_scope(actor)
        target_scope = await self.get_user_scope(target)
        if not actor_scope.strictly_includes(target_scope):
            raise AuthorizationError(f"不能{action}同级或更高权限账户")

    async def ensure_can_assign_role_ids(self, *, actor: User, role_ids: list[int] | None, action: str) -> None:
        if actor.is_superuser:
            return

        actor_scope = await self.get_user_scope(actor)
        target_scope = await self.get_scope_for_role_ids(role_ids)
        if not actor_scope.strictly_includes(target_scope):
            raise AuthorizationError(f"不能{action}同级或更高权限角色")

    async def ensure_can_create_user(self, *, actor: User, is_superuser: bool, role_ids: list[int] | None) -> None:
        if actor.is_superuser:
            return
        if is_superuser:
            raise AuthorizationError("只有超级管理员可以授予超级管理员身份")

        await self.ensure_can_assign_role_ids(actor=actor, role_ids=role_ids, action="授予")

    async def ensure_can_update_user(
        self,
        *,
        actor: User,
        target: User,
        next_is_superuser: bool,
        role_ids: list[int] | None,
    ) -> None:
        if actor.is_superuser:
            return

        await self.ensure_can_manage_user(actor=actor, target=target, action="修改")
        if next_is_superuser:
            raise AuthorizationError("只有超级管理员可以授予超级管理员身份")
        if role_ids is not None:
            await self.ensure_can_assign_role_ids(actor=actor, role_ids=role_ids, action="授予")

    async def ensure_can_create_role(self, *, actor: User, menu_paths: list[str], api_ids: list[int]) -> None:
        if actor.is_superuser:
            return

        actor_scope = await self.get_user_scope(actor)
        target_scope = PermissionScope.from_bundle(menu_paths=menu_paths, api_ids=api_ids)
        if not actor_scope.strictly_includes(target_scope):
            raise AuthorizationError("不能创建同级或更高权限角色")

    async def ensure_can_manage_role(self, *, actor: User, role: Role, action: str) -> None:
        if actor.is_superuser:
            return

        actor_scope = await self.get_user_scope(actor)
        role_scope = self.get_scope_for_role(role)
        if not actor_scope.strictly_includes(role_scope):
            raise AuthorizationError(f"不能{action}同级或更高权限角色")

    async def ensure_can_update_role(
        self,
        *,
        actor: User,
        current_role: Role,
        next_menu_paths: list[str],
        next_api_ids: list[int],
    ) -> None:
        if actor.is_superuser:
            return

        await self.ensure_can_manage_role(actor=actor, role=current_role, action="修改")
        actor_scope = await self.get_user_scope(actor)
        next_scope = PermissionScope.from_bundle(menu_paths=next_menu_paths, api_ids=next_api_ids)
        if not actor_scope.strictly_includes(next_scope):
            raise AuthorizationError("不能修改为同级或更高权限角色")


admin_permission_service = AdminPermissionService()
