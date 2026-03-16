from __future__ import annotations

import asyncio
from datetime import datetime, time, timedelta

from app.models.admin import Api, AuditLog, Dept, Role, User
from app.settings import settings


async def get_platform_overview() -> dict:
    today_start = datetime.combine(datetime.now().date(), time.min)
    today_end = today_start + timedelta(days=1)

    (
        user_total,
        active_user_total,
        role_total,
        dept_total,
        api_total,
        today_audit_total,
        recent_logs,
        audit_statistics,
    ) = await asyncio.gather(
        User.all().count(),
        User.filter(is_active=True).count(),
        Role.all().count(),
        Dept.filter(is_deleted=False).count(),
        Api.all().count(),
        AuditLog.filter(created_at__gte=today_start, created_at__lt=today_end, is_deleted=False).count(),
        AuditLog.filter(is_deleted=False).order_by("-created_at").limit(8),
        AuditLog.get_logs_statistics(days=7),
    )

    recent_activities = []
    for log in recent_logs:
        recent_activities.append(
            {
                "id": log.id,
                "username": log.username or "system",
                "module": log.module or "基础模块",
                "action": log.summary or log.operation_type or f"{log.method} {log.path}",
                "path": log.path,
                "method": log.method,
                "status": log.status,
                "log_level": log.log_level,
                "response_time": log.response_time,
                "created_at": log.created_at.strftime(settings.DATETIME_FORMAT) if log.created_at else None,
            }
        )

    audit_trend = [{"date": date, "count": count} for date, count in audit_statistics.items()]

    return {
        "summary": {
            "user_total": user_total,
            "active_user_total": active_user_total,
            "role_total": role_total,
            "dept_total": dept_total,
            "api_total": api_total,
            "today_audit_total": today_audit_total,
        },
        "system": {
            "app_title": settings.APP_TITLE,
            "version": settings.VERSION,
            "environment": settings.APP_ENV,
            "database": settings.DB_CONNECTION,
            "access_log_enabled": settings.LOG_ENABLE_ACCESS_LOG,
            "auto_bootstrap": settings.AUTO_BOOTSTRAP,
            "run_migrations_on_startup": settings.should_run_migrations_on_startup,
            "seed_base_data_on_startup": settings.should_seed_base_data_on_startup,
            "refresh_api_metadata_on_startup": settings.should_refresh_api_metadata_on_startup,
        },
        "audit_trend": audit_trend,
        "recent_activities": recent_activities,
    }
