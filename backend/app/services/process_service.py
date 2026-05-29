from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from typing import Any, Optional

from app.services.ssh_account_service import ssh_account_service

logger = logging.getLogger(__name__)

# 支持的信号映射
SIGNAL_MAP: dict[str, int] = {
    "SIGTERM": 15,
    "SIGKILL": 9,
    "SIGHUP": 1,
    "SIGSTOP": 19,
    "SIGCONT": 18,
}

# ps STAT 列第一个字符到可读状态的映射
STATUS_MAP: dict[str, str] = {
    "R": "running",
    "S": "sleeping",
    "D": "sleeping",
    "Z": "zombie",
    "T": "stopped",
    "t": "stopped",
    "I": "idle",
    "X": "dead",
}

# 默认告警阈值
DEFAULT_ALERT_CONFIG: dict[str, Any] = {
    "cpu_threshold": 90.0,
    "mem_threshold": 80.0,
    "duration_seconds": 5,
}


class ProcessService:
    """远程 Linux 服务器进程管理服务。"""

    def __init__(self) -> None:
        # 异常检测历史: alias -> {pid -> deque of timestamps}
        self._anomaly_history: dict[str, dict[int, deque[float]]] = defaultdict(
            lambda: defaultdict(lambda: deque(maxlen=100))
        )
        # 流媒体相关
        self._stream_tasks: dict[str, asyncio.Task] = {}
        self._stream_subscribers: dict[str, set] = defaultdict(set)
        # 进程列表缓存: alias -> (processes, timestamp)
        self._process_cache: dict[str, tuple[list[dict], float]] = {}

    # ── SSH 连接辅助 ──────────────────────────────────────────────

    def _conn(self, alias: str):
        """获取指定别名对应的 SSH 连接。"""
        account = ssh_account_service.get_account(alias)
        if account is None:
            raise ValueError(f"SSH 账户 '{alias}' 不存在")
        return ssh_account_service.pool.get_connection(account)

    def _exec(self, alias: str, cmd: str, timeout: float = 30.0) -> tuple[int, str, str]:
        """在远程服务器上执行命令。"""
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

    async def _exec_async(self, alias: str, cmd: str, timeout: float = 30.0) -> tuple[int, str, str]:
        """异步执行远程命令（通过 run_in_executor 包装 _exec）。"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._exec, alias, cmd, timeout)

    # ── 进程列表 ──────────────────────────────────────────────────

    def get_all_processes(self, alias: str) -> list[dict[str, Any]]:
        """获取所有进程，返回包含完整字段的进程列表。

        使用单次复合命令同时获取基础字段、args 和 cwd，在本地解析。
        """
        # 检查缓存
        now = time.time()
        cached = self._process_cache.get(alias)
        if cached is not None:
            processes, ts = cached
            if now - ts < 1.0:
                return processes

        # 单次复合命令
        batch_cmd = (
            "ps -eo pid,ppid,user,pcpu,pmem,vsz,rss,tty,stat,start,time,nlwp,comm "
            "--no-headers --sort=-pcpu 2>/dev/null && echo '---ARGS---' && "
            "ps -eo pid,args --no-headers 2>/dev/null && echo '---CWD---' && "
            "for p in $(ps -eo pid --no-headers 2>/dev/null | head -50); do "
            'echo "$p:$(readlink /proc/$p/cwd 2>/dev/null)"; done'
        )
        code, out, err = self._exec(alias, batch_cmd, 30)
        if code != 0 and not out:
            logger.error(f"[process] batch ps failed for {alias}: {err}")
            return []

        # 按分隔符分割输出
        parts = out.split("---ARGS---")
        basic_part = parts[0].strip() if len(parts) > 0 else ""
        rest = parts[1] if len(parts) > 1 else ""
        args_part = ""
        cwd_part = ""
        if "---CWD---" in rest:
            args_part, cwd_part = rest.split("---CWD---", 1)
            args_part = args_part.strip()
            cwd_part = cwd_part.strip()
        else:
            args_part = rest.strip()

        # 解析 args
        args_map: dict[int, str] = {}
        for line in args_part.split("\n") if args_part else []:
            parts_line = line.strip().split(None, 1)
            if len(parts_line) >= 2 and parts_line[0].isdigit():
                args_map[int(parts_line[0])] = parts_line[1].strip()

        # 解析 cwd
        cwd_map: dict[int, str] = {}
        for line in cwd_part.split("\n") if cwd_part else []:
            if ":" in line:
                p_str, cwd_val = line.split(":", 1)
                if p_str.isdigit():
                    cwd_map[int(p_str)] = cwd_val

        # 解析基础字段
        pids_for_cwd: list[int] = []
        processes: list[dict[str, Any]] = []
        for line in basic_part.split("\n") if basic_part else []:
            parts_line = line.split()
            if len(parts_line) < 13:
                continue

            try:
                pid = int(parts_line[0])
                ppid = int(parts_line[1])
                user = parts_line[2]
                cpu_percent = float(parts_line[3])
                mem_percent = float(parts_line[4])
                vsz = int(parts_line[5])
                rss = int(parts_line[6])
                tty = parts_line[7]
                stat_raw = parts_line[8]
                start_time = parts_line[9]
                cpu_time = parts_line[10]
                thread_count = int(parts_line[11])
                name = parts_line[12]
            except (ValueError, IndexError):
                continue

            status_char = stat_raw[0] if stat_raw else "S"
            status = STATUS_MAP.get(status_char, "unknown")
            command = args_map.get(pid, name)

            if len(pids_for_cwd) < 50:
                pids_for_cwd.append(pid)

            processes.append({
                "pid": pid,
                "ppid": ppid,
                "user": user,
                "cpu_percent": cpu_percent,
                "mem_percent": mem_percent,
                "vsz": vsz,
                "rss": rss,
                "tty": tty,
                "status": status,
                "start_time": start_time,
                "cpu_time": cpu_time,
                "thread_count": thread_count,
                "name": name,
                "command": command,
                "cwd": cwd_map.get(pid, ""),
            })

        # 更新缓存
        self._process_cache[alias] = (processes, time.time())
        return processes

    # ── 进程详情 ──────────────────────────────────────────────────

    async def get_process_detail(self, pid: int, alias: str) -> dict[str, Any]:
        """获取单个进程的详细信息。"""
        # 先获取基本信息
        procs = self.get_all_processes(alias)
        basic = None
        for p in procs:
            if p["pid"] == pid:
                basic = p
                break

        if basic is None:
            # 进程不存在，尝试直接查询
            cmd = f"ps -p {pid} -o pid,ppid,user,pcpu,pmem,vsz,rss,tty,stat,start,time,nlwp,comm --no-headers 2>/dev/null"
            code, out, _ = await self._exec_async(alias, cmd, 10)
            if not out:
                return {"error": f"进程 {pid} 不存在"}
            parts = out.split()
            if len(parts) < 13:
                return {"error": f"无法解析进程 {pid} 信息"}

            stat_raw = parts[8]
            status_char = stat_raw[0] if stat_raw else "S"
            status = STATUS_MAP.get(status_char, "unknown")

            # 获取 args
            cmd_args = f"ps -p {pid} -o args --no-headers 2>/dev/null"
            _, args_out, _ = await self._exec_async(alias, cmd_args, 10)

            basic = {
                "pid": int(parts[0]),
                "ppid": int(parts[1]),
                "user": parts[2],
                "cpu_percent": float(parts[3]),
                "mem_percent": float(parts[4]),
                "vsz": int(parts[5]),
                "rss": int(parts[6]),
                "tty": parts[7],
                "status": status,
                "start_time": parts[9],
                "cpu_time": parts[10],
                "thread_count": int(parts[11]),
                "name": parts[12],
                "command": args_out.strip() if args_out else parts[12],
                "cwd": "",
            }

        # 并行获取详细信息
        async def _get_environ() -> list[str]:
            try:
                _, env_out, _ = await self._exec_async(
                    alias,
                    f"cat /proc/{pid}/environ 2>/dev/null | tr '\\0' '\\n' | head -100",
                    10,
                )
                return [e for e in env_out.split("\n") if e] if env_out else []
            except Exception:
                return []

        async def _get_fd_count() -> int:
            try:
                _, fd_out, _ = await self._exec_async(
                    alias, f"ls /proc/{pid}/fd 2>/dev/null | wc -l", 10
                )
                return int(fd_out.strip()) if fd_out.strip().isdigit() else 0
            except Exception:
                return 0

        async def _get_net_connections() -> int:
            try:
                _, net_out, _ = await self._exec_async(
                    alias,
                    f"cat /proc/{pid}/net/tcp /proc/{pid}/net/tcp6 /proc/{pid}/net/udp /proc/{pid}/net/udp6 2>/dev/null | grep -v '^  sl' | wc -l",
                    10,
                )
                return int(net_out.strip()) if net_out.strip().isdigit() else 0
            except Exception:
                return 0

        async def _get_cgroup() -> str:
            try:
                _, cg_out, _ = await self._exec_async(alias, f"cat /proc/{pid}/cgroup 2>/dev/null", 10)
                return cg_out.strip() if cg_out else ""
            except Exception:
                return ""

        async def _get_status_file() -> dict[str, str]:
            try:
                _, st_out, _ = await self._exec_async(
                    alias, f"cat /proc/{pid}/status 2>/dev/null", 10
                )
                if not st_out:
                    return {}
                key_fields = ["Name", "State", "Threads", "VmPeak", "VmSize", "VmRSS", "VmSwap"]
                result: dict[str, str] = {}
                for line in st_out.split("\n"):
                    if ":" in line:
                        key, _, val = line.partition(":")
                        key = key.strip()
                        if key in key_fields:
                            result[key] = val.strip()
                return result
            except Exception:
                return {}

        async def _get_cwd() -> str:
            try:
                _, cwd_out, _ = await self._exec_async(
                    alias, f"readlink /proc/{pid}/cwd 2>/dev/null", 10
                )
                return cwd_out.strip() if cwd_out else ""
            except Exception:
                return ""

        environ, fd_count, net_connections, cgroup, status_file, cwd = await asyncio.gather(
            _get_environ(),
            _get_fd_count(),
            _get_net_connections(),
            _get_cgroup(),
            _get_status_file(),
            _get_cwd(),
        )

        basic["cwd"] = cwd
        basic["environ"] = environ
        basic["fd_count"] = fd_count
        basic["net_connections"] = net_connections
        basic["cgroup"] = cgroup
        basic["status_file"] = status_file

        return basic

    # ── 进程控制 ──────────────────────────────────────────────────

    def kill_process(self, pid: int, signal_name: str, alias: str) -> dict[str, Any]:
        """向进程发送信号。

        支持的信号: SIGTERM, SIGKILL, SIGHUP, SIGSTOP, SIGCONT
        """
        signal_name = signal_name.upper()
        if signal_name not in SIGNAL_MAP:
            return {
                "success": False,
                "message": f"不支持的信号: {signal_name}，支持的信号: {', '.join(SIGNAL_MAP.keys())}",
            }

        signal_num = SIGNAL_MAP[signal_name]
        cmd = f"kill -{signal_num} {pid} 2>&1"
        try:
            code, out, err = self._exec(alias, cmd, 10)
            if code == 0:
                return {"success": True, "message": f"已向进程 {pid} 发送 {signal_name}"}
            else:
                return {"success": False, "message": f"发送信号失败: {err or out}"}
        except Exception as e:
            logger.error(f"[process] kill 失败: {e}")
            return {"success": False, "message": f"执行失败: {str(e)}"}

    def set_nice(self, pid: int, nice_value: int, alias: str) -> dict[str, Any]:
        """调整进程优先级。nice_value 范围: -20 ~ 19。"""
        if nice_value < -20 or nice_value > 19:
            return {
                "success": False,
                "message": f"nice 值必须在 -20 到 19 之间，当前值: {nice_value}",
                "new_nice": nice_value,
            }

        cmd = f"renice -n {nice_value} -p {pid} 2>&1"
        try:
            code, out, err = self._exec(alias, cmd, 10)
            if code == 0:
                return {"success": True, "message": out.strip(), "new_nice": nice_value}
            else:
                return {"success": False, "message": f"renice 失败: {err or out}", "new_nice": nice_value}
        except Exception as e:
            logger.error(f"[process] renice 失败: {e}")
            return {"success": False, "message": f"执行失败: {str(e)}", "new_nice": nice_value}

    def batch_kill(
        self, pids: list[int], signal_name: str, alias: str
    ) -> list[dict[str, Any]]:
        """批量终止多个进程。"""
        results: list[dict[str, Any]] = []
        for pid in pids:
            result = self.kill_process(pid, signal_name, alias)
            results.append({"pid": pid, "success": result["success"], "message": result["message"]})
        return results

    # ── systemd 服务控制 ──────────────────────────────────────────

    def is_systemd_service(self, pid: int, alias: str) -> dict[str, Any]:
        """检查 PID 是否为 systemd 服务进程。"""
        # 方法 1: 检查 cgroup
        try:
            _, cg_out, _ = self._exec(alias, f"cat /proc/{pid}/cgroup 2>/dev/null", 10)
            if cg_out and "systemd" in cg_out.lower():
                # 尝试提取服务名
                for line in cg_out.split("\n"):
                    if ".service" in line:
                        parts = line.split("/")
                        for part in parts:
                            if part.endswith(".service"):
                                service_name = part.replace(".service", "")
                                return {"is_service": True, "service_name": service_name}
        except Exception:
            pass

        # 方法 2: 使用 systemctl status 检查
        try:
            _, st_out, _ = self._exec(
                alias,
                f"systemctl status --no-pager 2>/dev/null | grep -w '{pid}' | head -1",
                10,
            )
            if st_out and ".service" in st_out:
                for word in st_out.split():
                    if word.endswith(".service"):
                        service_name = word.replace(".service", "")
                        return {"is_service": True, "service_name": service_name}
        except Exception:
            pass

        return {"is_service": False, "service_name": None}

    def service_control(
        self, service_name: str, action: str, alias: str
    ) -> dict[str, Any]:
        """控制 systemd 服务。

        支持的操作: start, stop, restart, reload, status
        """
        allowed_actions = {"start", "stop", "restart", "reload", "status"}
        action = action.lower()
        if action not in allowed_actions:
            return {
                "success": False,
                "message": f"不支持的操作: {action}，支持的操作: {', '.join(allowed_actions)}",
                "output": "",
            }

        # 清理服务名，防止命令注入
        service_name = service_name.replace(";", "").replace("&", "").replace("|", "").strip()
        if not service_name:
            return {"success": False, "message": "服务名不能为空", "output": ""}

        cmd = f"systemctl {action} {service_name} 2>&1"
        try:
            code, out, err = self._exec(alias, cmd, 30)
            output = out if out else err
            success = code == 0
            return {"success": success, "message": output, "output": output}
        except Exception as e:
            logger.error(f"[process] service_control 失败: {e}")
            return {"success": False, "message": f"执行失败: {str(e)}", "output": ""}

    # ── 异常检测 ──────────────────────────────────────────────────

    def detect_anomalies(
        self, alias: str, thresholds: dict[str, Any]
    ) -> dict[str, Any]:
        """检测异常进程。

        参数:
            alias: SSH 账户别名
            thresholds: {"cpu_threshold": float, "mem_threshold": float, "duration_seconds": int}

        返回:
            {"zombies": [pid...], "high_cpu": [{pid, cpu_percent, duration}],
             "high_mem": [{pid, mem_percent, duration}], "total_anomalies": int}
        """
        cpu_threshold = thresholds.get("cpu_threshold", 90.0)
        mem_threshold = thresholds.get("mem_threshold", 80.0)
        duration_seconds = thresholds.get("duration_seconds", 5)

        procs = self.get_all_processes(alias)
        now = time.time()

        zombies: list[int] = []
        high_cpu: list[dict[str, Any]] = []
        high_mem: list[dict[str, Any]] = []

        history = self._anomaly_history[alias]

        for proc in procs:
            pid = proc["pid"]
            cpu = proc["cpu_percent"]
            mem = proc["mem_percent"]
            status = proc["status"]

            # 僵尸进程
            if status == "zombie":
                zombies.append(pid)

            # CPU 异常
            if cpu >= cpu_threshold:
                if pid not in history:
                    history[pid] = deque()
                history[pid].append(now)
                # 检查是否持续超过阈值
                durations = history[pid]
                if durations:
                    earliest = durations[0]
                    duration = now - earliest
                    if duration >= duration_seconds:
                        high_cpu.append({
                            "pid": pid,
                            "cpu_percent": cpu,
                            "duration": round(duration, 1),
                        })
            else:
                # 恢复正常，清除历史
                if pid in history:
                    del history[pid]

            # 内存异常
            if mem >= mem_threshold:
                if pid not in history:
                    history[pid] = deque()
                history[pid].append(now)
                durations = history[pid]
                if durations:
                    earliest = durations[0]
                    duration = now - earliest
                    if duration >= duration_seconds:
                        high_mem.append({
                            "pid": pid,
                            "mem_percent": mem,
                            "duration": round(duration, 1),
                        })
            else:
                if pid in history:
                    del history[pid]

        total_anomalies = len(zombies) + len(high_cpu) + len(high_mem)

        return {
            "zombies": zombies,
            "high_cpu": high_cpu,
            "high_mem": high_mem,
            "total_anomalies": total_anomalies,
        }

    # ── 告警配置 ──────────────────────────────────────────────────

    def get_alert_config(self, alias: str) -> dict[str, Any]:
        """获取告警阈值配置。

        优先从 settings_service 加载，如果不存在则返回默认值。
        配置按 alias 独立存储。
        """
        from app.services.settings_service import settings_service

        key = f"process_alerts_{alias}"
        config = settings_service.get(key)
        if config and isinstance(config, dict):
            # 合并默认值
            merged = dict(DEFAULT_ALERT_CONFIG)
            merged.update(config)
            return merged
        return dict(DEFAULT_ALERT_CONFIG)

    def save_alert_config(self, alias: str, config: dict[str, Any]) -> bool:
        """保存告警阈值配置到 settings_service。"""
        from app.services.settings_service import settings_service

        key = f"process_alerts_{alias}"
        try:
            settings_service.set(key, config)
            return True
        except Exception as e:
            logger.error(f"[process] 保存告警配置失败: {e}")
            return False

    # ── WebSocket 流式推送 ────────────────────────────────────────

    def subscribe(self, alias: str, ws: Any) -> None:
        """订阅进程流数据。"""
        self._stream_subscribers[alias].add(ws)

    def unsubscribe(self, alias: str, ws: Any) -> None:
        """取消订阅进程流数据。"""
        self._stream_subscribers[alias].discard(ws)

    async def start_streaming(self, alias: str, interval: float = 3.0) -> None:
        """启动进程流式推送。

        定期获取进程列表并推送给所有订阅者。
        """
        if alias in self._stream_tasks and not self._stream_tasks[alias].done():
            return

        async def _stream() -> None:
            while True:
                start_time = time.time()
                try:
                    loop = asyncio.get_event_loop()
                    processes = await loop.run_in_executor(
                        None, self.get_all_processes, alias
                    )
                    data = {
                        "type": "process_stream",
                        "processes": processes,
                        "count": len(processes),
                        "timestamp": time.time(),
                    }
                    dead_ws = set()
                    for ws in self._stream_subscribers.get(alias, set()):
                        try:
                            await ws.send_json(data)
                        except Exception:
                            dead_ws.add(ws)
                    self._stream_subscribers[alias] -= dead_ws
                except Exception as e:
                    logger.error(f"[process-stream] 流式推送异常: {e}")
                sleep_time = max(0, interval - (time.time() - start_time))
                await asyncio.sleep(sleep_time)

        self._stream_tasks[alias] = asyncio.create_task(_stream())

    async def stop_streaming(self, alias: str) -> None:
        """停止进程流式推送。"""
        if alias in self._stream_tasks:
            self._stream_tasks[alias].cancel()
            try:
                await self._stream_tasks[alias]
            except asyncio.CancelledError:
                pass
            del self._stream_tasks[alias]


# 模块级单例
process_service = ProcessService()
