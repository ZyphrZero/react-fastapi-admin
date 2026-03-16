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
            RUN_MIGRATIONS_ON_STARTUP=
            SEED_BASE_DATA_ON_STARTUP=
            REFRESH_API_METADATA_ON_STARTUP=
            """
        )

        self.assertIsNone(settings.SERVER_RELOAD)
        self.assertIsNone(settings.RUN_MIGRATIONS_ON_STARTUP)
        self.assertIsNone(settings.SEED_BASE_DATA_ON_STARTUP)
        self.assertIsNone(settings.REFRESH_API_METADATA_ON_STARTUP)
        self.assertTrue(settings.server_reload_enabled)
        self.assertTrue(settings.should_run_migrations_on_startup)
        self.assertTrue(settings.should_seed_base_data_on_startup)
        self.assertTrue(settings.should_refresh_api_metadata_on_startup)

    def test_explicit_boolean_overrides_still_parse(self) -> None:
        settings = self.load_settings(
            """
            APP_ENV=production
            SERVER_RELOAD=true
            RUN_MIGRATIONS_ON_STARTUP=false
            SEED_BASE_DATA_ON_STARTUP=false
            REFRESH_API_METADATA_ON_STARTUP=true
            """
        )

        self.assertTrue(settings.SERVER_RELOAD)
        self.assertFalse(settings.RUN_MIGRATIONS_ON_STARTUP)
        self.assertFalse(settings.SEED_BASE_DATA_ON_STARTUP)
        self.assertTrue(settings.REFRESH_API_METADATA_ON_STARTUP)
        self.assertTrue(settings.server_reload_enabled)
        self.assertFalse(settings.should_run_migrations_on_startup)
        self.assertFalse(settings.should_seed_base_data_on_startup)
        self.assertTrue(settings.should_refresh_api_metadata_on_startup)


if __name__ == "__main__":
    unittest.main()
