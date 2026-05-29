from __future__ import annotations

import socket

from fastapi import APIRouter, HTTPException

from app.services.remote_drive_service import remote_drive_service
from app.services.settings_service import settings_service
from app.services.ssh_account_service import ssh_account_service

router = APIRouter(prefix="/remote-drive", tags=["remote-drive"])


@router.get("/status")
async def get_status():
    enabled = settings_service.get("remote_drive_enabled", False)
    port = settings_service.get("remote_drive_port", 8081)
    username = settings_service.get("remote_drive_username", "opsv")
    password_set = bool(settings_service.get_decrypted_password())
    running = remote_drive_service.is_running
    hostname = socket.gethostname()
    accounts = ssh_account_service.list_accounts() or []
    if not password_set and accounts:
        default_acct = next((a for a in accounts if a.is_default), accounts[0])
        username = default_acct.username or accounts[0].username or "opsv"
    mount_list = [
        {
            "alias": a.alias,
            "hostname": a.host,
            "port": a.port,
            "url": f"http://localhost:{port}/{a.alias}/",
            "windows_url": f"\\\\localhost@{port}\\DavWWWRoot\\{a.alias}\\",
        }
        for a in accounts
    ]
    return {
        "enabled": enabled,
        "running": running,
        "port": port,
        "hostname": hostname,
        "webdav_url": f"http://localhost:{port}/",
        "windows_url": f"\\\\localhost@{port}\\DavWWWRoot\\",
        "mounts": mount_list,
        "account_count": len(accounts),
        "auth_username": username,
        "auth_password_set": password_set,
    }
