from __future__ import annotations

import asyncio

from tortoise.expressions import Q

from app.core.exceptions import AuthenticationError, ValidationError
from app.repositories import dept_repository, user_repository
from app.schemas.users import UserCreate, UserUpdate
from app.utils.password import get_password_hash, validate_password_strength


class UserAdminService:
    def build_search_query(
        self,
        *,
        username: str = "",
        nickname: str = "",
        email: str = "",
        dept_id: int | None = None,
    ) -> Q:
        query = Q()
        if username:
            query &= Q(username__contains=username)
        if nickname:
            query &= Q(nickname__contains=nickname)
        if email:
            query &= Q(email__contains=email)
        if dept_id is not None:
            query &= Q(dept_id=dept_id)
        return query

    async def list_users(
        self,
        *,
        page: int,
        page_size: int,
        username: str = "",
        nickname: str = "",
        email: str = "",
        dept_id: int | None = None,
    ) -> dict:
        search = self.build_search_query(username=username, nickname=nickname, email=email, dept_id=dept_id)
        total, user_objects = await user_repository.list_users(page=page, page_size=page_size, search=search)
        data = list(await asyncio.gather(*(obj.to_dict(m2m=True, exclude_fields=["password"]) for obj in user_objects)))

        dept_ids = {item.get("dept_id") for item in data if item.get("dept_id")}
        dept_map = {}
        if dept_ids:
            dept_objects = await dept_repository.list_by_ids(dept_ids)
            dept_dicts = await asyncio.gather(*(dept.to_dict() for dept in dept_objects))
            dept_map = {dept["id"]: dept for dept in dept_dicts}

        for item in data:
            current_dept_id = item.pop("dept_id", None)
            item["dept"] = dept_map.get(current_dept_id, {})

        return {
            "data": data,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_user_detail(self, user_id: int) -> dict:
        user_obj = await user_repository.get(user_id)
        if not user_obj:
            raise AuthenticationError("用户不存在")

        return await user_obj.to_dict(exclude_fields=["password"])

    async def create_user(self, user_in: UserCreate) -> None:
        if user_in.email:
            existing_email_user = await user_repository.get_by_email(user_in.email)
            if existing_email_user:
                raise ValidationError("该邮箱地址已被使用")

        existing_username_user = await user_repository.get_by_username(user_in.username)
        if existing_username_user:
            raise ValidationError("该用户名已被使用")

        if user_in.password != "123456":
            is_valid, message = validate_password_strength(user_in.password)
            if not is_valid:
                raise ValidationError(f"密码强度不足: {message}")

        payload = user_in.create_dict()
        payload["password"] = get_password_hash(user_in.password)
        new_user = await user_repository.create(payload)
        if user_in.role_ids:
            await user_repository.assign_roles(new_user, user_in.role_ids)

    async def update_user(self, user_in: UserUpdate, *, current_user_id: int) -> None:
        existing_user = await user_repository.get(user_in.id)
        if not existing_user:
            raise AuthenticationError("用户不存在")

        if user_in.email:
            email_user = await user_repository.get_by_email(user_in.email)
            if email_user and email_user.id != user_in.id:
                raise ValidationError("该邮箱地址已被其他用户使用")

        if user_in.username:
            username_user = await user_repository.get_by_username(user_in.username)
            if username_user and username_user.id != user_in.id:
                raise ValidationError("该用户名已被其他用户使用")

        update_data = user_in.update_dict()
        if current_user_id == user_in.id and update_data.get("is_active") is False:
            raise ValidationError("不能禁用自己的账户")

        if "password" in update_data and update_data["password"]:
            is_valid, message = validate_password_strength(update_data["password"])
            if not is_valid:
                raise ValidationError(f"密码强度不足: {message}")
            update_data["password"] = get_password_hash(update_data["password"])

        user = existing_user
        if update_data:
            user = await user_repository.update(user_in.id, update_data)
            if not user:
                raise AuthenticationError("用户更新失败")

        if user_in.role_ids is not None:
            await user_repository.assign_roles(user, user_in.role_ids)

    async def delete_user(self, *, user_id: int, current_user_id: int) -> None:
        if current_user_id == user_id:
            raise ValidationError("不能删除自己的账户")

        user_to_delete = await user_repository.get(user_id)
        if not user_to_delete:
            raise AuthenticationError("要删除的用户不存在")

        if user_to_delete.is_superuser:
            superuser_count = await user_repository.count_superusers()
            if superuser_count <= 1:
                raise ValidationError("不能删除最后一个超级管理员账户")

        await user_repository.remove(user_id)

    async def reset_user_password(self, *, user_id: int, current_user_id: int) -> None:
        user_obj = await user_repository.get(user_id)
        if not user_obj:
            raise AuthenticationError("用户不存在")
        if user_obj.is_superuser and current_user_id != user_id:
            raise ValidationError("不允许重置其他超级管理员密码")

        user_obj.password = get_password_hash("123456")
        await user_obj.save()


user_admin_service = UserAdminService()
