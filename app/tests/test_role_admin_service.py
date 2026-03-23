import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.core.exceptions import AuthorizationError
from app.schemas.roles import RoleCreate, RoleUpdate
from app.services.role_admin_service import role_admin_service


class RoleAdminServiceTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_create_role_normalizes_parent_menu_selection(self) -> None:
        with (
            patch(
                "app.services.admin_permission_service.user_repository.get",
                new=AsyncMock(return_value=SimpleNamespace(id=1, is_superuser=True, is_active=True)),
            ),
            patch("app.services.role_admin_service.role_repository.exists_by_name", new=AsyncMock(return_value=False)),
            patch(
                "app.services.role_admin_service.api_repository.model.filter"
            ) as api_filter_mock,
            patch("app.services.role_admin_service.role_repository.create", new=AsyncMock()) as create_mock,
        ):
            api_filter_mock.return_value.values_list = AsyncMock(return_value=[101, 102])

            await role_admin_service.create_role(
                RoleCreate(
                    name="审计员",
                    desc="审计角色",
                    menu_paths=["/dashboard", "/system"],
                    api_ids=[101, 102],
                ),
                current_user_id=1,
            )

        create_payload = create_mock.await_args.args[0]
        self.assertEqual(create_payload["name"], "审计员")
        self.assertEqual(create_payload["desc"], "审计角色")
        self.assertIn("/dashboard", create_payload["menu_paths"])
        self.assertIn("/system/users", create_payload["menu_paths"])
        self.assertNotIn("/system", create_payload["menu_paths"])
        self.assertEqual(create_payload["api_ids"], [101, 102])

    async def test_non_superuser_cannot_create_role_with_equal_permissions(self) -> None:
        actor = SimpleNamespace(id=2, is_superuser=False, is_active=True)

        with (
            patch("app.services.admin_permission_service.user_repository.get", new=AsyncMock(return_value=actor)),
            patch("app.services.role_admin_service.role_repository.exists_by_name", new=AsyncMock(return_value=False)),
            patch(
                "app.services.admin_permission_service.role_repository.list_permissions_for_user",
                new=AsyncMock(return_value={"menu_paths": ["/dashboard", "/system/users"], "api_ids": [101, 102]}),
            ),
            patch(
                "app.services.role_admin_service.api_repository.model.filter"
            ) as api_filter_mock,
        ):
            api_filter_mock.return_value.values_list = AsyncMock(return_value=[101, 102])

            with self.assertRaisesRegex(AuthorizationError, "同级或更高权限角色"):
                await role_admin_service.create_role(
                    RoleCreate(
                        name="值班管理员",
                        desc="拥有与当前操作者相同的权限",
                        menu_paths=["/dashboard", "/system/users"],
                        api_ids=[101, 102],
                    ),
                    current_user_id=2,
                )

    async def test_non_superuser_cannot_expand_role_outside_own_scope(self) -> None:
        actor = SimpleNamespace(id=2, is_superuser=False, is_active=True)
        existing_role = SimpleNamespace(id=9, menu_paths=["/dashboard"], api_ids=[101])

        with (
            patch("app.services.admin_permission_service.user_repository.get", new=AsyncMock(return_value=actor)),
            patch("app.services.role_admin_service.role_repository.get_or_raise", new=AsyncMock(return_value=existing_role)),
            patch(
                "app.services.admin_permission_service.role_repository.list_permissions_for_user",
                new=AsyncMock(return_value={"menu_paths": ["/dashboard", "/system/users"], "api_ids": [101, 102]}),
            ),
            patch(
                "app.services.role_admin_service.api_repository.model.filter"
            ) as api_filter_mock,
            patch("app.services.role_admin_service.role_repository.update", new=AsyncMock()) as update_mock,
        ):
            api_filter_mock.return_value.values_list = AsyncMock(return_value=[101, 102])

            with self.assertRaisesRegex(AuthorizationError, "同级或更高权限角色"):
                await role_admin_service.update_role(
                    RoleUpdate(id=9, menu_paths=["/dashboard", "/system/users"], api_ids=[101, 102]),
                    current_user_id=2,
                )

        update_mock.assert_not_awaited()

    async def test_get_permission_options_groups_apis_by_tag(self) -> None:
        with patch(
            "app.services.role_admin_service.api_repository.list_all_for_permissions",
            new=AsyncMock(
                return_value=[
                    {"id": 1, "method": "GET", "path": "/api/v1/user/list", "summary": "查看用户列表", "tags": "用户管理"},
                    {"id": 2, "method": "POST", "path": "/api/v1/role/create", "summary": "创建角色", "tags": "角色管理"},
                ]
            ),
        ):
            options = await role_admin_service.get_permission_options()

        self.assertTrue(options["menu_tree"])
        self.assertEqual([item["tag"] for item in options["api_groups"]], ["用户管理", "角色管理"])


if __name__ == "__main__":
    unittest.main()
