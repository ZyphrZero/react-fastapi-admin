import base64
import csv
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Path as FastAPIPath, Query
from fastapi.responses import FileResponse
from tortoise.expressions import Q

from app.models.admin import AuditLog
from app.schemas import Success
from app.schemas.apis import *
from app.core.dependency import AuthControl

router = APIRouter()

AUDIT_LOG_LIST_FIELDS = (
    "id",
    "user_id",
    "username",
    "module",
    "summary",
    "method",
    "path",
    "status",
    "response_time",
    "ip_address",
    "operation_type",
    "log_level",
    "created_at",
)

AUDIT_LOG_DETAIL_FIELDS = AUDIT_LOG_LIST_FIELDS + (
    "request_args",
    "response_body",
    "user_agent",
    "updated_at",
)


def encode_cursor(created_at: Any, log_id: int) -> str:
    created_at_value = created_at if isinstance(created_at, str) else created_at.isoformat()
    payload = json.dumps({"created_at": created_at_value, "id": log_id}, separators=(",", ":"))
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("utf-8")


def decode_cursor(cursor: str) -> tuple[datetime, int]:
    try:
        payload = base64.urlsafe_b64decode(cursor.encode("utf-8")).decode("utf-8")
        parsed = json.loads(payload)
        return datetime.fromisoformat(parsed["created_at"]), int(parsed["id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise HTTPException(status_code=400, detail="无效的分页游标") from None


def build_query_filter(
    username: str = "",
    module: str = "",
    method: str = "",
    summary: str = "",
    status: Optional[int] = None,
    ip_address: str = "",
    operation_type: str = "",
    log_level: str = "",
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> Q:
    """Build a shared query filter.

    Normalize all query conditions into a single reusable `Q` object.
    """
    # Base condition: only non-deleted records.
    q = Q(is_deleted=False)

    # Add text-match conditions.
    if username:
        q &= Q(username__icontains=username)
    if module:
        q &= Q(module__icontains=module)
    if method:
        q &= Q(method=method.upper())
    if summary:
        q &= Q(summary__icontains=summary)
    if ip_address:
        q &= Q(ip_address__icontains=ip_address)
    if operation_type:
        q &= Q(operation_type__icontains=operation_type)
    if log_level:
        q &= Q(log_level=log_level.lower())

    # Add numeric-match conditions.
    if status is not None:
        q &= Q(status=status)

    # Add time-range conditions.
    if start_time and end_time:
        q &= Q(created_at__range=[start_time, end_time])
    elif start_time:
        q &= Q(created_at__gte=start_time)
    elif end_time:
        q &= Q(created_at__lte=end_time)

    return q


@router.get("/list", summary="查看操作日志")
async def get_audit_log_list(
    page_size: int = Query(100, description="每页数量", ge=1, le=200),
    cursor: Optional[str] = Query(None, description="游标，取上一页最后一条记录生成"),
    username: str = Query("", description="操作人名称"),
    module: str = Query("", description="功能模块"),
    method: str = Query("", description="请求方法"),
    summary: str = Query("", description="接口描述"),
    status: int = Query(None, description="状态码"),
    ip_address: str = Query("", description="IP地址"),
    operation_type: str = Query("", description="操作类型"),
    log_level: str = Query("", description="日志级别"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
):
    """
    Return a lightweight audit-log list using cursor pagination to reduce large-table query costs.
    """
    base_q = build_query_filter(
        username, module, method, summary, status, ip_address, operation_type, log_level, start_time, end_time
    )
    q = base_q

    if cursor:
        cursor_created_at, cursor_id = decode_cursor(cursor)
        q &= Q(created_at__lt=cursor_created_at) | (Q(created_at=cursor_created_at) & Q(id__lt=cursor_id))

    total, rows = await AuditLog.filter(base_q).count(), await AuditLog.filter(q).order_by("-created_at", "-id").limit(page_size + 1).values(*AUDIT_LOG_LIST_FIELDS)

    has_more = len(rows) > page_size
    data = rows[:page_size]
    next_cursor = encode_cursor(data[-1]["created_at"], data[-1]["id"]) if has_more and data else None

    return Success(data=data, total=total, page_size=page_size, has_more=has_more, next_cursor=next_cursor)


@router.get("/detail/{log_id}", summary="查看操作日志详情")
async def get_audit_log_detail(log_id: int = FastAPIPath(..., description="日志ID")):
    """
    Return the details for a single audit log and fetch large fields on demand.
    """
    detail_rows = await AuditLog.filter(id=log_id, is_deleted=False).limit(1).values(*AUDIT_LOG_DETAIL_FIELDS)

    if not detail_rows:
        raise HTTPException(status_code=404, detail="日志不存在")

    return Success(data=detail_rows[0])


@router.delete("/delete/{log_id}", summary="删除操作日志")
async def delete_audit_log(
    log_id: int = FastAPIPath(..., description="日志ID"), current_user=Depends(AuthControl.is_authed)
):
    """
    Soft-delete the specified audit log.
    """
    # Permission check.
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="权限不足，只有超级管理员可以删除日志")

    # Check whether the log exists.
    log = await AuditLog.get_or_none(id=log_id)
    if not log:
        raise HTTPException(status_code=404, detail="日志不存在")

    # Perform the soft delete.
    await AuditLog.filter(id=log_id).update(is_deleted=True)
    return Success(msg="删除成功")


@router.delete("/batch_delete", summary="批量删除操作日志")
async def batch_delete_audit_logs(
    log_ids: List[int] = Body(..., description="日志ID列表"), current_user=Depends(AuthControl.is_authed)
):
    """
    Soft-delete the specified audit logs in batch.
    """
    # Permission check.
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="权限不足，只有超级管理员可以删除日志")

    # Validate input.
    if not log_ids:
        raise HTTPException(status_code=400, detail="请提供要删除的日志ID")

    # Perform the batch soft delete.
    count = await AuditLog.batch_delete(log_ids)
    return Success(msg=f"成功删除{count}条日志")


@router.delete("/clear", summary="清空操作日志")
async def clear_audit_logs(
    days: Optional[int] = Query(None, description="清除多少天前的日志，不提供则清除所有"),
    current_user=Depends(AuthControl.is_authed),
):
    """
    Soft-delete all audit logs or only logs older than the specified number of days.
    """
    # Permission check.
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="权限不足，只有超级管理员可以清空日志")

    # Build the query filter.
    q = Q(is_deleted=False)
    if days:
        clear_date = datetime.now() - timedelta(days=days)
        clear_date_str = clear_date.strftime("%Y-%m-%d")
        q &= Q(created_at__lt=clear_date_str)

    # Perform the batch soft delete.
    count = await AuditLog.filter(q).update(is_deleted=True)
    return Success(msg=f"成功清除{count}条日志")


async def _export_logs_to_csv(
    start_time: Optional[datetime],
    end_time: Optional[datetime],
    filters: Dict[str, Any],
    export_path: str,
):
    """
    Export logs to a CSV file in a background task.
    """
    # Build the query filter.
    filter_params = {
        "username": filters.get("username", ""),
        "module": filters.get("module", ""),
        "method": filters.get("method", ""),
        "summary": filters.get("summary", ""),
        "status": filters.get("status"),
        "ip_address": filters.get("ip_address", ""),
        "operation_type": filters.get("operation_type", ""),
        "log_level": filters.get("log_level", ""),
    }
    q = build_query_filter(**filter_params, start_time=start_time, end_time=end_time)

    # Query the matching logs.
    logs = await AuditLog.filter(q).order_by("-created_at")

    # Ensure the export directory exists.
    export_dir = os.path.dirname(export_path)
    os.makedirs(export_dir, exist_ok=True)

    # Column display-name mapping.
    field_names_map = {
        "ID": "id",
        "用户ID": "user_id",
        "用户名": "username",
        "功能模块": "module",
        "请求描述": "summary",
        "请求方法": "method",
        "请求路径": "path",
        "状态码": "status",
        "响应时间(ms)": "response_time",
        "IP地址": "ip_address",
        "操作类型": "operation_type",
        "日志级别": "log_level",
        "创建时间": "created_at",
        "更新时间": "updated_at",
    }

    # Write the CSV file.
    try:
        with open(export_path, "w", newline="", encoding="utf-8-sig") as f:
            fieldnames = list(field_names_map.keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for log in logs:
                # Create a CSV row.
                row_data = {}
                for display_name, field_name in field_names_map.items():
                    value = getattr(log, field_name)
                    # Format timestamp fields.
                    if field_name in ("created_at", "updated_at") and value:
                        value = value.strftime("%Y-%m-%d %H:%M:%S")
                    row_data[display_name] = value

                writer.writerow(row_data)
    except Exception as e:
        # Log export failures without interrupting the process.
        import logging

        logging.error(f"Failed to export audit logs to CSV: {str(e)}")


@router.post("/export", summary="导出操作日志")
async def export_audit_logs(
    background_tasks: BackgroundTasks,
    username: str = Body("", description="操作人名称"),
    module: str = Body("", description="功能模块"),
    method: str = Body("", description="请求方法"),
    summary: str = Body("", description="接口描述"),
    status: Optional[int] = Body(None, description="状态码"),
    ip_address: str = Body("", description="IP地址"),
    operation_type: str = Body("", description="操作类型"),
    log_level: str = Body("", description="日志级别"),
    start_time: Optional[datetime] = Body(None, description="开始时间"),
    end_time: Optional[datetime] = Body(None, description="结束时间"),
    current_user=Depends(AuthControl.is_authed),
):
    """
    Export audit logs to a CSV file.
    """
    # Generate the export file name and path.
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    export_dir = Path("./exports/auditlogs")
    export_dir.mkdir(parents=True, exist_ok=True)
    export_file = f"auditlog_export_{timestamp}.csv"
    export_path = export_dir / export_file

    # Prepare the filter payload.
    filters = {
        "username": username,
        "module": module,
        "method": method,
        "summary": summary,
        "status": status,
        "ip_address": ip_address,
        "operation_type": operation_type,
        "log_level": log_level,
    }

    # Start the background export task.
    background_tasks.add_task(_export_logs_to_csv, start_time, end_time, filters, str(export_path))

    return Success(msg=f"正在导出日志，文件将保存为 {export_file}")


@router.get("/download/{filename}", summary="下载导出的日志文件")
async def download_export_file(
    filename: str = FastAPIPath(..., description="导出文件名"), current_user=Depends(AuthControl.is_authed)
):
    """
    Download a previously exported audit-log file.
    """
    # Validate the file name to prevent path traversal.
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="无效的文件名")

    file_path = Path(f"./exports/auditlogs/{filename}")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在或已被删除")

    return FileResponse(path=str(file_path), filename=filename, media_type="text/csv")


@router.get("/statistics", summary="获取操作日志统计信息")
async def get_audit_log_statistics(
    days: int = Query(7, description="统计最近几天的数据", ge=1, le=30), current_user=Depends(AuthControl.is_authed)
):
    """
    Return audit-log statistics for the most recent N days.
    """
    # Apply additional bounds checking.
    if days < 1:
        days = 1
    elif days > 30:
        days = 30

    statistics = await AuditLog.get_logs_statistics(days)
    return Success(data=statistics)
