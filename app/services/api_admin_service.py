from __future__ import annotations

from collections.abc import Iterable

from tortoise.expressions import Q

from app.repositories import api_repository
from app.schemas.apis import ApiUpdate


class ApiAdminService:
    def build_search_query(self, *, path: str | None = None, summary: str | None = None, tags: str | None = None) -> Q:
        query = Q()
        if path:
            query &= Q(path__contains=path)
        if summary:
            query &= Q(summary__contains=summary)
        if tags:
            tag_values = [item.strip() for item in tags.split(",") if item.strip()]
            tag_query = Q()
            for tag in tag_values:
                tag_query |= Q(tags__contains=tag)
            if tag_values:
                query &= tag_query
        return query

    async def list_apis(
        self,
        *,
        page: int,
        page_size: int,
        path: str | None = None,
        summary: str | None = None,
        tags: str | None = None,
    ) -> dict:
        total, data = await api_repository.list_apis(
            page=page,
            page_size=page_size,
            search=self.build_search_query(path=path, summary=summary, tags=tags),
        )
        return {"data": data, "total": total, "page": page, "page_size": page_size}

    async def get_api_detail(self, api_id: int) -> dict:
        api = await api_repository.get_or_raise(api_id, "API不存在")
        return await api.to_dict()

    async def update_api(self, api_in: ApiUpdate) -> None:
        await api_repository.get_or_raise(api_in.id, "API不存在")
        await api_repository.update(api_in.id, api_in)

    async def delete_api(self, api_id: int) -> None:
        await api_repository.get_or_raise(api_id, "API不存在")
        await api_repository.remove(api_id)

    async def refresh_api_catalog(self, routes: Iterable[object]) -> None:
        await api_repository.sync_routes(api_repository.build_route_definitions(routes))

    async def get_api_tags(self) -> list[dict]:
        return await api_repository.list_tags()


api_admin_service = ApiAdminService()
