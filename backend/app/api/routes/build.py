from __future__ import annotations

import asyncio
import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Path, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.services.build_service import build_service
from app.services.ssh_account_service import ssh_account_service

router = APIRouter(prefix="/environment", tags=["build"])
build_router = APIRouter(prefix="/build", tags=["build"])


class InstallRequest(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    java_version: Optional[str] = Field(default=None, description="需要安装的 Java 版本，如 11/17/21")
    project_path: Optional[str] = Field(default=None, description="项目远程路径（用于自动检测所需版本）")
    dnf_mirror: Optional[str] = Field(default=None, description="DNF 镜像源 URL")
    proxy: Optional[str] = Field(default=None, description="代理地址")


class CheckResponse(BaseModel):
    account_alias: str
    project_path: str
    java: dict
    maven: dict
    all_ready: bool


class TaskStatusResponse(BaseModel):
    task_id: str
    account_alias: str
    components: list[str]
    status: str
    progress: float
    message: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


def _verify_account(account_alias: str) -> None:
    account = ssh_account_service.get_account(account_alias)
    if account is None:
        raise HTTPException(
            status_code=404, detail=f"SSH 账户 '{account_alias}' 不存在"
        )


@router.get("/check", response_model=CheckResponse)
async def check_environment(
    account_alias: str = Query(..., description="SSH 账户别名"),
    project_path: str = Query(..., description="远程项目路径"),
):
    _verify_account(account_alias)
    try:
        result = build_service.check_environment(account_alias, project_path)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"环境检查失败: {e}"
        )


@router.post("/install", response_model=TaskStatusResponse)
async def install_environment(data: InstallRequest):
    _verify_account(data.account_alias)

    java_version = data.java_version
    if java_version is None and data.project_path:
        try:
            check_result = build_service.check_java(
                data.account_alias, data.project_path
            )
            required = check_result.get("required", "")
            if required and not check_result.get("compatible", False):
                java_version = required.split(".")[0]
        except Exception:
            pass

    task = build_service.install_environment(
        account_alias=data.account_alias,
        java_version=java_version,
        dnf_mirror=data.dnf_mirror,
        proxy=data.proxy,
    )
    return TaskStatusResponse(**task.to_dict())


@router.get("/status", response_model=TaskStatusResponse)
async def get_install_status(
    task_id: str = Query(..., description="安装任务 ID"),
):
    task_dict = build_service.get_task_dict(task_id)
    if task_dict is None:
        raise HTTPException(status_code=404, detail=f"任务 '{task_id}' 不存在")
    return TaskStatusResponse(**task_dict)


@router.websocket("/ws/status")
async def environment_status_ws(websocket: WebSocket):
    await websocket.accept()
    subscribed_tasks: set[str] = set()

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "无效的 JSON"})
                continue

            msg_type = msg.get("type")

            if msg_type == "subscribe":
                task_id = msg.get("task_id")
                if not task_id:
                    await websocket.send_json(
                        {"type": "error", "message": "缺少 task_id"}
                    )
                    continue

                task = build_service.get_task(task_id)
                if task is None:
                    await websocket.send_json(
                        {"type": "error", "message": f"任务 '{task_id}' 不存在"}
                    )
                    continue

                subscribed_tasks.add(task_id)

                def _make_callback(tid: str, ws: WebSocket):
                    def _push(update):
                        try:
                            asyncio.run_coroutine_threadsafe(
                                ws.send_json(
                                    {
                                        "type": "status_update",
                                        "task_id": tid,
                                        "data": update.to_dict(),
                                    }
                                ),
                                asyncio.get_event_loop(),
                            )
                        except Exception:
                            pass

                    return _push

                cb = _make_callback(task_id, websocket)
                task.add_callback(cb)

                await websocket.send_json(
                    {
                        "type": "subscribed",
                        "task_id": task_id,
                        "data": task.to_dict(),
                    }
                )

            elif msg_type == "unsubscribe":
                task_id = msg.get("task_id")
                if task_id in subscribed_tasks:
                    subscribed_tasks.discard(task_id)
                await websocket.send_json(
                    {"type": "unsubscribed", "task_id": task_id}
                )

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            else:
                await websocket.send_json(
                    {"type": "error", "message": f"未知消息类型: {msg_type}"}
                )

    except WebSocketDisconnect:
        pass
    except Exception:
        pass


# ── 编译运行 API 请求/响应模型 ─────────────────────────────────


