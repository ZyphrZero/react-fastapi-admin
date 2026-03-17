from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


class StorageProvider(str, Enum):
    LOCAL = "local"
    OSS = "oss"


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
