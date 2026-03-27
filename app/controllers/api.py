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
        """刷新API列表 - 扫描应用程序路由并同步到数据库"""
        route_definitions = build_api_catalog_route_definitions()
        await api_repository.sync_routes(route_definitions)
        logger.info("API 元数据已刷新")

    async def get_all_tags(self):
        """获取所有API标签"""
        try:
            # 查询所有不重复的标签
            apis = await Api.all()
            tags = set()
            for api in apis:
                if api.tags:
                    tags.add(api.tags)
            return sorted(list(tags))
        except Exception as e:
            logger.error(f"获取API标签失败: {str(e)}")
            return []

    async def _delete_api_permission(self, api_obj):
        """删除API对应的权限记录 - 已简化，不再需要权限管理"""
        # 权限系统已被移除，此方法保留为空以保持兼容性
        logger.debug(f"API删除: {api_obj.method} {api_obj.path} (权限系统已简化)")


api_controller = ApiController()
