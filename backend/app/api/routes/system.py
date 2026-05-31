from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.services.system_service import system_service

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/info")
async def get_system_info(
    alias: str = Query(..., description="SSH 账户别名"),
):
    try:
        return system_service.get_system_info(alias)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取系统信息失败: {e}")


@router.get("/performance")
async def get_performance(
    alias: str = Query(..., description="SSH 账户别名"),
):
    try:
        return system_service.get_performance(alias)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取性能数据失败: {e}")


@router.get("/disks")
async def get_disks(
    alias: str = Query(..., description="SSH 账户别名"),
):
    try:
        return {"disks": system_service.get_disks_detail(alias)}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取磁盘信息失败: {e}")


@router.post("/reboot")
async def reboot_system(
    alias: str = Query(..., description="SSH 账户别名"),
):
    try:
        message = system_service.reboot(alias)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"重启失败: {e}")


@router.post("/shutdown")
async def shutdown_system(
    alias: str = Query(..., description="SSH 账户别名"),
):
    try:
        message = system_service.shutdown(alias)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"关机失败: {e}")


@router.post("/reload/network")
async def reload_network(
    alias: str = Query(..., description="SSH 账户别名"),
):
    try:
        message = system_service.reload_network(alias)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"网络重启失败: {e}")


@router.post("/reload/ssh")
async def reload_ssh(
    alias: str = Query(..., description="SSH 账户别名"),
):
    try:
        message = system_service.reload_ssh(alias)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"SSH重启失败: {e}")


@router.post("/cache/clear")
async def clear_cache(
    alias: str = Query(..., description="SSH 账户别名"),
):
    try:
        message = system_service.clear_cache(alias)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"清理缓存失败: {e}")


@router.get("/selinux")
async def get_selinux(
    alias: str = Query(..., description="SSH 账户别名"),
):
    try:
        return system_service.check_selinux(alias)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取SELinux状态失败: {e}")


@router.post("/selinux")
async def set_selinux(
    alias: str = Query(..., description="SSH 账户别名"),
    mode: str = Query(..., description="enforcing 或 permissive"),
):
    try:
        message = system_service.set_selinux(alias, mode)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"设置SELinux失败: {e}")


@router.get("/firewall/status", deprecated=True)
async def firewall_status(
    alias: str = Query(..., description="SSH 账户别名"),
):
    try:
        return system_service.get_firewall_status(alias)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取防火墙状态失败: {e}")


@router.post("/firewall/set", deprecated=True)
async def set_firewall(
    alias: str = Query(..., description="SSH 账户别名"),
    enable: bool = Query(..., description="true 开启, false 关闭"),
):
    try:
        message = system_service.set_firewall(alias, enable)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"设置防火墙失败: {e}")


@router.get("/firewall/rules", deprecated=True)
async def firewall_rules(
    alias: str = Query(..., description="SSH 账户别名"),
):
    try:
        rules = system_service.list_firewall_rules(alias)
        return {"rules": rules}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取防火墙规则失败: {e}")


@router.get("/firewall/zones", deprecated=True)
async def firewall_zones(
    alias: str = Query(..., description="SSH 账户别名"),
):
    try:
        zones = system_service.get_firewall_zones(alias)
        return {"zones": zones}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取防火墙区域失败: {e}")


@router.post("/firewall/port", deprecated=True)
async def add_port_rule(
    alias: str = Query(..., description="SSH 账户别名"),
    port: int = Query(..., description="端口号"),
    protocol: str = Query("tcp", description="tcp 或 udp"),
    zone: str = Query("public", description="防火墙区域"),
):
    try:
        message = system_service.add_port_rule(alias, port, protocol, zone)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"添加端口规则失败: {e}")


@router.delete("/firewall/port", deprecated=True)
async def remove_port_rule(
    alias: str = Query(..., description="SSH 账户别名"),
    port: int = Query(..., description="端口号"),
    protocol: str = Query("tcp", description="tcp 或 udp"),
    zone: str = Query("public", description="防火墙区域"),
):
    try:
        message = system_service.remove_port_rule(alias, port, protocol, zone)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"删除端口规则失败: {e}")


@router.post("/firewall/service", deprecated=True)
async def add_service_rule(
    alias: str = Query(..., description="SSH 账户别名"),
    service: str = Query(..., description="服务名称"),
    zone: str = Query("public", description="防火墙区域"),
):
    try:
        message = system_service.add_service_rule(alias, service, zone)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"添加服务规则失败: {e}")


