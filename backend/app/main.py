import asyncio
import logging
import time
from collections import defaultdict
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

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

# --- Rate limiter: try slowapi, fallback to in-memory ---
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded

    limiter = Limiter(key_func=get_remote_address)
    _RATE_LIMIT_BACKEND = "slowapi"
except Exception:
    limiter = None
    _RATE_LIMIT_BACKEND = "memory"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

app = FastAPI(
    title="OpsV-Kits API",
    description="OpsV-Kits Backend API",
    version="0.1.0",
)

# Attach slowapi limiter state if available
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

if STATIC_DIR.is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=str(STATIC_DIR / "assets")),
        name="frontend-assets",
    )


# --- In-memory rate limiter fallback ---
_MEMORY_LIMITS: dict[str, list[float]] = defaultdict(list)
_SENSITIVE_PATHS = {
    "/api/ssh-accounts/test-connection",
    "/api/ssh-accounts/workplace/init",
    "/api/webssh/test",
    "/api/webssh/connect",
    "/api/webssh/command",
    "/api/security/network/ping",
    "/api/security/network/traceroute",
    "/api/security/network/portscan",
    "/api/system/reboot",
    "/api/system/shutdown",
    "/api/system/reload/network",
    "/api/system/reload/ssh",
    "/api/build",
    "/api/docker",
    "/api/db-toolkit",
    "/api/cron-backup",
    "/api/git",
    "/api/workflow",
    "/api/scheduler",
    "/api/event-trigger",
}


def _is_sensitive(path: str) -> bool:
    p = path.lower()
    for sensitive in _SENSITIVE_PATHS:
        if p.startswith(sensitive.lower()):
            return True
    return False


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if _RATE_LIMIT_BACKEND == "slowapi" or not _is_sensitive(request.url.path):
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    window = 60
    max_requests = 30
    key = f"{client_ip}:{request.url.path}"

    _MEMORY_LIMITS[key] = [t for t in _MEMORY_LIMITS[key] if now - t < window]
    if len(_MEMORY_LIMITS[key]) >= max_requests:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Too many requests."},
        )
    _MEMORY_LIMITS[key].append(now)
    return await call_next(request)


@app.middleware("http")
async def spa_fallback_middleware(request, call_next):
    response = await call_next(request)
    if response.status_code == 404 and STATIC_DIR.is_dir():
        path = request.url.path
        if not path.startswith("/api") and not path.startswith("/assets"):
            index = STATIC_DIR / "index.html"
            if index.is_file():
                return FileResponse(str(index))
    return response


@app.on_event("startup")
async def startup_event():
    loop = asyncio.get_running_loop()
    sync_service.set_event_loop(loop)

    from app.services.remote_drive_service import remote_drive_service
    from app.services.settings_service import settings_service
    settings_service.update({"remote_drive_enabled": False})

    from app.services.performance_collector import performance_collector
    asyncio.create_task(performance_collector.initialize_all())

    from app.core.git_sync_scheduler import git_sync_scheduler
    await git_sync_scheduler.start()

    from app.services.audit_log_service import audit_log_service
    await audit_log_service.initialize()
    await audit_log_service.start_queue_consumer()

    from app.services.task_scheduler_service import task_scheduler_service
    task_scheduler_service.start()

    from app.services.event_bus_service import event_bus_service
    await event_bus_service.start_watchers()

    from app.services.log_storage_service import log_storage_service
    from app.services.log_alert_service import log_alert_service
    await log_storage_service.initialize()
    await log_alert_service.initialize()

    from app.services.health_probe_service import health_probe_service
    await health_probe_service.initialize()


@app.on_event("shutdown")
async def shutdown_event():
    from app.services.webssh_service import webssh_service
    webssh_service.shutdown()

    from app.services.remote_drive_service import remote_drive_service
    remote_drive_service.stop()

    from app.services.performance_collector import performance_collector
    await performance_collector.shutdown()

    from app.core.git_sync_scheduler import git_sync_scheduler
    await git_sync_scheduler.stop()

    from app.services.audit_log_service import audit_log_service
    await audit_log_service.stop_queue_consumer()
    await audit_log_service.shutdown()

    from app.services.task_scheduler_service import task_scheduler_service
    task_scheduler_service.shutdown()

    from app.services.log_collector_service import log_collector_service
    from app.services.log_alert_service import log_alert_service
    from app.services.log_storage_service import log_storage_service
    await log_collector_service.shutdown()
    await log_alert_service.shutdown()
    await log_storage_service.shutdown()

    from app.services.health_probe_service import health_probe_service
    await health_probe_service.shutdown()
