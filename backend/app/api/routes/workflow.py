from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.models.workflow import (
    TriggerType,
    WorkflowCreate,
    WorkflowUpdate,
)
from app.services.workflow_service import workflow_service

router = APIRouter(prefix="/workflow", tags=["workflow"])


class ValidateRequest(BaseModel):
    nodes: list[dict]
    edges: list[dict]


class SaveVersionRequest(BaseModel):
    change_note: Optional[str] = Field(default=None)


class RollbackRequest(BaseModel):
    version: int


class CreateFromTemplateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class ExecuteRequest(BaseModel):
    trigger_type: str = Field(..., description="触发类型")
    trigger_source: Optional[str] = Field(default=None, description="触发来源")


@router.get("/")
async def list_workflows():
    try:
        workflows = workflow_service.list_workflows()
        return {"items": [workflow.model_dump(mode="json") for workflow in workflows]}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取工作流列表失败: {e}")


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str):
    try:
        workflow = workflow_service.get_workflow(workflow_id)
        if not workflow:
            raise HTTPException(404, f"工作流 '{workflow_id}' 不存在")
        return workflow.model_dump(mode="json")
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取工作流失败: {e}")


@router.post("/")
async def create_workflow(data: WorkflowCreate):
    try:
        workflow = workflow_service.create_workflow(data)
        return workflow.model_dump(mode="json")
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"创建工作流失败: {e}")


@router.put("/{workflow_id}")
async def update_workflow(workflow_id: str, data: WorkflowUpdate):
    try:
        workflow = workflow_service.update_workflow(workflow_id, data)
        return workflow.model_dump(mode="json")
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"更新工作流失败: {e}")


@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: str):
    try:
        workflow_service.delete_workflow(workflow_id)
        return {"message": "工作流已删除"}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"删除工作流失败: {e}")


@router.post("/validate")
async def validate_workflow(req: ValidateRequest):
    try:
        result = workflow_service.validate_dag(req.nodes, req.edges)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"验证工作流失败: {e}")


@router.post("/{workflow_id}/save-version")
async def save_version(workflow_id: str, req: SaveVersionRequest):
    try:
        version = workflow_service.save_version(workflow_id, req.change_note)
        return version.model_dump(mode="json")
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"保存版本失败: {e}")


@router.get("/{workflow_id}/versions")
async def list_versions(workflow_id: str):
    try:
        versions = workflow_service.list_versions(workflow_id)
        return {"items": [v.model_dump(mode="json") for v in versions]}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取版本列表失败: {e}")


@router.post("/{workflow_id}/rollback")
async def rollback_version(workflow_id: str, req: RollbackRequest):
    try:
        workflow = workflow_service.rollback_version(workflow_id, req.version)
        return workflow.model_dump(mode="json")
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"回滚版本失败: {e}")


@router.get("/{workflow_id}/export")
async def export_workflow(workflow_id: str):
    try:
        result = workflow_service.export_workflow(workflow_id)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"导出工作流失败: {e}")


@router.post("/import")
async def import_workflow(data: dict):
    try:
        workflow = workflow_service.import_workflow(data)
        return workflow.model_dump(mode="json")
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"导入工作流失败: {e}")


@router.get("/templates")
async def list_templates():
    try:
        templates = workflow_service.list_templates()
        return {"items": [t.model_dump(mode="json") for t in templates]}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取模板列表失败: {e}")


@router.post("/templates/{template_id}/create")
async def create_from_template(template_id: str, req: CreateFromTemplateRequest):
    try:
        workflow = workflow_service.create_from_template(template_id, req.name)
        return workflow.model_dump(mode="json")
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"从模板创建工作流失败: {e}")


@router.post("/{workflow_id}/execute")
async def execute_workflow(workflow_id: str, req: ExecuteRequest):
    try:
        trigger_type = TriggerType(req.trigger_type)
        execution = workflow_service.execute_workflow(workflow_id, trigger_type, req.trigger_source)
        return execution.model_dump(mode="json")
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"执行工作流失败: {e}")


@router.post("/executions/{execution_id}/pause")
async def pause_execution(execution_id: str):
    try:
        workflow_service.pause_execution(execution_id)
        return {"message": "执行已暂停"}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"暂停执行失败: {e}")


@router.post("/executions/{execution_id}/resume")
async def resume_execution(execution_id: str):
    try:
        workflow_service.resume_execution(execution_id)
        return {"message": "执行已恢复"}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"恢复执行失败: {e}")


@router.post("/executions/{execution_id}/cancel")
async def cancel_execution(execution_id: str):
    try:
        workflow_service.cancel_execution(execution_id)
        return {"message": "执行已取消"}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"取消执行失败: {e}")


@router.get("/{workflow_id}/executions")
async def list_executions(
    workflow_id: str,
    limit: int = Query(50, ge=1),
):
    try:
        executions = workflow_service.list_executions(workflow_id, limit)
        return {"items": [e.model_dump(mode="json") for e in executions]}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取执行列表失败: {e}")


@router.get("/executions/{execution_id}")
async def get_execution(execution_id: str):
    try:
        execution = workflow_service.get_execution(execution_id)
        if not execution:
            raise HTTPException(404, f"执行记录 '{execution_id}' 不存在")
        node_executions = workflow_service.list_node_executions(execution_id)
        result = execution.model_dump(mode="json")
        result["node_executions"] = [ne.model_dump(mode="json") for ne in node_executions]
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取执行详情失败: {e}")


@router.get("/executions/{execution_id}/nodes")
async def list_node_executions(execution_id: str):
    try:
        node_executions = workflow_service.list_node_executions(execution_id)
        return {"items": [ne.model_dump(mode="json") for ne in node_executions]}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取节点执行记录失败: {e}")
