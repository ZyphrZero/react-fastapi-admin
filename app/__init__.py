from contextlib import asynccontextmanager
import asyncio
import mimetypes
import os

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from app.core.exceptions import SettingNotFound
from app.core.bootstrap import bootstrap_application
from app.core.db_runtime import DatabaseRuntime
from app.core.init_app import (
    make_middlewares,
    register_exceptions,
    register_routers,
)
from app.services import system_setting_service
from app.utils.log_control import logger, init_logging


# 加载环境变量
def load_environment():
    """加载.env文件中的环境变量"""
    # 不覆盖已存在的环境变量
    load_dotenv(override=False)

    # 获取当前环境
    app_env = os.getenv("APP_ENV", "development")
    logger.info(f"当前运行环境: {app_env}")


# 在导入settings之前加载环境变量
load_environment()
mimetypes.add_type("image/webp", ".webp")

try:
    from app.settings.config import settings
except ImportError:
    raise SettingNotFound


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理器，对热重载友好"""
    init_logging()
    logger.info("正在初始化应用...")
    app.state.db_runtime = DatabaseRuntime()

    try:
        await app.state.db_runtime.initialize()
        async with app.state.db_runtime.activate():
            await asyncio.shield(bootstrap_application())
            await system_setting_service.initialize_runtime_settings(app=app)
            logger.info("身份验证控制器初始化完成")
        logger.info("应用引导完成")

    except Exception as e:
        logger.error(f"应用引导出现问题: {str(e)}")
        raise

    try:
        yield
    except asyncio.CancelledError:
        logger.warning("应用运行被取消，正在执行关闭...")
    finally:
        logger.info("应用正在关闭...")
        db_runtime = getattr(app.state, "db_runtime", None)
        if db_runtime is not None:
            try:
                await asyncio.shield(db_runtime.close())
            except Exception:
                pass


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_TITLE,
        description=settings.APP_DESCRIPTION,
        version=settings.VERSION,
        openapi_url="/openapi.json",
        middleware=make_middlewares(),
        lifespan=lifespan,
        redirect_slashes=False,  # 禁用URL末尾斜杠重定向
    )
    register_exceptions(app)
    register_routers(app, prefix="/api")

    app.mount("/static", StaticFiles(directory=settings.storage_root_path, check_dir=False), name="static")

    @app.get("/")
    async def root():
        """根路径处理器，重定向到文档页。"""
        return RedirectResponse(url="/docs")

    @app.get("/health")
    async def health():
        """健康检查接口。"""
        return {
            "status": "ok",
            "app": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "environment": settings.APP_ENV,
        }

    return app


# 创建应用实例
app = create_app()
