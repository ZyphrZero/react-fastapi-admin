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
    Base model class with shared fields and serialization helpers.
    """

    id = fields.IntField(primary_key=True, description="ID")

    def _format_field_value(self, value: Any) -> Any:
        """
        Format a field value and normalize special types.

        Args:
            value: Raw field value.

        Returns:
            Any: Formatted value.
        """
        if isinstance(value, datetime):
            return value.strftime(settings.DATETIME_FORMAT)
        elif isinstance(value, decimal.Decimal):
            return str(value)
        else:
            return value

    async def to_dict(self, m2m: bool = False, exclude_fields: list[str] | None = None) -> Dict[str, Any]:
        """
        Convert a model instance to a dictionary.

        Args:
            m2m: Whether to include many-to-many fields.
            exclude_fields: Fields to exclude.

        Returns:
            Dict[str, Any]: Model data as a dictionary.
        """
        if exclude_fields is None:
            exclude_fields = []

        data = {}

        # Serialize regular database fields.
        for field in self._meta.db_fields:
            if field not in exclude_fields:
                value = getattr(self, field)
                data[field] = self._format_field_value(value)

        # Serialize many-to-many fields when requested.
        if m2m:
            # Resolve the M2M fields that should be included.
            m2m_fields = [field for field in self._meta.m2m_fields if field not in exclude_fields]
            if m2m_fields:
                # Fetch all M2M values concurrently.
                tasks = [self.__fetch_m2m_field(field) for field in m2m_fields]
                results = await asyncio.gather(*tasks)

                # Merge the results into the response payload.
                for field, values in results:
                    data[field] = values

        return data

    async def __fetch_m2m_field(self, field: str) -> tuple[str, list[Dict[str, Any]]]:
        """
        Fetch a many-to-many field asynchronously without applying extra filtering.

        Args:
            field: M2M field name.

        Returns:
            tuple: (field name, formatted value list)
        """
        # Fetch dictionary data for all related objects directly.
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
        Convert a model instance to a JSON string.

        Args:
            m2m: Whether to include many-to-many fields.
            exclude_fields: Fields to exclude.
            **kwargs: Extra `json.dumps` arguments.

        Returns:
            str: JSON string.
        """
        data = await self.to_dict(m2m=m2m, exclude_fields=exclude_fields)
        return json.dumps(data, ensure_ascii=False, default=str, **kwargs)

    @classmethod
    def get_pydantic_model(
        cls, exclude_fields: list[str] | None = None, include_relations: bool = True
    ) -> Type[PydanticBaseModel]:
        """
        Return the Pydantic model class for this model.

        Args:
            exclude_fields: Fields to exclude.
            include_relations: Whether to include relation fields.

        Returns:
            Type[PydanticBaseModel]: Pydantic model class.
        """
        if exclude_fields is None:
            exclude_fields = []

        # Build the Pydantic model with tortoise's `pydantic_model_creator`.
        pydantic_model = pydantic_model_creator(
            cls,
            exclude=tuple(exclude_fields) if exclude_fields else None,
            include=None if include_relations else (),
            name=f"{cls.__name__}Schema",
        )

        return pydantic_model

    async def get_pydantic_schema(self, m2m: bool = False, exclude_fields: list[str] | None = None) -> Dict[str, Any]:
        """
        Return a Pydantic-compatible data structure.

        Args:
            m2m: Whether to include many-to-many fields.
            exclude_fields: Fields to exclude.

        Returns:
            Dict[str, Any]: Pydantic-compatible dictionary.
        """
        return await self.to_dict(m2m=m2m, exclude_fields=exclude_fields)

    def __str__(self) -> str:
        """Return the string representation."""
        return f"<{self.__class__.__name__}(id={getattr(self, 'id', 'None')})>"

    def __repr__(self) -> str:
        """Return the developer-friendly string representation."""
        return self.__str__()

    class Meta:
        abstract = True


class TimestampMixin:
    """Mixin that adds timestamp fields to an existing model."""

    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")


class UUIDModel:
    """Mixin that adds UUID field support."""

    uuid = fields.CharField(max_length=36, unique=True, db_index=True, description="UUID标识")


class SoftDeleteMixin:
    """Mixin that adds soft-delete support."""

    is_deleted = fields.BooleanField(default=False, description="是否已删除")
    deleted_at = fields.DatetimeField(null=True, description="删除时间")

    def soft_delete(self):
        """Mark the record as soft-deleted."""
        self.is_deleted = True
        self.deleted_at = datetime.now()
