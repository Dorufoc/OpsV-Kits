from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Callable, Optional

from app.core.dedicated_ssh_session import DedicatedSSHSession
from app.models.ssh_account import SSHAccount
from app.services.ssh_account_service import ssh_account_service

logger = logging.getLogger(__name__)

_COLLECTION_INTERVAL = 2.0
_HISTORY_MAXLEN = 3600


class PerformanceCollector:
    def __init__(self):
        self._history: dict[str, deque[dict]] = defaultdict(
            lambda: deque(maxlen=_HISTORY_MAXLEN)
        )
        self._sessions: dict[str, DedicatedSSHSession] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._subscribers: dict[str, list[Callable[[dict], None]]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._prev_samples: dict[str, dict] = {}
        self._running = False

    # ── 生命周期 ──────────────────────────────────────────────────────

    async def initialize_all(self) -> None:
        async with self._lock:
            self._running = True
        accounts = ssh_account_service.list_accounts()
        # 并行启动所有账户的采集，避免串行阻塞启动流程
        if accounts:
            await asyncio.gather(
                *(self.start_collecting(account.alias) for account in accounts),
                return_exceptions=True,
            )

    async def shutdown(self) -> None:
        async with self._lock:
            self._running = False
        aliases = list(self._tasks.keys())
        for alias in aliases:
            await self.stop_collecting(alias)

    async def on_account_created(self, alias: str) -> None:
        await self.start_collecting(alias)

    async def on_account_deleted(self, alias: str) -> None:
        await self.stop_collecting(alias)

    # ── 采集控制 ──────────────────────────────────────────────────────

    async def start_collecting(self, alias: str) -> None:
        async with self._lock:
            if alias in self._tasks:
                return
            account = ssh_account_service.get_account(alias)
            if account is None:
                logger.warning(f"[PerformanceCollector] 账户 '{alias}' 不存在，无法启动采集")
                return
            session = DedicatedSSHSession(account)
            self._sessions[alias] = session
            connected = await session.connect(timeout=15.0)
            if not connected:
                logger.warning(f"[PerformanceCollector] 账户 '{alias}' SSH 连接失败，仍启动后台采集任务")
            self._tasks[alias] = asyncio.create_task(
                self._collection_loop(alias), name=f"perf-collect-{alias}"
            )
            logger.info(f"[PerformanceCollector] 已启动 '{alias}' 的性能采集")

    async def stop_collecting(self, alias: str) -> None:
        async with self._lock:
            task = self._tasks.pop(alias, None)
            session = self._sessions.pop(alias, None)
            self._prev_samples.pop(alias, None)
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        if session is not None:
            session.close()
        logger.info(f"[PerformanceCollector] 已停止 '{alias}' 的性能采集")

    # ── 订阅/发布 ─────────────────────────────────────────────────────

    def subscribe(self, alias: str, callback: Callable[[dict], None]) -> None:
        subs = self._subscribers[alias]
        if callback not in subs:
            subs.append(callback)

    def unsubscribe(self, alias: str, callback: Callable[[dict], None]) -> None:
        subs = self._subscribers.get(alias, [])
        if callback in subs:
            subs.remove(callback)

    def _notify_subscribers(self, alias: str, snapshot: dict) -> None:
        for callback in list(self._subscribers.get(alias, [])):
            try:
                callback(snapshot)
            except Exception:
                logger.exception(f"[PerformanceCollector] 通知订阅者失败: {alias}")

    # ── 历史访问 ──────────────────────────────────────────────────────

    def get_latest_snapshot(self, alias: str) -> Optional[dict]:
        hist = self._history.get(alias)
        if not hist:
            return None
        return hist[-1]

    def get_history(self, alias: str, seconds: int = 300) -> list[dict]:
        hist = self._history.get(alias)
        if not hist:
            return []
        cutoff = time.time() - seconds
        return [entry for entry in hist if entry.get("timestamp", 0) >= cutoff]

    # ── 采集循环 ──────────────────────────────────────────────────────

    async def _collection_loop(self, alias: str) -> None:
        while True:
            loop_start = time.monotonic()
            try:
                await asyncio.wait_for(self._collect_once(alias), timeout=_COLLECTION_INTERVAL)
            except asyncio.TimeoutError:
                logger.warning(f"[PerformanceCollector] 采集超时: {alias}")
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(f"[PerformanceCollector] 采集异常: {alias}")

            elapsed = time.monotonic() - loop_start
            sleep_time = max(0.0, _COLLECTION_INTERVAL - elapsed)
            await asyncio.sleep(sleep_time)

    async def _collect_once(self, alias: str) -> None:
        session = self._sessions.get(alias)
        if session is None:
            return

        if not session.connected:
            # SSH 断开时触发重连，而不是静默跳过
            if not session._closed:
                logger.debug(f"[PerformanceCollector] SSH 未连接，尝试重连: {alias}")
                await session.connect(timeout=10.0)
            if not session.connected:
                return

        now = time.time()
        snapshot = {
            "timestamp": now,
            "alias": alias,
            "datetime": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
        }

        # 并行批量采集基础指标
        results = await self._gather_basic_metrics(session)
        snapshot.update(results)

        # 计算速率类指标（需要前后两次采样）
        prev = self._prev_samples.get(alias)
        rate_metrics = self._compute_rate_metrics(prev, snapshot)
        snapshot.update(rate_metrics)

        # 存储当前采样供下次计算速率
        self._prev_samples[alias] = snapshot.copy()

        # 保存历史并通知订阅者
        self._history[alias].append(snapshot)
        self._notify_subscribers(alias, snapshot)

    async def _gather_basic_metrics(self, session: DedicatedSSHSession) -> dict:
        commands = {
            "cpu": "cat /proc/stat | head -1 && nproc",
            "cpu_per_core": "cat /proc/stat | grep '^cpu[0-9]'",
            "memory": "cat /proc/meminfo",
            "disk_stats": "df -k -x tmpfs -x devtmpfs -x overlay 2>/dev/null || df -k",
            "disk_io": "cat /proc/diskstats",
            "network": "cat /proc/net/dev",
            "loadavg": "cat /proc/loadavg",
            "processes": "ps -eo pid,ppid,pcpu,pmem,comm,args --sort=-pcpu | head -21",
            "connections": "ss -tan 2>/dev/null | wc -l && ss -tun 2>/dev/null | wc -l",
            "uptime": "cat /proc/uptime",
            "docker": "docker ps --format '{{json .}}' 2>/dev/null || echo '[]'",
            "temperatures": "cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null || echo ''",
        }

        coros = {
            key: session.exec_command(cmd, timeout=5.0)
            for key, cmd in commands.items()
        }

        gathered = {}
        for key, coro in coros.items():
            try:
                gathered[key] = await coro
            except Exception as e:
                logger.warning(f"[PerformanceCollector] 命令 '{key}' 执行异常: {e}")
                gathered[key] = (-1, "", str(e))

        return {
            "cpu": self._parse_cpu(gathered.get("cpu")),
            "cpu_per_core": self._parse_cpu_per_core(gathered.get("cpu_per_core")),
            "memory": self._parse_memory(gathered.get("memory")),
            "disk": self._parse_disk(gathered.get("disk_stats")),
            "disk_io_raw": self._parse_disk_io_raw(gathered.get("disk_io")),
            "network_raw": self._parse_network_raw(gathered.get("network")),
            "loadavg": self._parse_loadavg(gathered.get("loadavg")),
            "processes": self._parse_processes(gathered.get("processes")),
            "connections": self._parse_connections(gathered.get("connections")),
            "uptime": self._parse_uptime(gathered.get("uptime")),
            "docker": self._parse_docker(gathered.get("docker")),
            "temperatures": self._parse_temperatures(gathered.get("temperatures")),
        }

    def _compute_rate_metrics(self, prev: Optional[dict], curr: dict) -> dict:
        if prev is None:
            return {
                "cpu_percent": None,
                "cpu_per_core_percent": {},
                "disk_io_rate": {},
                "network_rate": {},
            }

        dt = curr.get("timestamp", 0) - prev.get("timestamp", 0)
        if dt <= 0:
            return {
                "cpu_percent": None,
                "cpu_per_core_percent": {},
                "disk_io_rate": {},
                "network_rate": {},
            }

        # CPU 总使用率
        cpu_percent = None
        prev_cpu = prev.get("cpu", {})
        curr_cpu = curr.get("cpu", {})
        if prev_cpu and curr_cpu:
            prev_total = prev_cpu.get("user", 0) + prev_cpu.get("nice", 0) + prev_cpu.get("system", 0) + prev_cpu.get("idle", 0) + prev_cpu.get("iowait", 0) + prev_cpu.get("irq", 0) + prev_cpu.get("softirq", 0) + prev_cpu.get("steal", 0)
            curr_total = curr_cpu.get("user", 0) + curr_cpu.get("nice", 0) + curr_cpu.get("system", 0) + curr_cpu.get("idle", 0) + curr_cpu.get("iowait", 0) + curr_cpu.get("irq", 0) + curr_cpu.get("softirq", 0) + curr_cpu.get("steal", 0)
            prev_idle = prev_cpu.get("idle", 0) + prev_cpu.get("iowait", 0)
            curr_idle = curr_cpu.get("idle", 0) + curr_cpu.get("iowait", 0)
            total_diff = curr_total - prev_total
            idle_diff = curr_idle - prev_idle
            if total_diff > 0:
                cpu_percent = round((1 - idle_diff / total_diff) * 100, 2)

        # CPU 每核使用率
        cpu_per_core_percent = {}
        prev_cores = prev.get("cpu_per_core", {})
        curr_cores = curr.get("cpu_per_core", {})
        for core_id, curr_core in curr_cores.items():
            prev_core = prev_cores.get(core_id)
            if prev_core:
                prev_total_c = prev_core.get("user", 0) + prev_core.get("nice", 0) + prev_core.get("system", 0) + prev_core.get("idle", 0) + prev_core.get("iowait", 0) + prev_core.get("irq", 0) + prev_core.get("softirq", 0) + prev_core.get("steal", 0)
                curr_total_c = curr_core.get("user", 0) + curr_core.get("nice", 0) + curr_core.get("system", 0) + curr_core.get("idle", 0) + curr_core.get("iowait", 0) + curr_core.get("irq", 0) + curr_core.get("softirq", 0) + curr_core.get("steal", 0)
                prev_idle_c = prev_core.get("idle", 0) + prev_core.get("iowait", 0)
                curr_idle_c = curr_core.get("idle", 0) + curr_core.get("iowait", 0)
                total_diff_c = curr_total_c - prev_total_c
                idle_diff_c = curr_idle_c - prev_idle_c
                if total_diff_c > 0:
                    cpu_per_core_percent[core_id] = round((1 - idle_diff_c / total_diff_c) * 100, 2)

        # 磁盘 IO 速率
        disk_io_rate = {}
        prev_disk = prev.get("disk_io_raw", {})
        curr_disk = curr.get("disk_io_raw", {})
        for dev, curr_dev in curr_disk.items():
            prev_dev = prev_disk.get(dev)
            if prev_dev:
                read_bytes_sec = round((curr_dev.get("read_bytes", 0) - prev_dev.get("read_bytes", 0)) / dt, 2)
                write_bytes_sec = round((curr_dev.get("write_bytes", 0) - prev_dev.get("write_bytes", 0)) / dt, 2)
                read_iops = round((curr_dev.get("reads", 0) - prev_dev.get("reads", 0)) / dt, 2)
                write_iops = round((curr_dev.get("writes", 0) - prev_dev.get("writes", 0)) / dt, 2)
                disk_io_rate[dev] = {
                    "read_bytes_sec": max(0, read_bytes_sec),
                    "write_bytes_sec": max(0, write_bytes_sec),
                    "read_iops": max(0, read_iops),
                    "write_iops": max(0, write_iops),
                }

        # 网络速率
        network_rate = {}
        prev_net = prev.get("network_raw", {})
        curr_net = curr.get("network_raw", {})
        for iface, curr_iface in curr_net.items():
            prev_iface = prev_net.get(iface)
            if prev_iface:
                rx_bytes_sec = round((curr_iface.get("rx_bytes", 0) - prev_iface.get("rx_bytes", 0)) / dt, 2)
                tx_bytes_sec = round((curr_iface.get("tx_bytes", 0) - prev_iface.get("tx_bytes", 0)) / dt, 2)
                rx_packets_sec = round((curr_iface.get("rx_packets", 0) - prev_iface.get("rx_packets", 0)) / dt, 2)
                tx_packets_sec = round((curr_iface.get("tx_packets", 0) - prev_iface.get("tx_packets", 0)) / dt, 2)
                network_rate[iface] = {
                    "rx_bytes_sec": max(0, rx_bytes_sec),
                    "tx_bytes_sec": max(0, tx_bytes_sec),
                    "rx_packets_sec": max(0, rx_packets_sec),
                    "tx_packets_sec": max(0, tx_packets_sec),
                }

        return {
            "cpu_percent": cpu_percent,
            "cpu_per_core_percent": cpu_per_core_percent,
            "disk_io_rate": disk_io_rate,
            "network_rate": network_rate,
        }

    # ── 解析器 ────────────────────────────────────────────────────────

    @staticmethod
    def _parse_cpu(result: Optional[tuple]) -> dict:
        if result is None:
            return {}
        code, stdout, _ = result
        if code != 0 or not stdout:
            return {}
        lines = stdout.strip().splitlines()
        if not lines:
            return {}
        parts = lines[0].split()
        if len(parts) < 5 or not parts[0].startswith("cpu"):
            return {}
        cpu_data = {
            "user": int(parts[1]),
            "nice": int(parts[2]),
            "system": int(parts[3]),
            "idle": int(parts[4]),
        }
        if len(parts) > 5:
            cpu_data["iowait"] = int(parts[5])
        if len(parts) > 6:
            cpu_data["irq"] = int(parts[6])
        if len(parts) > 7:
            cpu_data["softirq"] = int(parts[7])
        if len(parts) > 8:
            cpu_data["steal"] = int(parts[8])
        nproc = 1
        if len(lines) > 1:
            try:
                nproc = int(lines[1].strip())
            except ValueError:
                pass
        cpu_data["cores"] = nproc
        return cpu_data

    @staticmethod
    def _parse_cpu_per_core(result: Optional[tuple]) -> dict:
        if result is None:
            return {}
        code, stdout, _ = result
        if code != 0 or not stdout:
            return {}
        cores = {}
        for line in stdout.strip().splitlines():
            parts = line.split()
            if len(parts) < 5 or not parts[0].startswith("cpu"):
                continue
            core_id = parts[0]
            core_data = {
                "user": int(parts[1]),
                "nice": int(parts[2]),
                "system": int(parts[3]),
                "idle": int(parts[4]),
            }
            if len(parts) > 5:
                core_data["iowait"] = int(parts[5])
            if len(parts) > 6:
                core_data["irq"] = int(parts[6])
            if len(parts) > 7:
                core_data["softirq"] = int(parts[7])
            if len(parts) > 8:
                core_data["steal"] = int(parts[8])
            cores[core_id] = core_data
        return cores

    @staticmethod
    def _parse_memory(result: Optional[tuple]) -> dict:
        if result is None:
            return {}
        code, stdout, _ = result
        if code != 0 or not stdout:
            return {}
        meminfo = {}
        for line in stdout.strip().splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                try:
                    meminfo[key.strip()] = int(val.strip().split()[0]) * 1024
                except (ValueError, IndexError):
                    pass
        total = meminfo.get("MemTotal", 0)
        free = meminfo.get("MemFree", 0)
        available = meminfo.get("MemAvailable", 0)
        buffers = meminfo.get("Buffers", 0)
        cached = meminfo.get("Cached", 0)
        used = total - free - buffers - cached
        if available:
            used = total - available
        return {
            "total": total,
            "used": used,
            "free": free,
            "available": available,
            "buffers": buffers,
            "cached": cached,
            "percent": round(used / total * 100, 2) if total else 0,
        }

    @staticmethod
    def _parse_disk(result: Optional[tuple]) -> list[dict]:
        if result is None:
            return []
        code, stdout, _ = result
        if code != 0 or not stdout:
            return []
        disks = []
        lines = stdout.strip().splitlines()
        for line in lines[1:]:
            parts = line.split()
            if len(parts) < 6:
                continue
            try:
                disks.append({
                    "filesystem": parts[0],
                    "size": int(parts[1]) * 1024,
                    "used": int(parts[2]) * 1024,
                    "available": int(parts[3]) * 1024,
                    "percent": int(parts[4].replace("%", "")),
                    "mount": parts[5],
                })
            except (ValueError, IndexError):
                continue
        return disks

    @staticmethod
    def _parse_disk_io_raw(result: Optional[tuple]) -> dict:
        if result is None:
            return {}
        code, stdout, _ = result
        if code != 0 or not stdout:
            return {}
        ios = {}
        for line in stdout.strip().splitlines():
            parts = line.split()
            if len(parts) < 14:
                continue
            dev = parts[2]
            if dev.startswith("loop") or dev.startswith("ram"):
                continue
            try:
                ios[dev] = {
                    "reads": int(parts[3]),
                    "read_sectors": int(parts[5]),
                    "writes": int(parts[7]),
                    "write_sectors": int(parts[9]),
                    "read_bytes": int(parts[5]) * 512,
                    "write_bytes": int(parts[9]) * 512,
                }
            except (ValueError, IndexError):
                continue
        return ios

    @staticmethod
    def _parse_network_raw(result: Optional[tuple]) -> dict:
        if result is None:
            return {}
        code, stdout, _ = result
        if code != 0 or not stdout:
            return {}
        nets = {}
        for line in stdout.strip().splitlines()[2:]:
            parts = line.split()
            if len(parts) < 9:
                continue
            iface = parts[0].rstrip(":")
            if iface in ("lo",):
                continue
            try:
                nets[iface] = {
                    "rx_bytes": int(parts[1]),
                    "rx_packets": int(parts[2]),
                    "tx_bytes": int(parts[9]),
                    "tx_packets": int(parts[10]),
                }
            except (ValueError, IndexError):
                continue
        return nets

    @staticmethod
    def _parse_loadavg(result: Optional[tuple]) -> dict:
        if result is None:
            return {}
        code, stdout, _ = result
        if code != 0 or not stdout:
            return {}
        parts = stdout.strip().split()
        if len(parts) < 3:
            return {}
        try:
            return {
                "1min": float(parts[0]),
                "5min": float(parts[1]),
                "15min": float(parts[2]),
            }
        except ValueError:
            return {}

    @staticmethod
    def _parse_processes(result: Optional[tuple]) -> list[dict]:
        if result is None:
            return []
        code, stdout, _ = result
        if code != 0 or not stdout:
            return []
        processes = []
        lines = stdout.strip().splitlines()
        for line in lines[1:]:
            parts = line.split(None, 5)
            if len(parts) < 6:
                continue
            try:
                processes.append({
                    "pid": int(parts[0]),
                    "ppid": int(parts[1]),
                    "cpu": float(parts[2]),
                    "mem": float(parts[3]),
                    "comm": parts[4],
                    "args": parts[5],
                })
            except (ValueError, IndexError):
                continue
        return processes

    @staticmethod
    def _parse_connections(result: Optional[tuple]) -> dict:
        if result is None:
            return {}
        code, stdout, _ = result
        if code != 0 or not stdout:
            return {}
        lines = stdout.strip().splitlines()
        try:
            tcp = int(lines[0].strip()) if lines else 0
            total = int(lines[1].strip()) if len(lines) > 1 else tcp
            return {"tcp": tcp, "total": total}
        except (ValueError, IndexError):
            return {}

    @staticmethod
    def _parse_uptime(result: Optional[tuple]) -> dict:
        if result is None:
            return {}
        code, stdout, _ = result
        if code != 0 or not stdout:
            return {}
        parts = stdout.strip().split()
        if len(parts) < 2:
            return {}
        try:
            return {
                "uptime_seconds": float(parts[0]),
                "idle_seconds": float(parts[1]),
            }
        except ValueError:
            return {}

    @staticmethod
    def _parse_docker(result: Optional[tuple]) -> list[dict]:
        if result is None:
            return []
        code, stdout, _ = result
        if code != 0 or not stdout:
            return []
        containers = []
        for line in stdout.strip().splitlines():
            line = line.strip()
            if not line or line == "[]":
                continue
            try:
                containers.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return containers

    @staticmethod
    def _parse_temperatures(result: Optional[tuple]) -> list[dict]:
        if result is None:
            return []
        code, stdout, _ = result
        if code != 0 or not stdout:
            return []
        temps = []
        for idx, line in enumerate(stdout.strip().splitlines()):
            try:
                temp_millidegrees = int(line.strip())
                temps.append({
                    "zone": f"thermal_zone{idx}",
                    "temp_c": round(temp_millidegrees / 1000.0, 2),
                })
            except ValueError:
                continue
        return temps


performance_collector = PerformanceCollector()
