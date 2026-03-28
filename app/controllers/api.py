from app.api.catalog import build_api_catalog_route_definitions
from app.core.crud import CRUDBase
from app.utils.log_control import logger
from app.models.admin import Api
from app.repositories import api_repository
from app.schemas.apis import ApiCreate, ApiUpdate


class ApiController(CRUDBase[Api, ApiCreate, ApiUpdate]):
    def __init__(self):
        super().__init__(model=Api)

    async def refresh_api(self):
        """Refresh the API catalog by scanning application routes and syncing them to the database."""
        route_definitions = build_api_catalog_route_definitions()
        await api_repository.sync_routes(route_definitions)
        logger.info("API metadata refreshed")

    async def get_all_tags(self):
        """Return all API tags."""
        try:
            # Collect all unique tags.
            apis = await Api.all()
            tags = set()
            for api in apis:
                if api.tags:
                    tags.add(api.tags)
            return sorted(list(tags))
        except Exception as e:
            logger.error(f"Failed to fetch API tags: {str(e)}")
            return []

    async def _delete_api_permission(self, api_obj):
        """Delete the permission record for an API. Kept as a no-op for compatibility after permission simplification."""
        # The permission system has been removed. This method remains as a compatibility no-op.
        logger.debug(f"API deleted: {api_obj.method} {api_obj.path} (permission system simplified)")


api_controller = ApiController()
