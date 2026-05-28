from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect

from app.services.monitor_service import monitor_service
from app.services.ssh_account_service import ssh_account_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitor", tags=["monitor"])


async def _ensure_account(alias: str) -> None:
    if not ssh_account_service.get_account(alias):
        raise HTTPException(404, f"SSH 账户 '{alias}' 不存在")


@router.get("/snapshot")
async def get_snapshot(alias: str = Query(..., description="SSH 账户别名")):
    try:
        return monitor_service.get_snapshot(alias)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取快照失败: {e}")


@router.get("/cpu")
async def get_cpu(alias: str = Query(...)):
    try:
        return monitor_service.get_cpu_percent(alias)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/cpu/cores")
async def get_cpu_cores(alias: str = Query(...)):
    try:
        return {"cores": monitor_service.get_cpu_per_core(alias)}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/memory")
async def get_memory(alias: str = Query(...)):
    try:
        return monitor_service.get_memory_stats(alias)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/disks")
async def get_disks(alias: str = Query(...)):
    try:
        return {"disks": monitor_service.get_disk_stats(alias)}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/disk-io")
async def get_disk_io(alias: str = Query(...)):
    try:
        return {"devices": monitor_service.get_disk_io_rate(alias)}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/network")
async def get_network(alias: str = Query(...)):
    try:
        return {"interfaces": monitor_service.get_network_rate(alias)}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/connections")
async def get_connections(alias: str = Query(...)):
    try:
        return monitor_service.get_network_connections(alias)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/load")
async def get_load(alias: str = Query(...)):
    try:
        return monitor_service.get_load_average(alias)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/processes")
async def get_processes(alias: str = Query(...), count: int = Query(10)):
    try:
        return {"processes": monitor_service.get_top_processes(alias, count)}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/docker")
async def get_docker_metrics(alias: str = Query(...)):
    try:
        return {"containers": monitor_service.get_docker_container_metrics(alias)}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/middleware")
async def get_middleware(alias: str = Query(...)):
    try:
        health = monitor_service.check_middleware_all(alias)
        metrics = monitor_service.get_middleware_metrics(alias)
        return {"health": health, "metrics": metrics}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/temperatures")
async def get_temperatures(alias: str = Query(...)):
    try:
        return {"temperatures": monitor_service.get_temperatures(alias)}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/history")
async def get_history(
    alias: str = Query(...),
    seconds: int = Query(300, description="回溯秒数"),
):
    try:
        return {"history": monitor_service.get_history(alias, seconds)}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/series/cpu")
async def get_cpu_series(alias: str = Query(...), points: int = Query(60)):
    try:
        return {"series": monitor_service.get_cpu_delta_series(alias, points)}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/series/memory")
async def get_memory_series(alias: str = Query(...), points: int = Query(60)):
    try:
        return {"series": monitor_service.get_memory_series(alias, points)}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


@router.websocket("/ws/stream")
async def monitor_websocket(websocket: WebSocket, alias: str = Query(...)):
    await websocket.accept()
    monitor_service.subscribe(alias, websocket)
    await monitor_service.start_streaming(alias, interval=2.0)
    logger.info(f"[monitor-ws] connected: alias={alias}")
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        logger.info(f"[monitor-ws] disconnected: alias={alias}")
    except Exception as e:
        logger.error(f"[monitor-ws] error: {e}")
    finally:
        monitor_service.unsubscribe(alias, websocket)