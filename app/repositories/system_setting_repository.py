from __future__ import annotations

from pydantic import BaseModel

from app.models.system_setting import SystemSetting
from app.repositories.base import BaseRepository


class SystemSettingRepository(BaseRepository[SystemSetting, BaseModel, BaseModel]):
    def __init__(self) -> None:
        super().__init__(model=SystemSetting)

    async def get_by_key(self, key: str) -> SystemSetting | None:
        return await self.model.get_or_none(key=key)

    async def get_value(self, key: str, default: dict | None = None) -> dict | None:
        setting = await self.get_by_key(key)
        if setting is None:
            return default
        return setting.value

    async def set_value(self, *, key: str, value: dict, description: str | None = None) -> SystemSetting:
        setting = await self.get_by_key(key)
        if setting is None:
            setting = await self.model.create(key=key, value=value, description=description)
            return setting

        setting.value = value
        if description is not None:
            setting.description = description
        await setting.save(update_fields=["value", "description", "updated_at"])
        return setting


system_setting_repository = SystemSettingRepository()
