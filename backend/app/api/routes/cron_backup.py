from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.models.cron_backup import (
    BackupPolicyCreate,
    BackupPolicyUpdate,
    CronJobCreate,
    CronJobUpdate,
    LogRetentionPolicyCreate,
    LogRetentionPolicyUpdate,
)
from app.services.cron_backup_service import cron_backup_service
from app.services.ssh_account_service import ssh_account_service

router = APIRouter(prefix="/cron-backup", tags=["cron-backup"])


async def _ensure_account(alias: str) -> None:
    if not ssh_account_service.get_account(alias):
        raise HTTPException(404, f"SSH 账户 '{alias}' 不存在")


# ── Cron 任务 ───────────────────────────────────────────────────

class CronJobCreateRequest(BaseModel):
    alias: str = Field(..., description="SSH 账户别名")
    data: CronJobCreate


class CronJobUpdateRequest(BaseModel):
    alias: str = Field(..., description="SSH 账户别名")
    data: CronJobUpdate


@router.get("/cron-jobs")
async def list_cron_jobs(alias: str = Query(..., description="SSH 账户别名")):
    try:
        await _ensure_account(alias)
        jobs = cron_backup_service.list_cron_jobs(alias)
        return {"items": [job.model_dump(mode="json") for job in jobs]}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取 Cron 任务列表失败: {e}")


@router.post("/cron-jobs")
async def create_cron_job(req: CronJobCreateRequest):
    try:
        await _ensure_account(req.alias)
        job = cron_backup_service.create_cron_job(req.alias, req.data)
        return job.model_dump(mode="json")
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"创建 Cron 任务失败: {e}")


@router.put("/cron-jobs/{job_id}")
async def update_cron_job(job_id: str, req: CronJobUpdateRequest):
    try:
        await _ensure_account(req.alias)
        job = cron_backup_service.update_cron_job(job_id, req.data)
        return job.model_dump(mode="json")
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"更新 Cron 任务失败: {e}")


@router.delete("/cron-jobs/{job_id}")
async def delete_cron_job(
    job_id: str,
    alias: str = Query(..., description="SSH 账户别名"),
):
    try:
        await _ensure_account(alias)
        cron_backup_service.delete_cron_job(job_id)
        return {"message": "Cron 任务已删除"}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"删除 Cron 任务失败: {e}")


@router.get("/cron-jobs/{job_id}/logs")
async def get_cron_job_logs(
    job_id: str,
    alias: str = Query(..., description="SSH 账户别名"),
    limit: int = Query(20, ge=1, le=100),
):
    try:
        await _ensure_account(alias)
        logs = cron_backup_service.list_execution_logs(alias, job_id, limit)
        return {"items": [log.model_dump(mode="json") for log in logs]}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取执行日志失败: {e}")


# ── 备份策略 ────────────────────────────────────────────────────

class BackupPolicyCreateRequest(BaseModel):
    alias: str = Field(..., description="SSH 账户别名")
    data: BackupPolicyCreate


class BackupPolicyUpdateRequest(BaseModel):
    alias: str = Field(..., description="SSH 账户别名")
    data: BackupPolicyUpdate


@router.get("/backup-policies")
async def list_backup_policies(alias: str = Query(..., description="SSH 账户别名")):
    try:
        await _ensure_account(alias)
        policies = cron_backup_service.list_backup_policies(alias)
        return {"items": [p.model_dump(mode="json") for p in policies]}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取备份策略列表失败: {e}")


@router.post("/backup-policies")
async def create_backup_policy(req: BackupPolicyCreateRequest):
    try:
        await _ensure_account(req.alias)
        policy = cron_backup_service.create_backup_policy(req.alias, req.data)
        return policy.model_dump(mode="json")
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"创建备份策略失败: {e}")


@router.put("/backup-policies/{policy_id}")
async def update_backup_policy(policy_id: str, req: BackupPolicyUpdateRequest):
    try:
        await _ensure_account(req.alias)
        policy = cron_backup_service.update_backup_policy(policy_id, req.data)
        return policy.model_dump(mode="json")
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"更新备份策略失败: {e}")


