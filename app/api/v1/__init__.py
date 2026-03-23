from fastapi import APIRouter

from app.core.dependency import RequirePermission

from .apis import apis_router
from .auditlog import auditlog_router
from .base import base_router
from .roles import roles_router
from .system_settings import system_settings_router
from .users import users_router

from .upload import upload_router

v1_router = APIRouter()

v1_router.include_router(base_router, prefix="/base")
v1_router.include_router(users_router, prefix="/user", dependencies=[RequirePermission])
v1_router.include_router(roles_router, prefix="/role", dependencies=[RequirePermission])
v1_router.include_router(apis_router, prefix="/api", dependencies=[RequirePermission])
v1_router.include_router(auditlog_router, prefix="/auditlog", dependencies=[RequirePermission])

v1_router.include_router(upload_router, prefix="/upload", dependencies=[RequirePermission])
v1_router.include_router(system_settings_router, prefix="/system_settings")
