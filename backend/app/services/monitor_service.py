from __future__ import annotations

import asyncio
import json
import math
import time
from collections import defaultdict, deque
from typing import Any, Optional

from app.services.ssh_account_service import ssh_account_service
from app.services.performance_collector import performance_collector


class MonitorService:
    def __init__(self, collector: Optional[Any] = None):
        self._collector = collector
        self._history: dict[str, deque[dict[str, Any]]] = defaultdict(
            lambda: deque(maxlen=3600)
        )
        self._subscribers: dict[str, set] = defaultdict(set)
        self._tasks: dict[str, asyncio.Task] = {}
        self._cache: dict[str, Any] = {}
        self._cache_ttl: dict[str, float] = {}
        self._cpu_prev: dict[str, dict[str, Any]] = {}
        self._cpu_core_prev: dict[str, list[dict[str, Any]]] = {}
        self._disk_io_prev: dict[str, list[dict[str, Any]]] = {}
        self._network_prev: dict[str, list[dict[str, Any]]] = {}
        self._collector_callbacks: dict[str, Any] = {}

    def _conn(self, alias: str):
        account = ssh_account_service.get_account(alias)
        if account is None:
            raise ValueError(f"SSH 账户 '{alias}' 不存在")
        return ssh_account_service.pool.get_connection(account)

    def _exec(self, alias: str, cmd: str, timeout: float = 30.0) -> tuple[int, str, str]:
        conn = self._conn(alias)
        try:
            code, stdout, stderr = conn.manager.exec_command(cmd, timeout=timeout)
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            return code, stdout.strip(), stderr.strip()
        finally:
            ssh_account_service.pool.release_connection(conn)

    def _get_cached(self, alias: str, key: str, ttl: float, getter) -> Any:
        cache_key = f"{alias}:{key}"
        now = time.time()
        if cache_key in self._cache and self._cache_ttl.get(cache_key, 0) > now:
            return self._cache[cache_key]
        value = getter(alias)
        self._cache[cache_key] = value
        self._cache_ttl[cache_key] = now + ttl
        return value

    def _adapt_collector_snapshot(self, collector_data: dict[str, Any]) -> dict[str, Any]:
        """将 PerformanceCollector 的 snapshot 格式转换为 MonitorService 的 snapshot 格式。"""
        alias = collector_data.get("alias", "")
        timestamp = collector_data.get("timestamp", time.time())

        # CPU
        cpu_raw = collector_data.get("cpu", {})
        cpu_percent = collector_data.get("cpu_percent")
        cpu_adapted = {
            "usage_percent": cpu_percent if cpu_percent is not None else 0,
            "cores": cpu_raw.get("cores", 1),
            "user_percent": 0,
            "system_percent": 0,
            "iowait_percent": 0,
        }

        # Cores
        cores_adapted = []
        cpu_per_core_percent = collector_data.get("cpu_per_core_percent", {})
        for core_id, usage in cpu_per_core_percent.items():
            core_num = int(core_id.replace("cpu", "")) if isinstance(core_id, str) else core_id
            cores_adapted.append({"core": core_num, "usage_percent": usage})
        cores_adapted.sort(key=lambda x: x["core"])

        # Memory
        mem_raw = collector_data.get("memory", {})
        total = mem_raw.get("total", 0)
        used = mem_raw.get("used", 0)
        available = mem_raw.get("available", 0)
        memory_adapted = {
            "total": total,
            "used": used,
            "free": mem_raw.get("free", 0),
            "available": available,
            "usage_percent": mem_raw.get("percent", 0),
            "available_percent": round(available / total * 100, 1) if total > 0 else 0,
            "swap": None,
        }

        # Disks
        disks_raw = collector_data.get("disk", [])
        disks_adapted = []
        for d in disks_raw:
            disks_adapted.append({
                "filesystem": d.get("filesystem", ""),
                "total": d.get("size", 0),
                "used": d.get("used", 0),
                "available": d.get("available", 0),
                "usage_percent": d.get("percent", 0),
                "mount": d.get("mount", ""),
            })

        # Network
        network_rate = collector_data.get("network_rate", {})
        network_adapted = []
        for iface, rate in network_rate.items():
            network_adapted.append({
                "interface": iface,
                "rx_bytes_per_sec": rate.get("rx_bytes_sec", 0),
                "tx_bytes_per_sec": rate.get("tx_bytes_sec", 0),
                "rx_packets_per_sec": rate.get("rx_packets_sec", 0),
                "tx_packets_per_sec": rate.get("tx_packets_sec", 0),
                "rx_errors_per_sec": 0,
                "tx_errors_per_sec": 0,
            })

        # Load
        loadavg = collector_data.get("loadavg", {})
        load_adapted = {
            "load_1m": loadavg.get("1min", 0),
            "load_5m": loadavg.get("5min", 0),
            "load_15m": loadavg.get("15min", 0),
            "running": 0,
            "total_processes": 0,
        }

        # Connections
        connections_adapted = collector_data.get("connections", {})

        # Top processes
        processes_raw = collector_data.get("processes", [])
        top_processes = []
        for p in processes_raw[:10]:
            top_processes.append({
                "pid": p.get("pid", 0),
                "user": "",
                "cpu_percent": p.get("cpu", 0),
                "mem_percent": p.get("mem", 0),
                "command": p.get("comm", ""),
            })

        # Uptime
        uptime_raw = collector_data.get("uptime", {})
        uptime_adapted = uptime_raw.get("uptime_seconds", 0)

        # Docker containers - collector stores docker ps output, which is incompatible
        # with docker stats format; return empty list as best-effort
        docker_adapted = []

        # Hostname - collector doesn't store it; try to get via SSH or use alias
        try:
            _, hostname, _ = self._exec(alias, "hostname", 5)
        except Exception:
            hostname = alias

        return {
            "timestamp": timestamp,
            "alias": alias,
            "hostname": hostname,
            "cpu": cpu_adapted,
            "cores": cores_adapted,
            "memory": memory_adapted,
            "disks": disks_adapted,
            "network": network_adapted,
            "load": load_adapted,
            "connections": connections_adapted,
            "top_processes": top_processes,
            "uptime": uptime_adapted,
            "docker_containers": docker_adapted,
        }

    # ── CPU ──────────────────────────────────────────────────────

    def get_cpu_stats(self, alias: str) -> dict[str, Any]:
        code, out, _ = self._exec(alias, "cat /proc/stat | head -1", 5)
        cpu_times = out.split()
        if len(cpu_times) < 5:
            return {"error": "cannot parse /proc/stat"}
        user = int(cpu_times[1])
        nice = int(cpu_times[2])
        system = int(cpu_times[3])
        idle = int(cpu_times[4])
        iowait = int(cpu_times[5]) if len(cpu_times) > 5 else 0
        irq = int(cpu_times[6]) if len(cpu_times) > 6 else 0
        softirq = int(cpu_times[7]) if len(cpu_times) > 7 else 0
        steal = int(cpu_times[8]) if len(cpu_times) > 8 else 0
        total = user + nice + system + idle + iowait + irq + softirq + steal
        return {
            "user": user,
            "nice": nice,
            "system": system,
            "idle": idle,
            "iowait": iowait,
            "irq": irq,
            "softirq": softirq,
            "steal": steal,
            "total": total,
        }

    def get_cpu_percent(self, alias: str) -> dict[str, Any]:
        s1 = self._cpu_prev.get(alias)
        s2 = self.get_cpu_stats(alias)
        if s1 is None or "error" in s1 or "error" in s2:
            self._cpu_prev[alias] = s2
            time.sleep(1)
            s1 = s2
            s2 = self.get_cpu_stats(alias)
            self._cpu_prev[alias] = s2
        if "error" in s1 or "error" in s2:
            return {"usage_percent": 0}
        delta_total = s2["total"] - s1["total"]
        delta_idle = s2["idle"] - s1["idle"]
        if delta_total == 0:
            return {"usage_percent": 0}
        usage = round((1 - delta_idle / delta_total) * 100, 1)
        _, cores_out, _ = self._exec(alias, "nproc 2>/dev/null || echo 1", 5)
        cores = int(cores_out.strip() or 1)
        return {
            "usage_percent": usage,
            "cores": cores,
            "user_percent": round((s2["user"] - s1["user"]) / delta_total * 100, 1),
            "system_percent": round((s2["system"] - s1["system"]) / delta_total * 100, 1),
            "iowait_percent": round((s2["iowait"] - s1["iowait"]) / delta_total * 100, 1),
        }

    async def async_get_cpu_percent(self, alias: str) -> dict[str, Any]:
        loop = asyncio.get_event_loop()
        s1 = self._cpu_prev.get(alias)
        s2 = await loop.run_in_executor(None, self.get_cpu_stats, alias)
        if s1 is None or "error" in s1 or "error" in s2:
            self._cpu_prev[alias] = s2
            await asyncio.sleep(1)
            s1 = s2
            s2 = await loop.run_in_executor(None, self.get_cpu_stats, alias)
            self._cpu_prev[alias] = s2
        if "error" in s1 or "error" in s2:
            return {"usage_percent": 0}
        delta_total = s2["total"] - s1["total"]
        delta_idle = s2["idle"] - s1["idle"]
        if delta_total == 0:
            return {"usage_percent": 0}
        usage = round((1 - delta_idle / delta_total) * 100, 1)
        _, cores_out, _ = await loop.run_in_executor(
            None, self._exec, alias, "nproc 2>/dev/null || echo 1", 5
        )
        cores = int(cores_out.strip() or 1)
        return {
            "usage_percent": usage,
            "cores": cores,
            "user_percent": round((s2["user"] - s1["user"]) / delta_total * 100, 1),
            "system_percent": round((s2["system"] - s1["system"]) / delta_total * 100, 1),
            "iowait_percent": round((s2["iowait"] - s1["iowait"]) / delta_total * 100, 1),
        }

    def get_cpu_per_core(self, alias: str) -> list[dict[str, Any]]:
        code, out, _ = self._exec(alias, "grep '^cpu[0-9]' /proc/stat", 5)
        core_stats = []
        for line in out.split("\n") if out else []:
            parts = line.split()
            if len(parts) < 5:
                continue
            core_id = parts[0].replace("cpu", "")
            total = sum(int(v) for v in parts[1:])
            idle = int(parts[4])
            core_stats.append({"core": int(core_id), "total": total, "idle": idle})
        prev = self._cpu_core_prev.get(alias)
        if prev is None:
            self._cpu_core_prev[alias] = core_stats
            time.sleep(0.5)
            code2, out2, _ = self._exec(alias, "grep '^cpu[0-9]' /proc/stat", 5)
            core_stats2 = []
            for line in out2.split("\n") if out2 else []:
                parts = line.split()
                if len(parts) < 5:
                    continue
                core_id = parts[0].replace("cpu", "")
                total = sum(int(v) for v in parts[1:])
                idle = int(parts[4])
                core_stats2.append({"core": int(core_id), "total": total, "idle": idle})
            self._cpu_core_prev[alias] = core_stats2
            prev = core_stats
            core_stats = core_stats2
        else:
            self._cpu_core_prev[alias] = core_stats
            core_stats2 = core_stats
            core_stats = prev
        if not core_stats or not core_stats2:
            return []
        result = []
        for c1, c2 in zip(core_stats, core_stats2):
            dt = c2["total"] - c1["total"]
            di = c2["idle"] - c1["idle"]
            usage = round((1 - di / dt) * 100, 1) if dt > 0 else 0
            result.append({"core": c1["core"], "usage_percent": usage})
        return result

    async def async_get_cpu_per_core(self, alias: str) -> list[dict[str, Any]]:
        loop = asyncio.get_event_loop()
        code, out, _ = await loop.run_in_executor(
            None, self._exec, alias, "grep '^cpu[0-9]' /proc/stat", 5
        )
        core_stats = []
        for line in out.split("\n") if out else []:
            parts = line.split()
            if len(parts) < 5:
                continue
            core_id = parts[0].replace("cpu", "")
            total = sum(int(v) for v in parts[1:])
            idle = int(parts[4])
            core_stats.append({"core": int(core_id), "total": total, "idle": idle})
        prev = self._cpu_core_prev.get(alias)
        if prev is None:
            self._cpu_core_prev[alias] = core_stats
            await asyncio.sleep(0.5)
            code2, out2, _ = await loop.run_in_executor(
                None, self._exec, alias, "grep '^cpu[0-9]' /proc/stat", 5
            )
            core_stats2 = []
            for line in out2.split("\n") if out2 else []:
                parts = line.split()
                if len(parts) < 5:
                    continue
                core_id = parts[0].replace("cpu", "")
                total = sum(int(v) for v in parts[1:])
                idle = int(parts[4])
                core_stats2.append({"core": int(core_id), "total": total, "idle": idle})
            self._cpu_core_prev[alias] = core_stats2
            prev = core_stats
            core_stats = core_stats2
        else:
            self._cpu_core_prev[alias] = core_stats
            core_stats2 = core_stats
            core_stats = prev
        if not core_stats or not core_stats2:
            return []
        result = []
        for c1, c2 in zip(core_stats, core_stats2):
            dt = c2["total"] - c1["total"]
            di = c2["idle"] - c1["idle"]
            usage = round((1 - di / dt) * 100, 1) if dt > 0 else 0
            result.append({"core": c1["core"], "usage_percent": usage})
        return result

    # ── Memory ───────────────────────────────────────────────────

    def get_memory_stats(self, alias: str) -> dict[str, Any]:
        raw = self._exec(alias, "free -b 2>/dev/null", 5)
        mem_line = ""
        swap_line = ""
        for line in raw[1].split("\n"):
            if line.lower().startswith("mem:"):
                mem_line = line
            elif line.lower().startswith("swap:"):
                swap_line = line
        result: dict[str, Any] = {}
        if mem_line:
            parts = mem_line.split()
            if len(parts) >= 3:
                total = int(parts[1])
                used = int(parts[2])
                free = int(parts[3])
                available = int(parts[6]) if len(parts) > 6 else total - used
                result["total"] = total
                result["used"] = used
                result["free"] = free
                result["available"] = available
                result["usage_percent"] = round(used / total * 100, 1) if total > 0 else 0
                result["available_percent"] = round(available / total * 100, 1) if total > 0 else 0
        if swap_line:
            parts = swap_line.split()
            if len(parts) >= 3:
                stotal = int(parts[1])
                sused = int(parts[2])
                sfree = int(parts[3])
                result["swap"] = {
                    "total": stotal,
                    "used": sused,
                    "free": sfree,
                    "usage_percent": round(sused / stotal * 100, 1) if stotal > 0 else 0,
                }
        return result

    # ── Disk ─────────────────────────────────────────────────────

    def get_disk_stats(self, alias: str) -> list[dict[str, Any]]:
        return self._get_cached(alias, "disk_stats", 10, self._get_disk_stats_raw)

    def _get_disk_stats_raw(self, alias: str) -> list[dict[str, Any]]:
        code, stdout, _ = self._exec(
            alias,
            "df -B1 2>/dev/null | tail -n +2",
            10,
        )
        mounts = []
        for line in stdout.split("\n") if stdout else []:
            parts = line.split()
            if len(parts) >= 6:
                try:
                    total = int(parts[1])
                    used = int(parts[2])
                    avail = int(parts[3])
                    usage = round(used / total * 100, 1) if total > 0 else 0
                    mounts.append({
                        "filesystem": parts[0],
                        "total": total,
                        "used": used,
                        "available": avail,
                        "usage_percent": usage,
                        "mount": parts[5],
                    })
                except (ValueError, IndexError):
                    continue
        return mounts

    def get_disk_io(self, alias: str) -> list[dict[str, Any]]:
        code, stdout, _ = self._exec(alias, "cat /proc/diskstats 2>/dev/null", 5)
        devices = []
        for line in stdout.split("\n") if stdout else []:
            parts = line.split()
            if len(parts) >= 14:
                name = parts[2]
                if name.startswith(("sd", "nvme", "vd", "xvd", "mmc")):
                    devices.append({
                        "device": name,
                        "reads_completed": int(parts[3]),
                        "reads_merged": int(parts[4]),
                        "sectors_read": int(parts[5]),
                        "read_time_ms": int(parts[6]),
                        "writes_completed": int(parts[7]),
                        "writes_merged": int(parts[8]),
                        "sectors_written": int(parts[9]),
                        "write_time_ms": int(parts[10]),
                    })
        return devices

    def get_disk_io_rate(self, alias: str) -> list[dict[str, Any]]:
        a = self._disk_io_prev.get(alias)
        b = self.get_disk_io(alias)
        if a is None:
            self._disk_io_prev[alias] = b
            time.sleep(1)
            a = b
            b = self.get_disk_io(alias)
            self._disk_io_prev[alias] = b
        result = []
        for da, db in zip(a, b):
            if da["device"] != db["device"]:
                continue
            result.append({
                "device": da["device"],
                "read_bytes_per_sec": (db["sectors_read"] - da["sectors_read"]) * 512,
                "write_bytes_per_sec": (db["sectors_written"] - da["sectors_written"]) * 512,
                "read_ops_per_sec": db["reads_completed"] - da["reads_completed"],
                "write_ops_per_sec": db["writes_completed"] - da["writes_completed"],
            })
        return result

    async def async_get_disk_io_rate(self, alias: str) -> list[dict[str, Any]]:
        loop = asyncio.get_event_loop()
        a = self._disk_io_prev.get(alias)
        b = await loop.run_in_executor(None, self.get_disk_io, alias)
        if a is None:
            self._disk_io_prev[alias] = b
            await asyncio.sleep(1)
            a = b
            b = await loop.run_in_executor(None, self.get_disk_io, alias)
            self._disk_io_prev[alias] = b
        result = []
        for da, db in zip(a, b):
            if da["device"] != db["device"]:
                continue
            result.append({
                "device": da["device"],
                "read_bytes_per_sec": (db["sectors_read"] - da["sectors_read"]) * 512,
                "write_bytes_per_sec": (db["sectors_written"] - da["sectors_written"]) * 512,
                "read_ops_per_sec": db["reads_completed"] - da["reads_completed"],
                "write_ops_per_sec": db["writes_completed"] - da["writes_completed"],
            })
        return result

    # ── Network ──────────────────────────────────────────────────

    def get_network_stats(self, alias: str) -> list[dict[str, Any]]:
        code, stdout, _ = self._exec(alias, "cat /proc/net/dev 2>/dev/null | tail -n +3", 5)
        interfaces = []
        for line in stdout.split("\n") if stdout else []:
            parts = line.replace(":", "").split()
            if len(parts) >= 10:
                interfaces.append({
                    "interface": parts[0],
                    "rx_bytes": int(parts[1]),
                    "rx_packets": int(parts[2]),
                    "rx_errors": int(parts[3]),
                    "rx_drop": int(parts[4]),
                    "tx_bytes": int(parts[9]),
                    "tx_packets": int(parts[10]),
                    "tx_errors": int(parts[11]),
                    "tx_drop": int(parts[12]),
                })
        return [i for i in interfaces if i["interface"] != "lo"]

    def get_network_rate(self, alias: str) -> list[dict[str, Any]]:
        a = self._network_prev.get(alias)
        b = self.get_network_stats(alias)
        if a is None:
            self._network_prev[alias] = b
            time.sleep(1)
            a = b
            b = self.get_network_stats(alias)
            self._network_prev[alias] = b
        if not a:
            return []
        result = []
        for da, db in zip(a, b):
            if da["interface"] != db["interface"]:
                continue
            result.append({
                "interface": da["interface"],
                "rx_bytes_per_sec": db["rx_bytes"] - da["rx_bytes"],
                "tx_bytes_per_sec": db["tx_bytes"] - da["tx_bytes"],
                "rx_packets_per_sec": db["rx_packets"] - da["rx_packets"],
                "tx_packets_per_sec": db["tx_packets"] - da["tx_packets"],
                "rx_errors_per_sec": db["rx_errors"] - da["rx_errors"],
                "tx_errors_per_sec": db["tx_errors"] - da["tx_errors"],
            })
        return result

    async def async_get_network_rate(self, alias: str) -> list[dict[str, Any]]:
        loop = asyncio.get_event_loop()
        a = self._network_prev.get(alias)
        b = await loop.run_in_executor(None, self.get_network_stats, alias)
        if a is None:
            self._network_prev[alias] = b
            await asyncio.sleep(1)
            a = b
            b = await loop.run_in_executor(None, self.get_network_stats, alias)
            self._network_prev[alias] = b
        if not a:
            return []
        result = []
        for da, db in zip(a, b):
            if da["interface"] != db["interface"]:
                continue
            result.append({
                "interface": da["interface"],
                "rx_bytes_per_sec": db["rx_bytes"] - da["rx_bytes"],
                "tx_bytes_per_sec": db["tx_bytes"] - da["tx_bytes"],
                "rx_packets_per_sec": db["rx_packets"] - da["rx_packets"],
                "tx_packets_per_sec": db["tx_packets"] - da["tx_packets"],
                "rx_errors_per_sec": db["rx_errors"] - da["rx_errors"],
                "tx_errors_per_sec": db["tx_errors"] - da["tx_errors"],
            })
        return result

    def get_network_connections(self, alias: str) -> dict[str, int]:
        code, stdout, _ = self._exec(alias, "ss -tan 2>/dev/null | tail -n +2 | awk '{print $1}' | sort | uniq -c", 10)
        counts: dict[str, int] = {}
        for line in stdout.split("\n") if stdout else []:
            parts = line.strip().split()
            if len(parts) == 2:
                try:
                    counts[parts[1]] = int(parts[0])
                except ValueError:
                    continue
        return counts

    # ── Processes / Load ─────────────────────────────────────────

    def get_load_average(self, alias: str) -> dict[str, Any]:
        code, out, _ = self._exec(alias, "cat /proc/loadavg", 5)
        parts = out.split()
        if len(parts) >= 3:
            return {
                "load_1m": float(parts[0]),
                "load_5m": float(parts[1]),
                "load_15m": float(parts[2]),
                "running": int(parts[3].split("/")[0]) if "/" in parts[3] else 0,
                "total_processes": int(parts[3].split("/")[1]) if "/" in parts[3] else 0,
            }
        return {"load_1m": 0, "load_5m": 0, "load_15m": 0}

    def get_top_processes(self, alias: str, count: int = 10) -> list[dict[str, Any]]:
        cmd = (
            f"ps aux --sort=-%cpu 2>/dev/null | head -{count + 1} | tail -{count} "
            f"| awk '{{print $2\",\"$1\",\"$3\",\"$4\",\"$11}}'"
        )
        code, stdout, _ = self._exec(alias, cmd, 10)
        processes = []
        for line in stdout.split("\n") if stdout else []:
            parts = line.strip().split(",")
            if len(parts) >= 5:
                processes.append({
                    "pid": int(parts[0]) if parts[0].isdigit() else parts[0],
                    "user": parts[1],
                    "cpu_percent": float(parts[2]),
                    "mem_percent": float(parts[3]),
                    "command": parts[4],
                })
        return processes

    # ── System Uptime & Temperature ──────────────────────────────

    def get_uptime(self, alias: str) -> float:
        code, out, _ = self._exec(alias, "cat /proc/uptime", 5)
        try:
            return float(out.split()[0])
        except (IndexError, ValueError):
            return 0

    def get_temperatures(self, alias: str) -> list[dict[str, Any]]:
        return self._get_cached(alias, "temperatures", 10, self._get_temperatures_raw)

    def _get_temperatures_raw(self, alias: str) -> list[dict[str, Any]]:
        code, stdout, _ = self._exec(alias, "cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null", 5)
        temps = []
        for i, line in enumerate(stdout.split("\n") if stdout else []):
            try:
                temp_c = int(line.strip()) / 1000
                temps.append({"sensor": f"thermal_zone{i}", "temperature_celsius": temp_c})
            except ValueError:
                continue
        if not temps:
            code2, out2, _ = self._exec(alias, "sensors 2>/dev/null | grep -i '°C' | head -5", 5)
            for line in out2.split("\n") if out2 else []:
                temps.append({"sensor": "unknown", "raw": line.strip()})
        return temps

    # ── Docker Container Metrics ─────────────────────────────────

    def get_docker_container_metrics(self, alias: str) -> list[dict[str, Any]]:
        return self._get_cached(alias, "docker_container_metrics", 10, self._get_docker_container_metrics_raw)

    def _get_docker_container_metrics_raw(self, alias: str) -> list[dict[str, Any]]:
        code, out, _ = self._exec(alias,
            "docker stats --no-stream --format '{{json .}}' 2>/dev/null", 15)
        containers = []
        for line in out.split("\n") if out else []:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                cpu_str = data.get("CPUPerc", "0%").replace("%", "")
                mem_str = data.get("MemPerc", "0%").replace("%", "")
                mem_usage_str = data.get("MemUsage", "0B / 0B")
                net_str = data.get("NetIO", "0B / 0B")
                block_str = data.get("BlockIO", "0B / 0B")
                def _parse_bytes(s: str) -> float:
                    s = s.strip()
                    if not s:
                        return 0.0
                    multipliers = {
                        "TiB": 1024**4, "TB": 1024**4,
                        "GiB": 1024**3, "GB": 1024**3,
                        "MiB": 1024**2, "MB": 1024**2,
                        "KiB": 1024, "KB": 1024,
                        "B": 1,
                    }
                    for unit, mult in multipliers.items():
                        if unit in s:
                            num_str = s.replace(unit, "").strip()
                            try:
                                return float(num_str) * mult
                            except ValueError:
                                return 0
                    try:
                        return float(s)
                    except ValueError:
                        return 0
                mem_parts = mem_usage_str.split("/")
                mem_used = _parse_bytes(mem_parts[0]) if len(mem_parts) > 0 else 0
                mem_total = _parse_bytes(mem_parts[1]) if len(mem_parts) > 1 else 0
                net_parts = net_str.split("/")
                net_rx = _parse_bytes(net_parts[0]) if len(net_parts) > 0 else 0
                net_tx = _parse_bytes(net_parts[1]) if len(net_parts) > 1 else 0
                block_parts = block_str.split("/")
                block_r = _parse_bytes(block_parts[0]) if len(block_parts) > 0 else 0
                block_w = _parse_bytes(block_parts[1]) if len(block_parts) > 1 else 0
                containers.append({
                    "name": data.get("Name", "").lstrip("/"),
                    "container_id": data.get("Container", "")[:12],
                    "cpu_percent": float(cpu_str) if cpu_str else 0,
                    "mem_percent": float(mem_str) if mem_str else 0,
                    "mem_used": mem_used,
                    "mem_total": mem_total,
                    "net_rx": net_rx,
                    "net_tx": net_tx,
                    "block_read": block_r,
                    "block_write": block_w,
                    "pids": int(data.get("PIDs", 0)),
                })
            except (json.JSONDecodeError, ValueError, KeyError):
                continue
        return containers

    # ── Middleware Health Checks ─────────────────────────────────

    def check_mysql(self, alias: str) -> dict[str, Any]:
        code, out, _ = self._exec(alias,
            "mysqladmin ping -u root --silent 2>/dev/null && echo 'ALIVE' || echo 'DEAD'", 10)
        return {"alive": "ALIVE" in out, "raw": out[:100]}

    def check_redis(self, alias: str) -> dict[str, Any]:
        code, out, _ = self._exec(alias,
            "redis-cli ping 2>/dev/null || echo 'NO_CONNECTION'", 10)
        return {"alive": "PONG" in out, "raw": out[:100]}

    def check_mq(self, alias: str, mq_type: str = "rabbitmq") -> dict[str, Any]:
        if mq_type == "rabbitmq":
            code, out, _ = self._exec(alias,
                "rabbitmqctl status 2>/dev/null | head -5 || echo 'DEAD'", 15)
            return {"alive": "Status" in out or "running" in out, "type": "rabbitmq", "raw": out[:200]}
        elif mq_type == "kafka":
            code, out, _ = self._exec(alias,
                "kafka-broker-api-versions.sh --bootstrap-server localhost:9092 2>/dev/null | head -1 || echo 'DEAD'", 15)
            return {"alive": "DEAD" not in out, "type": "kafka", "raw": out[:200]}
        return {"alive": False, "type": mq_type, "raw": "unsupported"}

    def check_nginx(self, alias: str) -> dict[str, Any]:
        code, out, _ = self._exec(alias,
            "nginx -t 2>&1 | head -1 || systemctl is-active nginx 2>/dev/null", 10)
        alive = "successful" in out.lower() or "active" in out.lower()
        return {"alive": alive, "raw": out[:100]}

    def check_middleware_all(self, alias: str) -> dict[str, Any]:
        return {
            "mysql": self.check_mysql(alias),
            "redis": self.check_redis(alias),
            "rabbitmq": self.check_mq(alias, "rabbitmq"),
            "nginx": self.check_nginx(alias),
        }

    def get_middleware_metrics(self, alias: str) -> dict[str, Any]:
        result: dict[str, Any] = {}
        code_mysql, out_mysql, _ = self._exec(alias,
            "mysql -u root -e \"SHOW GLOBAL STATUS LIKE 'Questions'; SHOW GLOBAL STATUS LIKE 'Threads_connected'; SHOW GLOBAL STATUS LIKE 'Slow_queries'\" 2>/dev/null | tail -3 | awk '{print $2}'", 10)
        lines = out_mysql.strip().split("\n") if out_mysql else []
        if len(lines) >= 3:
            try:
                result["mysql"] = {
                    "questions": int(lines[0].strip()),
                    "threads_connected": int(lines[1].strip()),
                    "slow_queries": int(lines[2].strip()),
                }
            except ValueError:
                pass
        code_redis, out_redis, _ = self._exec(alias,
            "redis-cli INFO stats 2>/dev/null | grep -E 'total_connections_received|total_commands_processed|keyspace_hits|keyspace_misses' | head -4", 10)
        redis_stats = {}
        for line in out_redis.split("\n") if out_redis else []:
            if ":" in line:
                k, v = line.split(":", 1)
                try:
                    redis_stats[k.strip()] = int(v.strip())
                except ValueError:
                    redis_stats[k.strip()] = v.strip()
        if redis_stats:
            result["redis"] = redis_stats
        return result

    # ── All-in-One Snapshot ──────────────────────────────────────

    def get_snapshot(self, alias: str) -> dict[str, Any]:
        if self._collector is not None:
            collector_data = self._collector.get_latest_snapshot(alias)
            if collector_data is not None:
                return self._adapt_collector_snapshot(collector_data)

        cpu = self.get_cpu_percent(alias)
        cores = self.get_cpu_per_core(alias)
        mem = self.get_memory_stats(alias)
        disks = self.get_disk_stats(alias)
        net_rate = self.get_network_rate(alias)
        load = self.get_load_average(alias)
        top = self.get_top_processes(alias)
        conns = self.get_network_connections(alias)
        uptime = self.get_uptime(alias)
        docker = self.get_docker_container_metrics(alias)
        return {
            "timestamp": time.time(),
            "alias": alias,
            "hostname": self._exec(alias, "hostname", 5)[1],
            "cpu": cpu,
            "cores": cores,
            "memory": mem,
            "disks": disks,
            "network": net_rate,
            "load": load,
            "connections": conns,
            "top_processes": top,
            "uptime": uptime,
            "docker_containers": docker,
        }

    async def async_get_snapshot(self, alias: str) -> dict[str, Any]:
        if self._collector is not None:
            collector_data = self._collector.get_latest_snapshot(alias)
            if collector_data is not None:
                return self._adapt_collector_snapshot(collector_data)

        loop = asyncio.get_event_loop()
        hostname_future = loop.run_in_executor(
            None, self._exec, alias, "hostname", 5
        )
        cpu_future = self.async_get_cpu_percent(alias)
        cores_future = self.async_get_cpu_per_core(alias)
        mem_future = loop.run_in_executor(None, self.get_memory_stats, alias)
        disks_future = loop.run_in_executor(None, self.get_disk_stats, alias)
        net_rate_future = self.async_get_network_rate(alias)
        load_future = loop.run_in_executor(None, self.get_load_average, alias)
        top_future = loop.run_in_executor(None, self.get_top_processes, alias)
        conns_future = loop.run_in_executor(None, self.get_network_connections, alias)
        uptime_future = loop.run_in_executor(None, self.get_uptime, alias)
        docker_future = loop.run_in_executor(None, self.get_docker_container_metrics, alias)
        (
            cpu, cores, mem, disks, net_rate, load, top, conns, uptime, docker, hostname_result
        ) = await asyncio.gather(
            cpu_future, cores_future, mem_future, disks_future, net_rate_future,
            load_future, top_future, conns_future, uptime_future, docker_future, hostname_future
        )
        return {
            "timestamp": time.time(),
            "alias": alias,
            "hostname": hostname_result[1],
            "cpu": cpu,
            "cores": cores,
            "memory": mem,
            "disks": disks,
            "network": net_rate,
            "load": load,
            "connections": conns,
            "top_processes": top,
            "uptime": uptime,
            "docker_containers": docker,
        }

    def store_snapshot(self, alias: str, data: dict[str, Any]) -> None:
        self._history[alias].append(data)

    def get_history(self, alias: str, seconds: int = 300) -> list[dict[str, Any]]:
        if self._collector is not None:
            collector_history = self._collector.get_history(alias, seconds)
            if collector_history:
                return [self._adapt_collector_snapshot(entry) for entry in collector_history]

        now = time.time()
        return [d for d in self._history.get(alias, []) if now - d.get("timestamp", 0) <= seconds]

    def subscribe(self, alias: str, ws) -> None:
        self._subscribers[alias].add(ws)

    def unsubscribe(self, alias: str, ws) -> None:
        self._subscribers[alias].discard(ws)

    async def start_streaming(self, alias: str, interval: float = 2.0) -> None:
        if alias in self._tasks and not self._tasks[alias].done():
            return

        # 如果 collector 可用且有该 alias 的数据，优先订阅 collector
        if self._collector is not None:
            latest = self._collector.get_latest_snapshot(alias)
            if latest is not None:
                def _on_collector_snapshot(snapshot: dict) -> None:
                    adapted = self._adapt_collector_snapshot(snapshot)
                    self.store_snapshot(alias, adapted)
                    dead_ws = set()
                    for ws in self._subscribers.get(alias, set()):
                        try:
                            # 同步调用 send_json 的同步包装
                            asyncio.create_task(ws.send_json(adapted))
                        except Exception:
                            dead_ws.add(ws)
                    if dead_ws:
                        self._subscribers[alias] -= dead_ws

                self._collector.subscribe(alias, _on_collector_snapshot)
                self._collector_callbacks[alias] = _on_collector_snapshot

                # 启动一个守护任务，防止 _tasks[alias] 被重复创建
                async def _collector_guard():
                    while True:
                        await asyncio.sleep(3600)
                self._tasks[alias] = asyncio.create_task(_collector_guard())
                return

        # Fallback: 使用原有的实时采集逻辑
        async def _stream():
            while True:
                start_time = time.time()
                try:
                    snapshot = await self.async_get_snapshot(alias)
                    self.store_snapshot(alias, snapshot)
                    dead_ws = set()
                    for ws in self._subscribers.get(alias, set()):
                        try:
                            await ws.send_json(snapshot)
                        except Exception:
                            dead_ws.add(ws)
                    self._subscribers[alias] -= dead_ws
                except Exception:
                    pass
                elapsed = time.time() - start_time
                sleep_time = max(0, interval - elapsed)
                await asyncio.sleep(sleep_time)
        self._tasks[alias] = asyncio.create_task(_stream())

    async def stop_streaming(self, alias: str) -> None:
        # 如果通过 collector 订阅，先取消订阅
        if self._collector is not None and alias in self._collector_callbacks:
            callback = self._collector_callbacks.pop(alias)
            self._collector.unsubscribe(alias, callback)

        if alias in self._tasks:
            self._tasks[alias].cancel()
            try:
                await self._tasks[alias]
            except asyncio.CancelledError:
                pass
            del self._tasks[alias]

    # ── Accumulated CPU delta (for dashboard line charts) ────────
    def get_cpu_delta_series(self, alias: str, points: int = 60) -> list[dict[str, Any]]:
        history = self.get_history(alias, 300)
        recent = list(history)[-points:]
        return [{"time": h["timestamp"], "cpu_percent": h.get("cpu", {}).get("usage_percent", 0)} for h in recent]

    def get_memory_series(self, alias: str, points: int = 60) -> list[dict[str, Any]]:
        history = self.get_history(alias, 300)
        recent = list(history)[-points:]
        return [{"time": h["timestamp"], "memory_percent": h.get("memory", {}).get("usage_percent", 0)} for h in recent]


monitor_service = MonitorService()
