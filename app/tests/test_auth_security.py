import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from starlette.requests import Request

from app.core.dependency import AuthControl, PermissionControl
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.middlewares import HttpAuditLogMiddleware
from app.services.auth_service import auth_service
from app.utils.jwt_utils import create_access_token, create_refresh_token


class DummyUser:
    def __init__(
        self,
        *,
        user_id: int = 1,
        session_version: int = 0,
        is_active: bool = True,
        is_superuser: bool = True,
    ) -> None:
        self.id = user_id
        self.username = "admin"
        self.is_superuser = is_superuser
        self.is_active = is_active
        self.session_version = session_version

    async def save(self, *args, **kwargs) -> None:
        return None


def make_request() -> Request:
    return make_route_request()


def make_route_request(*, method: str = "GET", path: str = "/api/v1/base/userinfo", path_format: str | None = None) -> Request:
    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "route": SimpleNamespace(path_format=path_format or path),
    }
    return Request(scope, receive)


class AuthServiceRefreshTokenTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_refresh_token_round_trip_succeeds(self) -> None:
        user = DummyUser(session_version=3)
        refresh_token = create_refresh_token(user_id=user.id, session_version=user.session_version)

        with patch("app.services.auth_service.user_repository.get", new=AsyncMock(return_value=user)):
            tokens = await auth_service.refresh_access_token(refresh_token)

        self.assertIn("access_token", tokens)
        self.assertIn("refresh_token", tokens)

    async def test_refresh_token_rejected_after_session_version_change(self) -> None:
        user = DummyUser(session_version=4)
        stale_refresh_token = create_refresh_token(user_id=user.id, session_version=3)

        with patch("app.services.auth_service.user_repository.get", new=AsyncMock(return_value=user)):
            with self.assertRaisesRegex(AuthenticationError, "登录状态已失效"):
                await auth_service.refresh_access_token(stale_refresh_token)

    async def test_get_current_user_menu_for_normal_user_excludes_admin_pages(self) -> None:
        user = DummyUser(is_superuser=False)

        with (
            patch("app.services.auth_service.user_repository.get", new=AsyncMock(return_value=user)),
            patch(
                "app.services.auth_service.role_repository.list_permissions_for_user",
                new=AsyncMock(return_value={"menu_paths": ["/dashboard"], "api_ids": []}),
            ),
        ):
            menu = await auth_service.get_current_user_menu(user.id)

        self.assertEqual([item["path"] for item in menu], ["/dashboard"])

    async def test_get_current_user_menu_for_superuser_keeps_admin_pages(self) -> None:
        user = DummyUser(is_superuser=True)

        with patch("app.services.auth_service.user_repository.get", new=AsyncMock(return_value=user)):
            menu = await auth_service.get_current_user_menu(user.id)

        self.assertIn("/dashboard", [item["path"] for item in menu])
        self.assertIn("/system", [item["path"] for item in menu])

    async def test_get_current_user_api_permissions_for_role_user_uses_role_bindings(self) -> None:
        user = DummyUser(is_superuser=False)

        with (
            patch("app.services.auth_service.user_repository.get", new=AsyncMock(return_value=user)),
            patch(
                "app.services.auth_service.role_repository.list_permissions_for_user",
                new=AsyncMock(return_value={"menu_paths": ["/dashboard"], "api_ids": [1, 2]}),
            ),
            patch(
                "app.services.auth_service.api_repository.list_permission_keys_by_ids",
                new=AsyncMock(return_value=["get/api/v1/user/list", "post/api/v1/role/create"]),
            ),
        ):
            permissions = await auth_service.get_current_user_api_permissions(user.id)

        self.assertEqual(permissions, ["get/api/v1/user/list", "post/api/v1/role/create"])


class AuthControlSecurityTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_dev_token_is_not_accepted(self) -> None:
        request = make_request()

        with self.assertRaisesRegex(AuthenticationError, "无效的Token"):
            await AuthControl.is_authed(request, "Bearer dev")

    async def test_access_token_requires_matching_session_version(self) -> None:
        request = make_request()
        user = DummyUser(session_version=2)
        access_token = create_access_token(
            user_id=user.id,
            username=user.username,
            is_superuser=user.is_superuser,
            session_version=1,
        )

        with patch("app.core.dependency.user_repository.get", new=AsyncMock(return_value=user)):
            with self.assertRaisesRegex(AuthenticationError, "登录状态已失效"):
                await AuthControl.is_authed(request, f"Bearer {access_token}")

    async def test_permission_control_allows_api_granted_by_role(self) -> None:
        request = make_route_request(path="/api/v1/user/list")
        user = DummyUser(is_superuser=False)

        with (
            patch(
                "app.core.dependency.role_repository.list_permissions_for_user",
                new=AsyncMock(return_value={"menu_paths": ["/system/users"], "api_ids": [1]}),
            ),
            patch(
                "app.core.dependency.api_repository.list_permission_keys_by_ids",
                new=AsyncMock(return_value=["get/api/v1/user/list"]),
            ),
        ):
            await PermissionControl.has_permission(request, current_user=user)

    async def test_permission_control_rejects_missing_api_grant(self) -> None:
        request = make_route_request(path="/api/v1/user/list")
        user = DummyUser(is_superuser=False)

        with (
            patch(
                "app.core.dependency.role_repository.list_permissions_for_user",
                new=AsyncMock(return_value={"menu_paths": ["/dashboard"], "api_ids": []}),
            ),
            patch(
                "app.core.dependency.api_repository.list_permission_keys_by_ids",
                new=AsyncMock(return_value=[]),
            ),
        ):
            with self.assertRaisesRegex(AuthorizationError, "权限不足"):
                await PermissionControl.has_permission(request, current_user=user)


class AuditLogMiddlewareSecurityTestCase(unittest.TestCase):
    def test_sensitive_fields_are_redacted(self) -> None:
        middleware = HttpAuditLogMiddleware(app=None, methods=["POST"], exclude_paths=[])
        payload = {
            "old_password": "OldPass1!",
            "new_password": "NewPass1!",
            "access_token": "secret-access-token",
            "profile": {"refresh_token": "secret-refresh-token"},
        }

        self.assertEqual(
            middleware.redact_sensitive_data(payload),
            {
                "old_password": "***REDACTED***",
                "new_password": "***REDACTED***",
                "access_token": "***REDACTED***",
                "profile": {"refresh_token": "***REDACTED***"},
            },
        )

    def test_request_body_parser_extracts_password_fields_before_redaction(self) -> None:
        async def receive():
            return {
                "type": "http.request",
                "body": json.dumps({"old_password": "OldPass1!", "new_password": "NewPass1!"}).encode(),
                "more_body": False,
            }

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/base/update_password",
            "query_string": b"",
            "headers": [(b"content-type", b"application/json")],
            "client": ("127.0.0.1", 12345),
        }
        request = Request(scope, receive)
        middleware = HttpAuditLogMiddleware(app=None, methods=["POST"], exclude_paths=[])

        parsed_args = __import__("asyncio").run(middleware.get_request_args(request))
        redacted_args = middleware.redact_sensitive_data(parsed_args)

        self.assertEqual(redacted_args["old_password"], "***REDACTED***")
        self.assertEqual(redacted_args["new_password"], "***REDACTED***")


if __name__ == "__main__":
    unittest.main()
