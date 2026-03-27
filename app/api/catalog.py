from app.repositories.api_repository import ApiRepository, ApiRouteDefinition


API_MOUNT_PREFIX = "/api"


def build_api_catalog_route_definitions() -> list[ApiRouteDefinition]:
    from app.api import api_router

    return ApiRepository.build_route_definitions(api_router.routes, path_prefix=API_MOUNT_PREFIX)