@router.delete("/backup-policies/{policy_id}")
async def delete_backup_policy(
    policy_id: str,
    alias: str = Query(..., description="SSH 账户别名"),
):
    try:
        await _ensure_account(alias)
        cron_backup_service.delete_backup_policy(policy_id)
        return {"message": "备份策略已删除"}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"删除备份策略失败: {e}")


@router.post("/backup-policies/{policy_id}/run")
async def run_backup_now(
    policy_id: str,
    alias: str = Query(..., description="SSH 账户别名"),
):
    try:
        await _ensure_account(alias)
        result = cron_backup_service.run_backup_now(policy_id)
        return result
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"手动执行备份失败: {e}")


@router.get("/backup-history")
async def list_backup_history(
    alias: str = Query(..., description="SSH 账户别名"),
    policy_id: Optional[str] = Query(None, description="策略 ID"),
    limit: int = Query(50, ge=1, le=200),
):
    try:
        await _ensure_account(alias)
        history = cron_backup_service.list_backup_history(alias, policy_id, limit)
        return {"items": [h.model_dump(mode="json") for h in history]}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取备份历史失败: {e}")


@router.get("/backup-history/{history_id}/download")
async def download_backup_file(
    history_id: str,
    alias: str = Query(..., description="SSH 账户别名"),
    file_path: str = Query(..., description="文件路径"),
):
    try:
        await _ensure_account(alias)
        data = cron_backup_service.download_backup_file(alias, file_path)
        filename = file_path.split("/")[-1]
        return StreamingResponse(
            iter([data]),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"下载备份文件失败: {e}")


# ── 日志保留策略 ────────────────────────────────────────────────

class LogPolicyCreateRequest(BaseModel):
    alias: str = Field(..., description="SSH 账户别名")
    data: LogRetentionPolicyCreate


class LogPolicyUpdateRequest(BaseModel):
    alias: str = Field(..., description="SSH 账户别名")
    data: LogRetentionPolicyUpdate


@router.get("/log-policies")
async def list_log_policies(alias: str = Query(..., description="SSH 账户别名")):
    try:
        await _ensure_account(alias)
        policies = cron_backup_service.list_log_policies(alias)
        return {"items": [p.model_dump(mode="json") for p in policies]}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取日志保留策略列表失败: {e}")


@router.post("/log-policies")
async def create_log_policy(req: LogPolicyCreateRequest):
    try:
        await _ensure_account(req.alias)
        policy = cron_backup_service.create_log_policy(req.alias, req.data)
        return policy.model_dump(mode="json")
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"创建日志保留策略失败: {e}")


@router.put("/log-policies/{policy_id}")
async def update_log_policy(policy_id: str, req: LogPolicyUpdateRequest):
    try:
        await _ensure_account(req.alias)
        policy = cron_backup_service.update_log_policy(policy_id, req.data)
        return policy.model_dump(mode="json")
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"更新日志保留策略失败: {e}")


@router.delete("/log-policies/{policy_id}")
async def delete_log_policy(
    policy_id: str,
    alias: str = Query(..., description="SSH 账户别名"),
):
    try:
        await _ensure_account(alias)
        cron_backup_service.delete_log_policy(policy_id)
        return {"message": "日志保留策略已删除"}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"删除日志保留策略失败: {e}")


@router.post("/log-policies/{policy_id}/preview")
async def preview_log_cleanup(
    policy_id: str,
    alias: str = Query(..., description="SSH 账户别名"),
):
    try:
        await _ensure_account(alias)
        files = cron_backup_service.preview_log_cleanup(policy_id)
        return {"items": [f.model_dump(mode="json") for f in files]}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"预览日志清理失败: {e}")


@router.post("/log-policies/{policy_id}/run")
async def run_log_cleanup_now(
    policy_id: str,
    alias: str = Query(..., description="SSH 账户别名"),
):
    try:
        await _ensure_account(alias)
        result = cron_backup_service.run_log_cleanup_now(policy_id)
        return result
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"执行日志清理失败: {e}")


# ── 磁盘空间告警 ────────────────────────────────────────────────

@router.get("/disk-alert")
async def get_disk_alert(alias: str = Query(..., description="SSH 账户别名")):
    try:
        await _ensure_account(alias)
        result = cron_backup_service.get_disk_alert(alias)
        return result
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取磁盘告警失败: {e}")
