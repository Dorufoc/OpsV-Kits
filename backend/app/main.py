import asyncio
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

from app.api.routes import build
from app.api.routes import docker
from app.api.routes import file_manager
from app.api.routes import health
from app.api.routes import project
from app.api.routes import remote_drive
from app.api.routes import settings as settings_route
from app.api.routes import ssh_account
from app.api.routes import sync as sync_route
from app.api.routes import system
from app.api.routes import webssh
from app.services.sync_service import sync_service

app = FastAPI(
    title="OpsV-Kits API",
    description="OpsV-Kits Backend API",
    version="0.1.0",
)

origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(ssh_account.router, prefix="/api", tags=["ssh-accounts"])
app.include_router(build.router, prefix="/api", tags=["build"])
app.include_router(build.build_router, prefix="/api", tags=["build"])
app.include_router(sync_route.router, prefix="/api", tags=["sync"])
app.include_router(file_manager.router, prefix="/api", tags=["file-manager"])
app.include_router(settings_route.router, prefix="/api", tags=["settings"])
app.include_router(docker.router, prefix="/api", tags=["docker"])
app.include_router(system.router, prefix="/api", tags=["system"])
app.include_router(project.router, prefix="/api", tags=["projects"])
app.include_router(webssh.router, prefix="/api", tags=["webssh"])
app.include_router(remote_drive.router, prefix="/api", tags=["remote-drive"])


STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if STATIC_DIR.is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=str(STATIC_DIR / "assets")),
        name="frontend-assets",
    )


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
    enabled = settings_service.get("remote_drive_enabled", True)
    if enabled:
        port = settings_service.get("remote_drive_port", 8081)
        remote_drive_service.start(port=port)


@app.on_event("shutdown")
async def shutdown_event():
    from app.services.webssh_service import webssh_service
    webssh_service.shutdown()

    from app.services.remote_drive_service import remote_drive_service
    remote_drive_service.stop()
