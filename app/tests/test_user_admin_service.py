import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.core.exceptions import AuthorizationError, ValidationError
from app.schemas.users import ResetPasswordRequest, UserCreate, UserUpdate
from app.services.user_admin_service import user_admin_service
from app.utils.password import get_password_hash, verify_password


class DummyUser:
    def __init__(
        self,
        *,
        id: int = 1,
        is_superuser: bool,
        password: str | None = None,
        is_active: bool = True,
    ) -> None:
        self.id = id
        self.is_superuser = is_superuser
        self.is_active = is_active
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
        actor = DummyUser(id=1, is_superuser=True)
        user = DummyUser(id=2, is_superuser=False)

        with patch(
            "app.services.user_admin_service.user_repository.get",
            new=AsyncMock(side_effect=lambda user_id: actor if user_id == 1 else user),
        ):
            await user_admin_service.reset_user_password(
                ResetPasswordRequest(user_id=2, new_password="Another1!"),
                current_user_id=1,
            )

        self.assertTrue(user.saved)
        self.assertEqual(user.session_version, 1)
        self.assertTrue(verify_password("Another1!", user.password))

    async def test_reset_password_rejects_same_password(self) -> None:
        actor = DummyUser(id=1, is_superuser=True)
        user = DummyUser(id=2, is_superuser=False)

        with patch(
            "app.services.user_admin_service.user_repository.get",
            new=AsyncMock(side_effect=lambda user_id: actor if user_id == 1 else user),
        ):
            with self.assertRaisesRegex(ValidationError, "新密码不能与当前密码相同"):
                await user_admin_service.reset_user_password(
                    ResetPasswordRequest(user_id=2, new_password="OldPass1!"),
                    current_user_id=1,
                )

    async def test_non_superuser_cannot_reset_peer_password(self) -> None:
        actor = DummyUser(id=1, is_superuser=False)
        target = DummyUser(id=2, is_superuser=False)

        with (
            patch(
                "app.services.user_admin_service.user_repository.get",
                new=AsyncMock(side_effect=lambda user_id: actor if user_id == 1 else target),
            ),
            patch(
                "app.services.user_admin_service.role_repository.list_permissions_for_user",
                new=AsyncMock(
                    side_effect=lambda user_id: (
                        {"menu_paths": ["/dashboard", "/system/users"], "api_ids": [1, 2]}
                        if user_id == 1
                        else {"menu_paths": ["/dashboard", "/system/users"], "api_ids": [1, 2]}
                    )
                ),
            ),
        ):
            with self.assertRaisesRegex(AuthorizationError, "同级或更高权限账户"):
                await user_admin_service.reset_user_password(
                    ResetPasswordRequest(user_id=2, new_password="Another1!"),
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
        actor = DummyUser(id=1, is_superuser=True)
        user = DummyUser(id=2, is_superuser=False)

        with (
            patch(
                "app.services.user_admin_service.user_repository.get",
                new=AsyncMock(side_effect=lambda user_id: actor if user_id == 1 else user),
            ),
            patch("app.services.user_admin_service.user_repository.update", new=AsyncMock(return_value=user)) as update_mock,
        ):
            await user_admin_service.update_user(UserUpdate(id=2, is_active=False), current_user_id=1)

        update_mock.assert_awaited_once_with(2, {"is_active": False})

    async def test_non_superuser_cannot_promote_user_to_superuser(self) -> None:
        actor = DummyUser(id=1, is_superuser=False)
        target = DummyUser(id=2, is_superuser=False)

        with (
            patch(
                "app.services.user_admin_service.user_repository.get",
                new=AsyncMock(side_effect=lambda user_id: actor if user_id == 1 else target),
            ),
            patch(
                "app.services.user_admin_service.role_repository.list_permissions_for_user",
                new=AsyncMock(
                    side_effect=lambda user_id: (
                        {"menu_paths": ["/dashboard", "/system/users"], "api_ids": [1, 2]}
                        if user_id == 1
                        else {"menu_paths": ["/dashboard"], "api_ids": []}
                    )
                ),
            ),
            patch("app.services.user_admin_service.user_repository.update", new=AsyncMock()) as update_mock,
        ):
            with self.assertRaisesRegex(AuthorizationError, "超级管理员"):
                await user_admin_service.update_user(UserUpdate(id=2, is_superuser=True), current_user_id=1)

        update_mock.assert_not_awaited()

    async def test_non_superuser_cannot_change_peer_password_via_update(self) -> None:
        actor = DummyUser(id=1, is_superuser=False)
        target = DummyUser(id=2, is_superuser=False)

        with (
            patch(
                "app.services.user_admin_service.user_repository.get",
                new=AsyncMock(side_effect=lambda user_id: actor if user_id == 1 else target),
            ),
            patch(
                "app.services.user_admin_service.role_repository.list_permissions_for_user",
                new=AsyncMock(
                    side_effect=lambda user_id: (
                        {"menu_paths": ["/dashboard", "/system/users"], "api_ids": [1, 2]}
                        if user_id == 1
                        else {"menu_paths": ["/dashboard", "/system/users"], "api_ids": [1, 2]}
                    )
                ),
            ),
            patch("app.services.user_admin_service.user_repository.update", new=AsyncMock()) as update_mock,
        ):
            with self.assertRaisesRegex(AuthorizationError, "同级或更高权限账户"):
                await user_admin_service.update_user(UserUpdate(id=2, password="Another1!"), current_user_id=1)

        update_mock.assert_not_awaited()


class UserAdminServiceCreateUserTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_normal_user_without_role_uses_default_role(self) -> None:
        actor = DummyUser(id=1, is_superuser=True)
        new_user = DummyUser(id=3, is_superuser=False)
        default_role = SimpleNamespace(id=9)

        with (
            patch("app.services.user_admin_service.user_repository.get", new=AsyncMock(return_value=actor)),
            patch("app.services.user_admin_service.user_repository.get_by_email", new=AsyncMock(return_value=None)),
            patch("app.services.user_admin_service.user_repository.get_by_username", new=AsyncMock(return_value=None)),
            patch("app.services.user_admin_service.role_repository.get_by_name", new=AsyncMock(return_value=default_role)),
            patch("app.services.user_admin_service.user_repository.create", new=AsyncMock(return_value=new_user)),
            patch("app.services.user_admin_service.user_repository.assign_roles", new=AsyncMock()) as assign_roles_mock,
        ):
            await user_admin_service.create_user(
                UserCreate(
                    username="demo-user",
                    email="demo@example.com",
                    password="ValidPass1!",
                    is_superuser=False,
                    role_ids=[],
                ),
                current_user_id=1,
            )

        assign_roles_mock.assert_awaited_once_with(new_user, [9])

    async def test_non_superuser_cannot_create_superuser_account(self) -> None:
        actor = DummyUser(id=1, is_superuser=False)

        with (
            patch("app.services.user_admin_service.user_repository.get", new=AsyncMock(return_value=actor)),
            patch("app.services.user_admin_service.user_repository.get_by_email", new=AsyncMock(return_value=None)),
            patch("app.services.user_admin_service.user_repository.get_by_username", new=AsyncMock(return_value=None)),
        ):
            with self.assertRaisesRegex(AuthorizationError, "超级管理员"):
                await user_admin_service.create_user(
                    UserCreate(
                        username="ops-admin",
                        email="ops@example.com",
                        password="ValidPass1!",
                        is_superuser=True,
                        role_ids=[],
                    ),
                    current_user_id=1,
                )


if __name__ == "__main__":
    unittest.main()
