from __future__ import annotations

from fastapi import FastAPI

from app.core.dependency import AuthControl
from app.repositories import system_setting_repository
from app.schemas.system_settings import (
    ApplicationSettingsDetail,
    ApplicationSettingsUpdate,
    LoggingSettingsDetail,
    LoggingSettingsUpdate,
    SecuritySettingsDetail,
    SecuritySettingsUpdate,
    StorageProvider,
    StorageSettingsDetail,
    StorageSettingsUpdate,
)
from app.settings import settings
from app.utils.log_control import log_manager


class SystemSettingService:
    APPLICATION_SETTING_KEY = "application_config"
    APPLICATION_SETTING_DESCRIPTION = "应用配置"
    LOGGING_SETTING_KEY = "logging_config"
    LOGGING_SETTING_DESCRIPTION = "日志配置"
    SECURITY_SETTING_KEY = "security_config"
    SECURITY_SETTING_DESCRIPTION = "安全配置"
    STORAGE_SETTING_KEY = "storage_config"
    STORAGE_SETTING_DESCRIPTION = "存储配置"

    def build_default_application_payload(self) -> dict:
        return {
            "app_title": settings.APP_TITLE,
            "project_name": settings.PROJECT_NAME,
            "app_description": settings.APP_DESCRIPTION,
            "debug": settings.DEBUG,
            "login_page_image_url": settings.LOGIN_PAGE_IMAGE_URL,
            "login_page_image_mode": settings.LOGIN_PAGE_IMAGE_MODE,
            "login_page_image_zoom": settings.LOGIN_PAGE_IMAGE_ZOOM,
            "login_page_image_position_x": settings.LOGIN_PAGE_IMAGE_POSITION_X,
            "login_page_image_position_y": settings.LOGIN_PAGE_IMAGE_POSITION_Y,
            "notification_position": settings.NOTIFICATION_POSITION,
            "notification_duration": settings.NOTIFICATION_DURATION,
            "notification_visible_toasts": settings.NOTIFICATION_VISIBLE_TOASTS,
        }

    def build_default_logging_payload(self) -> dict:
        return {
            "logs_root": settings.LOGS_ROOT,
            "log_retention_days": settings.LOG_RETENTION_DAYS,
            "log_rotation": settings.LOG_ROTATION,
            "log_max_file_size": settings.LOG_MAX_FILE_SIZE,
            "log_enable_access_log": settings.LOG_ENABLE_ACCESS_LOG,
        }

    def build_default_security_payload(self) -> dict:
        return {
            "password_min_length": settings.PASSWORD_MIN_LENGTH,
            "password_require_uppercase": settings.PASSWORD_REQUIRE_UPPERCASE,
            "password_require_lowercase": settings.PASSWORD_REQUIRE_LOWERCASE,
            "password_require_digits": settings.PASSWORD_REQUIRE_DIGITS,
            "password_require_special": settings.PASSWORD_REQUIRE_SPECIAL,
            "rate_limit_enabled": settings.RATE_LIMIT_ENABLED,
            "rate_limit_max_requests": settings.RATE_LIMIT_MAX_REQUESTS,
            "rate_limit_window_seconds": settings.RATE_LIMIT_WINDOW_SECONDS,
            "ip_whitelist": settings.IP_WHITELIST,
        }

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

    def build_application_detail(self, payload: dict | None = None) -> ApplicationSettingsDetail:
        merged_payload = {**self.build_default_application_payload(), **(payload or {})}
        normalized_payload = ApplicationSettingsUpdate(**merged_payload).model_dump()
        return ApplicationSettingsDetail(
            **normalized_payload,
            environment=settings.APP_ENV,
        )

    def build_logging_detail(self, payload: dict | None = None) -> LoggingSettingsDetail:
        merged_payload = {**self.build_default_logging_payload(), **(payload or {})}
        normalized_payload = LoggingSettingsUpdate(**merged_payload).model_dump()
        return LoggingSettingsDetail(
            **normalized_payload,
            access_log_requires_restart=True,
        )

    def build_security_detail(self, payload: dict | None = None) -> SecuritySettingsDetail:
        merged_payload = {**self.build_default_security_payload(), **(payload or {})}
        normalized_payload = SecuritySettingsUpdate(**merged_payload).model_dump()
        ip_whitelist = normalized_payload["ip_whitelist"]
        return SecuritySettingsDetail(
            **normalized_payload,
            ip_whitelist_items=[item.strip() for item in ip_whitelist.split(",") if item.strip()],
        )

    def apply_application_settings(self, payload: dict) -> None:
        settings.APP_TITLE = payload["app_title"]
        settings.PROJECT_NAME = payload["project_name"]
        settings.APP_DESCRIPTION = payload["app_description"]
        settings.DEBUG = payload["debug"]
        settings.LOGIN_PAGE_IMAGE_URL = payload["login_page_image_url"]
        settings.LOGIN_PAGE_IMAGE_MODE = payload["login_page_image_mode"]
        settings.LOGIN_PAGE_IMAGE_ZOOM = payload["login_page_image_zoom"]
        settings.LOGIN_PAGE_IMAGE_POSITION_X = payload["login_page_image_position_x"]
        settings.LOGIN_PAGE_IMAGE_POSITION_Y = payload["login_page_image_position_y"]
        settings.NOTIFICATION_POSITION = payload["notification_position"]
        settings.NOTIFICATION_DURATION = payload["notification_duration"]
        settings.NOTIFICATION_VISIBLE_TOASTS = payload["notification_visible_toasts"]

    def apply_logging_settings(self, payload: dict) -> None:
        settings.LOGS_ROOT = payload["logs_root"]
        settings.LOG_RETENTION_DAYS = payload["log_retention_days"]
        settings.LOG_ROTATION = payload["log_rotation"]
        settings.LOG_MAX_FILE_SIZE = payload["log_max_file_size"]
        settings.LOG_ENABLE_ACCESS_LOG = payload["log_enable_access_log"]

    def apply_security_settings(self, payload: dict) -> None:
        settings.PASSWORD_MIN_LENGTH = payload["password_min_length"]
        settings.PASSWORD_REQUIRE_UPPERCASE = payload["password_require_uppercase"]
        settings.PASSWORD_REQUIRE_LOWERCASE = payload["password_require_lowercase"]
        settings.PASSWORD_REQUIRE_DIGITS = payload["password_require_digits"]
        settings.PASSWORD_REQUIRE_SPECIAL = payload["password_require_special"]
        settings.RATE_LIMIT_ENABLED = payload["rate_limit_enabled"]
        settings.RATE_LIMIT_MAX_REQUESTS = payload["rate_limit_max_requests"]
        settings.RATE_LIMIT_WINDOW_SECONDS = payload["rate_limit_window_seconds"]
        settings.IP_WHITELIST = payload["ip_whitelist"]

    @staticmethod
    def apply_app_metadata(app: FastAPI | None = None) -> None:
        if app is None:
            return

        app.title = settings.APP_TITLE
        app.description = settings.APP_DESCRIPTION
        app.openapi_schema = None

    async def refresh_runtime_state(self, *, app: FastAPI | None = None, reconfigure_logging: bool = False) -> None:
        if reconfigure_logging:
            log_manager.setup_logger(force=True)
        self.apply_app_metadata(app)
        await AuthControl.initialize()

    async def initialize_runtime_settings(self, *, app: FastAPI | None = None) -> None:
        application_payload = await system_setting_repository.get_value(self.APPLICATION_SETTING_KEY, default=None)
        logging_payload = await system_setting_repository.get_value(self.LOGGING_SETTING_KEY, default=None)
        security_payload = await system_setting_repository.get_value(self.SECURITY_SETTING_KEY, default=None)

        if application_payload:
            normalized_application_payload = self.build_application_detail(application_payload).model_dump(
                exclude={"environment"}
            )
            self.apply_application_settings(normalized_application_payload)

        if logging_payload:
            normalized_logging_payload = self.build_logging_detail(logging_payload).model_dump(
                exclude={"access_log_requires_restart"}
            )
            self.apply_logging_settings(normalized_logging_payload)

        if security_payload:
            normalized_security_payload = self.build_security_detail(security_payload).model_dump(
                exclude={"ip_whitelist_items"}
            )
            self.apply_security_settings(normalized_security_payload)

        await self.refresh_runtime_state(app=app, reconfigure_logging=bool(application_payload or logging_payload))

    async def get_application_settings(self) -> dict:
        stored_payload = await system_setting_repository.get_value(self.APPLICATION_SETTING_KEY, default=None)
        return self.build_application_detail(stored_payload).model_dump()

    async def update_application_settings(self, payload: ApplicationSettingsUpdate, *, app: FastAPI | None = None) -> dict:
        normalized_payload = payload.model_dump()
        await system_setting_repository.set_value(
            key=self.APPLICATION_SETTING_KEY,
            value=normalized_payload,
            description=self.APPLICATION_SETTING_DESCRIPTION,
        )
        self.apply_application_settings(normalized_payload)
        await self.refresh_runtime_state(app=app, reconfigure_logging=True)
        return await self.get_application_settings()

    async def get_logging_settings(self) -> dict:
        stored_payload = await system_setting_repository.get_value(self.LOGGING_SETTING_KEY, default=None)
        return self.build_logging_detail(stored_payload).model_dump()

    async def update_logging_settings(self, payload: LoggingSettingsUpdate, *, app: FastAPI | None = None) -> dict:
        normalized_payload = payload.model_dump()
        await system_setting_repository.set_value(
            key=self.LOGGING_SETTING_KEY,
            value=normalized_payload,
            description=self.LOGGING_SETTING_DESCRIPTION,
        )
        self.apply_logging_settings(normalized_payload)
        await self.refresh_runtime_state(app=app, reconfigure_logging=True)
        return await self.get_logging_settings()

    async def get_security_settings(self) -> dict:
        stored_payload = await system_setting_repository.get_value(self.SECURITY_SETTING_KEY, default=None)
        return self.build_security_detail(stored_payload).model_dump()

    async def update_security_settings(self, payload: SecuritySettingsUpdate, *, app: FastAPI | None = None) -> dict:
        normalized_payload = payload.model_dump()
        await system_setting_repository.set_value(
            key=self.SECURITY_SETTING_KEY,
            value=normalized_payload,
            description=self.SECURITY_SETTING_DESCRIPTION,
        )
        self.apply_security_settings(normalized_payload)
        await self.refresh_runtime_state(app=app)
        return await self.get_security_settings()

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
