from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from typing import Any

from fastapi import WebSocket

from app.models.db_toolkit import MySqlConnectionParams, RedisConnectionParams
from app.services.ssh_account_service import ssh_account_service

logger = logging.getLogger(__name__)


def _safe_ws_send(websocket: WebSocket, data: dict[str, Any]) -> None:
    try:
        asyncio.get_event_loop().run_until_complete(websocket.send_json(data))
    except RuntimeError:
        try:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(
                    asyncio.run,
                    websocket.send_json(data),
                )
                future.result(timeout=5)
        except Exception:
            pass
    except Exception:
        pass


class DbToolkitWebSocketHandler:
    async def _handle_cli_direct(
        self,
        websocket: WebSocket,
        account_alias: str,
        container_id: str,
        connection: MySqlConnectionParams | RedisConnectionParams,
        db_type: str,
    ) -> None:
        if db_type == "mysql":
            conn = connection
            parts = [f"mysql -h {conn.host} -P {conn.port} -u {conn.user}"]
            if conn.password:
                parts.append(f"-p {conn.password}")
            if conn.database:
                parts.append(conn.database)
            cli_command = " ".join(parts)
            safe_parts = [f"mysql -h {conn.host} -P {conn.port} -u {conn.user}"]
            if conn.password:
                safe_parts.append("-p ***")
            if conn.database:
                safe_parts.append(conn.database)
            safe_command = " ".join(safe_parts)
        else:
            conn = connection
            parts = [f"redis-cli -h {conn.host} -p {conn.port}"]
            if conn.password:
                parts.append(f"-a {conn.password}")
            parts.append(f"-n {conn.db}")
            cli_command = " ".join(parts)
            safe_parts = [f"redis-cli -h {conn.host} -p {conn.port}"]
            if conn.password:
                safe_parts.append("-a ***")
            safe_parts.append(f"-n {conn.db}")
            safe_command = " ".join(safe_parts)

        await self._handle_cli_after_accept(
            websocket, account_alias, container_id, cli_command, safe_command
        )

    async def _handle_cli_after_accept(
        self,
        websocket: WebSocket,
        account_alias: str,
        container_id: str,
        cli_command: str,
        safe_command: str,
    ) -> None:
        try:
            account = ssh_account_service.get_account(account_alias)
            if account is None:
                await websocket.send_json({
                    "type": "error",
                    "message": f"SSH 账户 '{account_alias}' 不存在",
                })
                await websocket.close()
                return
        except Exception as e:
            await websocket.send_json({"type": "error", "message": str(e)})
            await websocket.close()
            return

        conn = None
        chan = None
        stop_event = threading.Event()

        try:
            conn = ssh_account_service.pool.get_connection(account)
            transport = conn.manager._transport
            if transport is None:
                raise RuntimeError("SSH 传输通道未建立")

            chan = transport.open_session()
            chan.get_pty(term="xterm-256color", width=80, height=24)
            docker_cmd = f"docker exec -i {container_id} {cli_command}"
            chan.exec_command(docker_cmd)

            logger.info(
                "DB CLI 终端连接 [account=%s, container=%s, cmd=%s]",
                account_alias, container_id, safe_command,
            )

            await websocket.send_json({
                "type": "info",
                "encoding": "utf-8",
            })

            def _read_output():
                try:
                    while not stop_event.is_set():
                        if chan.recv_ready():
                            raw = chan.recv(4096)
                            if not raw:
                                break
                            text = raw.decode("utf-8", errors="replace")
                            _safe_ws_send(websocket, {
                                "type": "data",
                                "content": text,
                            })
                        elif chan.exit_status_ready():
                            remaining = b""
                            while chan.recv_ready():
                                remaining += chan.recv(4096)
                            if remaining:
                                text = remaining.decode("utf-8", errors="replace")
                                _safe_ws_send(websocket, {
                                    "type": "data",
                                    "content": text,
                                })
                            break
                        else:
                            time.sleep(0.02)
                except Exception as e:
                    _safe_ws_send(websocket, {
                        "type": "error",
                        "message": str(e),
                    })
                finally:
                    _safe_ws_send(websocket, {"type": "disconnected"})

            reader_thread = threading.Thread(target=_read_output, daemon=True)
            reader_thread.start()

            try:
                while True:
                    raw = await websocket.receive_text()
                    msg = json.loads(raw)
                    msg_type = msg.get("type")

                    if msg_type == "input":
                        data = msg.get("data", "")
                        if chan and not chan.exit_status_ready():
                            chan.send(data)
                    elif msg_type == "resize":
                        w = msg.get("width", 80)
                        h = msg.get("height", 24)
                        if chan:
                            try:
                                chan.resize_pty(width=w, height=h)
                            except Exception:
                                pass
                    elif msg_type == "ping":
                        await websocket.send_json({"type": "pong"})
                    elif msg_type == "disconnect":
                        break
            except Exception:
                pass
            finally:
                stop_event.set()
                if chan:
                    try:
                        chan.close()
                    except Exception:
                        pass

        except Exception as e:
            logger.error(
                "DB CLI 终端异常 [account=%s, container=%s]: %s",
                account_alias, container_id, e,
            )
            try:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                })
            except Exception:
                pass
        finally:
            stop_event.set()
            if chan:
                try:
                    chan.close()
                except Exception:
                    pass
            if conn is not None:
                ssh_account_service.pool.release_connection(conn)

    async def _handle_cli(
        self,
        websocket: WebSocket,
        account_alias: str,
        container_id: str,
        cli_command: str,
        safe_command: str,
    ) -> None:
        await websocket.accept()

        try:
            account = ssh_account_service.get_account(account_alias)
            if account is None:
                await websocket.send_json({
                    "type": "error",
                    "message": f"SSH 账户 '{account_alias}' 不存在",
                })
                await websocket.close()
                return
        except Exception as e:
            await websocket.send_json({"type": "error", "message": str(e)})
            await websocket.close()
            return

        conn = None
        chan = None
        stop_event = threading.Event()

        try:
            conn = ssh_account_service.pool.get_connection(account)
            transport = conn.manager._transport
            if transport is None:
                raise RuntimeError("SSH 传输通道未建立")

            chan = transport.open_session()
            chan.get_pty(term="xterm-256color", width=80, height=24)
            docker_cmd = f"docker exec -i {container_id} {cli_command}"
            chan.exec_command(docker_cmd)

            logger.info(
                "DB CLI 终端连接 [account=%s, container=%s, cmd=%s]",
                account_alias, container_id, safe_command,
            )

            await websocket.send_json({
                "type": "info",
                "encoding": "utf-8",
            })

            def _read_output():
                try:
                    while not stop_event.is_set():
                        if chan.recv_ready():
                            raw = chan.recv(4096)
                            if not raw:
                                break
                            text = raw.decode("utf-8", errors="replace")
                            _safe_ws_send(websocket, {
                                "type": "data",
                                "content": text,
                            })
                        elif chan.exit_status_ready():
                            remaining = b""
                            while chan.recv_ready():
                                remaining += chan.recv(4096)
                            if remaining:
                                text = remaining.decode("utf-8", errors="replace")
                                _safe_ws_send(websocket, {
                                    "type": "data",
                                    "content": text,
                                })
                            break
                        else:
                            time.sleep(0.02)
                except Exception as e:
                    _safe_ws_send(websocket, {
                        "type": "error",
                        "message": str(e),
                    })
                finally:
                    _safe_ws_send(websocket, {"type": "disconnected"})

            reader_thread = threading.Thread(target=_read_output, daemon=True)
            reader_thread.start()

            try:
                while True:
                    raw = await websocket.receive_text()
                    msg = json.loads(raw)
                    msg_type = msg.get("type")

                    if msg_type == "input":
                        data = msg.get("data", "")
                        if chan and not chan.exit_status_ready():
                            chan.send(data)
                    elif msg_type == "resize":
                        w = msg.get("width", 80)
                        h = msg.get("height", 24)
                        if chan:
                            try:
                                chan.resize_pty(width=w, height=h)
                            except Exception:
                                pass
                    elif msg_type == "ping":
                        await websocket.send_json({"type": "pong"})
                    elif msg_type == "disconnect":
                        break
            except Exception:
                pass
            finally:
                stop_event.set()
                if chan:
                    try:
                        chan.close()
                    except Exception:
                        pass

        except Exception as e:
            logger.error(
                "DB CLI 终端异常 [account=%s, container=%s]: %s",
                account_alias, container_id, e,
            )
            try:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                })
            except Exception:
                pass
        finally:
            stop_event.set()
            if chan:
                try:
                    chan.close()
                except Exception:
                    pass
            if conn is not None:
                ssh_account_service.pool.release_connection(conn)

    async def handle_mysql_cli(
        self,
        websocket: WebSocket,
        account_alias: str,
        container_id: str,
        connection: MySqlConnectionParams,
    ) -> None:
        parts = [f"mysql -h {connection.host} -P {connection.port} -u {connection.user}"]
        if connection.password:
            parts.append(f"-p {connection.password}")
        if connection.database:
            parts.append(connection.database)
        cli_command = " ".join(parts)

        safe_parts = [f"mysql -h {connection.host} -P {connection.port} -u {connection.user}"]
        if connection.password:
            safe_parts.append("-p ***")
        if connection.database:
            safe_parts.append(connection.database)
        safe_command = " ".join(safe_parts)

        await self._handle_cli(
            websocket, account_alias, container_id, cli_command, safe_command
        )

    async def handle_redis_cli(
        self,
        websocket: WebSocket,
        account_alias: str,
        container_id: str,
        connection: RedisConnectionParams,
    ) -> None:
        parts = [f"redis-cli -h {connection.host} -p {connection.port}"]
        if connection.password:
            parts.append(f"-a {connection.password}")
        parts.append(f"-n {connection.db}")
        cli_command = " ".join(parts)

        safe_parts = [f"redis-cli -h {connection.host} -p {connection.port}"]
        if connection.password:
            safe_parts.append("-a ***")
        safe_parts.append(f"-n {connection.db}")
        safe_command = " ".join(safe_parts)

        await self._handle_cli(
            websocket, account_alias, container_id, cli_command, safe_command
        )


db_toolkit_ws_handler = DbToolkitWebSocketHandler()
