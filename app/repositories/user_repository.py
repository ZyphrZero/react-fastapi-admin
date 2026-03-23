from __future__ import annotations

from datetime import datetime

from tortoise.expressions import Q

from app.core.exceptions import ValidationError
from app.models.admin import Role, User
from app.repositories.base import BaseRepository
from app.schemas.users import UserCreate, UserUpdate


class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
    def __init__(self) -> None:
        super().__init__(model=User)

    async def exists_any(self) -> bool:
        return await self.model.exists()

    async def get_first(self) -> User | None:
        return await self.model.all().first()

    async def get_by_email(self, email: str) -> User | None:
        return await self.model.filter(email=email).first()

    async def get_by_username(self, username: str) -> User | None:
        return await self.model.filter(username=username).first()

    async def list_users(self, *, page: int, page_size: int, search: Q) -> tuple[int, list[User]]:
        return await self.list(page=page, page_size=page_size, search=search, order=["id"], prefetch_related=["roles"])

    async def update_last_login(self, user_id: int) -> None:
        user = await self.get_or_raise(user_id, "用户不存在")
        user.last_login = datetime.now()
        await user.save()

    async def bump_session_version(self, user: User) -> int:
        user.session_version += 1
        await user.save(update_fields=["session_version", "updated_at"])
        return user.session_version

    async def count_superusers(self) -> int:
        return await self.model.filter(is_superuser=True).count()

    async def assign_roles(self, user: User, role_ids: list[int]) -> None:
        role_objects = await Role.filter(id__in=role_ids).all()
        role_map = {role.id: role for role in role_objects}
        missing_role_ids = [role_id for role_id in role_ids if role_id not in role_map]
        if missing_role_ids:
            raise ValidationError(f"角色不存在: {', '.join(str(role_id) for role_id in missing_role_ids)}")

        await user.roles.clear()
        if not role_ids:
            return

        for role_id in role_ids:
            await user.roles.add(role_map[role_id])


user_repository = UserRepository()
