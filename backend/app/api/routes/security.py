from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.services.security_service import security_service
from app.services.audit_log_service import audit_log_service
from app.models.audit_log import AuditLogQuery

router = APIRouter(prefix="/security", tags=["security"])


# ── 防火墙 ──────────────────────────────────────────────────────

@router.get("/firewall/backend")
async def detect_firewall_backend(
    alias: str = Query(..., description="SSH 账户别名"),
):
    try:
        return security_service.detect_firewall_backend(alias)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"检测防火墙后端失败: {e}")


@router.get("/firewall/rules")
async def list_firewall_rules(
    alias: str = Query(..., description="SSH 账户别名"),
):
    try:
        return {"rules": security_service.list_all_rules(alias)}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取防火墙规则失败: {e}")


@router.post("/firewall/port")
async def add_firewall_port(
    alias: str = Query(..., description="SSH 账户别名"),
    port: int = Query(..., description="端口号"),
    protocol: str = Query("tcp", description="tcp 或 udp"),
    zone: str = Query("public", description="防火墙区域"),
):
    try:
        message = security_service.add_port_rule(alias, port, protocol, zone)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"添加端口规则失败: {e}")


@router.delete("/firewall/port")
async def remove_firewall_port(
    alias: str = Query(..., description="SSH 账户别名"),
    port: int = Query(..., description="端口号"),
    protocol: str = Query("tcp", description="tcp 或 udp"),
    zone: str = Query("public", description="防火墙区域"),
):
    try:
        message = security_service.remove_port_rule(alias, port, protocol, zone)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"删除端口规则失败: {e}")


@router.post("/firewall/ip")
async def add_firewall_ip(
    alias: str = Query(..., description="SSH 账户别名"),
    ip: str = Query(..., description="IP 地址或网段"),
    action: str = Query("allow", description="allow 或 deny"),
    zone: str = Query("public", description="防火墙区域"),
):
    try:
        message = security_service.add_ip_rule(alias, ip, action, zone)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"添加 IP 规则失败: {e}")


@router.delete("/firewall/ip")
async def remove_firewall_ip(
    alias: str = Query(..., description="SSH 账户别名"),
    ip: str = Query(..., description="IP 地址或网段"),
    zone: str = Query("public", description="防火墙区域"),
):
    try:
        message = security_service.remove_ip_rule(alias, ip, zone)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"删除 IP 规则失败: {e}")


# ── SSH 管理 ────────────────────────────────────────────────────

@router.get("/ssh/config")
async def get_ssh_config(
    alias: str = Query(..., description="SSH 账户别名"),
):
    try:
        return security_service.get_ssh_config(alias)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取 SSH 配置失败: {e}")


@router.post("/ssh/port")
async def set_ssh_port(
    alias: str = Query(..., description="SSH 账户别名"),
    port: int = Query(..., description="新的 SSH 端口号"),
):
    try:
        message = security_service.set_ssh_port(alias, port)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"修改 SSH 端口失败: {e}")


@router.post("/ssh/password-auth")
async def toggle_ssh_password_auth(
    alias: str = Query(..., description="SSH 账户别名"),
    enabled: bool = Query(..., description="true 开启, false 关闭"),
):
    try:
        message = security_service.set_ssh_password_auth(alias, enabled)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"切换 SSH 密码认证失败: {e}")


@router.get("/ssh/keys")
async def list_authorized_keys(
    alias: str = Query(..., description="SSH 账户别名"),
):
    try:
        return {"keys": security_service.list_authorized_keys(alias)}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取 authorized_keys 失败: {e}")


@router.post("/ssh/keys")
async def add_authorized_key(
    alias: str = Query(..., description="SSH 账户别名"),
    public_key: str = Query(..., description="公钥内容"),
):
    try:
        message = security_service.add_authorized_key(alias, public_key)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"添加公钥失败: {e}")


@router.delete("/ssh/keys")
async def remove_authorized_key(
    alias: str = Query(..., description="SSH 账户别名"),
    fingerprint: str = Query("", description="公钥指纹"),
    comment: str = Query("", description="公钥注释"),
):
    try:
        message = security_service.remove_authorized_key(alias, fingerprint, comment)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"删除公钥失败: {e}")


@router.post("/ssh/keys/generate")
async def generate_ssh_key_pair(
    alias: str = Query(..., description="SSH 账户别名"),
    key_type: str = Query("ed25519", description="密钥类型"),
    bits: int = Query(4096, description="密钥位数"),
    comment: str = Query("", description="密钥注释"),
):
    try:
        return security_service.generate_key_pair(alias, key_type, bits, comment or "opsv-kits")
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"生成密钥对失败: {e}")


# ── 审计 ────────────────────────────────────────────────────────

@router.get("/audit/login-logs")
async def get_login_logs(
    alias: str = Query(..., description="SSH 账户别名"),
    limit: int = Query(100, description="返回条数"),
    user: str = Query("", description="筛选用户"),
    failed_only: bool = Query(False, description="仅失败登录"),
):
    try:
        return {"logs": security_service.get_login_logs(alias, limit, user, failed_only)}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取登录日志失败: {e}")


@router.get("/audit/fail2ban")
async def get_fail2ban_status(
    alias: str = Query(..., description="SSH 账户别名"),
):
    try:
        return security_service.get_fail2ban_status(alias)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取 fail2ban 状态失败: {e}")


@router.post("/audit/fail2ban/unban")
async def unban_ip(
    alias: str = Query(..., description="SSH 账户别名"),
    ip: str = Query(..., description="要解封的 IP"),
    jail: str = Query("", description="指定的 jail，为空则自动查找"),
):
    try:
        message = security_service.unban_ip(alias, ip, jail)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"解封 IP 失败: {e}")


@router.get("/audit/ops-logs")
async def get_ops_logs(
    alias: str = Query(..., description="SSH 账户别名"),
    limit: int = Query(100, description="返回条数"),
    action: str = Query("", description="按动作筛选"),
):
    try:
        logs = security_service.get_ops_logs(alias, limit, action)
        return {"logs": logs}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取操作审计日志失败: {e}")


# ── 网络诊断 ────────────────────────────────────────────────────

@router.post("/network/ping")
async def run_ping(
    alias: str = Query(..., description="SSH 账户别名"),
    host: str = Query(..., description="目标主机"),
    count: int = Query(4, description="ping 次数"),
):
    try:
        return security_service.run_ping(alias, host, count)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"执行 ping 失败: {e}")


@router.post("/network/traceroute")
async def run_traceroute(
    alias: str = Query(..., description="SSH 账户别名"),
    host: str = Query(..., description="目标主机"),
    max_hops: int = Query(30, description="最大跳数"),
):
    try:
        return security_service.run_traceroute(alias, host, max_hops)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"执行 traceroute 失败: {e}")


@router.post("/network/portscan")
async def run_port_scan(
    alias: str = Query(..., description="SSH 账户别名"),
    host: str = Query(..., description="目标主机"),
    ports: str = Query("1-1000", description="端口范围"),
):
    try:
        return security_service.run_port_scan(alias, host, ports)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"执行端口扫描失败: {e}")
