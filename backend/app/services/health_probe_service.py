from __future__ import annotations

import asyncio
import json
import logging
import re
import sqlite3
import subprocess
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiohttp
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.models.health_probe import (
    HttpProbeConfig,
    ProbeOverview,
    ProbeResult,
    ProbeStatistics,
    ProbeStatus,
    ProbeTarget,
    ProbeTargetCreate,
    ProbeTargetUpdate,
    ProbeType,
)

_PERSIST_DIR = Path.home() / ".opsv-kits"
_DB_PATH = _PERSIST_DIR / "health_probe.db"
_MAX_LOGS_PER_TARGET = 10000

_logger = logging.getLogger(__name__)


class HealthProbeService:
    def __init__(self):
        self._lock = threading.RLock()
        self._scheduler: Optional[AsyncIOScheduler] = None
        self._targets: dict[str, ProbeTarget] = {}
        self._init_db()

    def _init_db(self) -> None:
        _PERSIST_DIR.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(_DB_PATH)) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS probe_targets (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    probe_type TEXT NOT NULL,
                    target TEXT NOT NULL,
                    interval_seconds INTEGER DEFAULT 60,
                    timeout_seconds INTEGER DEFAULT 10,
                    enabled INTEGER DEFAULT 1,
                    failure_threshold INTEGER DEFAULT 3,
                    recovery_threshold INTEGER DEFAULT 2,
                    http_config TEXT,
                    tags TEXT,
                    current_status TEXT DEFAULT 'unknown',
                    consecutive_failures INTEGER DEFAULT 0,
                    consecutive_successes INTEGER DEFAULT 0,
                    last_probe_time TEXT,
                    last_success_time TEXT,
                    last_failure_time TEXT,
                    created_at TEXT,
                    updated_at TEXT
                );

                CREATE TABLE IF NOT EXISTS probe_results (
                    id TEXT PRIMARY KEY,
                    target_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    probe_type TEXT NOT NULL,
                    target TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    response_time_ms REAL,
                    status_code INTEGER,
                    error_message TEXT,
                    content_matched INTEGER,
                    FOREIGN KEY (target_id) REFERENCES probe_targets(id)
                );

                CREATE INDEX IF NOT EXISTS idx_probe_results_target_id ON probe_results(target_id);
                CREATE INDEX IF NOT EXISTS idx_probe_results_timestamp ON probe_results(timestamp);
                """
            )

    def _load_targets_from_db(self) -> None:
        with sqlite3.connect(str(_DB_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM probe_targets").fetchall()
        for row in rows:
            http_config = None
            if row["http_config"]:
                try:
                    http_config = HttpProbeConfig(**json.loads(row["http_config"]))
                except Exception:
                    pass
            tags = []
            if row["tags"]:
                try:
                    tags = json.loads(row["tags"])
                except Exception:
                    pass
            target = ProbeTarget(
                id=row["id"],
                name=row["name"],
                probe_type=ProbeType(row["probe_type"]),
                target=row["target"],
                interval_seconds=row["interval_seconds"],
                timeout_seconds=row["timeout_seconds"],
                enabled=bool(row["enabled"]),
                failure_threshold=row["failure_threshold"],
                recovery_threshold=row["recovery_threshold"],
                http_config=http_config,
                tags=tags,
                current_status=ProbeStatus(row["current_status"]),
                consecutive_failures=row["consecutive_failures"],
                consecutive_successes=row["consecutive_successes"],
                last_probe_time=datetime.fromisoformat(row["last_probe_time"]) if row["last_probe_time"] else None,
                last_success_time=datetime.fromisoformat(row["last_success_time"]) if row["last_success_time"] else None,
                last_failure_time=datetime.fromisoformat(row["last_failure_time"]) if row["last_failure_time"] else None,
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
                updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.now(),
            )
            self._targets[target.id] = target

    def _save_target_to_db(self, target: ProbeTarget) -> None:
        with sqlite3.connect(str(_DB_PATH)) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO probe_targets
                (id, name, probe_type, target, interval_seconds, timeout_seconds, enabled,
                 failure_threshold, recovery_threshold, http_config, tags, current_status,
                 consecutive_failures, consecutive_successes, last_probe_time, last_success_time,
                 last_failure_time, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    target.id,
                    target.name,
                    target.probe_type.value,
                    target.target,
                    target.interval_seconds,
                    target.timeout_seconds,
                    int(target.enabled),
                    target.failure_threshold,
                    target.recovery_threshold,
                    target.http_config.model_dump_json() if target.http_config else None,
                    json.dumps(target.tags) if target.tags else None,
                    target.current_status.value,
                    target.consecutive_failures,
                    target.consecutive_successes,
                    target.last_probe_time.isoformat() if target.last_probe_time else None,
                    target.last_success_time.isoformat() if target.last_success_time else None,
                    target.last_failure_time.isoformat() if target.last_failure_time else None,
                    target.created_at.isoformat() if target.created_at else None,
                    target.updated_at.isoformat() if target.updated_at else None,
                ),
            )

    def _delete_target_from_db(self, target_id: str) -> None:
        with sqlite3.connect(str(_DB_PATH)) as conn:
            conn.execute("DELETE FROM probe_results WHERE target_id = ?", (target_id,))
            conn.execute("DELETE FROM probe_targets WHERE id = ?", (target_id,))

    def _save_result_to_db(self, result: ProbeResult) -> None:
        with sqlite3.connect(str(_DB_PATH)) as conn:
            conn.execute(
                """
                INSERT INTO probe_results
                (id, target_id, timestamp, probe_type, target, success, response_time_ms,
                 status_code, error_message, content_matched)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.id,
                    result.target_id,
                    result.timestamp.isoformat(),
                    result.probe_type.value,
                    result.target,
                    int(result.success),
                    result.response_time_ms,
                    result.status_code,
                    result.error_message,
                    int(result.content_matched) if result.content_matched is not None else None,
                ),
            )
            count = conn.execute(
                "SELECT COUNT(*) FROM probe_results WHERE target_id = ?",
                (result.target_id,),
            ).fetchone()[0]
            if count > _MAX_LOGS_PER_TARGET:
                excess = count - _MAX_LOGS_PER_TARGET
                conn.execute(
                    """
                    DELETE FROM probe_results WHERE id IN (
                        SELECT id FROM probe_results
                        WHERE target_id = ?
                        ORDER BY timestamp ASC
                        LIMIT ?
                    )
                    """,
                    (result.target_id, excess),
                )

    def create_target(self, data: ProbeTargetCreate) -> ProbeTarget:
        http_cfg = None
        if data.http_config:
            http_cfg = HttpProbeConfig(**data.http_config.model_dump())
        target = ProbeTarget(
            id=str(uuid.uuid4()),
            name=data.name,
            probe_type=data.probe_type,
            target=data.target,
            interval_seconds=data.interval_seconds,
            timeout_seconds=data.timeout_seconds,
            enabled=data.enabled,
            failure_threshold=data.failure_threshold,
            recovery_threshold=data.recovery_threshold,
            http_config=http_cfg,
            tags=data.tags,
        )
        with self._lock:
            self._targets[target.id] = target
        self._save_target_to_db(target)
        if target.enabled and self._scheduler and self._scheduler.running:
            self._add_probe_job(target)
        return target

    def get_target(self, target_id: str) -> Optional[ProbeTarget]:
        return self._targets.get(target_id)

    def list_targets(self, tag: Optional[str] = None, probe_type: Optional[ProbeType] = None) -> list[ProbeTarget]:
        targets = list(self._targets.values())
        if tag:
            targets = [t for t in targets if tag in t.tags]
        if probe_type:
            targets = [t for t in targets if t.probe_type == probe_type]
        return targets

    def update_target(self, target_id: str, data: ProbeTargetUpdate) -> Optional[ProbeTarget]:
        target = self._targets.get(target_id)
        if target is None:
            return None
        was_enabled = target.enabled
        old_interval = target.interval_seconds
        update_data = data.model_dump(exclude_unset=True)
        if "http_config" in update_data and update_data["http_config"] is not None:
            update_data["http_config"] = HttpProbeConfig(**update_data["http_config"])
        for key, value in update_data.items():
            setattr(target, key, value)
        target.updated_at = datetime.now()
        self._save_target_to_db(target)
        if self._scheduler and self._scheduler.running:
            need_reschedule = (
                (not was_enabled and target.enabled)
                or (was_enabled and not target.enabled)
                or (target.enabled and old_interval != target.interval_seconds)
            )
            if need_reschedule:
                self._remove_probe_job(target_id)
                if target.enabled:
                    self._add_probe_job(target)
        return target

    def delete_target(self, target_id: str) -> bool:
        target = self._targets.pop(target_id, None)
        if target is None:
            return False
        self._remove_probe_job(target_id)
        self._delete_target_from_db(target_id)
        return True

    async def _execute_http_probe(self, target: ProbeTarget) -> ProbeResult:
        config = target.http_config or HttpProbeConfig()
        start_time = time.monotonic()
        status_code = None
        content_matched = None
        error_message = None
        success = False
        try:
            timeout = aiohttp.ClientTimeout(total=target.timeout_seconds)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                kwargs: dict = {
                    "method": config.method,
                    "allow_redirects": config.follow_redirects,
                }
                if config.headers:
                    kwargs["headers"] = config.headers
                async with session.request(target.target, **kwargs) as resp:
                    status_code = resp.status
                    if status_code in config.expected_status_codes:
                        if config.content_match:
                            body = await resp.text()
                            try:
                                matched = bool(re.search(config.content_match, body))
                            except re.error:
                                matched = False
                            content_matched = matched
                            if matched:
                                success = True
                            else:
                                success = False
                                error_message = "Content does not match pattern"
                        else:
                            success = True
                    else:
                        success = False
                        error_message = f"Status code {status_code} not in expected {config.expected_status_codes}"
        except asyncio.TimeoutError:
            error_message = f"Request timed out after {target.timeout_seconds}s"
        except aiohttp.ClientError as e:
            error_message = str(e)[:200]
        except Exception as e:
            error_message = str(e)[:200]
        elapsed_ms = (time.monotonic() - start_time) * 1000
        return ProbeResult(
            id=str(uuid.uuid4()),
            target_id=target.id,
            timestamp=datetime.now(),
            probe_type=ProbeType.HTTP,
            target=target.target,
            success=success,
            response_time_ms=round(elapsed_ms, 2),
            status_code=status_code,
            error_message=error_message,
            content_matched=content_matched,
        )

    async def _execute_tcp_probe(self, target: ProbeTarget) -> ProbeResult:
        start_time = time.monotonic()
        error_message = None
        success = False
        try:
            parts = target.target.rsplit(":", 1)
            if len(parts) != 2:
                raise ValueError(f"Invalid TCP target format: {target.target}, expected host:port")
            host, port_str = parts
            port = int(port_str)
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=target.timeout_seconds,
            )
            writer.close()
            await writer.wait_closed()
            success = True
        except asyncio.TimeoutError:
            error_message = f"Connection timed out after {target.timeout_seconds}s"
        except ConnectionRefusedError:
            error_message = "Connection refused"
        except OSError as e:
            error_message = str(e)[:200]
        except ValueError as e:
            error_message = str(e)
        except Exception as e:
            error_message = str(e)[:200]
        elapsed_ms = (time.monotonic() - start_time) * 1000
        return ProbeResult(
            id=str(uuid.uuid4()),
            target_id=target.id,
            timestamp=datetime.now(),
            probe_type=ProbeType.TCP,
            target=target.target,
            success=success,
            response_time_ms=round(elapsed_ms, 2),
            error_message=error_message,
        )

    async def _execute_icmp_probe(self, target: ProbeTarget) -> ProbeResult:
        start_time = time.monotonic()
        error_message = None
        success = False
        response_time_ms = None
        try:
            cmd = ["ping", "-n", "1", "-w", str(target.timeout_seconds * 1000), target.target]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=target.timeout_seconds + 5,
            )
            output = stdout.decode("gbk", errors="replace") + stderr.decode("gbk", errors="replace")
            if proc.returncode == 0:
                success = True
                time_match = re.search(r"时间[=<](\d+)ms", output)
                if time_match:
                    response_time_ms = float(time_match.group(1))
                else:
                    time_match_en = re.search(r"time[=<](\d+)ms", output, re.IGNORECASE)
                    if time_match_en:
                        response_time_ms = float(time_match_en.group(1))
            else:
                if "请求超时" in output or "timed out" in output.lower() or "Request timed out" in output:
                    error_message = "Request timed out"
                elif "目标主机不可达" in output or "Destination host unreachable" in output:
                    error_message = "Destination host unreachable"
                elif "找不到主机" in output or "could not find host" in output.lower():
                    error_message = "Host not found"
                else:
                    error_message = output.strip()[:200] if output.strip() else "Ping failed"
        except asyncio.TimeoutError:
            error_message = f"Ping command timed out after {target.timeout_seconds + 5}s"
        except FileNotFoundError:
            error_message = "ping command not found"
        except Exception as e:
            error_message = str(e)[:200]
        if response_time_ms is None:
            elapsed_ms = (time.monotonic() - start_time) * 1000
            response_time_ms = round(elapsed_ms, 2) if success else None
        return ProbeResult(
            id=str(uuid.uuid4()),
            target_id=target.id,
            timestamp=datetime.now(),
            probe_type=ProbeType.ICMP,
            target=target.target,
            success=success,
            response_time_ms=response_time_ms,
            error_message=error_message,
        )

    async def _execute_probe(self, target_id: str) -> None:
        target = self._targets.get(target_id)
        if target is None or not target.enabled:
            return
        try:
            if target.probe_type == ProbeType.HTTP:
                result = await self._execute_http_probe(target)
            elif target.probe_type == ProbeType.TCP:
                result = await self._execute_tcp_probe(target)
            elif target.probe_type == ProbeType.ICMP:
                result = await self._execute_icmp_probe(target)
            else:
                return
        except Exception as e:
            _logger.error(f"Probe execution error for target {target_id}: {e}")
            result = ProbeResult(
                id=str(uuid.uuid4()),
                target_id=target_id,
                timestamp=datetime.now(),
                probe_type=target.probe_type,
                target=target.target,
                success=False,
                error_message=f"Internal error: {str(e)[:200]}",
            )
        self._update_target_status(target, result)
        self._save_result_to_db(result)

    def _update_target_status(self, target: ProbeTarget, result: ProbeResult) -> None:
        now = datetime.now()
        target.last_probe_time = now
        if result.success:
            target.consecutive_failures = 0
            target.consecutive_successes += 1
            target.last_success_time = now
            if target.current_status == ProbeStatus.UNAVAILABLE and target.consecutive_successes >= target.recovery_threshold:
                target.current_status = ProbeStatus.AVAILABLE
                _logger.info(f"Target '{target.name}' recovered to available")
            elif target.current_status == ProbeStatus.UNKNOWN:
                target.current_status = ProbeStatus.AVAILABLE
        else:
            target.consecutive_successes = 0
            target.consecutive_failures += 1
            target.last_failure_time = now
            if target.current_status == ProbeStatus.AVAILABLE and target.consecutive_failures >= target.failure_threshold:
                target.current_status = ProbeStatus.UNAVAILABLE
                _logger.warning(f"Target '{target.name}' became unavailable")
            elif target.current_status == ProbeStatus.UNKNOWN:
                if target.consecutive_failures >= target.failure_threshold:
                    target.current_status = ProbeStatus.UNAVAILABLE
        target.updated_at = now
        self._save_target_to_db(target)

    async def probe_now(self, target_id: str) -> Optional[ProbeResult]:
        target = self._targets.get(target_id)
        if target is None:
            return None
        try:
            if target.probe_type == ProbeType.HTTP:
                result = await self._execute_http_probe(target)
            elif target.probe_type == ProbeType.TCP:
                result = await self._execute_tcp_probe(target)
            elif target.probe_type == ProbeType.ICMP:
                result = await self._execute_icmp_probe(target)
            else:
                return None
        except Exception as e:
            result = ProbeResult(
                id=str(uuid.uuid4()),
                target_id=target_id,
                timestamp=datetime.now(),
                probe_type=target.probe_type,
                target=target.target,
                success=False,
                error_message=f"Internal error: {str(e)[:200]}",
            )
        self._update_target_status(target, result)
        self._save_result_to_db(result)
        return result

    def _add_probe_job(self, target: ProbeTarget) -> None:
        if self._scheduler is None or not self._scheduler.running:
            return
        job_id = f"health_probe_{target.id}"
        try:
            self._scheduler.remove_job(job_id)
        except Exception:
            pass
        self._scheduler.add_job(
            self._execute_probe,
            "interval",
            seconds=target.interval_seconds,
            id=job_id,
            args=[target.id],
            replace_existing=True,
        )
        _logger.info(f"Scheduled probe job for target '{target.name}' every {target.interval_seconds}s")

    def _remove_probe_job(self, target_id: str) -> None:
        if self._scheduler is None:
            return
        job_id = f"health_probe_{target_id}"
        try:
            self._scheduler.remove_job(job_id)
        except Exception:
            pass

    def query_probe_logs(
        self,
        target_id: str,
        limit: int = 50,
        offset: int = 0,
        time_start: Optional[datetime] = None,
        time_end: Optional[datetime] = None,
        success: Optional[bool] = None,
    ) -> tuple[list[ProbeResult], int]:
        conditions = ["target_id = ?"]
        params: list = [target_id]
        if time_start:
            conditions.append("timestamp >= ?")
            params.append(time_start.isoformat())
        if time_end:
            conditions.append("timestamp <= ?")
            params.append(time_end.isoformat())
        if success is not None:
            conditions.append("success = ?")
            params.append(int(success))
        where_clause = " AND ".join(conditions)
        with sqlite3.connect(str(_DB_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            total = conn.execute(
                f"SELECT COUNT(*) FROM probe_results WHERE {where_clause}",
                params,
            ).fetchone()[0]
            rows = conn.execute(
                f"SELECT * FROM probe_results WHERE {where_clause} ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                params + [limit, offset],
            ).fetchall()
        results = []
        for row in rows:
            results.append(
                ProbeResult(
                    id=row["id"],
                    target_id=row["target_id"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    probe_type=ProbeType(row["probe_type"]),
                    target=row["target"],
                    success=bool(row["success"]),
                    response_time_ms=row["response_time_ms"],
                    status_code=row["status_code"],
                    error_message=row["error_message"],
                    content_matched=bool(row["content_matched"]) if row["content_matched"] is not None else None,
                )
            )
        return results, total

    def calculate_statistics(
        self,
        target_id: str,
        time_start: Optional[datetime] = None,
        time_end: Optional[datetime] = None,
    ) -> Optional[ProbeStatistics]:
        target = self._targets.get(target_id)
        if target is None:
            return None
        conditions = ["target_id = ?"]
        params: list = [target_id]
        if time_start:
            conditions.append("timestamp >= ?")
            params.append(time_start.isoformat())
        if time_end:
            conditions.append("timestamp <= ?")
            params.append(time_end.isoformat())
        where_clause = " AND ".join(conditions)
        with sqlite3.connect(str(_DB_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                f"""
                SELECT
                    COUNT(*) as total_probes,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failure_count,
                    AVG(CASE WHEN success = 1 AND response_time_ms IS NOT NULL THEN response_time_ms END) as avg_rt,
                    MAX(CASE WHEN response_time_ms IS NOT NULL THEN response_time_ms END) as max_rt,
                    MIN(CASE WHEN response_time_ms IS NOT NULL THEN response_time_ms END) as min_rt
                FROM probe_results
                WHERE {where_clause}
                """,
                params,
            ).fetchone()
        total = row["total_probes"]
        success_count = row["success_count"] or 0
        failure_count = row["failure_count"] or 0
        uptime_percent = round(success_count / total * 100, 2) if total > 0 else 0.0
        return ProbeStatistics(
            target_id=target_id,
            uptime_percent=uptime_percent,
            avg_response_time_ms=round(row["avg_rt"], 2) if row["avg_rt"] is not None else None,
            max_response_time_ms=row["max_rt"],
            min_response_time_ms=row["min_rt"],
            total_probes=total,
            success_count=success_count,
            failure_count=failure_count,
            current_status=target.current_status,
            last_probe_time=target.last_probe_time,
            last_success_time=target.last_success_time,
            last_failure_time=target.last_failure_time,
        )

    def get_overview(self) -> ProbeOverview:
        targets = list(self._targets.values())
        available = sum(1 for t in targets if t.current_status == ProbeStatus.AVAILABLE)
        unavailable = sum(1 for t in targets if t.current_status == ProbeStatus.UNAVAILABLE)
        unknown = sum(1 for t in targets if t.current_status == ProbeStatus.UNKNOWN)
        return ProbeOverview(
            total_targets=len(targets),
            available_count=available,
            unavailable_count=unavailable,
            unknown_count=unknown,
            targets=targets,
        )

    async def initialize(self) -> None:
        self._load_targets_from_db()
        self._scheduler = AsyncIOScheduler()
        self._scheduler.start()
        for target in self._targets.values():
            if target.enabled:
                self._add_probe_job(target)
        _logger.info(f"HealthProbeService initialized with {len(self._targets)} targets")

    async def shutdown(self) -> None:
        if self._scheduler:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None
        _logger.info("HealthProbeService shutdown")


health_probe_service = HealthProbeService()
