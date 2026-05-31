from __future__ import annotations

import json
from typing import Any, Optional

from app.services.ssh_account_service import ssh_account_service


class SystemService:
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

    # ── 系统信息 ──────────────────────────────────────────────────

    def get_system_info(self, alias: str) -> dict[str, Any]:
        info: dict[str, Any] = {}
        _, info["hostname"], _ = self._exec(alias, "hostname 2>/dev/null", 5)
        _, os_release, _ = self._exec(alias, "cat /etc/redhat-release 2>/dev/null || cat /etc/os-release 2>/dev/null | head -5", 5)
        info["os"] = os_release[:200] if os_release else "unknown"
        _, uptime, _ = self._exec(alias, "uptime -p 2>/dev/null || uptime 2>/dev/null", 5)
        info["uptime"] = uptime[:200] if uptime else ""
        _, kernel, _ = self._exec(alias, "uname -r 2>/dev/null", 5)
        info["kernel"] = kernel.strip()
        return info

    def get_performance(self, alias: str) -> dict[str, Any]:
        result: dict[str, Any] = {}

        _, cpu_out, _ = self._exec(alias, "top -bn1 | head -3 2>/dev/null", 10)
        result["cpu_raw"] = cpu_out

        _, cpu_cores, _ = self._exec(alias, "nproc 2>/dev/null", 5)
        result["cpu_cores"] = cpu_cores.strip()

        _, cpu_model, _ = self._exec(alias, "lscpu 2>/dev/null | grep 'Model name' | cut -d: -f2 | xargs", 5)
        result["cpu_model"] = cpu_model.strip() if cpu_model else ""

        _, mem_out, _ = self._exec(alias, "free -b 2>/dev/null | grep Mem", 5)
        mem_parts = mem_out.split()
        if len(mem_parts) >= 3:
            total = int(mem_parts[1])
            used = int(mem_parts[2])
            result["memory"] = {
                "total": total,
                "used": used,
                "available": total - used,
                "usage_percent": round(used / total * 100, 1) if total > 0 else 0,
            }

        _, disk_out, _ = self._exec(alias, "df -B1 --total 2>/dev/null | grep '^total' || df -B1 / 2>/dev/null | tail -1", 5)
        disk_parts = disk_out.split()
        if len(disk_parts) >= 3:
            dtotal = int(disk_parts[1])
            dused = int(disk_parts[2])
            result["disk"] = {
                "total": dtotal,
                "used": dused,
                "available": dtotal - dused,
                "usage_percent": round(dused / dtotal * 100, 1) if dtotal > 0 else 0,
            }

        _, load_out, _ = self._exec(alias, "cat /proc/loadavg 2>/dev/null | awk '{print $1,$2,$3}'", 5)
        result["loadavg"] = load_out.strip()

        return result

    def get_disks_detail(self, alias: str) -> list[dict[str, Any]]:
        code, stdout, _ = self._exec(alias, "df -B1 --type=xfs --type=ext4 --type=ext3 2>/dev/null | tail -n +2 || df -B1 2>/dev/null | tail -n +2", 10)
        mounts = []
        for line in stdout.split("\n") if stdout else []:
            parts = line.split()
            if len(parts) >= 6:
                total = int(parts[1]) if parts[1].isdigit() else 0
                used = int(parts[2]) if parts[2].isdigit() else 0
                mounts.append({
                    "filesystem": parts[0],
                    "size": total,
                    "used": used,
                    "available": total - used,
                    "usage_percent": round(used / total * 100, 1) if total > 0 else 0,
                    "mount": parts[5],
                })
        return mounts

    # ── 系统操作 ──────────────────────────────────────────────────

    def reboot(self, alias: str) -> str:
        self._exec(alias, "sudo reboot 2>/dev/null || reboot 2>/dev/null", 5)
        return "服务器正在重启..."

    def shutdown(self, alias: str) -> str:
        self._exec(alias, "sudo poweroff 2>/dev/null || poweroff 2>/dev/null", 5)
        return "服务器正在关机..."

    def reload_network(self, alias: str) -> str:
        code, _, stderr = self._exec(alias, "sudo systemctl restart network 2>/dev/null || sudo systemctl restart NetworkManager 2>/dev/null", 30)
        if code != 0:
            code, _, stderr = self._exec(alias, "sudo service network restart 2>/dev/null", 30)
        if code == 0:
            return "网络服务已重启"
        return f"网络重启失败: {stderr}"

    def reload_ssh(self, alias: str) -> str:
        code, _, stderr = self._exec(alias, "sudo systemctl restart sshd 2>/dev/null || sudo systemctl restart ssh 2>/dev/null", 15)
        if code == 0:
            return "SSH 服务已重启"
        return f"SSH 重启失败: {stderr}"

    def clear_cache(self, alias: str) -> str:
        code, _, stderr = self._exec(alias, "sudo sync && echo 3 > /proc/sys/vm/drop_caches 2>/dev/null", 10)
        if code == 0:
            return "缓存已清理"
        return f"缓存清理失败: {stderr}"

    def check_selinux(self, alias: str) -> dict[str, Any]:
        code, stdout, _ = self._exec(alias, "getenforce 2>/dev/null", 5)
        status = stdout.strip() if code == 0 else "unknown"
        return {"status": status, "enabled": status.upper() != "DISABLED"}

    def set_selinux(self, alias: str, mode: str) -> str:
        if mode not in ("enforcing", "permissive"):
            return f"无效模式: {mode}"
        code, _, stderr = self._exec(alias, f"sudo setenforce 0 2>/dev/null" if mode == "permissive" else f"sudo setenforce 1 2>/dev/null", 10)
        if code == 0:
            return f"SELinux 已切换为 {mode}"
        return f"切换失败: {stderr}"

    # ── 防火墙管理 (CentOS firewalld) ────────────────────────────

    def get_firewall_status(self, alias: str) -> dict[str, Any]:
        result: dict[str, Any] = {"installed": False, "active": False}
        code, stdout, _ = self._exec(alias, "which firewall-cmd 2>/dev/null", 5)
        if code == 0:
            result["installed"] = True
            code2, out2, _ = self._exec(alias, "sudo firewall-cmd --state 2>/dev/null", 5)
            result["active"] = code2 == 0
        return result

    def set_firewall(self, alias: str, enable: bool) -> str:
        action = "start" if enable else "stop"
        code, _, stderr = self._exec(alias, f"sudo systemctl {action} firewalld 2>/dev/null", 30)
        if code != 0:
            code, _, stderr = self._exec(alias, f"sudo service firewalld {action} 2>/dev/null", 30)
        if code == 0:
            return f"防火墙已{'开启' if enable else '关闭'}"
        return f"操作失败: {stderr}"

    def list_firewall_rules(self, alias: str) -> list[dict[str, Any]]:
        code, stdout, _ = self._exec(alias, "sudo firewall-cmd --list-all 2>/dev/null", 10)
        rules: list[dict[str, Any]] = []
        if code != 0:
            code, stdout, _ = self._exec(alias, "sudo iptables -L INPUT -n --line-numbers 2>/dev/null", 10)
            if code == 0:
                rules.append({"source": "iptables", "raw": stdout})
            return rules

        lines = stdout.strip().split("\n")
        current_zone = ""
        ports: list[str] = []
        sources: list[str] = []
        services: list[str] = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("  ports:"):
                continue
            if "ports:" in line and not line.startswith("  "):
                continue

            low = line.lower()
            if low.startswith("target:"):
                continue
            if low.startswith("icmp-block-inversion:"):
                continue
            if low.startswith("icmp-block:"):
                continue
            if low.startswith("masquerade:"):
                continue
            if low.startswith("forward-ports:"):
                continue
            if low.startswith("source-ports:"):
                continue

            parts = line.split()
            if len(parts) >= 2 and parts[1].strip():
                val = parts[0]
                if val.startswith("ports:"):
                    ports.append(val.split(":", 1)[1].strip() if ":" in val else "")
                elif val.startswith("services:"):
                    services.append(val.split(":", 1)[1].strip() if ":" in val else "")
                elif val.startswith("sources:"):
                    sources.append(val.split(":", 1)[1].strip() if ":" in val else "")

        return [{
            "type": "port",
            "value": p,
            "zone": current_zone or "public",
        } for p in ports if p] + [{
            "type": "service",
            "value": s,
            "zone": current_zone or "public",
        } for s in services if s]

    def add_port_rule(self, alias: str, port: int, protocol: str = "tcp", zone: str = "public") -> str:
        code, _, stderr = self._exec(
            alias,
            f"sudo firewall-cmd --zone={zone} --add-port={port}/{protocol} --permanent 2>/dev/null",
            10,
        )
        if code == 0:
            self._exec(alias, "sudo firewall-cmd --reload 2>/dev/null", 10)
            return f"端口 {port}/{protocol} 已添加到 {zone} 区域（永久）"
        return f"添加失败: {stderr}"

    def remove_port_rule(self, alias: str, port: int, protocol: str = "tcp", zone: str = "public") -> str:
        code, _, stderr = self._exec(
            alias,
            f"sudo firewall-cmd --zone={zone} --remove-port={port}/{protocol} --permanent 2>/dev/null",
            10,
        )
        if code == 0:
            self._exec(alias, "sudo firewall-cmd --reload 2>/dev/null", 10)
            return f"端口 {port}/{protocol} 已从 {zone} 区域删除"
        return f"删除失败: {stderr}"

    def add_service_rule(self, alias: str, service: str, zone: str = "public") -> str:
        code, _, stderr = self._exec(
            alias,
            f"sudo firewall-cmd --zone={zone} --add-service={service} --permanent 2>/dev/null",
            10,
        )
        if code == 0:
            self._exec(alias, "sudo firewall-cmd --reload 2>/dev/null", 10)
            return f"服务 {service} 已添加到 {zone} 区域"
        return f"添加失败: {stderr}"

    def remove_service_rule(self, alias: str, service: str, zone: str = "public") -> str:
        code, _, stderr = self._exec(
            alias,
            f"sudo firewall-cmd --zone={zone} --remove-service={service} --permanent 2>/dev/null",
            10,
        )
        if code == 0:
            self._exec(alias, "sudo firewall-cmd --reload 2>/dev/null", 10)
            return f"服务 {service} 已从 {zone} 区域删除"
        return f"删除失败: {stderr}"

    def get_firewall_zones(self, alias: str) -> list[str]:
        code, stdout, _ = self._exec(alias, "sudo firewall-cmd --get-active-zones 2>/dev/null", 5)
        zones = []
        for line in stdout.strip().split("\n") if stdout else []:
            line = line.strip()
            if line and ":" not in line and "interfaces" not in line.lower():
                zones.append(line)
        return zones or ["public"]

    # ── 工具箱：扩展系统操作 ──────────────────────────────────────

    def sync_time(self, alias: str) -> str:
        code, _, stderr = self._exec(alias, "sudo chronyd -q 2>/dev/null || sudo ntpdate -s pool.ntp.org 2>/dev/null", 30)
        if code == 0:
            return "系统时间已同步"
        code2, _, _ = self._exec(alias, "sudo timedatectl set-ntp true 2>/dev/null", 10)
        if code2 == 0:
            return "NTP 时间同步已启用"
        return f"时间同步失败: {stderr}"

    def set_hostname(self, alias: str, hostname: str) -> str:
        code, _, stderr = self._exec(alias, f"sudo hostnamectl set-hostname {hostname} 2>/dev/null", 10)
        if code == 0:
            return f"主机名已修改为 {hostname}"
        return f"修改失败: {stderr}"

    def get_timezone(self, alias: str) -> dict[str, Any]:
        code, stdout, _ = self._exec(alias, "timedatectl show --property=Timezone --value 2>/dev/null || cat /etc/timezone 2>/dev/null", 5)
        tz = stdout.strip()
        _, tz_list, _ = self._exec(alias, "timedatectl list-timezones 2>/dev/null | grep Asia/Shanghai || echo 'Asia/Shanghai'", 5)
        return {"timezone": tz, "suggested": tz_list.strip()}

    def set_timezone(self, alias: str, timezone: str) -> str:
        code, _, stderr = self._exec(alias, f"sudo timedatectl set-timezone {timezone} 2>/dev/null", 10)
        if code == 0:
            return f"时区已修改为 {timezone}"
        return f"修改失败: {stderr}"

    # ── 工具箱：诊断工具 ──────────────────────────────────────────

    def get_logged_users(self, alias: str) -> dict[str, Any]:
        _, who_out, _ = self._exec(alias, "who 2>/dev/null", 5)
        _, w_out, _ = self._exec(alias, "w -i 2>/dev/null", 5)
        users: list[dict[str, str]] = []
        for line in who_out.split("\n") if who_out else []:
            parts = line.split()
            if len(parts) >= 5:
                users.append({
                    "user": parts[0],
                    "tty": parts[1],
                    "login_time": f"{parts[2]} {parts[3]}",
                    "from": parts[4] if parts[4].startswith("(") else "",
                })
        return {"users": users, "raw": w_out}

    def get_boot_time(self, alias: str) -> dict[str, Any]:
        _, boot_out, _ = self._exec(alias, "who -b 2>/dev/null", 5)
        _, uptime_out, _ = self._exec(alias, "uptime -s 2>/dev/null", 5)
        return {"boot_time": boot_out.strip(), "since": uptime_out.strip()}

    def get_kernel_modules(self, alias: str) -> dict[str, Any]:
        _, lsmod_out, _ = self._exec(alias, "lsmod 2>/dev/null | head -50", 5)
        _, count_out, _ = self._exec(alias, "lsmod 2>/dev/null | wc -l", 5)
        modules: list[dict[str, str]] = []
        lines = (lsmod_out.split("\n") if lsmod_out else [])[1:]
        for line in lines:
            parts = line.split()
            if len(parts) >= 3:
                modules.append({
                    "name": parts[0],
                    "size": parts[1],
                    "used_by": parts[2] if len(parts) > 2 else "0",
                })
        return {"modules": modules, "count": int(count_out.strip()) - 1 if count_out.strip().isdigit() else 0}

    def get_enabled_services(self, alias: str) -> dict[str, Any]:
        _, svc_out, _ = self._exec(alias, "systemctl list-unit-files --type=service --state=enabled 2>/dev/null | head -40", 5)
        return {"services": svc_out}

    def get_dns_config(self, alias: str) -> dict[str, Any]:
        _, resolv, _ = self._exec(alias, "cat /etc/resolv.conf 2>/dev/null", 5)
        return {"resolv_conf": resolv}

    def get_ulimit(self, alias: str) -> dict[str, Any]:
        _, ulimit_out, _ = self._exec(alias, "ulimit -a 2>/dev/null", 5)
        return {"ulimit": ulimit_out}

    # ── 工具箱：清理维护 ──────────────────────────────────────────

    def get_swap_status(self, alias: str) -> dict[str, Any]:
        _, swapon_out, _ = self._exec(alias, "swapon --show 2>/dev/null", 5)
        _, free_out, _ = self._exec(alias, "free -h 2>/dev/null | grep -i swap", 5)
        return {"swapon": swapon_out, "free": free_out}

    def swap_refresh(self, alias: str) -> str:
        code, _, stderr = self._exec(alias, "sudo swapoff -a 2>/dev/null && sudo swapon -a 2>/dev/null", 30)
        if code == 0:
            return "SWAP 已刷新"
        return f"刷新失败: {stderr}"

    def cleanup_old_kernels(self, alias: str) -> str:
        code, stdout, stderr = self._exec(
            alias,
            "sudo dnf remove --oldinstallonly --setopt=installonly_limit=2 -y 2>/dev/null || sudo package-cleanup --oldkernels --count=2 -y 2>/dev/null",
            120,
        )
        if code == 0:
            return "旧内核已清理" if not stdout else stdout.strip()[:200]
        if "Nothing to do" in stderr or "No old kernels" in stderr:
            return "没有旧内核需要清理"
        return f"清理失败: {stderr}"

    def cleanup_journal(self, alias: str, days: int = 7) -> str:
        code, _, stderr = self._exec(alias, f"sudo journalctl --vacuum-time={days}d 2>/dev/null", 30)
        if code == 0:
            return f"已清理 {days} 天前的 journal 日志"
        return f"清理失败: {stderr}"

    def check_updates(self, alias: str) -> dict[str, Any]:
        code, stdout, _ = self._exec(alias, "dnf check-update 2>/dev/null || yum check-update 2>/dev/null", 60)
        lines = stdout.strip().split("\n") if stdout else []
        count = 0
        updates: list[str] = []
        for line in lines:
            if line.strip() and not line.startswith("Loading") and not line.startswith("Last metadata"):
                updates.append(line.strip())
                count += 1
        return {"update_count": count, "updates": updates[:30], "raw": stdout}


system_service = SystemService()
