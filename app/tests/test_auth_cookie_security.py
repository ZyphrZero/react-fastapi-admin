import unittest

from starlette.responses import Response

from app.api.v1.base.base import build_public_token_payload, clear_refresh_token_cookie, set_refresh_token_cookie


class AuthCookieSecurityTestCase(unittest.TestCase):
    def test_public_token_payload_excludes_refresh_token(self) -> None:
        payload = {
            "access_token": "access-token",
            "refresh_token": "refresh-token",
            "username": "admin",
            "token_type": "bearer",
        }

        public_payload = build_public_token_payload(payload)

        self.assertNotIn("refresh_token", public_payload)
        self.assertEqual(public_payload["access_token"], "access-token")
        self.assertEqual(public_payload["username"], "admin")

    def test_set_refresh_token_cookie_marks_cookie_http_only(self) -> None:
        response = Response()

        set_refresh_token_cookie(response, "refresh-token")

        cookie_header = response.headers.get("set-cookie", "")
        self.assertIn("refresh_token=refresh-token", cookie_header)
        self.assertIn("HttpOnly", cookie_header)
        self.assertIn("Path=/api", cookie_header)
        self.assertIn("SameSite=lax", cookie_header)

    def test_clear_refresh_token_cookie_expires_cookie(self) -> None:
        response = Response()

        clear_refresh_token_cookie(response)

        cookie_header = response.headers.get("set-cookie", "")
        self.assertIn("refresh_token=", cookie_header)
        self.assertIn("Max-Age=0", cookie_header)
        self.assertIn("Path=/api", cookie_header)


if __name__ == "__main__":
    unittest.main()
