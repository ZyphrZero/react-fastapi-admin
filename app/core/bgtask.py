from starlette.background import BackgroundTasks

from .ctx import CTX_BG_TASKS
from app.utils.log_control import logger


class BgTasks:
    """后台任务统一管理"""

    @classmethod
    async def init_bg_tasks_obj(cls):
        """实例化后台任务，并设置到上下文"""
        bg_tasks = BackgroundTasks()
        CTX_BG_TASKS.set(bg_tasks)

    @classmethod
    async def get_bg_tasks_obj(cls):
        """从上下文中获取后台任务实例"""
        return CTX_BG_TASKS.get()

    @classmethod
    async def add_task(cls, func, *args, **kwargs):
        """添加后台任务"""
        bg_tasks = await cls.get_bg_tasks_obj()
        bg_tasks.add_task(func, *args, **kwargs)

    @classmethod
    async def execute_tasks(cls):
        """执行后台任务，一般是请求结果返回之后执行"""
        bg_tasks = await cls.get_bg_tasks_obj()
        if not bg_tasks or not bg_tasks.tasks:
            return

        for task in list(bg_tasks.tasks):
            try:
                await task()
            except Exception:
                logger.exception("后台任务执行失败，异常已被隔离")
