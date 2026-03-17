import unittest
from unittest.mock import AsyncMock, patch

from fastapi import APIRouter, Depends
from fastapi import HTTPException
from pydantic import ValidationError as PydanticValidationError

from app.controllers.upload import upload_controller
from app.repositories.api_repository import ApiRepository
from app.schemas.system_settings import StorageProvider, StorageSettingsUpdate
from app.services.system_setting_service import system_setting_service


class SystemSettingServiceTestCase(unittest.IsolatedAsyncioTestCase):
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

        @router.get("/visible", dependencies=[Depends(dummy_dependency)])
        async def visible_route():
            return None

        @router.get(
            "/hidden",
            dependencies=[Depends(dummy_dependency)],
            openapi_extra={"skip_api_catalog": True},
        )
        async def hidden_route():
            return None

        definitions = ApiRepository.build_route_definitions(router.routes)
        paths = [item.path for item in definitions]

        self.assertIn("/visible", paths)
        self.assertNotIn("/hidden", paths)


if __name__ == "__main__":
    unittest.main()
