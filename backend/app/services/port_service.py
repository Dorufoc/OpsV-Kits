from __future__ import annotations

import logging
import platform
import re
import subprocess
from typing import Any

logger = logging.getLogger(__name__)


class PortService:
    """本机端口占用管理服务。"""

    def get_port_list(self) -> list[dict[str, Any]]:
        """获取所有端口占用信息：协议、端口号、PID、进程名、状态。"""
        system = platform.system()
        if system == "Windows":
            return self._get_ports_windows()
        return self._get_ports_unix()

    def _get_ports_windows(self) -> list[dict[str, Any]]:
        """Windows: 使用 netstat -ano 获取端口信息。"""
        try:
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True,
                timeout=15,
                encoding="utf-8",
                errors="replace",
            )
            lines = result.stdout.strip().split("\n")
        except Exception as e:
            logger.error(f"[port] netstat failed: {e}")
            return []

        ports: list[dict[str, Any]] = []
        for line in lines:
            parts = line.split()
            if len(parts) < 5:
                continue
            proto = parts[0].upper()
            if proto not in ("TCP", "UDP"):
                continue

            local_addr = parts[1]
            state = parts[3] if proto == "TCP" and len(parts) >= 4 else ""
            pid_str = parts[-1]

            if not pid_str.isdigit():
                continue
            pid = int(pid_str)

            port_num = self._extract_port(local_addr)
            if port_num is None:
                continue

            # Windows TCP state mapping
            status = self._map_tcp_state(state, proto)

            proc_name = self._get_process_name(pid)

            ports.append({
                "protocol": proto,
                "port": port_num,
                "local_address": local_addr,
                "pid": pid,
                "process_name": proc_name,
                "status": state if proto == "TCP" else "",
            })

        # sort by port number
        ports.sort(key=lambda x: (x["port"], x["protocol"]))
        return ports

    def _get_ports_unix(self) -> list[dict[str, Any]]:
        """Linux/Mac: 使用 ss 或 lsof 获取端口信息。"""
        ports = self._try_ss()
        if not ports:
            ports = self._try_lsof()
        return ports

    def _try_ss(self) -> list[dict[str, Any]]:
        """尝试用 ss 命令获取端口信息。"""
        try:
            result = subprocess.run(
                ["ss", "-tunlp"],
                capture_output=True,
                text=True,
                timeout=15,
                encoding="utf-8",
                errors="replace",
            )
            lines = result.stdout.strip().split("\n")
        except FileNotFoundError:
            return []
        except Exception as e:
            logger.error(f"[port] ss failed: {e}")
            return []

        ports: list[dict[str, Any]] = []
        for line in lines[1:]:
            parts = line.split()
            if len(parts) < 5:
                continue

            proto_raw = parts[0].lower()
            if proto_raw == "tcp":
                proto = "TCP"
            elif proto_raw == "udp":
                proto = "UDP"
            else:
                continue

            local_addr = parts[4]
            state = parts[1] if proto == "TCP" else ""

            pid, proc_name = self._parse_ss_process(parts)

            port_num = self._extract_port(local_addr)
            if port_num is None:
                continue

            status = self._map_tcp_state(state, proto)

            ports.append({
                "protocol": proto,
                "port": port_num,
                "local_address": local_addr,
                "pid": pid,
                "process_name": proc_name,
                "status": status,
            })

        ports.sort(key=lambda x: (x["port"], x["protocol"]))
        return ports

    def _try_lsof(self) -> list[dict[str, Any]]:
        """尝试用 lsof 命令获取端口信息。"""
        try:
            result = subprocess.run(
                ["lsof", "-i", "-P", "-n"],
                capture_output=True,
                text=True,
                timeout=15,
                encoding="utf-8",
                errors="replace",
            )
            lines = result.stdout.strip().split("\n")
        except FileNotFoundError:
            return []
        except Exception as e:
            logger.error(f"[port] lsof failed: {e}")
            return []

        ports: list[dict[str, Any]] = []
        for line in lines[1:]:
            parts = line.split()
            if len(parts) < 9:
                continue

            proc_name = parts[0]
            pid = int(parts[1]) if parts[1].isdigit() else 0
            proto = parts[7].upper() if len(parts) > 7 else ""
            if proto not in ("TCP", "UDP"):
                continue

            addr_col = parts[8] if len(parts) > 8 else ""
            # lsof format: *:8080 or 127.0.0.1:8080 or [::1]:8080
            port_num = self._extract_port(addr_col)
            if port_num is None:
                continue

            state = ""
            status = ""
            if proto == "TCP" and len(parts) > 9:
                state = parts[9].strip("()")
                status = self._map_tcp_state(state, proto)

            ports.append({
                "protocol": proto,
                "port": port_num,
                "local_address": addr_col,
                "pid": pid,
                "process_name": proc_name,
                "status": status,
            })

        ports.sort(key=lambda x: (x["port"], x["protocol"]))
        return ports

    def check_port(self, port: int) -> dict[str, Any]:
        """检测指定端口是否被占用。"""
        all_ports = self.get_port_list()
        occupied = [p for p in all_ports if p["port"] == port]
        return {
            "port": port,
            "occupied": len(occupied) > 0,
            "details": occupied,
        }

    def kill_by_port(self, port: int, force: bool = False) -> dict[str, Any]:
        """终止占用指定端口的进程。"""
        check = self.check_port(port)
        if not check["occupied"]:
            return {
                "success": False,
                "message": f"端口 {port} 未被占用",
            }

        killed = []
        failed = []

        for proc in check["details"]:
            pid = proc["pid"]
            result = self._kill_process(pid, force)
            if result["success"]:
                killed.append({"pid": pid, "process_name": proc["process_name"]})
            else:
                failed.append({"pid": pid, "process_name": proc["process_name"], "error": result["message"]})

        if failed and not killed:
            return {
                "success": False,
                "message": f"无法终止端口 {port} 上的进程",
                "killed": killed,
                "failed": failed,
            }

        return {
            "success": True,
            "message": f"已终止端口 {port} 上 {len(killed)} 个进程",
            "killed": killed,
            "failed": failed,
        }

    def kill_by_pid(self, pid: int, force: bool = False) -> dict[str, Any]:
        """通过 PID 终止进程。"""
        proc_name = self._get_process_name(pid)
        result = self._kill_process(pid, force)
        if result["success"]:
            result["process_name"] = proc_name
        return result

    def _kill_process(self, pid: int, force: bool = False) -> dict[str, Any]:
        """终止本机进程。"""
        signal_flag = "-9" if force else "-15"
        system = platform.system()
        try:
            if system == "Windows":
                cmd = ["taskkill", "/F", "/PID", str(pid)] if force else ["taskkill", "/PID", str(pid)]
            else:
                cmd = ["kill", signal_flag, str(pid)]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode == 0:
                return {"success": True, "message": f"进程 {pid} 已终止"}
            else:
                stderr = result.stderr.strip()
                return {"success": False, "message": stderr or f"终止进程 {pid} 失败 (code={result.returncode})"}
        except Exception as e:
            logger.error(f"[port] kill {pid} failed: {e}")
            return {"success": False, "message": str(e)}

    def _get_process_name(self, pid: int) -> str:
        """通过 PID 获取进程名。"""
        system = platform.system()
        try:
            if system == "Windows":
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    encoding="utf-8",
                    errors="replace",
                )
                if result.stdout.strip():
                    # CSV format: "name","pid",...
                    line = result.stdout.strip().split("\n")[0]
                    parts = line.split('","')
                    if parts:
                        return parts[0].strip('"')
            else:
                if pid > 0:
                    try:
                        with open(f"/proc/{pid}/comm", "r") as f:
                            return f.read().strip()
                    except (FileNotFoundError, PermissionError):
                        pass

                    result = subprocess.run(
                        ["ps", "-p", str(pid), "-o", "comm="],
                        capture_output=True,
                        text=True,
                        timeout=10,
                        encoding="utf-8",
                        errors="replace",
                    )
                    if result.stdout.strip():
                        return result.stdout.strip()
        except Exception as e:
            logger.warning(f"[port] get process name for pid={pid}: {e}")

        return "unknown"

    @staticmethod
    def _extract_port(address: str) -> int | None:
        """从地址字符串中提取端口号。支持 IPv4:port, [IPv6]:port, *:port。"""
        try:
            # IPv6: [::1]:8080 or [::]:8080
            if address.startswith("["):
                bracket_end = address.rfind("]")
                if bracket_end != -1 and bracket_end + 1 < len(address):
                    port_str = address[bracket_end + 2:]  # skip "]:"
                    return int(port_str)
                return None

            # IPv4: 127.0.0.1:8080 or *:8080 or :::8080
            last_colon = address.rfind(":")
            if last_colon == -1:
                return None

            # Handle :::port (IPv6 without brackets)
            colon_count = address.count(":")
            if colon_count > 1:
                # last colon before port
                port_str = address[last_colon + 1 :]
                port = int(port_str)
                return port if 1 <= port <= 65535 else None

            port_str = address[last_colon + 1 :]
            port = int(port_str)
            return port if 1 <= port <= 65535 else None
        except (ValueError, IndexError):
            return None

    @staticmethod
    def _map_tcp_state(state: str, proto: str) -> str:
        """将 TCP state 转换为可读状态。"""
        if proto != "TCP" or not state:
            return ""
        state_map = {
            "LISTEN": "LISTEN",
            "LISTENING": "LISTEN",
            "ESTABLISHED": "ESTABLISHED",
            "ESTAB": "ESTABLISHED",
            "SYN_SENT": "SYN_SENT",
            "SYN_RECV": "SYN_RECV",
            "FIN_WAIT1": "FIN_WAIT",
            "FIN_WAIT2": "FIN_WAIT",
            "TIME_WAIT": "TIME_WAIT",
            "CLOSE": "CLOSED",
            "CLOSED": "CLOSED",
            "CLOSE_WAIT": "CLOSE_WAIT",
            "LAST_ACK": "LAST_ACK",
            "CLOSING": "CLOSING",
        }
        return state_map.get(state.upper(), state)

    @staticmethod
    def _parse_ss_process(parts: list[str]) -> tuple[int, str]:
        """从 ss 输出行解析 PID 和进程名。"""
        pid = 0
        proc_name = "unknown"
        # ss -tunlp 输出中的 process 列: users:(("name",pid=1234,fd=5))
        for part in parts:
            if "pid=" in part:
                match = re.search(r"pid=(\d+)", part)
                if match:
                    pid = int(match.group(1))
            if '("' in part:
                match = re.search(r'"([^"]+)"', part)
                if match:
                    proc_name = match.group(1)
        return pid, proc_name


port_service = PortService()
