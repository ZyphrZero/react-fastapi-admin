import asyncio
import atexit
from contextlib import asynccontextmanager
import mimetypes
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.celery import start_celery_beat, start_celery_worker, stop_celery_beat, stop_celery_worker
from app.core.db_runtime import DatabaseRuntime
from app.core.init_app import make_middlewares, register_exceptions, register_routers
from app.repositories.api_repository import ApiRepository
from app.services import system_setting_service
from app.settings import settings
from app.utils.log_control import init_logging, logger
from app.utils.minio_utils import StorageUnavailableError, get_storage


mimetypes.add_type("image/webp", ".webp")


class SPAStaticFiles(StaticFiles):
    """StaticFiles variant that falls back to index.html for SPA routes."""

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404:
                raise
            if "." in Path(path).name:
                raise
            return await super().get_response("index.html", scope)


def get_frontend_dist_path() -> Path:
    """Return the built frontend distribution path."""
    return settings.BASE_DIR / "web" / "dist"


def _stop_embedded_celery() -> None:
    """Stop embedded Celery worker/beat; safe to call multiple times."""
    stop_celery_worker()
    stop_celery_beat()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    init_logging()
    logger.info(f"Starting application in environment: {settings.APP_ENV}")
    app.state.db_runtime = DatabaseRuntime()

    try:
        await app.state.db_runtime.initialize()
        async with app.state.db_runtime.activate():
            await system_setting_service.initialize_runtime_settings(app=app)
            logger.info("Runtime settings initialized")
            if settings.MINIO_ENABLED:
                try:
                    await get_storage().ensure_buckets()
                    logger.info("MinIO buckets ensured")
                except StorageUnavailableError as exc:
                    # MinIO 不可达时降级启动：用时再验由各存储操作的 503 STORAGE_UNAVAILABLE
                    # 转译覆盖，避免断连期服务整体不可用
                    logger.warning(f"MinIO buckets ensure failed, starting in degraded mode: {exc}")
        # 开发环境便利开关：随进程内嵌启动 Celery worker 与 beat（生产环境应使用独立容器，保持关闭）
        if settings.CELERY_AUTOSTART:
            atexit.register(_stop_embedded_celery)
            start_celery_worker()
            start_celery_beat()
        logger.info("Application startup completed")
    except Exception as exc:
        logger.error(f"Application startup failed: {exc}")
        raise

    try:
        yield
    except asyncio.CancelledError:
        logger.warning("Application execution was cancelled; shutting down...")
    finally:
        logger.info("Shutting down application...")
        if settings.CELERY_AUTOSTART:
            _stop_embedded_celery()
        db_runtime = getattr(app.state, "db_runtime", None)
        if db_runtime is not None:
            try:
                await asyncio.shield(db_runtime.close())
            except Exception:
                pass


def create_app() -> FastAPI:
    frontend_dist_path = get_frontend_dist_path()
    frontend_index_path = frontend_dist_path / "index.html"

    app = FastAPI(
        title=settings.APP_TITLE,
        description=settings.APP_DESCRIPTION,
        version=settings.VERSION,
        openapi_url="/openapi.json",
        swagger_ui_parameters={"persistAuthorization": True},
        middleware=make_middlewares(),
        lifespan=lifespan,
        redirect_slashes=False,
    )
    register_exceptions(app)
    register_routers(app, prefix="/api")

    app.mount("/static", StaticFiles(directory=settings.storage_root_path, check_dir=False), name="static")

    @app.get("/health", summary="健康检查")
    async def health():
        return {
            "status": "ok",
            "app": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "environment": settings.APP_ENV,
        }

    if settings.is_production and frontend_index_path.exists():
        logger.info(f"Frontend bundle detected at: {frontend_dist_path}")
        app.mount("/", SPAStaticFiles(directory=frontend_dist_path, html=True), name="frontend")
    else:
        logger.info(
            f"Frontend bundle unavailable for runtime mode; root will redirect to /docs "
            f"(env={settings.APP_ENV}, path={frontend_dist_path})"
        )

        @app.get("/", summary="根路径重定向")
        async def root():
            return RedirectResponse(url="/docs")

    ApiRepository.validate_route_summaries(app.routes)
    return app
