from __future__ import annotations

import asyncio

from tortoise.expressions import Q

from app.core.exceptions import AuthenticationError, ValidationError
from app.repositories import role_repository, user_repository
from app.schemas.users import ResetPasswordRequest, UserCreate, UserUpdate
from app.services.admin_permission_service import admin_permission_service
from app.services.auth_service import USER_RESPONSE_EXCLUDED_FIELDS
from app.utils.password import get_password_hash, validate_password_strength, verify_password


class UserAdminService:
    def build_search_query(
        self,
        *,
        username: str = "",
        nickname: str = "",
        email: str = "",
    ) -> Q:
        query = Q()
        if username:
            query &= Q(username__contains=username)
        if nickname:
            query &= Q(nickname__contains=nickname)
        if email:
            query &= Q(email__contains=email)
        return query

    async def list_users(
        self,
        *,
        page: int,
        page_size: int,
        username: str = "",
        nickname: str = "",
        email: str = "",
    ) -> dict:
        search = self.build_search_query(username=username, nickname=nickname, email=email)
        total, user_objects = await user_repository.list_users(page=page, page_size=page_size, search=search)
        data = list(
            await asyncio.gather(
                *(obj.to_dict(m2m=True, exclude_fields=USER_RESPONSE_EXCLUDED_FIELDS) for obj in user_objects)
            )
        )

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

        return await user_obj.to_dict(exclude_fields=USER_RESPONSE_EXCLUDED_FIELDS)

    async def create_user(self, user_in: UserCreate, *, current_user_id: int) -> None:
        actor = await admin_permission_service.get_actor(current_user_id)

        if user_in.email:
            existing_email_user = await user_repository.get_by_email(user_in.email)
            if existing_email_user:
                raise ValidationError("该邮箱地址已被使用")

        existing_username_user = await user_repository.get_by_username(user_in.username)
        if existing_username_user:
            raise ValidationError("该用户名已被使用")

        is_valid, message = validate_password_strength(user_in.password)
        if not is_valid:
            raise ValidationError(f"密码强度不足: {message}")

        payload = user_in.create_dict()
        role_ids = list(user_in.role_ids or [])
        if not user_in.is_superuser and not role_ids:
            default_role = await role_repository.get_by_name("普通用户")
            if not default_role:
                raise ValidationError("默认角色不存在，请先初始化基础角色")
            role_ids = [default_role.id]

        await admin_permission_service.ensure_can_create_user(
            actor=actor,
            is_superuser=bool(user_in.is_superuser),
            role_ids=role_ids,
        )

        payload["password"] = get_password_hash(user_in.password)
        new_user = await user_repository.create(payload)
        if role_ids:
            await user_repository.assign_roles(new_user, role_ids)

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

        actor = await admin_permission_service.get_actor(current_user_id)
        await admin_permission_service.ensure_can_update_user(
            actor=actor,
            target=existing_user,
            next_is_superuser=bool(update_data.get("is_superuser", existing_user.is_superuser)),
            role_ids=user_in.role_ids,
        )
        if update_data.get("password"):
            raise ValidationError("请使用重置密码接口修改用户密码")

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

        actor = await admin_permission_service.get_actor(current_user_id)
        await admin_permission_service.ensure_can_manage_user(actor=actor, target=user_to_delete, action="删除")

        if user_to_delete.is_superuser:
            superuser_count = await user_repository.count_superusers()
            if superuser_count <= 1:
                raise ValidationError("不能删除最后一个超级管理员账户")

        await user_repository.remove(user_id)

    async def reset_user_password(self, payload: ResetPasswordRequest, *, current_user_id: int) -> None:
        actor = await admin_permission_service.get_actor(current_user_id)
        user_obj = await user_repository.get(payload.user_id)
        if not user_obj:
            raise AuthenticationError("用户不存在")
        if user_obj.is_superuser and current_user_id != payload.user_id:
            raise ValidationError("不允许重置其他超级管理员密码")
        if current_user_id != payload.user_id:
            await admin_permission_service.ensure_can_manage_user(actor=actor, target=user_obj, action="重置密码")
        if verify_password(payload.new_password, user_obj.password):
            raise ValidationError("新密码不能与当前密码相同")

        is_valid, message = validate_password_strength(payload.new_password)
        if not is_valid:
            raise ValidationError(f"密码强度不足: {message}")

        user_obj.password = get_password_hash(payload.new_password)
        user_obj.session_version += 1
        user_obj.refresh_token_jti = None
        await user_obj.save()


user_admin_service = UserAdminService()
