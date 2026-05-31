from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.models.audit_log import (
    AuditArchiveInfo,
    AuditLog,
    AuditLogExportRequest,
    AuditLogPageResult,
    AuditLogQuery,
    AuditLogStatistics,
    AuditLogVerifyResult,
)
from app.services.audit_log_service import audit_log_service

router = APIRouter(prefix="/audit-log", tags=["audit-log"])

_export_tasks: dict[str, dict] = {}


@router.post("/query", response_model=AuditLogPageResult)
async def query_audit_logs(body: AuditLogQuery):
    try:
        return await audit_log_service.query(body)
    except Exception as e:
        raise HTTPException(500, f"查询审计日志失败: {e}")


@router.get("/{log_id}", response_model=AuditLog)
async def get_audit_log(log_id: str):
    try:
        result = await audit_log_service.get_by_id(log_id)
        if result is None:
            raise HTTPException(404, f"审计日志不存在: {log_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"获取审计日志详情失败: {e}")


@router.get("/statistics", response_model=AuditLogStatistics)
async def get_statistics(
    time_start: Optional[str] = Query(None, description="起始时间"),
    time_end: Optional[str] = Query(None, description="结束时间"),
    granularity: str = Query("day", description="统计粒度: minute/hour/day/week/month"),
):
    try:
        ts = None
        te = None
        if time_start:
            ts = datetime.fromisoformat(time_start)
        if time_end:
            te = datetime.fromisoformat(time_end)
        return await audit_log_service.get_statistics(ts, te, granularity)
    except Exception as e:
        raise HTTPException(500, f"获取审计统计失败: {e}")


@router.post("/export")
async def export_audit_logs(body: AuditLogExportRequest):
    try:
        export_query = body.query.model_copy(update={"page_size": 10000})
        result = await audit_log_service.query(export_query)
        record_count = result.total

        file_ext = body.format if body.format in ("xlsx", "csv", "pdf") else "xlsx"
        task_id = uuid.uuid4().hex
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        exports_dir = project_root / "data" / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(exports_dir / f"audit_export_{task_id}.{file_ext}")

        download_url = f"/api/audit-log/export/{task_id}/download?format={file_ext}"

        if record_count < 1000:

            async def _sync_export():
                if file_ext == "xlsx":
                    await audit_log_service.export_excel(export_query, output_path)
                elif file_ext == "csv":
                    await audit_log_service.export_csv(export_query, output_path)
                elif file_ext == "pdf":
                    await audit_log_service.export_pdf(export_query, output_path)

            await _sync_export()
            _export_tasks[task_id] = {
                "status": "completed",
                "output_path": output_path,
                "format": file_ext,
                "record_count": record_count,
            }
        else:

            async def _async_export():
                try:
                    if file_ext == "xlsx":
                        await audit_log_service.export_excel(export_query, output_path)
                    elif file_ext == "csv":
                        await audit_log_service.export_csv(export_query, output_path)
                    elif file_ext == "pdf":
                        await audit_log_service.export_pdf(export_query, output_path)
                    _export_tasks[task_id] = {
                        "status": "completed",
                        "output_path": output_path,
                        "format": file_ext,
                        "record_count": record_count,
                    }
                except Exception as exc:
                    _export_tasks[task_id] = {
                        "status": "failed",
                        "error": str(exc),
                        "format": file_ext,
                        "record_count": record_count,
                    }

            _export_tasks[task_id] = {
                "status": "processing",
                "output_path": output_path,
                "format": file_ext,
                "record_count": record_count,
            }
            asyncio.create_task(_async_export())

        return {
            "task_id": task_id,
            "download_url": download_url,
            "format": file_ext,
            "record_count": record_count,
        }
    except Exception as e:
        raise HTTPException(500, f"导出审计日志失败: {e}")


@router.get("/export/{task_id}/download")
async def download_export(task_id: str, format: str = Query("xlsx", description="文件格式")):
    try:
        task_info = _export_tasks.get(task_id)
        if task_info is None:
            raise HTTPException(404, f"导出任务不存在: {task_id}")
        if task_info.get("status") == "processing":
            raise HTTPException(202, "导出任务正在处理中")
        if task_info.get("status") == "failed":
            raise HTTPException(500, f"导出任务失败: {task_info.get('error', '未知错误')}")

        output_path = task_info.get("output_path", "")
        file_path = Path(output_path)
        if not file_path.exists():
            raise HTTPException(404, f"导出文件不存在: {file_path.name}")

        media_types = {
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "csv": "text/csv",
            "pdf": "application/pdf",
        }
        media_type = media_types.get(format, "application/octet-stream")
        return FileResponse(
            path=str(file_path),
            media_type=media_type,
            filename=file_path.name,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"下载导出文件失败: {e}")


@router.post("/verify", response_model=AuditLogVerifyResult)
async def verify_audit_logs(body: Optional[dict] = None):
    try:
        log_id = None
        if body and "log_id" in body:
            log_id = body["log_id"]
        return await audit_log_service.verify_integrity(log_id)
    except Exception as e:
        raise HTTPException(500, f"校验审计日志完整性失败: {e}")


@router.get("/archives", response_model=List[AuditArchiveInfo])
async def list_archives():
    try:
        return await audit_log_service.list_archives()
    except Exception as e:
        raise HTTPException(500, f"获取归档列表失败: {e}")


@router.get("/recent", response_model=List[AuditLog])
async def get_recent_logs(limit: int = Query(5, description="返回条数")):
    try:
        return await audit_log_service.get_recent_logs(limit)
    except Exception as e:
        raise HTTPException(500, f"获取最近审计日志失败: {e}")
