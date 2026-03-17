from __future__ import annotations

from app.repositories import system_setting_repository
from app.schemas.system_settings import StorageProvider, StorageSettingsDetail, StorageSettingsUpdate


class SystemSettingService:
    STORAGE_SETTING_KEY = "storage_config"
    STORAGE_SETTING_DESCRIPTION = "存储配置"

    def build_default_storage_payload(self) -> dict:
        return {
            "provider": StorageProvider.LOCAL.value,
            "local_upload_dir": "uploads",
            "local_full_url": "",
            "oss_access_key_id": "",
            "oss_access_key_secret": "",
            "oss_bucket_name": "",
            "oss_endpoint": "",
            "oss_bucket_domain": "",
            "oss_upload_dir": "uploads",
        }

    @staticmethod
    def build_local_url_prefix(local_upload_dir: str) -> str:
        return f"/static/{local_upload_dir.strip('/')}"

    def build_storage_detail(self, payload: dict | None = None) -> StorageSettingsDetail:
        merged_payload = {**self.build_default_storage_payload(), **(payload or {})}
        normalized_payload = StorageSettingsUpdate(**merged_payload).model_dump()
        return StorageSettingsDetail(
            **normalized_payload,
            local_url_prefix=self.build_local_url_prefix(normalized_payload["local_upload_dir"]),
        )

    async def get_storage_settings(self) -> dict:
        stored_payload = await system_setting_repository.get_value(self.STORAGE_SETTING_KEY, default=None)
        return self.build_storage_detail(stored_payload).model_dump()

    async def get_runtime_storage_settings(self) -> dict:
        stored_payload = await system_setting_repository.get_value(self.STORAGE_SETTING_KEY, default=None)
        return self.build_storage_detail(stored_payload).model_dump()

    async def update_storage_settings(self, payload: StorageSettingsUpdate) -> dict:
        normalized_payload = payload.model_dump()
        await system_setting_repository.set_value(
            key=self.STORAGE_SETTING_KEY,
            value=normalized_payload,
            description=self.STORAGE_SETTING_DESCRIPTION,
        )
        return await self.get_storage_settings()


system_setting_service = SystemSettingService()
