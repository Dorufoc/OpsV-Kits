import asyncio
import json
import logging
import time
from collections import defaultdict
from pathlib import Path

# ██ 启动进度报告（必须在任何可能阻塞的导入之前）██
_PROGRESS_FILE = Path(__file__).resolve().parent.parent / ".startup_progress.json"

def _report_progress(step: int, total: int, message: str) -> None:
    try:
        _PROGRESS_FILE.write_text(
            json.dumps({"step": step, "total": total, "message": message, "done": False}),
            encoding="utf-8",
        )
    except Exception:
        pass

def _mark_startup_done() -> None:
    try:
        if _PROGRESS_FILE.exists():
            data = json.loads(_PROGRESS_FILE.read_text(encoding="utf-8"))
            data["done"] = True
            _PROGRESS_FILE.write_text(json.dumps(data), encoding="utf-8")
    except Exception:
        pass

_MODULE_TOTAL = 5
_report_progress(0, 10 + _MODULE_TOTAL, "正在加载后端模块...")

# ── 第一阶段：基础库导入 ──
_report_progress(1, 10 + _MODULE_TOTAL, "正在加载Web框架...")
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

# ── 第二阶段：API路由导入 ──
_report_progress(2, 10 + _MODULE_TOTAL, "正在加载API路由...")
from app.api.routes import build
from app.api.routes import db_toolkit
from app.api.routes import docker
from app.api.routes import docker_store
from app.api.routes import file_manager
from app.api.routes import health
from app.api.routes import monitor
from app.api.routes import port
from app.api.routes import process as process_route
from app.api.routes import project
from app.api.routes import remote_drive
from app.api.routes import settings as settings_route
from app.api.routes import ssh_account
from app.api.routes import sync as sync_route
from app.api.routes import cron_backup
from app.api.routes import security
from app.api.routes import system
from app.api.routes import vite_deploy
from app.api.routes import webssh
from app.api.routes import git_integration
from app.api.routes import audit_log
from app.api.routes import workflow
from app.api.routes import scheduler
from app.api.routes import event_trigger
from app.api.routes import log_analysis
from app.api.routes import health_probe
from app.core.audit_middleware import AuditMiddleware
from app.services.sync_service import sync_service

# ── 第三阶段：限流器 ──
_report_progress(3, 10 + _MODULE_TOTAL, "正在配置限流器...")
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded

    limiter = Limiter(key_func=get_remote_address)
    _RATE_LIMIT_BACKEND = "slowapi"
except Exception:
    limiter = None
    _RATE_LIMIT_BACKEND = "memory"

# ── 第四阶段：日志配置 ──
_report_progress(4, 10 + _MODULE_TOTAL, "正在配置日志系统...")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logging.getLogger("apscheduler.executors.default").setLevel(logging.WARNING)
logging.getLogger("apscheduler.scheduler").setLevel(logging.WARNING)

# ── 第五阶段：FastAPI应用 ──
_report_progress(5, 10 + _MODULE_TOTAL, "正在初始化FastAPI应用...")

app = FastAPI(
    title="OpsV-Kits API",
    description="OpsV-Kits Backend API",
    version="0.1.0",
)

if limiter is not None:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]

app.add_middleware(AuditMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Accept", "Origin"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(ssh_account.router, prefix="/api", tags=["ssh-accounts"])
app.include_router(build.router, prefix="/api", tags=["build"])
app.include_router(build.build_router, prefix="/api", tags=["build"])
app.include_router(sync_route.router, prefix="/api", tags=["sync"])
app.include_router(file_manager.router, prefix="/api", tags=["file-manager"])
app.include_router(settings_route.router, prefix="/api", tags=["settings"])
app.include_router(docker.router, prefix="/api", tags=["docker"])
app.include_router(docker_store.router, prefix="/api", tags=["docker-store"])
app.include_router(db_toolkit.router, prefix="/api", tags=["db-toolkit"])
app.include_router(cron_backup.router, prefix="/api", tags=["cron-backup"])
app.include_router(security.router, prefix="/api", tags=["security"])
app.include_router(system.router, prefix="/api", tags=["system"])
app.include_router(project.router, prefix="/api", tags=["projects"])
app.include_router(webssh.router, prefix="/api", tags=["webssh"])
app.include_router(remote_drive.router, prefix="/api", tags=["remote-drive"])
app.include_router(monitor.router, prefix="/api", tags=["monitor"])
app.include_router(process_route.router, prefix="/api", tags=["process"])
app.include_router(port.router, prefix="/api", tags=["port"])
app.include_router(vite_deploy.router, prefix="/api", tags=["vite-deploy"])
app.include_router(vite_deploy.deploy_router, prefix="/api", tags=["vite-deploy"])
app.include_router(git_integration.router, prefix="/api", tags=["git-integration"])
app.include_router(git_integration.webhook_router, prefix="/api", tags=["git-webhook"])
app.include_router(audit_log.router, prefix="/api", tags=["audit-log"])
app.include_router(workflow.router, prefix="/api", tags=["workflow"])
app.include_router(scheduler.router, prefix="/api", tags=["scheduler"])
app.include_router(event_trigger.router, prefix="/api", tags=["event-trigger"])
app.include_router(log_analysis.router, prefix="/api", tags=["log-analysis"])
app.include_router(health_probe.router, prefix="/api", tags=["health-probe"])


STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


# ── 健康检查 ──

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "timestamp": time.time()}


