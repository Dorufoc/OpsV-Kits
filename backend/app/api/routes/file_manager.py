from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

from app.services.file_manager_service import file_manager_service

router = APIRouter(tags=["file-manager"])


# ---- 请求模型 ----

class SaveContentRequest(BaseModel):
    alias: str = Field(..., description="SSH 账户别名")
    path: str = Field(..., description="远程文件路径")
    content: str = Field(..., description="文件内容")


class MkdirRequest(BaseModel):
    alias: str = Field(..., description="SSH 账户别名")
    path: str = Field(..., description="远程目录路径")


class DeleteRequest(BaseModel):
    alias: str = Field(..., description="SSH 账户别名")
    path: str = Field(..., description="远程文件或目录路径")


class RenameRequest(BaseModel):
    alias: str = Field(..., description="SSH 账户别名")
    src: str = Field(..., description="源路径")
    dst: str = Field(..., description="目标路径")


class CopyRequest(BaseModel):
    alias: str = Field(..., description="SSH 账户别名")
    src: str = Field(..., description="源路径")
    dst: str = Field(..., description="目标路径")


class ChmodRequest(BaseModel):
    alias: str = Field(..., description="SSH 账户别名")
    path: str = Field(..., description="远程文件或目录路径")
    mode: str = Field(..., description="权限模式，如 755、644")


class ChownRequest(BaseModel):
    alias: str = Field(..., description="SSH 账户别名")
    path: str = Field(..., description="远程文件或目录路径")
    user: Optional[str] = Field(default=None, description="新所有者用户名")
    group: Optional[str] = Field(default=None, description="新用户组名")


class ExecCommandRequest(BaseModel):
    alias: str = Field(..., description="SSH 账户别名")
    command: str = Field(..., description="要执行的命令")
    timeout: float = Field(default=30.0, description="超时时间（秒）")


class ExecBatchRequest(BaseModel):
    alias: str = Field(..., description="SSH 账户别名")
    commands: list[str] = Field(..., description="命令列表")
    timeout: float = Field(default=60.0, description="超时时间（秒）")


class BookmarkAddRequest(BaseModel):
    alias: str = Field(..., description="SSH 账户别名")
    path: str = Field(..., description="书签路径")
    label: str = Field(..., description="书签标签")


class BookmarkRemoveRequest(BaseModel):
    alias: str = Field(..., description="SSH 账户别名")
    path: str = Field(..., description="书签路径")


class BatchDeleteRequest(BaseModel):
    alias: str = Field(..., description="SSH 账户别名")
    paths: list[str] = Field(..., description="待删除路径列表")


class BatchChmodRequest(BaseModel):
    alias: str = Field(..., description="SSH 账户别名")
    paths: list[str] = Field(..., description="待修改权限路径列表")
    mode: str = Field(..., description="权限模式，如 755")
    recursive: bool = Field(default=False, description="是否递归应用到子目录")


# ---- 远程文件管理 API ----

@router.get("/files/list")
async def list_directory(
    alias: str = Query(..., description="SSH 账户别名"),
    path: str = Query(..., description="远程目录路径"),
):
    try:
        entries = file_manager_service.list_directory(alias, path)
        return {
            "path": path,
            "entries": [
                {
                    "name": e.name,
                    "path": e.path,
                    "is_dir": e.is_dir,
                    "size": e.size,
                    "permission": e.permissions,
                    "owner": e.owner,
                    "group": e.group,
                    "modified": e.modify_time,
                }
                for e in entries
            ],
        }
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/stat")
async def get_file_stat(
    alias: str = Query(..., description="SSH 账户别名"),
    path: str = Query(..., description="远程文件或目录路径"),
):
    try:
        info = file_manager_service.get_file_info(alias, path)
        return {
            "path": info.path,
            "is_dir": info.is_dir,
            "is_file": info.is_file,
            "is_link": info.is_link,
            "is_socket": info.is_socket,
            "is_fifo": info.is_fifo,
            "is_block_device": info.is_block_device,
            "is_char_device": info.is_char_device,
            "size": info.size,
            "blocks": info.blocks,
            "permissions": info.permissions,
            "permission_mode": info.permission_mode,
            "modify_time": info.modify_time,
            "access_time": info.access_time,
            "change_time": info.change_time,
            "owner": info.owner,
            "group": info.group,
            "link_target": info.link_target,
        }
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/content")
async def read_file_content(
    alias: str = Query(..., description="SSH 账户别名"),
    path: str = Query(..., description="远程文件路径"),
):
    try:
        content = file_manager_service.read_file(alias, path)
        return {"path": path, "content": content}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files/content")
