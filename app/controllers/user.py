from datetime import datetime
from typing import List, Optional, Tuple

from fastapi.exceptions import HTTPException

from app.core.crud import CRUDBase
from app.models.admin import User
from app.schemas.login import CredentialsSchema
from app.schemas.users import UserCreate, UserUpdate
from app.utils.password import get_password_hash, verify_password, validate_password_strength

from .role import role_controller


class UserController(CRUDBase[User, UserCreate, UserUpdate]):
    def __init__(self):
        super().__init__(model=User)

    async def get_by_email(self, email: str) -> Optional[User]:
        return await self.model.filter(email=email).first()

    async def get_by_username(self, username: str) -> Optional[User]:
        return await self.model.filter(username=username).first()

    async def validate_password(self, password: str) -> Tuple[bool, str]:
        """
        Validate password strength.
        :param password: Password to validate.
        :return: (whether validation passed, failure reason)
        """
        return validate_password_strength(password)

    async def create_user(self, obj_in: UserCreate) -> User:
        is_valid, message = await self.validate_password(obj_in.password)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"密码强度不足: {message}")

        obj_in.password = get_password_hash(password=obj_in.password)
        obj = await self.create(obj_in)
        return obj

    async def update_last_login(self, id: int) -> None:
        user = await self.model.get(id=id)
        user.last_login = datetime.now()
        await user.save()

    async def authenticate(self, credentials: CredentialsSchema) -> Optional["User"]:
        # Fetch the user.
        user = await self.model.filter(username=credentials.username).first()
        if not user:
            # Avoid revealing whether the user exists to reduce enumeration risk.
            raise HTTPException(status_code=400, detail="用户名或密码错误")

        # Verify the password.
        verified = verify_password(credentials.password, user.password)
        if not verified:
            # Avoid revealing whether the password was wrong to reduce enumeration risk.
            raise HTTPException(status_code=400, detail="用户名或密码错误")

        # Check the user status.
        if not user.is_active:
            raise HTTPException(status_code=400, detail="用户已被禁用")

        return user

    async def update_roles(self, user: User, role_ids: List[int]) -> None:
        await user.roles.clear()
        for role_id in role_ids:
            role_obj = await role_controller.get(id=role_id)
            await user.roles.add(role_obj)

        # The permission cache has been removed, so no cache invalidation is required anymore.

    async def reset_password(self, user_id: int, new_password: str = "123456", current_user_id: Optional[int] = None):
        user_obj = await self.get(id=user_id)
        if user_obj.is_superuser and current_user_id != user_id:
            raise HTTPException(status_code=403, detail="不允许重置其他超级管理员密码")

        # Validate the new password unless the default password is being used.
        is_valid, message = await self.validate_password(new_password)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"密码强度不足: {message}")

        user_obj.password = get_password_hash(password=new_password)
        user_obj.session_version += 1
        await user_obj.save()


user_controller = UserController()
