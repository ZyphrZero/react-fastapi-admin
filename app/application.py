import asyncio
from contextlib import asynccontextmanager
import mimetypes

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.core.db_runtime import DatabaseRuntime
from app.core.init_app import make_middlewares, register_exceptions, register_routers
from app.repositories.api_repository import ApiRepository
from app.services import system_setting_service
from app.settings import settings
from app.utils.log_control import init_logging, logger


mimetypes.add_type("image/webp", ".webp")


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
        redirect_slashes=False,
    )
    register_exceptions(app)
    register_routers(app, prefix="/api")

    app.mount("/static", StaticFiles(directory=settings.storage_root_path, check_dir=False), name="static")

    @app.get("/", summary="根路径重定向")
    async def root():
        return RedirectResponse(url="/docs")

    @app.get("/health", summary="健康检查")
    async def health():
        return {
            "status": "ok",
            "app": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "environment": settings.APP_ENV,
        }

    ApiRepository.validate_route_summaries(app.routes)
    return app