# ── SPA fallback ──

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    if STATIC_DIR.is_dir():
        index = STATIC_DIR / "index.html"
        if index.is_file():
            from fastapi.responses import FileResponse as FR
            return FR(str(index))
    from fastapi.responses import JSONResponse as JR
    return JR(status_code=404, content={"detail": "Not Found"})


@app.middleware("http")
async def spa_fallback_middleware(request: Request, call_next):
    response = await call_next(request)
    if response.status_code == 404 and STATIC_DIR.is_dir():
        accept = request.headers.get("accept", "")
        if "text/html" in accept or not request.url.path.startswith("/api/"):
            index = STATIC_DIR / "index.html"
            if index.is_file():
                from fastapi.responses import FileResponse as FR
                return FR(str(index))
    return response


# ── Uvicorn startup / shutdown ──

from app.core.logging_config import patch_uvicorn_logging
patch_uvicorn_logging()

from app.services.sync_service import sync_service


@app.on_event("startup")
async def startup_event():
    PROGRESS_TOTAL = 10 + _MODULE_TOTAL
    OFFSET = _MODULE_TOTAL

    loop = asyncio.get_running_loop()
    sync_service.set_event_loop(loop)
    _report_progress(OFFSET + 1, PROGRESS_TOTAL, "正在准备运行环境...")

    from app.services.remote_drive_service import remote_drive_service
    from app.services.settings_service import settings_service
    settings_service.update({"remote_drive_enabled": False})
    _report_progress(OFFSET + 2, PROGRESS_TOTAL, "正在初始化远程驱动器服务...")

    from app.services.performance_collector import performance_collector
    asyncio.create_task(performance_collector.initialize_all())
    _report_progress(OFFSET + 3, PROGRESS_TOTAL, "正在初始化性能采集器...")

    from app.core.git_sync_scheduler import git_sync_scheduler
    await git_sync_scheduler.start()
    _report_progress(OFFSET + 4, PROGRESS_TOTAL, "正在启动Git同步调度器...")

    from app.services.audit_log_service import audit_log_service
    await audit_log_service.initialize()
    _report_progress(OFFSET + 5, PROGRESS_TOTAL, "正在初始化审计日志服务...")

    from app.services.task_scheduler_service import task_scheduler_service
    task_scheduler_service.start()
    _report_progress(OFFSET + 6, PROGRESS_TOTAL, "正在启动任务调度器...")

    from app.services.event_bus_service import event_bus_service
    event_bus_service.start()
    _report_progress(OFFSET + 7, PROGRESS_TOTAL, "正在启动事件总线...")

    from app.services.log_storage_service import log_storage_service
    from app.services.log_alert_service import log_alert_service
    await log_storage_service.initialize()
    _report_progress(OFFSET + 8, PROGRESS_TOTAL, "正在初始化日志存储服务...")
    await log_alert_service.initialize()
    _report_progress(OFFSET + 9, PROGRESS_TOTAL, "正在初始化日志告警服务...")

    from app.services.health_probe_service import health_probe_service
    await health_probe_service.initialize()
    _report_progress(OFFSET + 10, PROGRESS_TOTAL, "正在初始化健康探针服务...")

    _mark_startup_done()


@app.on_event("shutdown")
async def shutdown_event():
    from app.services.webssh_service import webssh_service
    webssh_service.shutdown()

    from app.services.remote_drive_service import remote_drive_service
    remote_drive_service.stop()

    from app.services.performance_collector import performance_collector
    await performance_collector.shutdown()

    from app.services.health_probe_service import health_probe_service
    await health_probe_service.shutdown()
