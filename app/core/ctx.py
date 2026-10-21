import contextvars

from starlette.background import BackgroundTasks

CTX_BG_TASKS: contextvars.ContextVar[BackgroundTasks | None] = contextvars.ContextVar("bg_task", default=None)
CTX_USER_ID: contextvars.ContextVar[int] = contextvars.ContextVar("user_id", default=0)
CTX_USER_NAME: contextvars.ContextVar[str] = contextvars.ContextVar("user_name", default="")
CTX_REQUEST_ID: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")
CTX_TASK_RUN_ID: contextvars.ContextVar[str] = contextvars.ContextVar("task_run_id", default="")