class CompileRequest(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    project_path: str = Field(..., description="远程项目路径")
    command: str = Field(default="mvn clean compile", description="Maven 编译命令")


class PackageRequest(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    project_path: str = Field(..., description="远程项目路径")
    command: str = Field(
        default="mvn clean package -DskipTests", description="Maven 打包命令"
    )


class RunJarRequest(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    project_path: str = Field(..., description="远程项目路径")
    jar_path: str = Field(..., description="JAR 文件相对/绝对路径")
    jvm_args: str = Field(default="", description="JVM 参数")
    app_args: str = Field(default="", description="应用参数")


class RunSpringBootRequest(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    project_path: str = Field(..., description="远程项目路径")
    main_class: Optional[str] = Field(default=None, description="Spring Boot 主类")


class RunExecJavaRequest(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    project_path: str = Field(..., description="远程项目路径")
    main_class: str = Field(..., description="要执行的 Java 主类")


class BuildTaskResponse(BaseModel):
    task_id: str
    account_alias: str
    project_path: str
    action: str
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    log: str = ""
    exit_code: Optional[int] = None
    pid: Optional[int] = None


class BuildHistoryResponse(BaseModel):
    tasks: list[BuildTaskResponse]


# ── 编译运行 API 端点 ──────────────────────────────────────────


@build_router.post("/compile", response_model=BuildTaskResponse)
async def api_compile(data: CompileRequest):
    _verify_account(data.account_alias)
    try:
        task = build_service.compile_project(
            account_alias=data.account_alias,
            project_path=data.project_path,
            command=data.command,
        )
        return BuildTaskResponse(**task.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动编译失败: {e}")


@build_router.post("/package", response_model=BuildTaskResponse)
async def api_package(data: PackageRequest):
    _verify_account(data.account_alias)
    try:
        task = build_service.package_project(
            account_alias=data.account_alias,
            project_path=data.project_path,
            command=data.command,
        )
        return BuildTaskResponse(**task.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动打包失败: {e}")


@build_router.post("/run/jar", response_model=BuildTaskResponse)
async def api_run_jar(data: RunJarRequest):
    _verify_account(data.account_alias)
    try:
        task = build_service.run_jar(
            account_alias=data.account_alias,
            project_path=data.project_path,
            jar_path=data.jar_path,
            jvm_args=data.jvm_args,
            app_args=data.app_args,
        )
        return BuildTaskResponse(**task.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动运行失败: {e}")


@build_router.post("/run/spring-boot", response_model=BuildTaskResponse)
async def api_run_spring_boot(data: RunSpringBootRequest):
    _verify_account(data.account_alias)
    try:
        task = build_service.run_spring_boot(
            account_alias=data.account_alias,
            project_path=data.project_path,
            main_class=data.main_class,
        )
        return BuildTaskResponse(**task.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动 Spring Boot 失败: {e}")


@build_router.post("/run/exec", response_model=BuildTaskResponse)
async def api_run_exec_java(data: RunExecJavaRequest):
    _verify_account(data.account_alias)
    try:
        task = build_service.run_exec_java(
            account_alias=data.account_alias,
            project_path=data.project_path,
            main_class=data.main_class,
        )
        return BuildTaskResponse(**task.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动 exec:java 失败: {e}")


@build_router.post("/stop/{task_id}", response_model=dict)
async def api_stop_task(
    task_id: str = Path(..., description="构建任务 ID"),
):
    task = build_service.get_build_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务 '{task_id}' 不存在")

    success = build_service.stop_build_task(task_id)
    if not success:
        raise HTTPException(
            status_code=409,
            detail=f"任务 '{task_id}' 当前状态为 '{task.status}'，无法停止",
        )
    return {"task_id": task_id, "status": "stopped", "message": "停止请求已发送"}


@build_router.get("/status/{task_id}", response_model=BuildTaskResponse)
async def api_get_build_status(
    task_id: str = Path(..., description="构建任务 ID"),
):
    task = build_service.get_build_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务 '{task_id}' 不存在")
    return BuildTaskResponse(**task.to_dict())


@build_router.get("/history", response_model=BuildHistoryResponse)
async def api_get_build_history(
    account_alias: Optional[str] = Query(default=None, description="SSH 账户别名"),
    limit: int = Query(default=50, ge=1, le=200, description="返回记录数量上限"),
):
    tasks = build_service.get_build_history(
        account_alias=account_alias, limit=limit
    )
    return BuildHistoryResponse(tasks=[BuildTaskResponse(**t) for t in tasks])


# ── 实时日志 WebSocket ─────────────────────────────────────────


@build_router.websocket("/ws/logs/{task_id}")
async def build_logs_ws(
    websocket: WebSocket,
    task_id: str = Path(..., description="构建任务 ID"),
):
    await websocket.accept()

    task = build_service.get_build_task(task_id)
    if task is None:
        await websocket.send_json({
            "type": "error",
            "message": f"任务 '{task_id}' 不存在",
        })
        await websocket.close()
        return

    await websocket.send_json({
        "type": "task_info",
        "data": task.to_dict(),
    })

    stopped = False

    def _push_update(t: object) -> None:
        nonlocal stopped
        if stopped:
            return
        try:
            asyncio.run_coroutine_threadsafe(
                websocket.send_json({
                    "type": "log_update",
                    "data": t.to_dict(),
                }),
                asyncio.get_event_loop(),
            )
        except Exception:
            stopped = True

    task.add_callback(_push_update)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "无效的 JSON"})
                continue

            msg_type = msg.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            elif msg_type == "get_log":
                await websocket.send_json({
                    "type": "log_update",
                    "data": task.to_dict(),
                })
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"未知消息类型: {msg_type}",
                })
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
