from __future__ import annotations

import jwt

from app.core.exceptions import AuthenticationError, ValidationError
from app.core.navigation import get_system_menu_tree
from app.core.overview import get_platform_overview
from app.models.admin import User
from app.repositories import api_repository, role_repository, user_repository
from app.schemas.login import CredentialsSchema, JWTOut
from app.schemas.users import ProfileUpdate, UpdatePassword
from app.utils.jwt_utils import create_access_token, create_refresh_token, decode_token
from app.utils.password import get_password_hash, validate_password_strength, verify_password


class AuthService:
    def build_token_pair(self, user: User) -> dict:
        return JWTOut(
            access_token=create_access_token(
                user_id=user.id,
                username=user.username,
                is_superuser=user.is_superuser,
                session_version=user.session_version,
            ),
            refresh_token=create_refresh_token(user_id=user.id, session_version=user.session_version),
            username=user.username,
        ).model_dump()

    async def login(self, credentials: CredentialsSchema) -> dict:
        user = await user_repository.get_by_username(credentials.username)
        if not user or not verify_password(credentials.password, user.password):
            raise ValidationError("用户名或密码错误")

        if not user.is_active:
            raise ValidationError("用户已被禁用")

        await user_repository.update_last_login(user.id)
        return self.build_token_pair(user)

    async def refresh_access_token(self, refresh_token: str) -> dict:
        try:
            decoded = decode_token(refresh_token, expected_type="refresh")
        except jwt.ExpiredSignatureError as exc:
            raise AuthenticationError("刷新令牌已过期") from exc
        except jwt.InvalidTokenError as exc:
            raise AuthenticationError("无效的刷新令牌") from exc

        user_id = decoded.get("user_id")
        if not user_id:
            raise AuthenticationError("刷新令牌中缺少用户标识")
        session_version = decoded.get("session_version")
        if session_version is None:
            raise AuthenticationError("刷新令牌中缺少会话版本")

        user = await self.get_current_user(user_id)
        if not user.is_active:
            raise AuthenticationError("用户已被禁用")
        if user.session_version != int(session_version):
            raise AuthenticationError("登录状态已失效，请重新登录")
        return self.build_token_pair(user)

    async def get_current_user(self, user_id: int) -> User:
        if not user_id:
            raise AuthenticationError("用户ID不存在")

        user = await user_repository.get(user_id)
        if not user:
            raise AuthenticationError("用户不存在")

        return user

    async def get_current_user_info(self, user_id: int) -> dict:
        user = await self.get_current_user(user_id)
        return await user.to_dict(exclude_fields=["password"])

    async def get_current_user_menu(self, user_id: int) -> list[dict]:
        user = await self.get_current_user(user_id)
        if user.is_superuser:
            return get_system_menu_tree(is_superuser=True)

        permission_bundle = await role_repository.list_permissions_for_user(user.id)
        allowed_menu_paths = set(permission_bundle["menu_paths"] or ["/dashboard"])
        return get_system_menu_tree(
            is_superuser=False,
            allowed_menu_paths=allowed_menu_paths,
        )

    async def get_current_user_api_permissions(self, user_id: int) -> list[str]:
        user = await self.get_current_user(user_id)
        if not user.is_superuser:
            permission_bundle = await role_repository.list_permissions_for_user(user.id)
            return await api_repository.list_permission_keys_by_ids(permission_bundle["api_ids"])

        return await api_repository.list_permission_keys()

    async def get_platform_overview(self) -> dict:
        return await get_platform_overview()

    async def update_current_user_password(self, user_id: int, payload: UpdatePassword) -> None:
        user = await self.get_current_user(user_id)
        if not verify_password(payload.old_password, user.password):
            raise ValidationError("旧密码验证错误")
        if verify_password(payload.new_password, user.password):
            raise ValidationError("新密码不能与当前密码相同")

        is_valid, message = validate_password_strength(payload.new_password)
        if not is_valid:
            raise ValidationError(f"密码强度不足: {message}")

        user.password = get_password_hash(payload.new_password)
        user.session_version += 1
        await user.save()

    async def update_current_user_profile(self, user_id: int, payload: ProfileUpdate) -> None:
        user = await self.get_current_user(user_id)

        if payload.email and payload.email != user.email:
            existing_user = await user_repository.get_by_email(payload.email)
            if existing_user and existing_user.id != user_id:
                raise ValidationError("该邮箱地址已被其他用户使用")

        update_data = payload.update_dict()
        if not update_data:
            return

        for key, value in update_data.items():
            if not hasattr(user, key):
                continue

            field = user._meta.fields_map.get(key)
            if field and value is None and not field.null:
                continue
            setattr(user, key, value)

        await user.save()

    async def logout(self, user_id: int) -> None:
        user = await self.get_current_user(user_id)
        user.session_version += 1
        await user.save(update_fields=["session_version", "updated_at"])


auth_service = AuthService()
