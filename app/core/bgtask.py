from starlette.background import BackgroundTasks

from .ctx import CTX_BG_TASKS
from app.utils.log_control import logger


class BgTasks:
    """Centralized background task manager."""

    @classmethod
    async def init_bg_tasks_obj(cls):
        """Create the background task container and store it in context."""
        bg_tasks = BackgroundTasks()
        CTX_BG_TASKS.set(bg_tasks)

    @classmethod
    async def get_bg_tasks_obj(cls):
        """Return the background task container from context."""
        return CTX_BG_TASKS.get()

    @classmethod
    async def add_task(cls, func, *args, **kwargs):
        """Register a background task."""
        bg_tasks = await cls.get_bg_tasks_obj()
        bg_tasks.add_task(func, *args, **kwargs)

    @classmethod
    async def execute_tasks(cls):
        """Execute background tasks, typically after the response has been sent."""
        bg_tasks = await cls.get_bg_tasks_obj()
        if not bg_tasks or not bg_tasks.tasks:
            return

        for task in list(bg_tasks.tasks):
            try:
                await task()
            except Exception:
                logger.exception("Background task execution failed and the exception was isolated")
