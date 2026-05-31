from __future__ import annotations

import asyncio
import time
import uuid
from pathlib import Path
from typing import Optional

from app.services.log_alert_service import log_alert_service
from app.services.log_parser_service import log_parser_service
from app.services.log_storage_service import log_storage_service
from app.services.ssh_account_service import ssh_account_service


class _UdpLogProtocol(asyncio.DatagramProtocol):
    def __init__(self, collector: LogCollectorService):
        self._collector = collector
        self.transport: Optional[asyncio.DatagramTransport] = None

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:
        self.transport = transport

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        try:
            text = data.decode("utf-8", errors="replace").strip()
            if not text:
                return
            loop = asyncio.get_event_loop()
            loop.call_soon_threadsafe(
                lambda: asyncio.ensure_future(
                    self._collector._process_log_line(
                        text, "udp_server", {"host": addr[0]}
                    )
                )
            )
        except Exception:
            pass

    def error_received(self, exc: Exception) -> None:
        pass

    def connection_lost(self, exc: Optional[Exception]) -> None:
        pass


class LogCollectorService:
    def __init__(self):
        self._sources: dict[str, dict] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._tcp_server: Optional[asyncio.Server] = None
        self._udp_transport: Optional[asyncio.DatagramTransport] = None
        self._subscribers: list = []
        self._file_offsets: dict[str, tuple[int, int]] = {}
        self._watchdog_observer = None
        self._watchdog_handlers: dict[str, object] = {}

    def add_source(self, source_config: dict) -> str:
        source_id = uuid.uuid4().hex[:8]
        source = {
            "id": source_id,
            "type": source_config.get("type", "system"),
            "alias": source_config.get("alias"),
            "path": source_config.get("path"),
            "container": source_config.get("container"),
            "host": source_config.get("host", "0.0.0.0"),
            "port": source_config.get("port", 9514),
            "enabled": source_config.get("enabled", True),
            "labels": source_config.get("labels") or {},
            "status": "stopped",
        }
        self._sources[source_id] = source
        return source_id

    async def delete_source(self, source_id: str) -> None:
        if source_id not in self._sources:
            raise ValueError(f"采集源 '{source_id}' 不存在")
        await self.stop_source(source_id)
        self._sources.pop(source_id, None)
        self._file_offsets.pop(source_id, None)
        handler = self._watchdog_handlers.pop(source_id, None)
        if handler is not None and self._watchdog_observer is not None:
            try:
                self._watchdog_observer.remove_handler_for_path(
                    str(Path(self._sources.get(source_id, {}).get("path", "")).parent)
                )
            except Exception:
                pass

    def get_sources(self) -> list[dict]:
        return list(self._sources.values())

    def get_source(self, source_id: str) -> dict | None:
        return self._sources.get(source_id)

    def update_source(self, source_id: str, updates: dict) -> None:
        source = self._sources.get(source_id)
        if source is None:
            raise ValueError(f"采集源 '{source_id}' 不存在")
        for key, value in updates.items():
            if key in ("type", "alias", "path", "container", "host", "port", "enabled", "labels"):
                source[key] = value

    def subscribe(self, ws, filters: dict = None) -> None:
        self._subscribers.append({"ws": ws, "filters": filters or {}})

    def unsubscribe(self, ws) -> None:
        self._subscribers = [s for s in self._subscribers if s["ws"] != ws]

    def update_filters(self, ws, filters: dict) -> None:
        for sub in self._subscribers:
            if sub["ws"] == ws:
                sub["filters"] = filters
                break

    async def _notify_subscribers(self, log_entry: dict) -> None:
        dead = []
        for sub in self._subscribers:
            ws = sub["ws"]
            filters = sub.get("filters", {})
            if filters:
                match = True
                if filters.get("level") and log_entry.get("level") != filters["level"]:
                    match = False
                if filters.get("source") and log_entry.get("source") != filters["source"]:
                    match = False
                if filters.get("keyword") and filters["keyword"].lower() not in log_entry.get("content", "").lower():
                    match = False
                if not match:
                    continue
            try:
                await ws.send_json(log_entry)
            except Exception:
                dead.append(sub)
        for d in dead:
            if d in self._subscribers:
                self._subscribers.remove(d)

    async def _process_log_line(
        self, line: str, source_id: str, extra: dict = None
    ) -> None:
        if not line.strip():
            return
        parsed = log_parser_service.parse(line)
        source = self._sources.get(source_id, {})
        labels = dict(source.get("labels", {}))
        extra = extra or {}
        if "labels" in extra:
            labels.update(extra.pop("labels"))

        log_entry = {
            "timestamp": parsed.get("timestamp") or time.time(),
            "source": source_id,
            "level": parsed.get("level", "INFO"),
            "content": parsed.get("message", line),
            "structured_data": parsed.get("fields"),
            "container_name": extra.get("container_name"),
            "container_id": extra.get("container_id"),
            "host": extra.get("host"),
            "labels": labels if labels else None,
        }

        await log_storage_service.write_log(log_entry)
        await log_alert_service.check_alert(log_entry)
        await self._notify_subscribers(log_entry)

    def _read_channel_data(self, chan) -> bytes | None:
        try:
            if chan.recv_ready():
                return chan.recv(4096)
            return b""
        except Exception:
            return None

    async def start_system_log_collection(
        self,
        source_id: str,
        alias: str,
        log_path: str,
        labels: dict = None,
    ) -> None:
        source = self._sources.get(source_id)
        if source is None:
            return
        source["status"] = "running"

        retry_count = 0
        max_retries = 3

        while source.get("status") == "running" and retry_count < max_retries:
            try:
                account = ssh_account_service.get_account(alias)
                if account is None:
                    source["status"] = "error"
                    return

                conn = ssh_account_service.pool.get_connection(account)
                try:
                    transport = conn.manager.client.get_transport()
                    if transport is None:
                        raise RuntimeError("SSH transport is None")

                    chan = transport.open_session()
                    chan.exec_command(f"tail -F {log_path}")

                    buffer = ""
                    loop = asyncio.get_event_loop()

                    while source.get("status") == "running":
                        data = await loop.run_in_executor(
                            None, self._read_channel_data, chan
                        )
                        if data is None:
                            break
                        if data:
                            encoding = conn.manager.encoding or "utf-8"
                            text = data.decode(encoding, errors="replace")
                            buffer += text
                            while "\n" in buffer:
                                line, buffer = buffer.split("\n", 1)
                                extra = dict(labels) if labels else {}
                                await self._process_log_line(line, source_id, extra)
                            retry_count = 0
                        elif chan.exit_status_ready():
                            break
                        else:
                            await asyncio.sleep(0.1)

                    try:
                        chan.close()
                    except Exception:
                        pass
                finally:
                    ssh_account_service.pool.release_connection(conn)

                if source.get("status") != "running":
                    return

                retry_count += 1
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                source["status"] = "stopped"
                return
            except Exception:
                retry_count += 1
                if retry_count >= max_retries:
                    source["status"] = "error"
                    return
                await asyncio.sleep(5)

        if source.get("status") == "running":
            source["status"] = "error"

    async def start_docker_log_collection(
        self,
        source_id: str,
        alias: str,
        container: str,
        labels: dict = None,
    ) -> None:
        source = self._sources.get(source_id)
        if source is None:
            return
        source["status"] = "running"

        retry_count = 0
        max_retries = 3

        while source.get("status") == "running" and retry_count < max_retries:
            try:
                account = ssh_account_service.get_account(alias)
                if account is None:
                    source["status"] = "error"
                    return

                conn = ssh_account_service.pool.get_connection(account)
                try:
                    transport = conn.manager.client.get_transport()
                    if transport is None:
                        raise RuntimeError("SSH transport is None")

                    chan = transport.open_session()
                    chan.exec_command(f"docker logs -f {container}")

                    buffer = ""
                    loop = asyncio.get_event_loop()

                    while source.get("status") == "running":
                        data = await loop.run_in_executor(
                            None, self._read_channel_data, chan
                        )
                        if data is None:
                            break
                        if data:
                            encoding = conn.manager.encoding or "utf-8"
                            text = data.decode(encoding, errors="replace")
                            buffer += text
                            while "\n" in buffer:
                                line, buffer = buffer.split("\n", 1)
                                extra = dict(labels) if labels else {}
                                extra["container_name"] = container
                                extra["container_id"] = container
                                await self._process_log_line(line, source_id, extra)
                            retry_count = 0
                        elif chan.exit_status_ready():
                            break
                        else:
                            await asyncio.sleep(0.1)

                    try:
                        chan.close()
                    except Exception:
                        pass
                finally:
                    ssh_account_service.pool.release_connection(conn)

                if source.get("status") != "running":
                    return

                retry_count += 1
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                source["status"] = "stopped"
                return
            except Exception:
                retry_count += 1
                if retry_count >= max_retries:
                    source["status"] = "error"
                    return
                await asyncio.sleep(5)

        if source.get("status") == "running":
            source["status"] = "error"

    async def start_tcp_server(
        self, host: str = "0.0.0.0", port: int = 9514
    ) -> None:
        async def handle_client(
            reader: asyncio.StreamReader, writer: asyncio.StreamWriter
        ):
            addr = writer.get_extra_info("peername")
            client_host = addr[0] if addr else "unknown"
            try:
                while True:
                    data = await reader.readline()
                    if not data:
                        break
                    line = data.decode("utf-8", errors="replace").strip()
                    if line:
                        await self._process_log_line(
                            line, "tcp_server", {"host": client_host}
                        )
            except Exception:
                pass
            finally:
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:
                    pass

        self._tcp_server = await asyncio.start_server(
            handle_client, host, port
        )

    async def start_udp_server(
        self, host: str = "0.0.0.0", port: int = 9514
    ) -> None:
        loop = asyncio.get_event_loop()
        transport, _ = await loop.create_datagram_endpoint(
            lambda: _UdpLogProtocol(self),
            local_addr=(host, port),
        )
        self._udp_transport = transport

    async def start_file_watcher(
        self,
        source_id: str,
        file_path: str,
        labels: dict = None,
    ) -> None:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer

        source = self._sources.get(source_id)
        if source is None:
            return
        source["status"] = "running"

        path = Path(file_path)
        if not path.exists():
            source["status"] = "error"
            return

        file_stat = path.stat()
        self._file_offsets[source_id] = (file_stat.st_ino, file_stat.st_size)

        loop = asyncio.get_event_loop()
        service = self

        class _FileHandler(FileSystemEventHandler):
            def on_modified(self, event):
                if Path(event.src_path) != path:
                    return
                try:
                    if not path.exists():
                        return
                    current_stat = path.stat()
                    stored = service._file_offsets.get(source_id)
                    if stored is None:
                        service._file_offsets[source_id] = (
                            current_stat.st_ino,
                            0,
                        )
                        stored = (current_stat.st_ino, 0)

                    stored_inode, stored_offset = stored
                    if current_stat.st_ino != stored_inode:
                        offset = 0
                    else:
                        offset = stored_offset

                    if current_stat.st_size < offset:
                        offset = 0

                    with open(path, "rb") as f:
                        f.seek(offset)
                        new_data = f.read()

                    new_offset = offset + len(new_data)
                    service._file_offsets[source_id] = (
                        current_stat.st_ino,
                        new_offset,
                    )

                    new_content = new_data.decode("utf-8", errors="replace")
                    for line in new_content.splitlines():
                        if line.strip():
                            extra = dict(labels) if labels else {}
                            loop.call_soon_threadsafe(
                                lambda l=line, e=extra: asyncio.ensure_future(
                                    service._process_log_line(l, source_id, e)
                                )
                            )
                except Exception:
                    pass

        if self._watchdog_observer is None:
            self._watchdog_observer = Observer()
            self._watchdog_observer.start()

        handler = _FileHandler()
        self._watchdog_handlers[source_id] = handler
        self._watchdog_observer.schedule(
            handler, str(path.parent), recursive=False
        )

        try:
            while source.get("status") == "running":
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            self._watchdog_handlers.pop(source_id, None)
            self._file_offsets.pop(source_id, None)
            if not self._watchdog_handlers and self._watchdog_observer is not None:
                self._watchdog_observer.stop()
                self._watchdog_observer.join(timeout=5)
                self._watchdog_observer = None
            source["status"] = "stopped"

    async def start_source(self, source_id: str) -> None:
        source = self._sources.get(source_id)
        if source is None:
            return
        if source_id in self._tasks:
            return

        source_type = source.get("type")
        if source_type == "system":
            task = asyncio.create_task(
                self.start_system_log_collection(
                    source_id,
                    source["alias"],
                    source["path"],
                    source.get("labels"),
                )
            )
        elif source_type == "docker":
            task = asyncio.create_task(
                self.start_docker_log_collection(
                    source_id,
                    source["alias"],
                    source["container"],
                    source.get("labels"),
                )
            )
        elif source_type == "tcp":
            task = asyncio.create_task(
                self.start_tcp_server(
                    source.get("host", "0.0.0.0"),
                    source.get("port", 9514),
                )
            )
        elif source_type == "udp":
            task = asyncio.create_task(
                self.start_udp_server(
                    source.get("host", "0.0.0.0"),
                    source.get("port", 9514),
                )
            )
        elif source_type == "file":
            task = asyncio.create_task(
                self.start_file_watcher(
                    source_id,
                    source["path"],
                    source.get("labels"),
                )
            )
        else:
            return

        self._tasks[source_id] = task

    async def stop_source(self, source_id: str) -> None:
        source = self._sources.get(source_id)
        if source is not None:
            source["status"] = "stopped"

        task = self._tasks.pop(source_id, None)
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def start_all(self) -> None:
        for source_id, source in self._sources.items():
            if source.get("enabled", True):
                await self.start_source(source_id)

    async def stop_all(self) -> None:
        for source_id in list(self._tasks.keys()):
            await self.stop_source(source_id)

    async def shutdown(self) -> None:
        await self.stop_all()

        if self._tcp_server is not None:
            self._tcp_server.close()
            await self._tcp_server.wait_closed()
            self._tcp_server = None

        if self._udp_transport is not None:
            self._udp_transport.close()
            self._udp_transport = None

        if self._watchdog_observer is not None:
            self._watchdog_observer.stop()
            self._watchdog_observer.join(timeout=5)
            self._watchdog_observer = None

        self._watchdog_handlers.clear()
        self._file_offsets.clear()
        self._subscribers.clear()


log_collector_service = LogCollectorService()