@router.delete("/firewall/service", deprecated=True)
async def remove_service_rule(
    alias: str = Query(..., description="SSH 账户别名"),
    service: str = Query(..., description="服务名称"),
    zone: str = Query("public", description="防火墙区域"),
):
    try:
        message = system_service.remove_service_rule(alias, service, zone)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"删除服务规则失败: {e}")


# ── 工具箱：扩展系统操作 ──────────────────────────────────────────

@router.post("/toolkit/sync-time")
async def toolkit_sync_time(
    alias: str = Query(..., description="SSH 账户别名"),
):
    try:
        message = system_service.sync_time(alias)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"时间同步失败: {e}")


@router.post("/toolkit/hostname")
async def toolkit_set_hostname(
    alias: str = Query(..., description="SSH 账户别名"),
    hostname: str = Query(..., description="新主机名"),
):
    try:
        message = system_service.set_hostname(alias, hostname)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"修改主机名失败: {e}")


@router.get("/toolkit/timezone")
async def toolkit_get_timezone(
    alias: str = Query(..., description="SSH 账户别名"),
):
    try:
        return system_service.get_timezone(alias)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取时区失败: {e}")


@router.post("/toolkit/timezone")
async def toolkit_set_timezone(
    alias: str = Query(..., description="SSH 账户别名"),
    timezone: str = Query(..., description="时区，如 Asia/Shanghai"),
):
    try:
        message = system_service.set_timezone(alias, timezone)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"设置时区失败: {e}")


# ── 工具箱：诊断工具 ──────────────────────────────────────────────

@router.get("/toolkit/logged-users")
async def toolkit_logged_users(
    alias: str = Query(..., description="SSH 账户别名"),
):
    try:
        return system_service.get_logged_users(alias)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取登录用户失败: {e}")


@router.get("/toolkit/boot-time")
async def toolkit_boot_time(
    alias: str = Query(..., description="SSH 账户别名"),
):
    try:
        return system_service.get_boot_time(alias)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取启动时间失败: {e}")


@router.get("/toolkit/kernel-modules")
async def toolkit_kernel_modules(
    alias: str = Query(..., description="SSH 账户别名"),
):
    try:
        return system_service.get_kernel_modules(alias)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取内核模块失败: {e}")


@router.get("/toolkit/enabled-services")
async def toolkit_enabled_services(
    alias: str = Query(..., description="SSH 账户别名"),
):
    try:
        return system_service.get_enabled_services(alias)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取开机自启服务失败: {e}")


@router.get("/toolkit/dns-config")
async def toolkit_dns_config(
    alias: str = Query(..., description="SSH 账户别名"),
):
    try:
        return system_service.get_dns_config(alias)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取 DNS 配置失败: {e}")


@router.get("/toolkit/ulimit")
async def toolkit_ulimit(
    alias: str = Query(..., description="SSH 账户别名"),
):
    try:
        return system_service.get_ulimit(alias)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取资源限制失败: {e}")


# ── 工具箱：清理维护 ──────────────────────────────────────────────

@router.get("/toolkit/swap-status")
async def toolkit_swap_status(
    alias: str = Query(..., description="SSH 账户别名"),
):
    try:
        return system_service.get_swap_status(alias)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取 SWAP 状态失败: {e}")


@router.post("/toolkit/swap-refresh")
async def toolkit_swap_refresh(
    alias: str = Query(..., description="SSH 账户别名"),
):
    try:
        message = system_service.swap_refresh(alias)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"刷新 SWAP 失败: {e}")


@router.post("/toolkit/cleanup-kernels")
async def toolkit_cleanup_kernels(
    alias: str = Query(..., description="SSH 账户别名"),
):
    try:
        message = system_service.cleanup_old_kernels(alias)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"清理旧内核失败: {e}")


@router.post("/toolkit/cleanup-journal")
async def toolkit_cleanup_journal(
    alias: str = Query(..., description="SSH 账户别名"),
    days: int = Query(7, description="保留最近 N 天的日志"),
):
    try:
        message = system_service.cleanup_journal(alias, days)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"清理 journal 失败: {e}")


@router.get("/toolkit/check-updates")
async def toolkit_check_updates(
    alias: str = Query(..., description="SSH 账户别名"),
):
    try:
        return system_service.check_updates(alias)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"检查系统更新失败: {e}")