async def save_file_content(data: SaveContentRequest):
    try:
        file_manager_service.write_file(data.alias, data.path, data.content)
        return {"path": data.path, "status": "saved"}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files/mkdir")
async def create_directory(data: MkdirRequest):
    try:
        file_manager_service.create_directory(data.alias, data.path)
        return {"path": data.path, "status": "created"}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files/delete")
async def delete_path(data: DeleteRequest):
    try:
        file_manager_service.delete(data.alias, data.path)
        return {"path": data.path, "status": "deleted"}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files/rename")
async def rename_path(data: RenameRequest):
    try:
        file_manager_service.rename(data.alias, data.src, data.dst)
        return {"src": data.src, "dst": data.dst, "status": "renamed"}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files/copy")
async def copy_path(data: CopyRequest):
    try:
        file_manager_service.copy(data.alias, data.src, data.dst)
        return {"src": data.src, "dst": data.dst, "status": "copied"}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files/chmod")
async def chmod_path(data: ChmodRequest):
    try:
        file_manager_service.chmod(data.alias, data.path, data.mode)
        return {"path": data.path, "mode": data.mode, "status": "changed"}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files/chown")
async def chown_path(data: ChownRequest):
    try:
        file_manager_service.chown(data.alias, data.path, user=data.user, group=data.group)
        return {
            "path": data.path,
            "user": data.user,
            "group": data.group,
            "status": "changed",
        }
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files/upload")
async def upload_file(
    alias: str = Query(..., description="SSH 账户别名"),
    remote_path: str = Query(..., description="远程目标路径"),
    local_path: str = Query(..., description="本地文件路径"),
):
    try:
        file_manager_service.upload(alias, local_path, remote_path)
        return {
            "local_path": local_path,
            "remote_path": remote_path,
            "status": "uploaded",
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/download")
async def download_file(
    alias: str = Query(..., description="SSH 账户别名"),
    remote_path: str = Query(..., description="远程文件路径"),
    local_path: str = Query(..., description="本地保存路径"),
):
    try:
        file_manager_service.download(alias, remote_path, local_path)
        return {
            "remote_path": remote_path,
            "local_path": local_path,
            "status": "downloaded",
        }
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/search")
async def search_files(
    alias: str = Query(..., description="SSH 账户别名"),
    path: str = Query(..., description="搜索起始目录"),
    pattern: str = Query(..., description="文件名模式（支持通配符）"),
    max_depth: Optional[int] = Query(None, description="最大搜索深度"),
    file_type: Optional[str] = Query(None, description="文件类型: file / directory"),
):
    try:
        results = file_manager_service.search(
            alias, path, pattern, max_depth=max_depth, file_type=file_type
        )
        return {
            "path": path,
            "pattern": pattern,
            "results": [
                {
                    "path": r.path,
                    "name": r.name,
                    "is_dir": r.is_dir,
                    "size": r.size,
                    "permissions": r.permissions,
                    "modify_time": r.modify_time,
                }
                for r in results
            ],
        }
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---- 远程命令执行 API ----

@router.post("/command/exec")
async def exec_command(data: ExecCommandRequest):
    is_dangerous, reason = file_manager_service._is_dangerous_command(data.command)
    if is_dangerous:
        file_manager_service._record_operation(
            data.alias, "exec_command", "", "blocked", f"危险命令: {reason}"
        )
        raise HTTPException(status_code=400, detail=f"危险命令被拒绝: {reason}")
    try:
        result = file_manager_service.exec_command(data.alias, data.command, timeout=data.timeout)
        return result
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except TimeoutError as e:
        raise HTTPException(status_code=408, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/command/exec/batch")
async def exec_batch_commands(data: ExecBatchRequest):
    for cmd in data.commands:
        is_dangerous, reason = file_manager_service._is_dangerous_command(cmd)
        if is_dangerous:
            file_manager_service._record_operation(
                data.alias, "exec_batch", "", "blocked", f"危险命令: {reason}"
            )
            raise HTTPException(status_code=400, detail=f"危险命令被拒绝: {reason}")
    try:
        results = file_manager_service.exec_batch(data.alias, data.commands, timeout=data.timeout)
        return {"results": results}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except TimeoutError as e:
        raise HTTPException(status_code=408, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/command/history")
async def get_command_history(
    alias: Optional[str] = Query(None, description="SSH 账户别名（可选）"),
    limit: int = Query(100, description="返回条数上限"),
):
    records = file_manager_service.get_command_history(alias=alias, limit=limit)
    return {
        "records": [
            {
                "timestamp": r.timestamp,
                "account_alias": r.account_alias,
                "command": r.command,
                "exit_code": r.exit_code,
                "stdout": r.stdout,
                "stderr": r.stderr,
            }
            for r in records
        ]
    }


# ---- 权限检查 API ----

@router.get("/permission/check")
async def check_permission(
    alias: str = Query(..., description="SSH 账户别名"),
    path: str = Query(..., description="远程路径"),
):
    try:
        perm = file_manager_service.check_permission(alias, path)
        return {
            "path": perm.path,
            "exists": perm.exists,
            "readable": perm.readable,
            "writable": perm.writable,
            "executable": perm.executable,
            "permissions": perm.permission_str,
            "permission_mode": perm.permission_mode,
            "owner": perm.owner,
            "group": perm.group,
            "current_user": perm.current_user,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/permission/user")
async def get_user_info(
    alias: str = Query(..., description="SSH 账户别名"),
):
    try:
        info = file_manager_service.get_user_info(alias)
        return {
            "username": info.username,
            "uid": info.uid,
            "gid": info.gid,
            "groups": info.groups,
            "home": info.home,
            "shell": info.shell,
            "is_root": info.is_root,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/permission/sudo")
async def check_sudo(
    alias: str = Query(..., description="SSH 账户别名"),
):
    try:
        has_sudo = file_manager_service.check_sudo(alias)
        return {"alias": alias, "has_sudo": has_sudo}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---- 书签管理 API ----

@router.get("/bookmarks")
async def list_bookmarks(
    alias: Optional[str] = Query(None, description="SSH 账户别名（可选）"),
):
    bookmarks = file_manager_service.list_bookmarks(alias=alias)
    return {
        "bookmarks": [
            {
                "alias": b.alias,
                "path": b.path,
                "label": b.label,
                "created_at": b.created_at,
            }
            for b in bookmarks
        ]
    }


@router.post("/bookmarks")
async def add_bookmark(data: BookmarkAddRequest):
    bookmark = file_manager_service.add_bookmark(data.alias, data.path, data.label)
    return {
        "alias": bookmark.alias,
        "path": bookmark.path,
        "label": bookmark.label,
        "created_at": bookmark.created_at,
        "status": "added",
    }


@router.delete("/bookmarks")
async def remove_bookmark(data: BookmarkRemoveRequest):
    removed = file_manager_service.remove_bookmark(data.alias, data.path)
    if not removed:
        raise HTTPException(status_code=404, detail="书签不存在")
    return {"alias": data.alias, "path": data.path, "status": "removed"}


# ---- 操作历史 API ----

@router.get("/operations/history")
async def get_operation_history(
    alias: Optional[str] = Query(None, description="SSH 账户别名（可选）"),
    limit: int = Query(100, description="返回条数上限"),
):
    records = file_manager_service.get_operation_history(alias=alias, limit=limit)
    return {
        "records": [
            {
                "timestamp": r.timestamp,
                "account_alias": r.account_alias,
                "action": r.action,
                "path": r.path,
                "status": r.status,
                "detail": r.detail,
            }
            for r in records
        ]
    }


# ---- 批量操作 API ----

@router.post("/files/batch/delete")
async def batch_delete(data: BatchDeleteRequest):
    results = file_manager_service.batch_delete(data.alias, data.paths)
    return {"results": results}


@router.post("/files/batch/chmod")
async def batch_chmod(data: BatchChmodRequest):
    results = file_manager_service.batch_chmod(data.alias, data.paths, data.mode, recursive=data.recursive)
    return {"results": results}
