from __future__ import annotations

from typing import Any, Generic, NewType, TypeVar

from pydantic import BaseModel
from tortoise.expressions import Q
from tortoise.models import Model

from app.core.exceptions import InvalidParameterError, RecordNotFoundError

Total = NewType("Total", int)
ModelType = TypeVar("ModelType", bound=Model)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: type[ModelType]):
        self.model = model

    async def get(self, record_id: int) -> ModelType | None:
        return await self.model.get_or_none(id=record_id)

    async def get_or_raise(self, record_id: int, detail: str | None = None) -> ModelType:
        obj = await self.get(record_id)
        if obj is None:
            raise RecordNotFoundError(detail or f"{self.model.__name__}不存在")
        return obj

    async def list(
        self,
        *,
        page: int,
        page_size: int,
        search: Q = Q(),
        order: list[str] | None = None,
        prefetch_related: list[str] | None = None,
        select_related: list[str] | None = None,
    ) -> tuple[Total, list[ModelType]]:
        if page < 1:
            raise InvalidParameterError("页码必须大于0")
        if page_size < 1:
            raise InvalidParameterError("页面大小必须大于0")
        if page_size > 1000:
            raise InvalidParameterError("页面大小不能超过1000")

        order = order or []
        prefetch_related = prefetch_related or []
        select_related = select_related or []

        query = self.model.filter(search)
        total = await query.count()
        items_query = query.offset((page - 1) * page_size).limit(page_size).order_by(*order)

        if select_related:
            items_query = items_query.select_related(*select_related)

        if prefetch_related:
            items = await items_query.prefetch_related(*prefetch_related)
        else:
            items = await items_query

        return Total(total), items

    async def create(self, obj_in: CreateSchemaType | dict[str, Any]) -> ModelType:
        payload = obj_in if isinstance(obj_in, dict) else obj_in.model_dump()
        obj = self.model(**payload)
        await obj.save()
        return obj

    async def update(self, record_id: int, obj_in: UpdateSchemaType | dict[str, Any]) -> ModelType:
        obj = await self.get_or_raise(record_id)
        payload = obj_in if isinstance(obj_in, dict) else obj_in.model_dump(exclude_unset=True, exclude={"id"})
        obj.update_from_dict(payload)
        await obj.save()
        return obj

    async def remove(self, record_id: int) -> ModelType:
        obj = await self.get_or_raise(record_id)
        await obj.delete()
        return obj
