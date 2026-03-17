from tortoise import fields
from tortoise.queryset import Q

from .base import BaseModel, TimestampMixin
from .enums import MethodType


class User(BaseModel, TimestampMixin):
    username = fields.CharField(max_length=20, unique=True, description="用户名称", db_index=True)
    nickname = fields.CharField(max_length=30, null=True, description="昵称", db_index=True)
    email = fields.CharField(max_length=255, null=True, unique=True, description="邮箱", db_index=True)
    phone = fields.CharField(max_length=20, null=True, description="电话", db_index=True)
    password = fields.CharField(max_length=128, null=True, description="密码")
    is_active = fields.BooleanField(default=True, description="是否激活", db_index=True)
    is_superuser = fields.BooleanField(default=False, description="是否为超级管理员", db_index=True)
    last_login = fields.DatetimeField(null=True, description="最后登录时间", db_index=True)
    session_version = fields.IntField(default=0, description="会话版本", db_index=True)
    roles = fields.ManyToManyField("models.Role", related_name="user_roles")

    class Meta:
        table = "user"


class Role(BaseModel, TimestampMixin):
    name = fields.CharField(max_length=20, unique=True, description="角色名称", db_index=True)
    desc = fields.CharField(max_length=500, null=True, description="角色描述")
    menu_paths = fields.JSONField(default=list, description="菜单权限路径")
    api_ids = fields.JSONField(default=list, description="API权限ID列表")

    class Meta:
        table = "role"


class Api(BaseModel, TimestampMixin):
    path = fields.CharField(max_length=100, description="API路径", db_index=True)
    method = fields.CharEnumField(MethodType, description="请求方法", db_index=True)
    summary = fields.CharField(max_length=500, description="请求简介", db_index=True)
    tags = fields.CharField(max_length=100, description="API标签", db_index=True)

    class Meta:
        table = "api"


class AuditLog(BaseModel, TimestampMixin):
    user_id = fields.IntField(description="用户ID", db_index=True)
    username = fields.CharField(max_length=64, default="", description="用户名称", db_index=True)
    module = fields.CharField(max_length=64, default="", description="功能模块", db_index=True)
    summary = fields.CharField(max_length=128, default="", description="请求描述", db_index=True)
    method = fields.CharField(max_length=10, default="", description="请求方法", db_index=True)
    path = fields.CharField(max_length=255, default="", description="请求路径", db_index=True)
    status = fields.IntField(default=-1, description="状态码", db_index=True)
    response_time = fields.IntField(default=0, description="响应时间(单位ms)", db_index=True)
    request_args = fields.JSONField(null=True, description="请求参数")
    response_body = fields.JSONField(null=True, description="返回数据")
    ip_address = fields.CharField(max_length=64, default="", description="IP地址", db_index=True)
    user_agent = fields.CharField(max_length=512, default="", description="用户代理", db_index=True)
    operation_type = fields.CharField(max_length=32, default="", description="操作类型", db_index=True)
    log_level = fields.CharField(max_length=16, default="info", description="日志级别", db_index=True)
    is_deleted = fields.BooleanField(default=False, description="是否已删除", db_index=True)

    class Meta:
        table = "audit_log"
        indexes = [
            # 创建复合索引以提高查询性能
            ("created_at", "username"),
            ("created_at", "module"),
            ("created_at", "status"),
            ("created_at", "operation_type"),
            ("created_at", "log_level"),
        ]

    async def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.username,
            "module": self.module,
            "summary": self.summary,
            "method": self.method,
            "path": self.path,
            "status": self.status,
            "response_time": self.response_time,
            "request_args": self.request_args,
            "response_body": self.response_body,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "operation_type": self.operation_type,
            "log_level": self.log_level,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
        }

    @classmethod
    async def get_logs_by_date_range(cls, start_date, end_date, **filters):
        """根据日期范围和过滤条件获取日志"""
        q = Q(created_at__range=[start_date, end_date])
        for key, value in filters.items():
            if value:
                if isinstance(value, str) and key not in ["status", "user_id", "response_time"]:
                    q &= Q(**{f"{key}__icontains": value})
                else:
                    q &= Q(**{key: value})
        return await cls.filter(q & Q(is_deleted=False)).order_by("-created_at")

    @classmethod
    async def get_logs_statistics(cls, days=7):
        """获取最近n天的日志统计信息"""
        import datetime

        today = datetime.date.today()
        start_date = today - datetime.timedelta(days=days - 1)

        result = {}
        for i in range(days):
            current_date = start_date + datetime.timedelta(days=i)
            next_date = current_date + datetime.timedelta(days=1)
            count = await cls.filter(
                created_at__gte=current_date.strftime("%Y-%m-%d"),
                created_at__lt=next_date.strftime("%Y-%m-%d"),
                is_deleted=False,
            ).count()
            result[current_date.strftime("%Y-%m-%d")] = count

        return result

    @classmethod
    async def batch_delete(cls, ids):
        """批量删除日志(软删除)"""
        return await cls.filter(id__in=ids).update(is_deleted=True)
