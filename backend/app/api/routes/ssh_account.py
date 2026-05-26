from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.models.audit_log import AuditLog
from app.models.ssh_account import (
    AccountGroup,
    SSHAccount,
    SSHAccountCreate,
    SSHAccountUpdate,
)
from app.services.ssh_account_service import ssh_account_service

router = APIRouter(prefix="/accounts", tags=["ssh-accounts"])


@router.get("", response_model=list[SSHAccount])
async def list_accounts(
    group: Optional[str] = Query(None, description="按分组筛选"),
):
    return ssh_account_service.list_accounts(group=group)


@router.post("", response_model=SSHAccount, status_code=201)
async def create_account(data: SSHAccountCreate):
    try:
        return ssh_account_service.create_account(data)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{alias}", response_model=SSHAccount)
async def get_account(alias: str):
    account = ssh_account_service.get_account(alias)
    if account is None:
        raise HTTPException(status_code=404, detail=f"账户 '{alias}' 不存在")
    return account


@router.put("/{alias}", response_model=SSHAccount)
async def update_account(alias: str, data: SSHAccountUpdate):
    try:
        return ssh_account_service.update_account(alias, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{alias}", status_code=204)
async def delete_account(alias: str):
    try:
        ssh_account_service.delete_account(alias)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{alias}/test")
async def test_account(alias: str):
    try:
        success, message = ssh_account_service.test_account(alias)
        return {"alias": alias, "success": success, "message": message}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{alias}/default", response_model=SSHAccount)
async def set_default_account(alias: str):
    try:
        return ssh_account_service.set_default(alias)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/exists")
async def accounts_exist():
    accounts = ssh_account_service.list_accounts()
    return {"exists": len(accounts) > 0, "count": len(accounts)}


@router.get("/default/info", response_model=Optional[SSHAccount])
async def get_default_account():
    return ssh_account_service.get_default()


@router.get("/audit/logs", response_model=list[AuditLog])
async def get_audit_logs(
    account_alias: Optional[str] = Query(None, description="按账户别名筛选"),
    limit: int = Query(100, description="返回条数上限"),
):
    return ssh_account_service.get_audit_logs(
        account_alias=account_alias, limit=limit
    )


@router.post("/groups", response_model=AccountGroup, status_code=201)
async def create_group(name: str, accounts: Optional[list[str]] = None):
    try:
        return ssh_account_service.create_group(name, accounts)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/groups/list", response_model=list[AccountGroup])
async def list_groups():
    return ssh_account_service.list_groups()


@router.get("/groups", response_model=list[AccountGroup])
async def list_groups_short():
    return ssh_account_service.list_groups()


@router.delete("/groups/{name}", status_code=204)
async def delete_group(name: str):
    try:
        ssh_account_service.delete_group(name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
