from __future__ import annotations

import socket

from fastapi import APIRouter, HTTPException

from app.services.remote_drive_service import remote_drive_service
from app.services.settings_service import settings_service
from app.services.ssh_account_service import ssh_account_service

router = APIRouter(prefix="/remote-drive", tags=["remote-drive"])


@router.get("/status")
async def get_status():
    enabled = settings_service.get("remote_drive_enabled", True)
    port = settings_service.get("remote_drive_port", 8081)
    running = remote_drive_service.is_running
    hostname = socket.gethostname()
    accounts = ssh_account_service.list_accounts() or []
    mount_list = [
        {
            "alias": a.alias,
            "hostname": a.host,
            "port": a.port,
            "url": f"http://127.0.0.1:{port}/{a.alias}/",
            "windows_url": f"\\\\127.0.0.1@{port}\\DavWWWRoot\\{a.alias}\\",
        }
        for a in accounts
    ]
    return {
        "enabled": enabled,
        "running": running,
        "port": port,
        "hostname": hostname,
        "webdav_url": f"http://127.0.0.1:{port}/",
        "windows_url": f"\\\\127.0.0.1@{port}\\DavWWWRoot\\",
        "mounts": mount_list,
        "account_count": len(accounts),
    }
