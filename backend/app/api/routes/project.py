from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.project_config import ProjectConfig, ProjectConfigCreate, ProjectConfigUpdate
from app.services.project_config_service import project_config_service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectConfig])
async def list_projects():
    return project_config_service.list_projects()


@router.post("", response_model=ProjectConfig, status_code=201)
async def create_project(data: ProjectConfigCreate):
    try:
        return project_config_service.create_project(data)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{alias}", response_model=ProjectConfig)
async def get_project(alias: str):
    project = project_config_service.get_project(alias)
    if project is None:
        raise HTTPException(status_code=404, detail=f"项目 '{alias}' 不存在")
    return project


@router.put("/{alias}", response_model=ProjectConfig)
async def update_project(alias: str, data: ProjectConfigUpdate):
    try:
        return project_config_service.update_project(alias, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{alias}", status_code=204)
async def delete_project(alias: str):
    try:
        project_config_service.delete_project(alias)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
