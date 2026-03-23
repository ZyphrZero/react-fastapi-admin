import contextvars

from starlette.background import BackgroundTasks

CTX_BG_TASKS: contextvars.ContextVar[BackgroundTasks | None] = contextvars.ContextVar("bg_task", default=None)
