from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect

from app.models.webssh_session import (
    WebSSHCommandRequest,
    WebSSHConnectRequest,
    WebSSHDisconnectRequest,
    WebSSHResizeRequest,
)
from app.services.webssh_service import webssh_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webssh", tags=["webssh"])

_MAX_HISTORY = 500


@router.get("/sessions")
async def list_sessions(
    group: Optional[str] = Query(None, description="按分组筛选"),
):
    sessions = webssh_service.list_sessions(group=group)
    return {
        "sessions": [s.model_dump() for s in sessions],
        "count": len(sessions),
        "groups": webssh_service.list_groups(),
        "stats": webssh_service.get_session_count(),
    }


@router.post("/test")
async def test_connection(data: WebSSHConnectRequest):
    try:
        logger.info(f"test connection: account_alias={data.account_alias}, host={data.host}, username={data.username}")
        session = webssh_service.create_session(data)
        webssh_service.close_session(session.session_id)
        logger.info(f"test connection success: session_id={session.session_id}")
        return {"success": True, "message": "连接测试成功"}
    except ValueError as e:
        logger.warning(f"test connection validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        logger.warning(f"test connection runtime error: {e}")
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.exception(f"test connection unexpected error")
        raise HTTPException(status_code=500, detail=f"连接测试失败: {e}")


@router.post("/connect")
async def connect_ssh(data: WebSSHConnectRequest):
    try:
        logger.info(f"connect: account_alias={data.account_alias}, host={data.host}, username={data.username}")
        session = webssh_service.create_session(data)
        logger.info(f"connect success: session_id={session.session_id}, encoding={session.session_id}")
        return {"success": True, "session": session.model_dump()}
    except ValueError as e:
        logger.warning(f"connect validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        logger.warning(f"connect runtime error: {e}")
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.exception(f"connect unexpected error")
        raise HTTPException(status_code=500, detail=f"连接失败: {e}")


@router.post("/disconnect")
async def disconnect_ssh(data: WebSSHDisconnectRequest):
    logger.info(f"disconnect: session_id={data.session_id}")
    session = webssh_service.get_session(data.session_id)
    if session is None:
        raise HTTPException(
            status_code=404, detail=f"会话 '{data.session_id}' 不存在"
        )
    webssh_service.close_session(data.session_id)
    return {"success": True, "session_id": data.session_id}


@router.post("/resize")
async def resize_terminal(data: WebSSHResizeRequest):
    try:
        webssh_service.resize_session(data.session_id, data.width, data.height)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"调整终端大小失败: {e}"
        )


@router.post("/command")
async def send_command(data: WebSSHCommandRequest):
    try:
        encoded = data.command.encode("utf-8")
        webssh_service.write_to_session(data.session_id, encoded)
        _record_history(data.session_id, data.command)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"发送命令失败: {e}")


@router.get("/sessions/history")
async def get_session_history():
    return {
        "sessions": webssh_service.list_session_history(),
        "count": len(webssh_service.list_session_history()),
    }


@router.delete("/sessions/history/{session_id}")
async def delete_session_history(session_id: str):
    webssh_service.delete_session_history(session_id)
    return {"success": True}


@router.get("/history")
async def get_command_history(
    session_id: Optional[str] = Query(
        None, description="按会话ID筛选"
    ),
    limit: int = Query(50, description="返回条数上限"),
):
    if session_id:
        records = _history_store.get(session_id, [])[-limit:]
    else:
        all_records = []
        for records in _history_store.values():
            all_records.extend(records)
        records = sorted(
            all_records, key=lambda x: x["timestamp"], reverse=True
        )[:limit]
    return {"history": records, "count": len(records)}


@router.websocket("/ws/{session_id}")
async def webssh_websocket(
    websocket: WebSocket, session_id: str
):
    await websocket.accept()
    logger.info(f"[ws:{session_id}] WebSocket accepted")

    session = webssh_service.get_session(session_id)
    if session is None:
        logger.warning(f"[ws:{session_id}] session not found")
        await websocket.send_json(
            {
                "type": "error",
                "message": f"会话 '{session_id}' 不存在",
            }
        )
        await websocket.close()
        return

    entry = webssh_service._get_entry(session_id)
    if entry is None or entry.adapter is None:
        logger.warning(f"[ws:{session_id}] adapter not available")
        await websocket.send_json(
            {"type": "error", "message": "会话处理器不可用"}
        )
        await websocket.close()
        return

    adapter = entry.adapter
    encoding = adapter.encoding
    output_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=2048)
    current_loop = asyncio.get_event_loop()
    logger.info(f"[ws:{session_id}] starting WebSocket bridge, encoding={encoding}")

    await websocket.send_json(
        {
            "type": "info",
            "encoding": encoding,
            "session_id": session_id,
        }
    )

    def _ssh_callback(data: bytes) -> None:
        try:
            asyncio.run_coroutine_threadsafe(
                output_queue.put(data), current_loop
            )
        except Exception as e:
            logger.error(f"[ws:{session_id}] ssh_callback error: {e}")

    adapter.start_reader(_ssh_callback)

    async def ssh_reader():
        logger.info(f"[ws:{session_id}] ssh_reader task started")
        try:
            while True:
                data = await output_queue.get()
                if data == b"__SSH_DISCONNECTED__":
                    logger.info(f"[ws:{session_id}] received disconnect signal")
                    await websocket.send_json(
                        {"type": "disconnected"}
                    )
                    break
                try:
                    text = data.decode(encoding, errors="replace")
                    logger.debug(f"[ws:{session_id}] sending {len(text)} chars to WS")
                    await websocket.send_text(
                        json.dumps(
                            {"type": "data", "content": text}
                        )
                    )
                except Exception as e:
                    logger.error(f"[ws:{session_id}] ssh_reader decode/send error: {e}")
        except Exception as e:
            logger.error(f"[ws:{session_id}] ssh_reader exception: {e}")

    async def ws_writer():
        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                msg_type = msg.get("type", "")

                if msg_type == "input":
                    input_data = msg.get("data", "")
                    if isinstance(input_data, str):
                        encoded = input_data.encode(
                            encoding, errors="replace"
                        )
                        adapter.write(encoded)
                        command = input_data.strip()
                        if (
                            command
                            and not command.startswith("\x1b")
                        ):
                            _record_history(session_id, command)

                elif msg_type == "resize":
                    width = msg.get("width", 80)
                    height = msg.get("height", 24)
                    adapter.resize_pty(width, height)

                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})

                elif msg_type == "disconnect":
                    break

        except WebSocketDisconnect:
            pass
        except Exception:
            pass

    try:
        reader_task = asyncio.create_task(ssh_reader())
        writer_task = asyncio.create_task(ws_writer())
        done, pending = await asyncio.wait(
            [reader_task, writer_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
    except Exception:
        pass
    finally:
        webssh_service.close_session(session_id)
        try:
            await websocket.close()
        except Exception:
            pass


_history_store: dict[str, list[dict]] = {}


def _record_history(session_id: str, command: str) -> None:
    from datetime import datetime

    if session_id not in _history_store:
        _history_store[session_id] = []
    _history_store[session_id].append(
        {
            "session_id": session_id,
            "command": command,
            "timestamp": datetime.now().isoformat(),
        }
    )
    if len(_history_store[session_id]) > _MAX_HISTORY:
        _history_store[session_id] = _history_store[session_id][
            -_MAX_HISTORY:
        ]
