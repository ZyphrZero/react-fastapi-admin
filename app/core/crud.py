from typing import Any, Dict, Generic, List, NewType, Optional, Tuple, Type, TypeVar, Union

from pydantic import BaseModel
from tortoise.expressions import Q
from tortoise.models import Model

from app.core.exceptions import RecordNotFoundError, InvalidParameterError

Total = NewType("Total", int)
ModelType = TypeVar("ModelType", bound=Model)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get(self, id: int) -> Optional[ModelType]:
        """Return a record by ID, or `None` if it does not exist."""
        return await self.model.get_or_none(id=id)

    async def get_or_raise(self, id: int) -> ModelType:
        """Return a record by ID or raise when it does not exist."""
        obj = await self.model.get_or_none(id=id)
        if obj is None:
            raise RecordNotFoundError(detail=f"{self.model.__name__} with id {id} not found")
        return obj

    async def list(
        self,
        page: int,
        page_size: int,
        search: Q = Q(),
        order: list | None = None,
        prefetch_related: list[str] | None = None,
        select_related: list[str] | None = None,
    ) -> Tuple[Total, List[ModelType]]:
        """
        Return a paginated list with parameter validation and relation-query optimization.

        Args:
            page: Page number, starting at 1.
            page_size: Page size, up to 1000.
            search: Search condition.
            order: Ordering fields.
            prefetch_related: Prefetch many-to-many and reverse-foreign-key relations to avoid N+1 issues.
            select_related: Preload foreign-key relations via JOIN queries.
        """
        # Validate pagination parameters.
        if page < 1:
            raise InvalidParameterError(detail="页码必须大于0")
        if page_size < 1:
            raise InvalidParameterError(detail="页面大小必须大于0")
        if page_size > 1000:
            raise InvalidParameterError(detail="页面大小不能超过1000")

        if order is None:
            order = []
        if prefetch_related is None:
            prefetch_related = []
        if select_related is None:
            select_related = []

        # Build the base query.
        query = self.model.filter(search)

        # Count the total number of records without relation optimizations.
        total = await query.count()

        # Fetch paginated records and apply relation-query optimizations.
        items_query = query.offset((page - 1) * page_size).limit(page_size).order_by(*order)

        # Apply `select_related` for foreign keys via JOIN queries.
        if select_related:
            items_query = items_query.select_related(*select_related)

        # Apply `prefetch_related` for many-to-many and reverse-foreign-key relations.
        if prefetch_related:
            items = await items_query.prefetch_related(*prefetch_related)
        else:
            items = await items_query

        return Total(total), items

    async def create(self, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record."""
        if isinstance(obj_in, Dict):
            obj_dict = obj_in
        else:
            obj_dict = obj_in.model_dump()
        obj = self.model(**obj_dict)
        await obj.save()
        return obj

    async def update(self, id: int, obj_in: Union[UpdateSchemaType, Dict[str, Any]]) -> ModelType:
        """Update a record and raise when it does not exist."""
        obj = await self.get_or_raise(id=id)

        if isinstance(obj_in, Dict):
            obj_dict = obj_in
        else:
            obj_dict = obj_in.model_dump(exclude_unset=True, exclude={"id"})

        obj = obj.update_from_dict(obj_dict)
        await obj.save()
        return obj

    async def remove(self, id: int) -> ModelType:
        """Delete a record, raise when it does not exist, and return the deleted object."""
        obj = await self.get_or_raise(id=id)
        deleted_obj = obj  # Keep a reference for the return value.
        await obj.delete()
        return deleted_obj
