import unittest
from unittest.mock import AsyncMock, patch

from app.core.exceptions import ValidationError
from app.schemas.users import ResetPasswordRequest, UserUpdate
from app.services.user_admin_service import user_admin_service
from app.utils.password import get_password_hash, verify_password


class DummyUser:
    def __init__(self, *, id: int = 1, is_superuser: bool, password: str | None = None) -> None:
        self.id = id
        self.is_superuser = is_superuser
        self.password = password or get_password_hash("OldPass1!")
        self.session_version = 0
        self.saved = False

    async def save(self) -> None:
        self.saved = True


class UserAdminServiceResetPasswordTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_superuser_can_reset_own_password(self) -> None:
        user = DummyUser(is_superuser=True)

        with patch("app.services.user_admin_service.user_repository.get", new=AsyncMock(return_value=user)):
            await user_admin_service.reset_user_password(
                ResetPasswordRequest(user_id=1, new_password="NewPass1!"),
                current_user_id=1,
            )

        self.assertTrue(user.saved)
        self.assertEqual(user.session_version, 1)
        self.assertTrue(verify_password("NewPass1!", user.password))

    async def test_superuser_cannot_reset_other_superuser_password(self) -> None:
        user = DummyUser(is_superuser=True)

        with patch("app.services.user_admin_service.user_repository.get", new=AsyncMock(return_value=user)):
            with self.assertRaisesRegex(ValidationError, "不允许重置其他超级管理员密码"):
                await user_admin_service.reset_user_password(
                    ResetPasswordRequest(user_id=1, new_password="NewPass1!"),
                    current_user_id=2,
                )

        self.assertFalse(user.saved)

    async def test_normal_user_password_can_still_be_reset(self) -> None:
        user = DummyUser(is_superuser=False)

        with patch("app.services.user_admin_service.user_repository.get", new=AsyncMock(return_value=user)):
            await user_admin_service.reset_user_password(
                ResetPasswordRequest(user_id=2, new_password="Another1!"),
                current_user_id=1,
            )

        self.assertTrue(user.saved)
        self.assertEqual(user.session_version, 1)
        self.assertTrue(verify_password("Another1!", user.password))

    async def test_reset_password_rejects_same_password(self) -> None:
        user = DummyUser(is_superuser=False)

        with patch("app.services.user_admin_service.user_repository.get", new=AsyncMock(return_value=user)):
            with self.assertRaisesRegex(ValidationError, "新密码不能与当前密码相同"):
                await user_admin_service.reset_user_password(
                    ResetPasswordRequest(user_id=2, new_password="OldPass1!"),
                    current_user_id=1,
                )


class UserAdminServiceUpdateUserTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_current_user_cannot_disable_self(self) -> None:
        user = DummyUser(id=1, is_superuser=True)

        with (
            patch("app.services.user_admin_service.user_repository.get", new=AsyncMock(return_value=user)),
            patch("app.services.user_admin_service.user_repository.update", new=AsyncMock()) as update_mock,
        ):
            with self.assertRaisesRegex(ValidationError, "不能禁用自己的账户"):
                await user_admin_service.update_user(UserUpdate(id=1, is_active=False), current_user_id=1)

        update_mock.assert_not_awaited()

    async def test_admin_can_disable_other_user(self) -> None:
        user = DummyUser(id=2, is_superuser=False)

        with (
            patch("app.services.user_admin_service.user_repository.get", new=AsyncMock(return_value=user)),
            patch("app.services.user_admin_service.user_repository.update", new=AsyncMock(return_value=user)) as update_mock,
        ):
            await user_admin_service.update_user(UserUpdate(id=2, is_active=False), current_user_id=1)

        update_mock.assert_awaited_once_with(2, {"is_active": False})


if __name__ == "__main__":
    unittest.main()
