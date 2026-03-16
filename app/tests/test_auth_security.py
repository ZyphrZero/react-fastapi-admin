import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from starlette.requests import Request

from app.core.dependency import AuthControl
from app.core.exceptions import AuthenticationError
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
    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/base/userinfo",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 12345),
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

        with patch("app.services.auth_service.user_repository.get", new=AsyncMock(return_value=user)):
            menu = await auth_service.get_current_user_menu(user.id)

        self.assertEqual([item["path"] for item in menu], ["/dashboard"])

    async def test_get_current_user_menu_for_superuser_keeps_admin_pages(self) -> None:
        user = DummyUser(is_superuser=True)

        with patch("app.services.auth_service.user_repository.get", new=AsyncMock(return_value=user)):
            menu = await auth_service.get_current_user_menu(user.id)

        self.assertIn("/dashboard", [item["path"] for item in menu])
        self.assertIn("/system", [item["path"] for item in menu])


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
