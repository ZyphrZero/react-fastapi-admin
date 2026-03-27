import unittest
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi import APIRouter, Depends
from fastapi import HTTPException
from pydantic import ValidationError as PydanticValidationError

import app.application as app_module
from app.controllers.upload import upload_controller
from app.core.dependency import AuthControl
from app.repositories.api_repository import ApiRepository
from app.schemas.system_settings import (
    ApplicationSettingsUpdate,
    LoggingSettingsUpdate,
    SecuritySettingsUpdate,
    StorageProvider,
    StorageSettingsUpdate,
)
from app.services.system_setting_service import system_setting_service
from app.settings import settings


class SystemSettingServiceTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_get_application_settings_defaults_to_runtime_settings(self) -> None:
        with patch(
            "app.services.system_setting_service.system_setting_repository.get_value",
            new=AsyncMock(return_value=None),
        ):
            data = await system_setting_service.get_application_settings()

        self.assertEqual(data["app_title"], settings.APP_TITLE)
        self.assertEqual(data["debug"], settings.DEBUG)
        self.assertEqual(data["environment"], settings.APP_ENV)
        self.assertEqual(data["project_name"], settings.PROJECT_NAME)
        self.assertEqual(data["app_description"], settings.APP_DESCRIPTION)
        self.assertEqual(data["login_page_image_url"], settings.LOGIN_PAGE_IMAGE_URL)
        self.assertEqual(data["login_page_image_mode"], settings.LOGIN_PAGE_IMAGE_MODE)
        self.assertEqual(data["notification_position"], settings.NOTIFICATION_POSITION)
        self.assertEqual(data["notification_duration"], settings.NOTIFICATION_DURATION)
        self.assertEqual(data["notification_visible_toasts"], settings.NOTIFICATION_VISIBLE_TOASTS)

    async def test_get_logging_settings_defaults_to_runtime_settings(self) -> None:
        with patch(
            "app.services.system_setting_service.system_setting_repository.get_value",
            new=AsyncMock(return_value=None),
        ):
            data = await system_setting_service.get_logging_settings()

        self.assertEqual(data["logs_root"], settings.LOGS_ROOT)
        self.assertEqual(data["log_retention_days"], settings.LOG_RETENTION_DAYS)
        self.assertEqual(data["log_rotation"], settings.LOG_ROTATION)
        self.assertEqual(data["log_max_file_size"], settings.LOG_MAX_FILE_SIZE)
        self.assertEqual(data["log_enable_access_log"], settings.LOG_ENABLE_ACCESS_LOG)
        self.assertTrue(data["access_log_requires_restart"])

    async def test_get_storage_settings_defaults_to_local_mode(self) -> None:
        with patch(
            "app.services.system_setting_service.system_setting_repository.get_value",
            new=AsyncMock(return_value=None),
        ):
            data = await system_setting_service.get_storage_settings()

        self.assertEqual(data["provider"], StorageProvider.LOCAL.value)
        self.assertEqual(data["local_upload_dir"], "uploads")
        self.assertEqual(data["local_full_url"], "")
        self.assertEqual(data["oss_upload_dir"], "uploads")
        self.assertEqual(data["local_url_prefix"], "/static/uploads")

    async def test_update_storage_settings_persists_normalized_payload(self) -> None:
        saved_payload: dict = {}

        async def fake_set_value(*, key: str, value: dict, description: str | None = None):
            saved_payload.clear()
            saved_payload.update(value)
            return None

        async def fake_get_value(key: str, default=None):
            return saved_payload or default

        payload = StorageSettingsUpdate(
            provider=StorageProvider.OSS,
            local_upload_dir="/local-assets/",
            local_full_url="https://files.example.com",
            oss_access_key_id="access-key",
            oss_access_key_secret="secret-key",
            oss_bucket_name="media-bucket",
            oss_endpoint="oss-cn-hangzhou.aliyuncs.com",
            oss_bucket_domain="cdn.example.com",
            oss_upload_dir="/assets/",
        )

        with (
            patch(
                "app.services.system_setting_service.system_setting_repository.set_value",
                new=AsyncMock(side_effect=fake_set_value),
            ),
            patch(
                "app.services.system_setting_service.system_setting_repository.get_value",
                new=AsyncMock(side_effect=fake_get_value),
            ),
        ):
            data = await system_setting_service.update_storage_settings(payload)

        self.assertEqual(saved_payload["provider"], StorageProvider.OSS.value)
        self.assertEqual(saved_payload["local_upload_dir"], "local-assets")
        self.assertEqual(saved_payload["local_full_url"], "https://files.example.com")
        self.assertEqual(saved_payload["oss_upload_dir"], "assets")
        self.assertEqual(data["oss_bucket_domain"], "cdn.example.com")
        self.assertEqual(data["local_url_prefix"], "/static/local-assets")

    async def test_update_application_settings_persists_and_applies_runtime_payload(self) -> None:
        saved_payload: dict = {}
        original_app_title = settings.APP_TITLE
        original_project_name = settings.PROJECT_NAME
        original_app_description = settings.APP_DESCRIPTION
        original_debug = settings.DEBUG
        original_login_page_image_url = settings.LOGIN_PAGE_IMAGE_URL
        original_login_page_image_mode = settings.LOGIN_PAGE_IMAGE_MODE
        original_notification_position = settings.NOTIFICATION_POSITION
        original_notification_duration = settings.NOTIFICATION_DURATION
        original_notification_visible_toasts = settings.NOTIFICATION_VISIBLE_TOASTS

        async def fake_set_value(*, key: str, value: dict, description: str | None = None):
            saved_payload.clear()
            saved_payload.update(value)
            return None

        async def fake_get_value(key: str, default=None):
            return saved_payload or default

        payload = ApplicationSettingsUpdate(
            app_title="Control Hub",
            project_name="Control Platform",
            app_description="Unified admin control center",
            debug=False,
            login_page_image_url="/static/uploads/image/20260326/login.webp",
            login_page_image_mode="cover",
            notification_position="bottom-left",
            notification_duration=6500,
            notification_visible_toasts=5,
        )

        try:
            with (
                patch(
                    "app.services.system_setting_service.system_setting_repository.set_value",
                    new=AsyncMock(side_effect=fake_set_value),
                ),
                patch(
                    "app.services.system_setting_service.system_setting_repository.get_value",
                    new=AsyncMock(side_effect=fake_get_value),
                ),
                patch(
                    "app.services.system_setting_service.log_manager.setup_logger",
                ) as setup_logger_mock,
                patch.object(AuthControl, "initialize", new=AsyncMock()) as auth_initialize_mock,
            ):
                data = await system_setting_service.update_application_settings(payload)

            self.assertEqual(saved_payload["app_title"], "Control Hub")
            self.assertEqual(saved_payload["project_name"], "Control Platform")
            self.assertEqual(saved_payload["app_description"], "Unified admin control center")
            self.assertFalse(saved_payload["debug"])
            self.assertEqual(saved_payload["login_page_image_url"], "/static/uploads/image/20260326/login.webp")
            self.assertEqual(saved_payload["login_page_image_mode"], "cover")
            self.assertEqual(saved_payload["notification_position"], "bottom-left")
            self.assertEqual(saved_payload["notification_duration"], 6500)
            self.assertEqual(saved_payload["notification_visible_toasts"], 5)
            self.assertEqual(settings.APP_TITLE, "Control Hub")
            self.assertEqual(settings.PROJECT_NAME, "Control Platform")
            self.assertEqual(settings.APP_DESCRIPTION, "Unified admin control center")
            self.assertFalse(settings.DEBUG)
            self.assertEqual(settings.LOGIN_PAGE_IMAGE_URL, "/static/uploads/image/20260326/login.webp")
            self.assertEqual(settings.LOGIN_PAGE_IMAGE_MODE, "cover")
            self.assertEqual(settings.NOTIFICATION_POSITION, "bottom-left")
            self.assertEqual(settings.NOTIFICATION_DURATION, 6500)
            self.assertEqual(settings.NOTIFICATION_VISIBLE_TOASTS, 5)
            setup_logger_mock.assert_called_once_with(force=True)
            auth_initialize_mock.assert_awaited_once()
            self.assertEqual(data["app_title"], "Control Hub")
            self.assertEqual(data["login_page_image_url"], "/static/uploads/image/20260326/login.webp")
            self.assertEqual(data["login_page_image_mode"], "cover")
            self.assertEqual(data["notification_position"], "bottom-left")
            self.assertEqual(data["notification_duration"], 6500)
            self.assertEqual(data["notification_visible_toasts"], 5)
        finally:
            settings.APP_TITLE = original_app_title
            settings.PROJECT_NAME = original_project_name
            settings.APP_DESCRIPTION = original_app_description
            settings.DEBUG = original_debug
            settings.LOGIN_PAGE_IMAGE_URL = original_login_page_image_url
            settings.LOGIN_PAGE_IMAGE_MODE = original_login_page_image_mode
            settings.NOTIFICATION_POSITION = original_notification_position
            settings.NOTIFICATION_DURATION = original_notification_duration
            settings.NOTIFICATION_VISIBLE_TOASTS = original_notification_visible_toasts

    async def test_update_logging_settings_persists_and_applies_runtime_payload(self) -> None:
        saved_payload: dict = {}
        original_values = {
            "LOGS_ROOT": settings.LOGS_ROOT,
            "LOG_RETENTION_DAYS": settings.LOG_RETENTION_DAYS,
            "LOG_ROTATION": settings.LOG_ROTATION,
            "LOG_MAX_FILE_SIZE": settings.LOG_MAX_FILE_SIZE,
            "LOG_ENABLE_ACCESS_LOG": settings.LOG_ENABLE_ACCESS_LOG,
        }

        async def fake_set_value(*, key: str, value: dict, description: str | None = None):
            saved_payload.clear()
            saved_payload.update(value)
            return None

        async def fake_get_value(key: str, default=None):
            return saved_payload or default

        payload = LoggingSettingsUpdate(
            logs_root="runtime/logs",
            log_retention_days=30,
            log_rotation="00:00",
            log_max_file_size="50 MB",
            log_enable_access_log=False,
        )

        try:
            with (
                patch(
                    "app.services.system_setting_service.system_setting_repository.set_value",
                    new=AsyncMock(side_effect=fake_set_value),
                ),
                patch(
                    "app.services.system_setting_service.system_setting_repository.get_value",
                    new=AsyncMock(side_effect=fake_get_value),
                ),
                patch(
                    "app.services.system_setting_service.log_manager.setup_logger",
                ) as setup_logger_mock,
                patch.object(AuthControl, "initialize", new=AsyncMock()) as auth_initialize_mock,
            ):
                data = await system_setting_service.update_logging_settings(payload)

            self.assertEqual(saved_payload["logs_root"], "runtime/logs")
            self.assertEqual(saved_payload["log_retention_days"], 30)
            self.assertEqual(settings.LOGS_ROOT, "runtime/logs")
            self.assertEqual(settings.LOG_RETENTION_DAYS, 30)
            self.assertEqual(settings.LOG_ROTATION, "00:00")
            self.assertEqual(settings.LOG_MAX_FILE_SIZE, "50 MB")
            self.assertFalse(settings.LOG_ENABLE_ACCESS_LOG)
            setup_logger_mock.assert_called_once_with(force=True)
            auth_initialize_mock.assert_awaited_once()
            self.assertTrue(data["access_log_requires_restart"])
        finally:
            for key, value in original_values.items():
                setattr(settings, key, value)

    async def test_update_security_settings_normalizes_whitelist_and_applies_runtime_payload(self) -> None:
        saved_payload: dict = {}
        original_values = {
            "PASSWORD_MIN_LENGTH": settings.PASSWORD_MIN_LENGTH,
            "PASSWORD_REQUIRE_UPPERCASE": settings.PASSWORD_REQUIRE_UPPERCASE,
            "PASSWORD_REQUIRE_LOWERCASE": settings.PASSWORD_REQUIRE_LOWERCASE,
            "PASSWORD_REQUIRE_DIGITS": settings.PASSWORD_REQUIRE_DIGITS,
            "PASSWORD_REQUIRE_SPECIAL": settings.PASSWORD_REQUIRE_SPECIAL,
            "RATE_LIMIT_ENABLED": settings.RATE_LIMIT_ENABLED,
            "RATE_LIMIT_MAX_REQUESTS": settings.RATE_LIMIT_MAX_REQUESTS,
            "RATE_LIMIT_WINDOW_SECONDS": settings.RATE_LIMIT_WINDOW_SECONDS,
            "IP_WHITELIST": settings.IP_WHITELIST,
        }

        async def fake_set_value(*, key: str, value: dict, description: str | None = None):
            saved_payload.clear()
            saved_payload.update(value)
            return None

        async def fake_get_value(key: str, default=None):
            return saved_payload or default

        payload = SecuritySettingsUpdate(
            password_min_length=10,
            password_require_uppercase=True,
            password_require_lowercase=True,
            password_require_digits=True,
            password_require_special=False,
            rate_limit_enabled=True,
            rate_limit_max_requests=120,
            rate_limit_window_seconds=90,
            ip_whitelist="127.0.0.1\n192.168.1.10,127.0.0.1",
        )

        try:
            with (
                patch(
                    "app.services.system_setting_service.system_setting_repository.set_value",
                    new=AsyncMock(side_effect=fake_set_value),
                ),
                patch(
                    "app.services.system_setting_service.system_setting_repository.get_value",
                    new=AsyncMock(side_effect=fake_get_value),
                ),
                patch.object(AuthControl, "initialize", new=AsyncMock()) as auth_initialize_mock,
            ):
                data = await system_setting_service.update_security_settings(payload)

            self.assertEqual(saved_payload["ip_whitelist"], "127.0.0.1,192.168.1.10")
            self.assertEqual(settings.PASSWORD_MIN_LENGTH, 10)
            self.assertEqual(settings.RATE_LIMIT_MAX_REQUESTS, 120)
            self.assertEqual(settings.RATE_LIMIT_WINDOW_SECONDS, 90)
            self.assertEqual(settings.IP_WHITELIST, "127.0.0.1,192.168.1.10")
            auth_initialize_mock.assert_awaited_once()
            self.assertEqual(data["ip_whitelist_items"], ["127.0.0.1", "192.168.1.10"])
        finally:
            for key, value in original_values.items():
                setattr(settings, key, value)

    def test_storage_settings_require_credentials_in_oss_mode(self) -> None:
        with self.assertRaises(PydanticValidationError):
            StorageSettingsUpdate(provider=StorageProvider.OSS)


class UploadControllerStorageModeTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_upload_to_oss_uses_local_storage_when_provider_is_local(self) -> None:
        storage_settings = {
            "provider": StorageProvider.LOCAL.value,
            "local_upload_dir": "uploads",
            "local_url_prefix": "/static/uploads",
            "local_full_url": "",
        }

        with (
            patch.object(upload_controller, "get_storage_settings", new=AsyncMock(return_value=storage_settings)),
            patch.object(
                upload_controller,
                "upload_to_local",
                new=AsyncMock(return_value="/static/uploads/image/test.png"),
            ) as mock_upload_to_local,
        ):
            result = await upload_controller.upload_to_oss(b"binary-content", "test.png", "image")

        self.assertEqual(result, "/static/uploads/image/test.png")
        mock_upload_to_local.assert_awaited_once()

    async def test_upload_to_oss_rejects_incomplete_object_storage_config(self) -> None:
        storage_settings = {
            "provider": StorageProvider.OSS.value,
            "oss_access_key_id": "",
            "oss_access_key_secret": "",
            "oss_bucket_name": "",
            "oss_endpoint": "",
            "oss_bucket_domain": "",
            "oss_upload_dir": "uploads",
            "local_upload_dir": "uploads",
            "local_url_prefix": "/static/uploads",
            "local_full_url": "",
        }

        with (
            patch("app.controllers.upload.OSS_AVAILABLE", True),
            patch.object(upload_controller, "get_storage_settings", new=AsyncMock(return_value=storage_settings)),
        ):
            with self.assertRaisesRegex(HTTPException, "对象存储配置不完整"):
                await upload_controller.upload_to_oss(b"binary-content", "test.png", "image")


