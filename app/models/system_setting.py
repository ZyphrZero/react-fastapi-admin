from tortoise import fields

from .base import BaseModel, TimestampMixin


class SystemSetting(BaseModel, TimestampMixin):
    key = fields.CharField(max_length=100, unique=True, description="配置键", db_index=True)
    value = fields.JSONField(default=dict, description="配置值")
    description = fields.CharField(max_length=255, null=True, description="配置说明")

    class Meta:
        table = "system_setting"
