from fastapi.routing import APIRoute

from app.core.crud import CRUDBase
from app.utils.log_control import logger
from app.models.admin import Api
from app.repositories.api_repository import ApiRepository
from app.schemas.apis import ApiCreate, ApiUpdate


class ApiController(CRUDBase[Api, ApiCreate, ApiUpdate]):
    def __init__(self):
        super().__init__(model=Api)

    async def refresh_api(self):
        """刷新API列表 - 扫描应用程序路由并同步到数据库"""
        from app import app

        # 获取当前应用中所有需要权限控制的API路由
        current_api_list = []
        for route in app.routes:
            # 只处理有依赖项（通常是权限控制）的API路由
            if isinstance(route, APIRoute) and len(route.dependencies) > 0:
                method = ApiRepository.get_route_primary_method(route)
                path = route.path_format
                current_api_list.append((method, path))

        # 删除数据库中已不存在的API记录
        existing_apis = await Api.all()
        for api in existing_apis:
            if (api.method, api.path) not in current_api_list:
                logger.debug(f"删除已废弃的API: {api.method} {api.path}")
                await api.delete()

        # 添加或更新API记录
        for route in app.routes:
            if isinstance(route, APIRoute) and len(route.dependencies) > 0:
                method = ApiRepository.get_route_primary_method(route)
                path = route.path_format
                summary = ApiRepository.require_route_summary(route)
                tags = list(route.tags)[0] if route.tags else "未分类"

                # 检查API是否已存在
                existing_api = await Api.filter(method=method, path=path).first()
                if existing_api:
                    # 更新现有API记录
                    await existing_api.update_from_dict({
                        "method": method,
                        "path": path,
                        "summary": summary,
                        "tags": tags
                    }).save()
                else:
                    # 创建新的API记录
                    logger.debug(f"创建新API记录: {method} {path}")
                    await Api.create(
                        method=method,
                        path=path,
                        summary=summary,
                        tags=tags
                    )

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