class ApiCatalogFilterTestCase(unittest.TestCase):
    def test_skip_api_catalog_routes_are_excluded_from_api_metadata(self) -> None:
        router = APIRouter()

        async def dummy_dependency():
            return None

        @router.get("/visible", dependencies=[Depends(dummy_dependency)], summary="可见接口")
        async def visible_route():
            return None

        @router.get(
            "/hidden",
            dependencies=[Depends(dummy_dependency)],
            summary="隐藏接口",
            openapi_extra={"skip_api_catalog": True},
        )
        async def hidden_route():
            return None

        definitions = ApiRepository.build_route_definitions(router.routes, path_prefix="/api")
        paths = [item.path for item in definitions]

        self.assertIn("/api/visible", paths)
        self.assertNotIn("/api/hidden", paths)

    def test_routes_without_summary_are_rejected(self) -> None:
        router = APIRouter()

        async def dummy_dependency():
            return None

        @router.get("/missing-summary", dependencies=[Depends(dummy_dependency)])
        async def missing_summary_route():
            return None

        with self.assertRaisesRegex(ValueError, "must declare summary"):
            ApiRepository.build_route_definitions(router.routes)

    def test_create_app_rejects_routes_without_summary(self) -> None:
        original_register_routers = app_module.register_routers

        def fake_register_routers(app: FastAPI, prefix: str = "/api") -> None:
            original_register_routers(app, prefix=prefix)

            @app.get("/missing-summary")
            async def missing_summary_route():
                return None

        with patch("app.application.register_routers", side_effect=fake_register_routers):
            with self.assertRaisesRegex(ValueError, "must declare summary"):
                app_module.create_app()


if __name__ == "__main__":
    unittest.main()
