from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.core.ssh_client import SSHClientManager
from app.models.audit_log import AuditLog
from app.models.ssh_account import (
    AccountGroup,
    AccountGroupCreate,
    AccountGroupUpdate,
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


@router.get("/exists")
async def accounts_exist():
    accounts = ssh_account_service.list_accounts()
    return {"exists": len(accounts) > 0, "count": len(accounts)}


@router.post("/workplace/init")
async def init_workplace(
    alias: str = Query(..., description="SSH 账户别名"),
):
    try:
        message = ssh_account_service.init_workplace(alias)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


@router.post("/test-connection")
async def test_connection_direct(data: SSHAccountCreate):
    """直接测试SSH连接，不保存账户信息"""
    try:
        account = SSHAccount(
            alias="__temp_test__",
            host=data.host,
            port=data.port,
            username=data.username,
            auth_type=data.auth_type,
            password=data.password,
            private_key=data.private_key,
            key_passphrase=data.key_passphrase,
            totp_secret=data.totp_secret,
        )
        manager = SSHClientManager(account)
        success, message = manager.test_connection(timeout=10.0)
        return {"success": success, "message": message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"测试连接失败: {e}")


@router.post("/groups", response_model=AccountGroup, status_code=201)
async def create_group(data: AccountGroupCreate):
    try:
        return ssh_account_service.create_group(data.name, data.accounts)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/groups/list", response_model=list[AccountGroup])
async def list_groups():
    return ssh_account_service.list_groups()


@router.get("/groups", response_model=list[AccountGroup])
async def list_groups_short():
    return ssh_account_service.list_groups()


@router.put("/groups/{name}", response_model=AccountGroup)
async def update_group(name: str, data: AccountGroupUpdate):
    try:
        return ssh_account_service.update_group(name, new_name=data.new_name, accounts=data.accounts)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/groups/{name}", status_code=204)
async def delete_group(name: str):
    try:
        ssh_account_service.delete_group(name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


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


@router.delete("/clear-all", status_code=204)
async def clear_all_accounts(confirm: str = Query(..., description="确认删除所有账户，传入 'yes' 确认")):
    """清空所有SSH账户（用于异常情况下的清理）"""
    if confirm != "yes":
        raise HTTPException(status_code=400, detail="请传入 confirm=yes 确认删除所有账户")
    try:
        ssh_account_service.clear_all_accounts()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理账户失败: {e}")


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


@router.get("/storage/info")
async def get_storage_info():
    """获取数据存储路径和状态（用于诊断）"""
    from pathlib import Path
    persist_dir = Path.home() / ".opsv-kits"
    accounts_path = persist_dir / "accounts.json"
    return {
        "home_directory": str(Path.home()),
        "persist_directory": str(persist_dir),
        "accounts_file_path": str(accounts_path),
        "persist_dir_exists": persist_dir.exists(),
        "accounts_file_exists": accounts_path.exists(),
        "accounts_count": len(ssh_account_service.list_accounts()),
    }
