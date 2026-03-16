import unittest
from unittest.mock import AsyncMock, patch

from app.schemas.roles import RoleCreate
from app.services.role_admin_service import role_admin_service


class RoleAdminServiceTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_create_role_normalizes_parent_menu_selection(self) -> None:
        with (
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
                )
            )

        create_payload = create_mock.await_args.args[0]
        self.assertEqual(create_payload["name"], "审计员")
        self.assertEqual(create_payload["desc"], "审计角色")
        self.assertIn("/dashboard", create_payload["menu_paths"])
        self.assertIn("/system/users", create_payload["menu_paths"])
        self.assertNotIn("/system", create_payload["menu_paths"])
        self.assertEqual(create_payload["api_ids"], [101, 102])

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
