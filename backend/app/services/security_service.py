from __future__ import annotations

import re
from typing import Any, Optional

from app.services.ssh_account_service import ssh_account_service


class SecurityService:
    # ── SSH 执行基础 ──────────────────────────────────────────────

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

    def _exec_stream(self, alias: str, cmd: str, timeout: float = 60.0):
        conn = self._conn(alias)
        try:
            code, stdout, stderr = conn.manager.exec_command(cmd, timeout=timeout)
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            yield code, stdout, stderr
        finally:
            ssh_account_service.pool.release_connection(conn)

    # ── 防火墙引擎自动检测 ─────────────────────────────────────────

    def detect_firewall_backend(self, alias: str) -> dict[str, Any]:
        code, _, _ = self._exec(alias, "which firewall-cmd 2>/dev/null", 5)
        if code == 0:
            code2, _, _ = self._exec(alias, "sudo firewall-cmd --state 2>/dev/null", 5)
            if code2 == 0:
                return {"backend": "firewalld", "running": True}
        code, _, _ = self._exec(alias, "which ufw 2>/dev/null", 5)
        if code == 0:
            code2, out2, _ = self._exec(alias, "sudo ufw status 2>/dev/null | head -1", 5)
            if code2 == 0 and ("active" in out2.lower() or "inactive" in out2.lower()):
                return {"backend": "ufw", "running": "active" in out2.lower()}
        code, _, _ = self._exec(alias, "which iptables 2>/dev/null", 5)
        if code == 0:
            return {"backend": "iptables", "running": True}
        return {"backend": "unknown", "running": False}

    # ── 端口规则管理 ──────────────────────────────────────────────

    def list_all_rules(self, alias: str) -> list[dict[str, Any]]:
        backend_info = self.detect_firewall_backend(alias)
        backend = backend_info.get("backend", "unknown")
        rules: list[dict[str, Any]] = []
        if backend == "firewalld":
            code, stdout, _ = self._exec(alias, "sudo firewall-cmd --list-all 2>/dev/null", 10)
            if code == 0:
                for line in stdout.split("\n"):
                    line = line.strip()
                    if line.startswith("ports:"):
                        val = line.split(":", 1)[1].strip()
                        for p in val.split():
                            if "/" in p:
                                port, proto = p.split("/", 1)
                                rules.append({"port": port, "protocol": proto, "backend": "firewalld"})
                            else:
                                rules.append({"port": p, "protocol": "tcp", "backend": "firewalld"})
        elif backend == "ufw":
            code, stdout, _ = self._exec(alias, "sudo ufw status 2>/dev/null", 10)
            if code == 0:
                for line in stdout.split("\n"):
                    line = line.strip()
                    if not line or line.startswith("Status") or line.startswith("To"):
                        continue
                    parts = line.split()
                    if len(parts) >= 2:
                        to_field = parts[0]
                        if "/" in to_field:
                            port, proto = to_field.split("/", 1)
                            rules.append({"port": port, "protocol": proto, "backend": "ufw", "raw": line})
                        elif to_field.isdigit():
                            rules.append({"port": to_field, "protocol": "any", "backend": "ufw", "raw": line})
        elif backend == "iptables":
            code, stdout, _ = self._exec(alias, "sudo iptables -L INPUT -n --line-numbers 2>/dev/null", 10)
            if code == 0:
                for line in stdout.split("\n"):
                    line = line.strip()
                    if not line or line.startswith("Chain") or line.startswith("num"):
                        continue
                    parts = line.split()
                    if len(parts) >= 7 and parts[5] == "dpt:":
                        rules.append({"port": parts[6], "protocol": parts[3], "backend": "iptables", "raw": line})
        return rules

    def add_port_rule(self, alias: str, port: int, protocol: str = "tcp", zone: str = "public") -> str:
        backend = self.detect_firewall_backend(alias).get("backend", "unknown")
        if backend == "firewalld":
            code, _, stderr = self._exec(
                alias,
                f"sudo firewall-cmd --zone={zone} --add-port={port}/{protocol} --permanent 2>/dev/null",
                10,
            )
            if code == 0:
                self._exec(alias, "sudo firewall-cmd --reload 2>/dev/null", 10)
                return f"端口 {port}/{protocol} 已添加到 {zone} 区域（永久）"
            return f"添加失败: {stderr}"
        elif backend == "ufw":
            code, _, stderr = self._exec(
                alias,
                f"sudo ufw allow {port}/{protocol} 2>/dev/null",
                10,
            )
            if code == 0:
                return f"端口 {port}/{protocol} 已通过 ufw 允许"
            return f"添加失败: {stderr}"
        elif backend == "iptables":
            code, _, stderr = self._exec(
                alias,
                f"sudo iptables -A INPUT -p {protocol} --dport {port} -j ACCEPT 2>/dev/null",
                10,
            )
            if code == 0:
                return f"端口 {port}/{protocol} 已通过 iptables 允许"
            return f"添加失败: {stderr}"
        return "未检测到支持的防火墙后端"

    def remove_port_rule(self, alias: str, port: int, protocol: str = "tcp", zone: str = "public") -> str:
        backend = self.detect_firewall_backend(alias).get("backend", "unknown")
        if backend == "firewalld":
            code, _, stderr = self._exec(
                alias,
                f"sudo firewall-cmd --zone={zone} --remove-port={port}/{protocol} --permanent 2>/dev/null",
                10,
            )
            if code == 0:
                self._exec(alias, "sudo firewall-cmd --reload 2>/dev/null", 10)
                return f"端口 {port}/{protocol} 已从 {zone} 区域删除"
            return f"删除失败: {stderr}"
        elif backend == "ufw":
            code, _, stderr = self._exec(
                alias,
                f"sudo ufw delete allow {port}/{protocol} 2>/dev/null",
                10,
            )
            if code == 0:
                return f"端口 {port}/{protocol} 已从 ufw 删除"
            return f"删除失败: {stderr}"
        elif backend == "iptables":
            code, _, stderr = self._exec(
                alias,
                f"sudo iptables -D INPUT -p {protocol} --dport {port} -j ACCEPT 2>/dev/null",
                10,
            )
            if code == 0:
                return f"端口 {port}/{protocol} 已从 iptables 删除"
            return f"删除失败: {stderr}"
        return "未检测到支持的防火墙后端"

    # ── IP 允许/拒绝管理 ──────────────────────────────────────────

    def list_ip_rules(self, alias: str) -> list[dict[str, Any]]:
        backend = self.detect_firewall_backend(alias).get("backend", "unknown")
        rules: list[dict[str, Any]] = []
        if backend == "firewalld":
            code, stdout, _ = self._exec(alias, "sudo firewall-cmd --list-rich-rules 2>/dev/null", 10)
            if code == 0:
                for line in stdout.split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    rules.append({"backend": "firewalld", "raw": line})
        elif backend == "ufw":
            code, stdout, _ = self._exec(alias, "sudo ufw status 2>/dev/null", 10)
            if code == 0:
                for line in stdout.split("\n"):
                    line = line.strip()
                    if not line or line.startswith("Status") or line.startswith("To"):
                        continue
                    if "ALLOW" in line or "DENY" in line:
                        rules.append({"backend": "ufw", "raw": line})
        elif backend == "iptables":
            code, stdout, _ = self._exec(alias, "sudo iptables -L INPUT -n --line-numbers 2>/dev/null", 10)
            if code == 0:
                for line in stdout.split("\n"):
                    line = line.strip()
                    if not line or line.startswith("Chain") or line.startswith("num"):
                        continue
                    if "source" in line.lower():
                        rules.append({"backend": "iptables", "raw": line})
        return rules

    def add_ip_rule(self, alias: str, ip: str, action: str = "allow", zone: str = "public") -> str:
        if action == "allow":
            return self.allow_ip(alias, ip, zone)
        return self.deny_ip(alias, ip, zone)

    def allow_ip(self, alias: str, ip: str, zone: str = "public") -> str:
        backend = self.detect_firewall_backend(alias).get("backend", "unknown")
        if backend == "firewalld":
            code, _, stderr = self._exec(
                alias,
                f"sudo firewall-cmd --zone={zone} --add-rich-rule='rule family=\"ipv4\" source address=\"{ip}\" accept' --permanent 2>/dev/null",
                10,
            )
            if code == 0:
                self._exec(alias, "sudo firewall-cmd --reload 2>/dev/null", 10)
                return f"IP {ip} 已允许（firewalld rich rule）"
            return f"添加失败: {stderr}"
        elif backend == "ufw":
            code, _, stderr = self._exec(
                alias,
                f"sudo ufw allow from {ip} 2>/dev/null",
                10,
            )
            if code == 0:
                return f"IP {ip} 已通过 ufw 允许"
            return f"添加失败: {stderr}"
        elif backend == "iptables":
            code, _, stderr = self._exec(
                alias,
                f"sudo iptables -A INPUT -s {ip} -j ACCEPT 2>/dev/null",
                10,
            )
            if code == 0:
                return f"IP {ip} 已通过 iptables 允许"
            return f"添加失败: {stderr}"
        return "未检测到支持的防火墙后端"

    def deny_ip(self, alias: str, ip: str, zone: str = "public") -> str:
        backend = self.detect_firewall_backend(alias).get("backend", "unknown")
        if backend == "firewalld":
            code, _, stderr = self._exec(
                alias,
                f"sudo firewall-cmd --zone={zone} --add-rich-rule='rule family=\"ipv4\" source address=\"{ip}\" reject' --permanent 2>/dev/null",
                10,
            )
            if code == 0:
                self._exec(alias, "sudo firewall-cmd --reload 2>/dev/null", 10)
                return f"IP {ip} 已拒绝（firewalld rich rule）"
            return f"添加失败: {stderr}"
        elif backend == "ufw":
            code, _, stderr = self._exec(
                alias,
                f"sudo ufw deny from {ip} 2>/dev/null",
                10,
            )
            if code == 0:
                return f"IP {ip} 已通过 ufw 拒绝"
            return f"添加失败: {stderr}"
        elif backend == "iptables":
            code, _, stderr = self._exec(
                alias,
                f"sudo iptables -A INPUT -s {ip} -j DROP 2>/dev/null",
                10,
            )
            if code == 0:
                return f"IP {ip} 已通过 iptables 丢弃"
            return f"添加失败: {stderr}"
        return "未检测到支持的防火墙后端"

    def remove_ip_rule(self, alias: str, ip: str, action: str = "allow", zone: str = "public") -> str:
        backend = self.detect_firewall_backend(alias).get("backend", "unknown")
        if backend == "firewalld":
            target = "accept" if action == "allow" else "reject"
            code, _, stderr = self._exec(
                alias,
                f"sudo firewall-cmd --zone={zone} --remove-rich-rule='rule family=\"ipv4\" source address=\"{ip}\" {target}' --permanent 2>/dev/null",
                10,
            )
            if code == 0:
                self._exec(alias, "sudo firewall-cmd --reload 2>/dev/null", 10)
                return f"IP {ip} 的 rich rule 已删除"
            return f"删除失败: {stderr}"
        elif backend == "ufw":
            ufw_action = "allow" if action == "allow" else "deny"
            code, _, stderr = self._exec(
                alias,
                f"sudo ufw delete {ufw_action} from {ip} 2>/dev/null",
                10,
            )
            if code == 0:
                return f"IP {ip} 的 ufw 规则已删除"
            return f"删除失败: {stderr}"
        elif backend == "iptables":
            target = "ACCEPT" if action == "allow" else "DROP"
            code, _, stderr = self._exec(
                alias,
                f"sudo iptables -D INPUT -s {ip} -j {target} 2>/dev/null",
                10,
            )
            if code == 0:
                return f"IP {ip} 的 iptables 规则已删除"
            return f"删除失败: {stderr}"
        return "未检测到支持的防火墙后端"

    # ── SSH 配置管理 ──────────────────────────────────────────────

    def get_ssh_config(self, alias: str) -> dict[str, Any]:
        result: dict[str, Any] = {"port": 22, "password_auth": True, "root_login": True, "pubkey_auth": True, "raw": ""}
        code, stdout, _ = self._exec(alias, "sudo cat /etc/ssh/sshd_config 2>/dev/null || cat /etc/ssh/sshd_config 2>/dev/null", 10)
        if code == 0:
            result["raw"] = stdout
            for line in stdout.split("\n"):
                line = line.strip()
                if line.lower().startswith("port "):
                    try:
                        result["port"] = int(line.split()[1])
                    except (IndexError, ValueError):
                        pass
                elif line.lower().startswith("passwordauthentication "):
                    val = line.split()[1].lower()
                    result["password_auth"] = val in ("yes", "1", "true")
                elif line.lower().startswith("permitrootlogin "):
                    val = line.split()[1].lower()
                    result["root_login"] = val in ("yes", "1", "true", "prohibit-password")
                elif line.lower().startswith("pubkeyauthentication "):
                    val = line.split()[1].lower()
                    result["pubkey_auth"] = val in ("yes", "1", "true")
        return result

    def set_ssh_port(self, alias: str, port: int) -> str:
        if not (1 <= port <= 65535):
            return f"无效端口: {port}"
        code, stdout, _ = self._exec(alias, "sudo cat /etc/ssh/sshd_config 2>/dev/null", 10)
        if code != 0:
            return "无法读取 sshd_config"
        lines = stdout.split("\n")
        new_lines: list[str] = []
        replaced = False
        for line in lines:
            stripped = line.strip()
            if stripped.lower().startswith("port "):
                new_lines.append(f"Port {port}")
                replaced = True
            else:
                new_lines.append(line)
        if not replaced:
            new_lines.append(f"Port {port}")
        config_text = "\n".join(new_lines)
        code, _, stderr = self._exec(
            alias,
            f"echo '{config_text}' | sudo tee /etc/ssh/sshd_config >/dev/null 2>&1",
            10,
        )
        if code != 0:
            return f"写入 sshd_config 失败: {stderr}"
        restart_msg = self.restart_sshd(alias)
        fw_msg = self.add_port_rule(alias, port, "tcp")
        return f"SSH 端口已修改为 {port}。{restart_msg}；防火墙: {fw_msg}"

    def set_ssh_password_auth(self, alias: str, enabled: bool) -> str:
        code, stdout, _ = self._exec(alias, "sudo cat /etc/ssh/sshd_config 2>/dev/null", 10)
        if code != 0:
            return "无法读取 sshd_config"
        lines = stdout.split("\n")
        new_lines: list[str] = []
        replaced = False
        value = "yes" if enabled else "no"
        for line in lines:
            stripped = line.strip()
            if stripped.lower().startswith("passwordauthentication "):
                new_lines.append(f"PasswordAuthentication {value}")
                replaced = True
            else:
                new_lines.append(line)
        if not replaced:
            new_lines.append(f"PasswordAuthentication {value}")
        config_text = "\n".join(new_lines)
        code, _, stderr = self._exec(
            alias,
            f"echo '{config_text}' | sudo tee /etc/ssh/sshd_config >/dev/null 2>&1",
            10,
        )
        if code != 0:
            return f"写入 sshd_config 失败: {stderr}"
        restart_msg = self.restart_sshd(alias)
        return f"PasswordAuthentication 已设置为 {value}。{restart_msg}"

    def restart_sshd(self, alias: str) -> str:
        code, _, stderr = self._exec(alias, "sudo systemctl restart sshd 2>/dev/null || sudo systemctl restart ssh 2>/dev/null", 15)
        if code == 0:
            return "SSH 服务已重启"
        code, _, stderr = self._exec(alias, "sudo service sshd restart 2>/dev/null || sudo service ssh restart 2>/dev/null", 15)
        if code == 0:
            return "SSH 服务已重启"
        return f"SSH 重启失败: {stderr}"

    # ── SSH 密钥管理 ──────────────────────────────────────────────

    def list_authorized_keys(self, alias: str) -> list[dict[str, Any]]:
        code, stdout, _ = self._exec(alias, "cat ~/.ssh/authorized_keys 2>/dev/null", 10)
        keys: list[dict[str, Any]] = []
        if code != 0 or not stdout:
            return keys
        for idx, line in enumerate(stdout.split("\n"), start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            key_type = parts[0] if len(parts) >= 1 else "unknown"
            fingerprint = parts[1][:32] if len(parts) > 1 else ""
            comment = parts[2] if len(parts) > 2 else ""
            keys.append({
                "index": idx,
                "type": key_type,
                "fingerprint": fingerprint,
                "comment": comment,
                "raw": line,
            })
        return keys

    def add_authorized_key(self, alias: str, public_key: str) -> str:
        public_key = public_key.strip()
        if not public_key:
            return "公钥不能为空"
        code, _, stderr = self._exec(
            alias,
            f"mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo '{public_key}' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys",
            10,
        )
        if code == 0:
            return "公钥已添加"
        return f"添加失败: {stderr}"

    def remove_authorized_key(self, alias: str, fingerprint: str = "", comment: str = "") -> str:
        keys = self.list_authorized_keys(alias)
        target = None
        for k in keys:
            if fingerprint and k.get("fingerprint") == fingerprint:
                target = k["raw"]
                break
            if comment and k.get("comment") == comment:
                target = k["raw"]
                break
        if target is None:
            return "未找到匹配的公钥"
        escaped = target.replace("'", "'\"'\"'")
        code, _, stderr = self._exec(
            alias,
            f"sed -i '/{escaped}/d' ~/.ssh/authorized_keys",
            10,
        )
        if code == 0:
            return "公钥已删除"
        return f"删除失败: {stderr}"

    def generate_key_pair(self, alias: str, key_type: str = "ed25519", bits: int = 4096, comment: str = "opsv-kits") -> dict[str, str]:
        key_type = key_type.lower()
        if key_type not in ("rsa", "ed25519"):
            return {"error": "仅支持 rsa 或 ed25519"}
        tmp_dir = f"/tmp/opsv_key_{key_type}"
        key_path = f"{tmp_dir}/id_{key_type}"
        if key_type == "rsa":
            cmd = f"rm -rf {tmp_dir} && mkdir -p {tmp_dir} && ssh-keygen -t rsa -b {bits} -C '{comment}' -f {key_path} -N '' 2>/dev/null"
        else:
            cmd = f"rm -rf {tmp_dir} && mkdir -p {tmp_dir} && ssh-keygen -t ed25519 -C '{comment}' -f {key_path} -N '' 2>/dev/null"
        code, _, stderr = self._exec(alias, cmd, 30)
        if code != 0:
            return {"error": f"密钥生成失败: {stderr}"}
        code_priv, priv_key, _ = self._exec(alias, f"cat {key_path}", 5)
        code_pub, pub_key, _ = self._exec(alias, f"cat {key_path}.pub", 5)
        self._exec(alias, f"rm -rf {tmp_dir}", 5)
        if code_priv != 0 or code_pub != 0:
            return {"error": "读取生成的密钥失败"}
        return {"private_key": priv_key, "public_key": pub_key}

    # ── 安全审计 ──────────────────────────────────────────────────

    def get_login_logs(self, alias: str, limit: int = 100, user: str = "", failed_only: bool = False) -> list[dict[str, Any]]:
        logs = self.audit_login_attempts(alias, limit)
        if user:
            logs = [log for log in logs if log.get("user") == user]
        if failed_only:
            logs = [log for log in logs if log.get("status") != "accepted"]
        return logs

    def get_ops_logs(self, alias: str, limit: int = 100, action: str = "") -> list[dict[str, Any]]:
        return []

    def audit_login_attempts(self, alias: str, lines: int = 200) -> list[dict[str, Any]]:
        log_paths = ["/var/log/secure", "/var/log/auth.log"]
        stdout = ""
        for path in log_paths:
            code, out, _ = self._exec(alias, f"sudo tail -n {lines} {path} 2>/dev/null", 15)
            if code == 0 and out:
                stdout = out
                break
        attempts: list[dict[str, Any]] = []
        if not stdout:
            return attempts
        ssh_pattern = re.compile(
            r"(?P<date>\w+\s+\d+\s+\d+:\d+:\d+)\s+.*sshd\[\d+\]:\s+(?P<message>.*)",
            re.IGNORECASE,
        )
        for line in stdout.split("\n"):
            match = ssh_pattern.search(line)
            if match:
                msg = match.group("message")
                ip_match = re.search(r"from\s+(?P<ip>[\d\.]+)", msg)
                user_match = re.search(r"user\s+(?P<user>\S+)", msg)
                status = "failed"
                if "accepted" in msg.lower():
                    status = "accepted"
                elif "invalid user" in msg.lower():
                    status = "invalid"
                attempts.append({
                    "timestamp": match.group("date"),
                    "ip": ip_match.group("ip") if ip_match else None,
                    "user": user_match.group("user") if user_match else None,
                    "status": status,
                    "message": msg,
                })
        return attempts

    def get_fail2ban_status(self, alias: str) -> dict[str, Any]:
        result: dict[str, Any] = {"installed": False, "active": False, "jails": [], "banned_ips": []}
        code, _, _ = self._exec(alias, "which fail2ban-client 2>/dev/null", 5)
        if code != 0:
            return result
        result["installed"] = True
        code2, out2, _ = self._exec(alias, "sudo fail2ban-client ping 2>/dev/null", 5)
        result["active"] = code2 == 0 and "pong" in out2.lower()
        if not result["active"]:
            return result
        code3, out3, _ = self._exec(alias, "sudo fail2ban-client status 2>/dev/null", 10)
        if code3 == 0:
            for line in out3.split("\n"):
                if "jail list" in line.lower():
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        result["jails"] = [j.strip() for j in parts[1].split(",") if j.strip()]
        for jail in result["jails"]:
            code4, out4, _ = self._exec(alias, f"sudo fail2ban-client status {jail} 2>/dev/null", 10)
            if code4 == 0:
                for line in out4.split("\n"):
                    if "ip list" in line.lower() or "banned ip" in line.lower():
                        parts = line.split(":", 1)
                        if len(parts) == 2:
                            ips = [ip.strip() for ip in parts[1].split(",") if ip.strip()]
                            for ip in ips:
                                result["banned_ips"].append({"jail": jail, "ip": ip})
        return result

    def unban_ip(self, alias: str, ip: str, jail: str = "") -> str:
        if not jail:
            status = self.get_fail2ban_status(alias)
            jails = status.get("jails", [])
            for j in jails:
                code, _, _ = self._exec(
                    alias,
                    f"sudo fail2ban-client set {j} unbanip {ip} 2>/dev/null",
                    10,
                )
                if code == 0:
                    return f"IP {ip} 已从 {j} 解封"
            return f"解封失败: 未找到包含该 IP 的 jail"
        code, _, stderr = self._exec(
            alias,
            f"sudo fail2ban-client set {jail} unbanip {ip} 2>/dev/null",
            10,
        )
        if code == 0:
            return f"IP {ip} 已从 {jail} 解封"
        return f"解封失败: {stderr}"

    # ── 网络诊断 ──────────────────────────────────────────────────

    def run_ping(self, alias: str, host: str, count: int = 4) -> dict[str, Any]:
        code, stdout, stderr = self._exec(alias, f"ping -c {count} {host} 2>&1", 30)
        return {"code": code, "output": stdout, "error": stderr}

    def run_traceroute(self, alias: str, host: str, max_hops: int = 30) -> dict[str, Any]:
        code, stdout, stderr = self._exec(alias, f"traceroute -n -m {max_hops} {host} 2>&1 || tracepath -n {host} 2>&1", 60)
        return {"code": code, "output": stdout, "error": stderr}

    def run_port_scan(self, alias: str, host: str, ports: str = "1-1000") -> dict[str, Any]:
        port_list = self._parse_port_range(ports)
        results = self.port_scan(alias, host, port_list)
        output_lines = [f"{r['port']}/tcp {r['status']}" for r in results]
        return {"code": 0, "output": "\n".join(output_lines), "error": "", "ports": results}

    def _parse_port_range(self, ports: str) -> list[int]:
        result: list[int] = []
        for part in ports.split(","):
            part = part.strip()
            if "-" in part:
                try:
                    start, end = part.split("-", 1)
                    result.extend(range(int(start), int(end) + 1))
                except ValueError:
                    pass
            else:
                try:
                    result.append(int(part))
                except ValueError:
                    pass
        return result

    def ping(self, alias: str, host: str, count: int = 4) -> dict[str, Any]:
        code, stdout, stderr = self._exec(alias, f"ping -c {count} {host} 2>&1", 30)
        return {"code": code, "stdout": stdout, "stderr": stderr}

    def traceroute(self, alias: str, host: str) -> dict[str, Any]:
        code, stdout, stderr = self._exec(alias, f"traceroute -n {host} 2>&1 || tracepath -n {host} 2>&1", 60)
        return {"code": code, "stdout": stdout, "stderr": stderr}

    def port_scan(self, alias: str, host: str, ports: list[int], timeout: float = 5.0) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        port_str = " ".join(str(p) for p in ports)
        code, stdout, _ = self._exec(
            alias,
            f"for p in {port_str}; do (timeout {int(timeout)} bash -c 'echo >/dev/tcp/{host}/$p' 2>/dev/null && echo \"$p open\" || echo \"$p closed\"); done",
            int(timeout) * len(ports) + 10,
        )
        if code == 0 and stdout:
            for line in stdout.split("\n"):
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) == 2:
                    results.append({"port": int(parts[0]), "status": parts[1]})
        if not results:
            for port in ports:
                code2, _, _ = self._exec(
                    alias,
                    f"nc -z -w {int(timeout)} {host} {port} 2>/dev/null && echo 'open' || echo 'closed'",
                    int(timeout) + 5,
                )
                results.append({"port": port, "status": "open" if code2 == 0 else "closed"})
        return results


security_service = SecurityService()
