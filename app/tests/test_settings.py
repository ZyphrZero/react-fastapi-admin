import os
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

from app.settings.config import Settings


class SettingsEnvParsingTestCase(unittest.TestCase):
    def load_settings(self, env_content: str) -> Settings:
        normalized_content = textwrap.dedent(env_content).strip()

        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text(f"{normalized_content}\n", encoding="utf-8")

            with patch.dict(os.environ, {}, clear=True):
                return Settings(_env_file=env_file)

    def test_blank_optional_booleans_use_derived_defaults(self) -> None:
        settings = self.load_settings(
            """
            APP_ENV=development
            SERVER_RELOAD=
            REFRESH_TOKEN_COOKIE_SECURE=
            """
        )

        self.assertIsNone(settings.SERVER_RELOAD)
        self.assertIsNone(settings.REFRESH_TOKEN_COOKIE_SECURE)
        self.assertTrue(settings.server_reload_enabled)
        self.assertFalse(settings.refresh_token_cookie_secure)

    def test_explicit_boolean_overrides_still_parse(self) -> None:
        settings = self.load_settings(
            """
            APP_ENV=production
            SECRET_KEY=production_secret_key_that_is_long_enough_1234567890
            SERVER_RELOAD=true
            REFRESH_TOKEN_COOKIE_SECURE=false
            """
        )

        self.assertTrue(settings.SERVER_RELOAD)
        self.assertFalse(settings.REFRESH_TOKEN_COOKIE_SECURE)
        self.assertTrue(settings.server_reload_enabled)
        self.assertFalse(settings.refresh_token_cookie_secure)

    def test_development_generates_secret_key_when_missing(self) -> None:
        settings = self.load_settings(
            """
            APP_ENV=development
            """
        )

        self.assertGreaterEqual(len(settings.SECRET_KEY), 32)

    def test_ip_whitelist_reads_direct_env_name(self) -> None:
        settings = self.load_settings(
            """
            APP_ENV=development
            IP_WHITELIST=192.168.1.100,10.0.0.1
            """
        )

        self.assertEqual(settings.ip_whitelist, ["192.168.1.100", "10.0.0.1"])


if __name__ == "__main__":
    unittest.main()
