#!/usr/bin/env python
# -*- coding: utf-8 -*-


import json
import asyncio
import decimal
from datetime import datetime
from typing import Optional, Dict, Any, Type
from tortoise import fields, models
from tortoise.contrib.pydantic import pydantic_model_creator
from pydantic import BaseModel as PydanticBaseModel
from app.settings.config import settings


class BaseModel(models.Model):
    """
    基础模型类 - 提供通用字段和序列化功能
    """

    id = fields.IntField(primary_key=True, description="ID")

    def _format_field_value(self, value: Any) -> Any:
        """
        格式化字段值，处理特殊类型转换

        Args:
            value: 原始字段值

        Returns:
            Any: 格式化后的值
        """
        if isinstance(value, datetime):
            return value.strftime(settings.DATETIME_FORMAT)
        elif isinstance(value, decimal.Decimal):
            return str(value)
        else:
            return value

    async def to_dict(self, m2m: bool = False, exclude_fields: list[str] | None = None) -> Dict[str, Any]:
        """
        将模型实例转换为字典

        Args:
            m2m: 是否包含多对多字段
            exclude_fields: 需要排除的字段列表

        Returns:
            Dict[str, Any]: 模型数据字典
        """
        if exclude_fields is None:
            exclude_fields = []

        data = {}

        # 处理数据库字段
        for field in self._meta.db_fields:
            if field not in exclude_fields:
                value = getattr(self, field)
                data[field] = self._format_field_value(value)

        # 处理多对多字段
        if m2m:
            # 获取需要处理的 M2M 字段
            m2m_fields = [field for field in self._meta.m2m_fields if field not in exclude_fields]
            if m2m_fields:
                # 并发获取所有多对多字段的值
                tasks = [self.__fetch_m2m_field(field) for field in m2m_fields]
                results = await asyncio.gather(*tasks)

                # 使用 dict.update 简化合并
                for field, values in results:
                    data[field] = values

        return data

    async def __fetch_m2m_field(self, field: str) -> tuple[str, list[Dict[str, Any]]]:
        """
        异步获取多对多字段的值（仅负责数据获取，不参与字段过滤）

        Args:
            field: M2M 字段名称

        Returns:
            tuple: (字段名, 格式化后的值列表)
        """
        # 直接获取所有相关对象的字典数据
        values = await getattr(self, field).all().values()
        formatted_values = []

        for value in values:
            formatted_value = {}
            for k, v in value.items():
                formatted_value[k] = self._format_field_value(v)
            formatted_values.append(formatted_value)

        return field, formatted_values

    async def to_json(self, m2m: bool = False, exclude_fields: list[str] | None = None, **kwargs) -> str:
        """
        将模型实例转换为 JSON 字符串

        Args:
            m2m: 是否包含多对多字段
            exclude_fields: 需要排除的字段列表
            **kwargs: json.dumps 的额外参数

        Returns:
            str: JSON 字符串
        """
        data = await self.to_dict(m2m=m2m, exclude_fields=exclude_fields)
        return json.dumps(data, ensure_ascii=False, default=str, **kwargs)

    @classmethod
    def get_pydantic_model(
        cls, exclude_fields: list[str] | None = None, include_relations: bool = True
    ) -> Type[PydanticBaseModel]:
        """
        获取模型对应的 Pydantic 模型类

        Args:
            exclude_fields: 需要排除的字段列表
            include_relations: 是否包含关联字段

        Returns:
            Type[PydanticBaseModel]: Pydantic 模型类
        """
        if exclude_fields is None:
            exclude_fields = []

        # 使用 tortoise 的 pydantic_model_creator 创建 Pydantic 模型
        pydantic_model = pydantic_model_creator(
            cls,
            exclude=tuple(exclude_fields) if exclude_fields else None,
            include=None if include_relations else (),
            name=f"{cls.__name__}Schema",
        )

        return pydantic_model

    async def get_pydantic_schema(self, m2m: bool = False, exclude_fields: list[str] | None = None) -> Dict[str, Any]:
        """
        获取 Pydantic 兼容的数据结构

        Args:
            m2m: 是否包含多对多字段
            exclude_fields: 需要排除的字段列表

        Returns:
            Dict[str, Any]: Pydantic 兼容的数据字典
        """
        return await self.to_dict(m2m=m2m, exclude_fields=exclude_fields)

    def __str__(self) -> str:
        """字符串表示"""
        return f"<{self.__class__.__name__}(id={getattr(self, 'id', 'None')})>"

    def __repr__(self) -> str:
        """开发者友好的字符串表示"""
        return self.__str__()

    class Meta:
        abstract = True


class TimestampMixin:
    """时间戳混合类 - 为已有模型添加时间戳字段"""

    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")


class UUIDModel:
    """UUID混合类 - 提供UUID字段支持"""

    uuid = fields.CharField(max_length=36, unique=True, db_index=True, description="UUID标识")


class SoftDeleteMixin:
    """软删除混合类 - 提供软删除功能"""

    is_deleted = fields.BooleanField(default=False, description="是否已删除")
    deleted_at = fields.DatetimeField(null=True, description="删除时间")

    def soft_delete(self):
        """软删除"""
        self.is_deleted = True
        self.deleted_at = datetime.now()
