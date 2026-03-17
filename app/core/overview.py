from __future__ import annotations

import asyncio
from collections import Counter
from datetime import datetime, time, timedelta

from app.models.admin import Api, AuditLog, Role, User
from app.settings import settings


STATUS_DISTRIBUTION_LABELS = {
    "2xx": "2xx 成功",
    "3xx": "3xx 重定向",
    "4xx": "4xx 请求异常",
    "5xx": "5xx 服务异常",
    "other": "其他状态",
}


def _calculate_share(count: int, total: int) -> int:
    if total <= 0:
        return 0
    return round((count / total) * 100)


def _resolve_status_bucket(status: int | None) -> str:
    try:
        status_code = int(status)
    except (TypeError, ValueError):
        return "other"

    if 200 <= status_code < 300:
        return "2xx"
    if 300 <= status_code < 400:
        return "3xx"
    if 400 <= status_code < 500:
        return "4xx"
    if 500 <= status_code < 600:
        return "5xx"
    return "other"


def _build_module_activity(rows: list[dict], limit: int = 5) -> list[dict]:
    total = len(rows)
    module_counter = Counter((row.get("module") or "基础模块") for row in rows)

    return [
        {
            "key": label,
            "label": label,
            "count": count,
            "share": _calculate_share(count, total),
        }
        for label, count in module_counter.most_common(limit)
    ]


def _build_status_distribution(rows: list[dict]) -> list[dict]:
    total = len(rows)
    status_counter = Counter(_resolve_status_bucket(row.get("status")) for row in rows)
    distribution: list[dict] = []

    for key in ("2xx", "3xx", "4xx", "5xx", "other"):
        count = status_counter.get(key, 0)
        if count <= 0:
            continue

        distribution.append(
            {
                "key": key,
                "label": STATUS_DISTRIBUTION_LABELS[key],
                "count": count,
                "share": _calculate_share(count, total),
            }
        )

    return distribution


async def get_platform_overview() -> dict:
    today_start = datetime.combine(datetime.now().date(), time.min)
    today_end = today_start + timedelta(days=1)
    trend_start = today_start - timedelta(days=6)

    (
        user_total,
        active_user_total,
        role_total,
        api_total,
        today_audit_total,
        recent_logs,
        audit_statistics,
        chart_rows,
    ) = await asyncio.gather(
        User.all().count(),
        User.filter(is_active=True).count(),
        Role.all().count(),
        Api.all().count(),
        AuditLog.filter(created_at__gte=today_start, created_at__lt=today_end, is_deleted=False).count(),
        AuditLog.filter(is_deleted=False).order_by("-created_at").limit(8),
        AuditLog.get_logs_statistics(days=7),
        AuditLog.filter(created_at__gte=trend_start, created_at__lt=today_end, is_deleted=False).values("module", "status"),
    )

    recent_activities = []
    for log in recent_logs:
        created_at_value = log.created_at.strftime(settings.DATETIME_FORMAT) if log.created_at else None
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
                "created_at": created_at_value,
            }
        )

    audit_trend = [{"date": date, "count": count} for date, count in audit_statistics.items()]
    module_activity = _build_module_activity(chart_rows)
    status_distribution = _build_status_distribution(chart_rows)

    return {
        "summary": {
            "user_total": user_total,
            "active_user_total": active_user_total,
            "role_total": role_total,
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
        "charts": {
            "module_activity": module_activity,
            "status_distribution": status_distribution,
        },
        "recent_activities": recent_activities,
    }
