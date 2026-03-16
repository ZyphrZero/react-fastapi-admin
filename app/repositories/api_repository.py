from __future__ import annotations

import asyncio
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from fastapi.routing import APIRoute
from tortoise.expressions import Q

from app.models.admin import Api
from app.repositories.base import BaseRepository
from app.schemas.apis import ApiCreate, ApiUpdate


@dataclass(slots=True)
class ApiRouteDefinition:
    method: str
    path: str
    summary: str
    tags: str


class ApiRepository(BaseRepository[Api, ApiCreate, ApiUpdate]):
    def __init__(self) -> None:
        super().__init__(model=Api)

    async def exists_any(self) -> bool:
        return await self.model.exists()

    async def list_apis(self, *, page: int, page_size: int, search: Q) -> tuple[int, list[dict]]:
        total, api_objects = await self.list(page=page, page_size=page_size, search=search, order=["tags", "id"])
        data = await asyncio.gather(*(api.to_dict() for api in api_objects))
        return total, list(data)

    async def list_tags(self) -> list[dict]:
        api_objects = await self.model.all().only("tags")
        tag_counter = Counter(api.tags for api in api_objects if api.tags)
        return [
            {"label": tag, "value": tag, "count": count}
            for tag, count in sorted(tag_counter.items(), key=lambda item: item[0])
        ]

    async def sync_routes(self, routes: Iterable[ApiRouteDefinition]) -> None:
        route_definitions = list(routes)
        existing_apis = await self.model.all()
        existing_map = {(api.method, api.path): api for api in existing_apis}
        current_keys = {(route.method, route.path) for route in route_definitions}

        stale_ids = [api.id for api in existing_apis if (api.method, api.path) not in current_keys]
        if stale_ids:
            await self.model.filter(id__in=stale_ids).delete()

        for route in route_definitions:
            existing = existing_map.get((route.method, route.path))
            if existing:
                existing.update_from_dict(
                    {
                        "method": route.method,
                        "path": route.path,
                        "summary": route.summary,
                        "tags": route.tags,
                    }
                )
                await existing.save()
                continue

            await self.model.create(
                method=route.method,
                path=route.path,
                summary=route.summary,
                tags=route.tags,
            )

    async def list_permission_keys(self) -> list[str]:
        api_objects = await self.model.all()
        return [f"{api.method.lower()}{api.path}" for api in api_objects]

    @staticmethod
    def build_route_definitions(routes: Iterable[object]) -> list[ApiRouteDefinition]:
        definitions: list[ApiRouteDefinition] = []
        for route in routes:
            if not isinstance(route, APIRoute) or not route.dependencies:
                continue

            methods = [method for method in route.methods if method not in {"HEAD", "OPTIONS"}]
            if not methods:
                continue

            definitions.append(
                ApiRouteDefinition(
                    method=sorted(methods)[0],
                    path=route.path_format,
                    summary=route.summary or "无描述",
                    tags=str(route.tags[0]) if route.tags else "未分类",
                )
            )

        return definitions


api_repository = ApiRepository()
