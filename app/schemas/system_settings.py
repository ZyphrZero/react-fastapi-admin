from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator

from app.settings import settings


class StorageProvider(str, Enum):
    LOCAL = "local"
    OSS = "oss"


class NotificationPosition(str, Enum):
    TOP_LEFT = "top-left"
    TOP_CENTER = "top-center"
    TOP_RIGHT = "top-right"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM_CENTER = "bottom-center"
    BOTTOM_RIGHT = "bottom-right"


class LoginPageImageMode(str, Enum):
    COVER = "cover"
    CONTAIN = "contain"
    FILL = "fill"
    REPEAT = "repeat"


class StorageSettingsUpdate(BaseModel):
    provider: StorageProvider = Field(default=StorageProvider.LOCAL, description="存储模式")
    local_upload_dir: str = Field(default="uploads", description="本地上传目录")
    local_full_url: str = Field(default="", description="本地完整访问地址")
    oss_access_key_id: str = Field(default="", description="OSS AccessKey ID")
    oss_access_key_secret: str = Field(default="", description="OSS AccessKey Secret")
    oss_bucket_name: str = Field(default="", description="OSS Bucket 名称")
    oss_endpoint: str = Field(default="", description="OSS Endpoint")
    oss_bucket_domain: str = Field(default="", description="OSS 自定义域名")
    oss_upload_dir: str = Field(default="uploads", description="OSS 上传目录")

    @field_validator(
        "local_upload_dir",
        "local_full_url",
        "oss_access_key_id",
        "oss_access_key_secret",
        "oss_bucket_name",
        "oss_endpoint",
        "oss_bucket_domain",
        "oss_upload_dir",
        mode="before",
    )
    @classmethod
    def normalize_text(cls, value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        return str(value).strip()

    @field_validator("local_upload_dir", "oss_upload_dir")
    @classmethod
    def normalize_upload_dir(cls, value: str) -> str:
        normalized = value.strip().strip("/")
        return normalized or "uploads"

    @model_validator(mode="after")
    def validate_oss_required_fields(self) -> "StorageSettingsUpdate":
        if self.provider != StorageProvider.OSS:
            return self

        required_fields = {
            "oss_access_key_id": "AccessKey ID",
            "oss_access_key_secret": "AccessKey Secret",
            "oss_bucket_name": "Bucket 名称",
            "oss_endpoint": "Endpoint",
        }
        missing_fields = [label for field, label in required_fields.items() if not getattr(self, field)]
        if missing_fields:
            raise ValueError(f"启用对象存储时必须填写: {', '.join(missing_fields)}")

        return self


class StorageSettingsDetail(StorageSettingsUpdate):
    local_url_prefix: str = Field(..., description="本地存储访问前缀")


class ApplicationSettingsUpdate(BaseModel):
    app_title: str = Field(default="React FastAPI Admin", description="应用标题")
    project_name: str = Field(default="React FastAPI Admin", description="项目名称")
    app_description: str = Field(default="React FastAPI Admin Description", description="应用描述")
    debug: bool = Field(default=False, description="调试模式")
    login_page_image_url: str = Field(default="", description="登录页展示图片地址")
    login_page_image_mode: LoginPageImageMode = Field(
        default=LoginPageImageMode.CONTAIN,
        description="登录页图片显示模式",
    )
    notification_position: NotificationPosition = Field(
        default=NotificationPosition.TOP_RIGHT,
        description="前端通知显示位置",
    )
    notification_duration: int = Field(default=4000, ge=1000, le=60000, description="前端通知显示时长（毫秒）")
    notification_visible_toasts: int = Field(default=3, ge=1, le=10, description="前端同时显示通知数量")

    @field_validator("app_title", "project_name", "app_description", "login_page_image_url", mode="before")
    @classmethod
    def normalize_text(cls, value: object) -> str:
        if value is None:
            return ""
        text = str(value).strip()
        return text

    @model_validator(mode="after")
    def validate_application_settings(self) -> "ApplicationSettingsUpdate":
        if not self.app_title:
            self.app_title = "React FastAPI Admin"
        if not self.project_name:
            self.project_name = self.app_title
        if not self.app_description:
            self.app_description = "React FastAPI Admin Description"
        if settings.is_production and self.debug:
            raise ValueError("生产环境必须关闭 DEBUG")
        return self


class ApplicationSettingsDetail(ApplicationSettingsUpdate):
    environment: str = Field(..., description="当前运行环境")


class SecuritySettingsUpdate(BaseModel):
    password_min_length: int = Field(default=8, ge=6, le=72, description="密码最小长度")
    password_require_uppercase: bool = Field(default=True, description="是否要求大写字母")
    password_require_lowercase: bool = Field(default=True, description="是否要求小写字母")
    password_require_digits: bool = Field(default=True, description="是否要求数字")
    password_require_special: bool = Field(default=True, description="是否要求特殊字符")
    rate_limit_enabled: bool = Field(default=True, description="是否启用请求限流")
    rate_limit_max_requests: int = Field(default=60, ge=1, le=100000, description="时间窗口内最大请求数")
    rate_limit_window_seconds: int = Field(default=60, ge=1, le=86400, description="时间窗口秒数")
    ip_whitelist: str = Field(default="", description="IP 白名单，支持逗号或换行分隔")

    @field_validator("ip_whitelist", mode="before")
    @classmethod
    def normalize_ip_whitelist(cls, value: object) -> str:
        if value is None:
            return ""

        if isinstance(value, (list, tuple, set)):
            parts = [str(item).strip() for item in value if str(item).strip()]
        else:
            text = str(value).replace("\r\n", "\n").replace(";", ",")
            parts = []
            for line in text.split("\n"):
                for item in line.split(","):
                    normalized = item.strip()
                    if normalized:
                        parts.append(normalized)

        deduplicated_parts = list(dict.fromkeys(parts))
        return ",".join(deduplicated_parts)


class SecuritySettingsDetail(SecuritySettingsUpdate):
    ip_whitelist_items: list[str] = Field(default_factory=list, description="归一化后的 IP 白名单")


class LoggingSettingsUpdate(BaseModel):
    logs_root: str = Field(default="app/logs", description="日志目录")
    log_retention_days: int = Field(default=7, ge=1, le=3650, description="日志保留天数")
    log_rotation: str = Field(default="1 day", description="日志轮转周期")
    log_max_file_size: str = Field(default="10 MB", description="单个日志文件最大大小")
    log_enable_access_log: bool = Field(default=True, description="是否启用访问日志")

    @field_validator("logs_root", "log_rotation", "log_max_file_size", mode="before")
    @classmethod
    def normalize_text(cls, value: object) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @model_validator(mode="after")
    def validate_logging_settings(self) -> "LoggingSettingsUpdate":
        if not self.logs_root:
            self.logs_root = "app/logs"
        if not self.log_rotation:
            self.log_rotation = "1 day"
        if not self.log_max_file_size:
            self.log_max_file_size = "10 MB"
        return self


class LoggingSettingsDetail(LoggingSettingsUpdate):
    access_log_requires_restart: bool = Field(default=True, description="访问日志开关变更是否需要重启")
