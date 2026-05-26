from __future__ import annotations

import argparse
import importlib
import os
import sys
import textwrap
import webbrowser
from pathlib import Path
from typing import Any, Optional


VERSION = "1.0.0"

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "settings.yaml"


def _lazy(module_path: str) -> Any:
    return importlib.import_module(module_path, package="app")


def _enable_vt_mode() -> None:
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)
            mode = ctypes.c_uint32()
            kernel32.GetConsoleMode(handle, ctypes.byref(mode))
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
        except Exception:
            pass


class Color:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    @staticmethod
    def ok(msg: str) -> str:
        return f"{Color.GREEN}{msg}{Color.RESET}"

    @staticmethod
    def err(msg: str) -> str:
        return f"{Color.RED}{msg}{Color.RESET}"

    @staticmethod
    def warn(msg: str) -> str:
        return f"{Color.YELLOW}{msg}{Color.RESET}"

    @staticmethod
    def info(msg: str) -> str:
        return f"{Color.CYAN}{msg}{Color.RESET}"

    @staticmethod
    def highlight(msg: str) -> str:
        return f"{Color.BOLD}{Color.BLUE}{msg}{Color.RESET}"

    @staticmethod
    def dim(msg: str) -> str:
        return f"{Color.DIM}{msg}{Color.RESET}"


def _print_success(msg: str) -> None:
    print(f"{Color.ok('✓')} {msg}")


def _print_error(msg: str) -> None:
    print(f"{Color.err('✗')} {msg}", file=sys.stderr)


def _print_warning(msg: str) -> None:
    print(f"{Color.warn('⚠')} {msg}")


def _print_info(msg: str) -> None:
    print(f"{Color.info('ℹ')} {msg}")


def _print_table(headers: list[str], rows: list[list[str]]) -> None:
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(cell))
    sep = "  "
    header_line = sep.join(
        Color.highlight(h.ljust(col_widths[i])) for i, h in enumerate(headers)
    )
    print(header_line)
    print(Color.dim("-" * len(header_line)))
    for row in rows:
        line = sep.join(
            cell.ljust(col_widths[i]) for i, cell in enumerate(row)
        )
        print(line)


def _load_config(config_path: Optional[str] = None) -> dict:
    yaml = _lazy("yaml")
    path = Path(config_path) if config_path else _DEFAULT_CONFIG_PATH
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _get_account_alias(args) -> str:
    ssh_account_service = _lazy("app.services.ssh_account_service")
    config = _load_config(getattr(args, "config", None))
    alias = getattr(args, "alias", None)
    if alias:
        return alias
    ssh_cfg = config.get("ssh", {})
    alias_from_config = ssh_cfg.get("account_alias") or ssh_cfg.get("alias")
    if alias_from_config:
        return alias_from_config
    default_acct = ssh_account_service.ssh_account_service.get_default()
    if default_acct is not None:
        return default_acct.alias
    raise ValueError(
        "未指定 SSH 账户别名。请使用 --alias 参数或设置默认账户。"
    )


def _cmd_init(args: argparse.Namespace) -> None:
    yaml = _lazy("yaml")
    if _DEFAULT_CONFIG_PATH.exists():
        _print_warning(f"配置文件已存在: {_DEFAULT_CONFIG_PATH}")
        answer = input("是否覆盖？(y/N): ").strip().lower()
        if answer != "y":
            _print_info("已取消")
            return
    _DEFAULT_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    default_config = {
        "ssh": {
            "host": "YOUR_SSH_HOST",
            "port": 22,
            "username": "YOUR_SSH_USERNAME",
            "password": "",
            "key_file": "",
            "timeout": 30,
        },
        "sync": {
            "local_dir": "./local_project",
            "remote_dir": "/remote/project/path",
            "exclude_patterns": ["__pycache__", ".git", "*.pyc", ".venv", "node_modules"],
        },
        "environment": {
            "remote_python": "/usr/bin/python3",
            "remote_work_dir": "/remote/project/path",
        },
        "build": {
            "enabled": False,
            "command": "",
        },
        "run": {
            "mode": "remote",
            "remote_command": "",
            "local_command": "",
        },
    }
    with open(_DEFAULT_CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)
    _print_success(f"配置文件已创建: {_DEFAULT_CONFIG_PATH}")


def _cmd_run(args: argparse.Namespace) -> None:
    _print_info("开始完整流程...")
    _cmd_sync(args)
    _cmd_setup(args)
    _cmd_build(args)
    _cmd_start(args)
    _print_success("完整流程执行完毕")


def _cmd_sync(args: argparse.Namespace) -> None:
    import asyncio
    sync_service = _lazy("app.services.sync_service")
    config = _load_config(args.config)
    local_path = args.local or config.get("sync", {}).get("local_dir", ".")
    remote_path = args.remote or config.get("sync", {}).get("remote_dir", "")
    if not remote_path:
        _print_error("请指定远程路径（--remote 或配置文件中 sync.remote_dir）")
        sys.exit(1)

    alias = args.alias or _get_account_alias(args)
    force = args.force or False

    _print_info(f"同步: {local_path} -> {remote_path} (账户: {alias})")
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        sync_service.sync_service.set_event_loop(loop)
        sync_id = loop.run_until_complete(
            sync_service.sync_service.start_sync(local_path, remote_path, alias, force=force)
        )
        loop.run_until_complete(asyncio.sleep(1))
        status = sync_service.sync_service.get_status(sync_id)
        if status and status.get("status") == "completed":
            _print_success(f"同步完成: {status.get('message', '')}")
        elif status:
            _print_warning(f"同步状态: {status.get('status')} - {status.get('message', '')}")
        else:
            _print_info(f"同步任务已启动 (ID: {sync_id})")
    except Exception as e:
        _print_error(f"同步失败: {e}")
        sys.exit(1)


def _cmd_setup(args: argparse.Namespace) -> None:
    docker_service = _lazy("app.services.docker_service")
    config = _load_config(args.config)
    alias = args.alias or _get_account_alias(args)
    _print_info("检查远程环境...")
    try:
        has_docker = docker_service.docker_service.check_docker_installed(alias)
        if has_docker:
            version = docker_service.docker_service.get_docker_version(alias)
            _print_success(f"Docker 已安装: {version}")
        else:
            _print_warning("Docker 未安装")
            env_config = config.get("environment", {})
            if env_config.get("auto_install", False):
                _print_info("正在自动安装 Docker...")
                result = docker_service.docker_service.install_docker(alias)
                _print_success(result)
            else:
                _print_info("跳过自动安装（auto_install 未启用）")
    except Exception as e:
        _print_error(f"环境检查失败: {e}")
        sys.exit(1)


def _cmd_build(args: argparse.Namespace) -> None:
    ssh_account_service = _lazy("app.services.ssh_account_service")
    config = _load_config(args.config)
    alias = args.alias or _get_account_alias(args)
    remote_path = args.remote or config.get("sync", {}).get("remote_dir", "")
    build_config = config.get("build", {})
    compile_cmd = build_config.get("command") or build_config.get("compile_cmd", "mvn clean compile")

    if not build_config.get("enabled", False):
        _print_info("编译功能未启用（build.enabled = false）")
        return

    _print_info(f"远程编译: {compile_cmd}")
    try:
        conn = ssh_account_service.ssh_account_service.pool.get_connection(
            ssh_account_service.ssh_account_service.get_account(alias)
        )
        try:
            exit_code, stdout, stderr = conn.manager.exec_command(
                f"cd {remote_path} && {compile_cmd}", timeout=600.0
            )
            if exit_code == 0:
                _print_success("编译成功")
            else:
                _print_error(f"编译失败 (exit code: {exit_code})")
                if stderr:
                    print(Color.err(stderr))
                sys.exit(1)
        finally:
            ssh_account_service.ssh_account_service.pool.release_connection(conn)
    except Exception as e:
        _print_error(f"编译失败: {e}")
        sys.exit(1)


def _cmd_start(args: argparse.Namespace) -> None:
    ssh_account_service = _lazy("app.services.ssh_account_service")
    config = _load_config(args.config)
    alias = args.alias or _get_account_alias(args)
    remote_path = args.remote or config.get("sync", {}).get("remote_dir", "")
    run_config = config.get("run", {})
    run_mode = run_config.get("mode", "remote")
    run_cmd = run_config.get("remote_command", "")

    if not run_cmd:
        _print_warning("未配置运行命令（run.remote_command）")
        return

    _print_info(f"运行 ({run_mode}): {run_cmd}")
    try:
        conn = ssh_account_service.ssh_account_service.pool.get_connection(
            ssh_account_service.ssh_account_service.get_account(alias)
        )
        try:
            exit_code, stdout, stderr = conn.manager.exec_command(
                f"cd {remote_path} && {run_cmd}", timeout=60.0
            )
            if exit_code == 0:
                _print_success("启动成功")
                if stdout:
                    print(stdout)
            else:
                _print_error(f"启动失败 (exit code: {exit_code})")
                if stderr:
                    print(Color.err(stderr))
                sys.exit(1)
        finally:
            ssh_account_service.ssh_account_service.pool.release_connection(conn)
    except Exception as e:
        _print_error(f"运行失败: {e}")
        sys.exit(1)


def _get_ssh_account_service():
    return _lazy("app.services.ssh_account_service").ssh_account_service


def _get_file_manager_service():
    return _lazy("app.services.file_manager_service").file_manager_service


def _get_docker_service():
    return _lazy("app.services.docker_service").docker_service


def _cmd_account_add(args: argparse.Namespace) -> None:
    SSHAccountCreate = _lazy("app.models.ssh_account").SSHAccountCreate
    svc = _get_ssh_account_service()
    alias = input("账户别名: ").strip()
    host = input("主机地址: ").strip()
    port_str = input("端口 (22): ").strip()
    port = int(port_str) if port_str else 22
    username = input("用户名: ").strip()
    print("认证方式:")
    print(f"  {Color.info('1')} 密码")
    print(f"  {Color.info('2')} SSH 密钥")
    print(f"  {Color.info('3')} SSH Agent")
    auth_choice = input("选择 (1/2/3) [1]: ").strip() or "1"
    auth_type = {"1": "password", "2": "key", "3": "agent"}.get(auth_choice, "password")
    password = None
    private_key = None
    key_passphrase = None
    if auth_type == "password":
        password = input("密码: ").strip()
    elif auth_type == "key":
        private_key = input("私钥路径: ").strip()
        kp = input("密钥密码 (可选): ").strip()
        key_passphrase = kp if kp else None
    default_str = input("设为默认账户? (y/N): ").strip().lower()
    is_default = default_str == "y"
    group = input("分组 (可选): ").strip() or None

    data = SSHAccountCreate(
        alias=alias,
        host=host,
        port=port,
        username=username,
        auth_type=auth_type,
        password=password,
        private_key=private_key,
        key_passphrase=key_passphrase,
        is_default=is_default,
        group=group,
    )
    try:
        account = svc.create_account(data)
        _print_success(f"账户 '{account.alias}' 创建成功")
    except ValueError as e:
        _print_error(str(e))
        sys.exit(1)


def _cmd_account_list(args: argparse.Namespace) -> None:
    svc = _get_ssh_account_service()
    accounts = svc.list_accounts()
    if not accounts:
        _print_info("暂无 SSH 账户")
        return
    headers = ["别名", "主机", "端口", "用户", "认证方式", "默认", "分组"]
    rows = []
    for acct in accounts:
        rows.append([
            acct.alias,
            acct.host,
            str(acct.port),
            acct.username,
            acct.auth_type,
            Color.ok("★") if acct.is_default else "",
            acct.group or "",
        ])
    _print_table(headers, rows)


def _cmd_account_test(args: argparse.Namespace) -> None:
    svc = _get_ssh_account_service()
    alias = args.alias
    _print_info(f"正在测试连接 '{alias}'...")
    try:
        success, message = svc.test_account(alias)
        if success:
            _print_success(f"{alias}: {message}")
        else:
            _print_error(f"{alias}: {message}")
            sys.exit(1)
    except ValueError as e:
        _print_error(str(e))
        sys.exit(1)


def _cmd_account_remove(args: argparse.Namespace) -> None:
    svc = _get_ssh_account_service()
    alias = args.alias
    account = svc.get_account(alias)
    if account is None:
        _print_error(f"账户 '{alias}' 不存在")
        sys.exit(1)
    print(f"账户信息: {account.alias} ({account.username}@{account.host})")
    confirm = input(f"确认删除账户 '{alias}'? (y/N): ").strip().lower()
    if confirm != "y":
        _print_info("已取消")
        return
    svc.delete_account(alias)
    _print_success(f"账户 '{alias}' 已删除")


def _cmd_account_default(args: argparse.Namespace) -> None:
    svc = _get_ssh_account_service()
    alias = args.alias
    try:
        account = svc.set_default(alias)
        _print_success(f"已设置 '{account.alias}' 为默认账户")
    except ValueError as e:
        _print_error(str(e))
        sys.exit(1)


def _cmd_account_edit(args: argparse.Namespace) -> None:
    SSHAccountUpdate = _lazy("app.models.ssh_account").SSHAccountUpdate
    svc = _get_ssh_account_service()
    alias = args.alias
    account = svc.get_account(alias)
    if account is None:
        _print_error(f"账户 '{alias}' 不存在")
        sys.exit(1)
    print(f"编辑账户 '{alias}' (直接回车保持不变):")
    host = input(f"主机地址 [{account.host}]: ").strip() or account.host
    port_str = input(f"端口 [{account.port}]: ").strip()
    port = int(port_str) if port_str else account.port
    username = input(f"用户名 [{account.username}]: ").strip() or account.username
    auth_type = account.auth_type
    print(f"当前认证方式: {auth_type}")
    change_auth = input("修改认证方式? (y/N): ").strip().lower()
    if change_auth == "y":
        print(f"  {Color.info('1')} 密码")
        print(f"  {Color.info('2')} SSH 密钥")
        print(f"  {Color.info('3')} SSH Agent")
        auth_choice = input("选择 (1/2/3): ").strip()
        auth_type = {"1": "password", "2": "key", "3": "agent"}.get(auth_choice, account.auth_type)
    update_data = SSHAccountUpdate(
        host=host,
        port=port,
        username=username,
        auth_type=auth_type,
    )
    try:
        svc.update_account(alias, update_data)
        _print_success(f"账户 '{alias}' 已更新")
    except ValueError as e:
        _print_error(str(e))
        sys.exit(1)


def _cmd_remote_ls(args: argparse.Namespace) -> None:
    fms = _get_file_manager_service()
    alias = _get_account_alias(args)
    path = args.path or "/"
    try:
        entries = fms.list_directory(alias, path)
        if not entries:
            _print_info("(空目录)")
            return
        headers = ["名称", "类型", "大小", "权限", "修改时间"]
        rows = []
        for e in entries:
            icon = "📁" if e.is_dir else "📄"
            rows.append([e.name, icon, str(e.size), e.permissions, e.modify_time])
        _print_table(headers, rows)
    except Exception as e:
        _print_error(str(e))
        sys.exit(1)


def _cmd_remote_cat(args: argparse.Namespace) -> None:
    fms = _get_file_manager_service()
    alias = _get_account_alias(args)
    path = args.path
    try:
        content = fms.read_file(alias, path)
        print(content)
    except Exception as e:
        _print_error(str(e))
        sys.exit(1)


def _cmd_remote_upload(args: argparse.Namespace) -> None:
    fms = _get_file_manager_service()
    alias = _get_account_alias(args)
    local_path = args.local
    remote_path = args.remote
    _print_info(f"上传: {local_path} -> {remote_path}")
    try:
        fms.upload(alias, local_path, remote_path)
        _print_success("上传完成")
    except Exception as e:
        _print_error(str(e))
        sys.exit(1)


def _cmd_remote_download(args: argparse.Namespace) -> None:
    fms = _get_file_manager_service()
    alias = _get_account_alias(args)
    remote_path = args.remote
    local_path = args.local or os.path.basename(remote_path)
    _print_info(f"下载: {remote_path} -> {local_path}")
    try:
        fms.download(alias, remote_path, local_path)
        _print_success("下载完成")
    except Exception as e:
        _print_error(str(e))
        sys.exit(1)


def _cmd_remote_rm(args: argparse.Namespace) -> None:
    fms = _get_file_manager_service()
    alias = _get_account_alias(args)
    path = args.path
    confirm = input(f"确认删除 '{path}'? (y/N): ").strip().lower()
    if confirm != "y":
        _print_info("已取消")
        return
    try:
        fms.delete(alias, path)
        _print_success(f"已删除: {path}")
    except Exception as e:
        _print_error(str(e))
        sys.exit(1)


def _cmd_remote_mkdir(args: argparse.Namespace) -> None:
    fms = _get_file_manager_service()
    alias = _get_account_alias(args)
    path = args.path
    try:
        fms.create_directory(alias, path)
        _print_success(f"已创建: {path}")
    except Exception as e:
        _print_error(str(e))
        sys.exit(1)


def _cmd_remote_mv(args: argparse.Namespace) -> None:
    fms = _get_file_manager_service()
    alias = _get_account_alias(args)
    try:
        fms.rename(alias, args.src, args.dst)
        _print_success(f"已移动: {args.src} -> {args.dst}")
    except Exception as e:
        _print_error(str(e))
        sys.exit(1)


def _cmd_remote_cp(args: argparse.Namespace) -> None:
    fms = _get_file_manager_service()
    alias = _get_account_alias(args)
    try:
        fms.copy(alias, args.src, args.dst)
        _print_success(f"已复制: {args.src} -> {args.dst}")
    except Exception as e:
        _print_error(str(e))
        sys.exit(1)


def _cmd_remote_chmod(args: argparse.Namespace) -> None:
    fms = _get_file_manager_service()
    alias = _get_account_alias(args)
    try:
        fms.chmod(alias, args.path, args.mode)
        _print_success(f"权限已修改: {args.path} ({args.mode})")
    except Exception as e:
        _print_error(str(e))
        sys.exit(1)


def _cmd_remote_exec(args: argparse.Namespace) -> None:
    fms = _get_file_manager_service()
    alias = _get_account_alias(args)
    command = args.command
    _print_info(f"执行: {command}")
    try:
        result = fms.exec_command(alias, command)
        print(Color.dim(f"Exit code: {result['exit_code']}"))
        if result["stdout"]:
            print(result["stdout"])
        if result["stderr"]:
            print(Color.err(result["stderr"]), file=sys.stderr)
    except Exception as e:
        _print_error(str(e))
        sys.exit(1)


def _cmd_remote_find(args: argparse.Namespace) -> None:
    fms = _get_file_manager_service()
    alias = _get_account_alias(args)
    path = args.path
    pattern = args.name
    _print_info(f"搜索: {path} -name '{pattern}'")
    try:
        results = fms.search(alias, path, pattern)
        if not results:
            _print_info("未找到匹配的文件")
            return
        for r in results:
            icon = "📁" if r.is_dir else "📄"
            print(f"{icon}  {r.path}  ({r.size} bytes, {r.permissions})")
        _print_info(f"共找到 {len(results)} 个匹配项")
    except Exception as e:
        _print_error(str(e))
        sys.exit(1)


def _cmd_docker_info(args: argparse.Namespace) -> None:
    ds = _get_docker_service()
    alias = _get_account_alias(args)
    try:
        installed = ds.check_docker_installed(alias)
        if installed:
            version = ds.get_docker_version(alias)
            _print_success(f"Docker: {version}")
        else:
            _print_warning("Docker 未安装")
        running = ds.check_docker_running(alias)
        if running:
            _print_success("Docker 守护进程: 运行中")
        else:
            _print_warning("Docker 守护进程: 未运行")
        perms = ds.check_docker_permissions(alias)
        print(f"  Docker 组: {Color.ok('是') if perms['in_docker_group'] else Color.err('否')}")
        print(f"  sudo 权限: {Color.ok('是') if perms['has_sudo_access'] else Color.err('否')}")
        print(f"  可运行: {Color.ok('是') if perms['can_run_docker'] else Color.err('否')}")
        _print_info(f"  详情: {perms['details']}")
    except Exception as e:
        _print_error(str(e))
        sys.exit(1)


def _cmd_docker_install(args: argparse.Namespace) -> None:
    ds = _get_docker_service()
    alias = _get_account_alias(args)
    _print_info("正在安装 Docker...")
    try:
        result = ds.install_docker(alias)
        _print_success(result)
    except Exception as e:
        _print_error(str(e))
        sys.exit(1)


def _cmd_docker_ps(args: argparse.Namespace) -> None:
    ds = _get_docker_service()
    alias = _get_account_alias(args)
    all_flag = getattr(args, "all", False)
    try:
        containers = ds.list_containers(alias, all=all_flag)
        if not containers:
            _print_info("无容器")
            return
        headers = ["容器ID", "名称", "镜像", "状态", "端口"]
        rows = []
        for c in containers:
            cid = (c.get("ID") or c.get("id", ""))[:12]
            name = c.get("Names") or c.get("name", "")
            image = c.get("Image") or c.get("image", "")
            status = c.get("Status") or c.get("status", "")
            ports = c.get("Ports") or c.get("ports", "")
            rows.append([cid, name, image, status, ports])
        _print_table(headers, rows)
    except Exception as e:
        _print_error(str(e))
        sys.exit(1)


def _cmd_docker_start(args: argparse.Namespace) -> None:
    ds = _get_docker_service()
    alias = _get_account_alias(args)
    try:
        result = ds.start_container(alias, args.container_id)
        _print_success(result)
    except Exception as e:
        _print_error(str(e))
        sys.exit(1)


def _cmd_docker_stop(args: argparse.Namespace) -> None:
    ds = _get_docker_service()
    alias = _get_account_alias(args)
    timeout = getattr(args, "timeout", None)
    try:
        result = ds.stop_container(alias, args.container_id, timeout=timeout)
        _print_success(result)
    except Exception as e:
        _print_error(str(e))
        sys.exit(1)


def _cmd_docker_restart(args: argparse.Namespace) -> None:
    ds = _get_docker_service()
    alias = _get_account_alias(args)
    try:
        result = ds.restart_container(alias, args.container_id)
        _print_success(result)
    except Exception as e:
        _print_error(str(e))
        sys.exit(1)


def _cmd_docker_kill(args: argparse.Namespace) -> None:
    ds = _get_docker_service()
    alias = _get_account_alias(args)
    try:
        result = ds.kill_container(alias, args.container_id)
        _print_success(result)
    except Exception as e:
        _print_error(str(e))
        sys.exit(1)


def _cmd_docker_rm(args: argparse.Namespace) -> None:
    ds = _get_docker_service()
    alias = _get_account_alias(args)
    force = getattr(args, "force", False)
    try:
        result = ds.remove_container(alias, args.container_id, force=force)
        _print_success(result)
    except Exception as e:
        _print_error(str(e))
        sys.exit(1)


def _cmd_docker_logs(args: argparse.Namespace) -> None:
    ds = _get_docker_service()
    alias = _get_account_alias(args)
    tail = args.n or 100
    try:
        logs = ds.get_container_logs(alias, args.container_id, tail=tail)
        print(logs)
    except Exception as e:
        _print_error(str(e))
        sys.exit(1)


def _cmd_docker_exec(args: argparse.Namespace) -> None:
    ds = _get_docker_service()
    alias = _get_account_alias(args)
    command = args.command or "/bin/bash"
    try:
        exit_code, stdout, stderr = ds.exec_in_container(alias, args.container_id, command)
        if stdout:
            print(stdout)
        if stderr:
            print(Color.err(stderr), file=sys.stderr)
    except Exception as e:
        _print_error(str(e))
        sys.exit(1)


def _cmd_docker_images(args: argparse.Namespace) -> None:
    ds = _get_docker_service()
    alias = _get_account_alias(args)
    try:
        images = ds.list_images(alias)
        if not images:
            _print_info("无镜像")
            return
        headers = ["仓库", "标签", "镜像ID", "大小"]
        rows = []
        for img in images:
            repo = img.get("Repository") or img.get("repository", "")
            tag = img.get("Tag") or img.get("tag", "")
            img_id = (img.get("ID") or img.get("id", ""))[:12]
            size = img.get("Size") or img.get("size", "")
            rows.append([repo, tag, img_id, size])
        _print_table(headers, rows)
    except Exception as e:
        _print_error(str(e))
        sys.exit(1)


def _cmd_docker_pull(args: argparse.Namespace) -> None:
    ds = _get_docker_service()
    alias = _get_account_alias(args)
    _print_info(f"拉取镜像: {args.image}")
    try:
        result = ds.pull_image(alias, args.image)
        _print_success(result)
    except Exception as e:
        _print_error(str(e))
        sys.exit(1)


def _cmd_docker_rmi(args: argparse.Namespace) -> None:
    ds = _get_docker_service()
    alias = _get_account_alias(args)
    try:
        result = ds.remove_image(alias, args.image_id)
        _print_success(result)
    except Exception as e:
        _print_error(str(e))
        sys.exit(1)


def _cmd_docker_prune(args: argparse.Namespace) -> None:
    ds = _get_docker_service()
    alias = _get_account_alias(args)
    try:
        result = ds.prune_images(alias)
        reclaimed = result.get("SpaceReclaimed", 0)
        _print_success(f"清理完成，回收空间: {reclaimed} bytes")
    except Exception as e:
        _print_error(str(e))
        sys.exit(1)


def _cmd_docker_build(args: argparse.Namespace) -> None:
    ds = _get_docker_service()
    alias = _get_account_alias(args)
    _print_info(f"构建镜像: {args.tag} 从 {args.path}")
    try:
        dockerfile_path = getattr(args, "dockerfile", f"{args.path}/Dockerfile")
        result = ds.build_image(alias, args.tag, dockerfile_path, args.path)
        _print_success("构建完成")
        if result:
            print(result)
    except Exception as e:
        _print_error(str(e))
        sys.exit(1)


def _cmd_docker_network_ls(args: argparse.Namespace) -> None:
    ds = _get_docker_service()
    alias = _get_account_alias(args)
    try:
        networks = ds.list_networks(alias)
        if not networks:
            _print_info("无网络")
            return
        headers = ["网络ID", "名称", "驱动", "范围"]
        rows = []
        for net in networks:
            nid = (net.get("ID") or net.get("id", ""))[:12]
            name = net.get("Name") or net.get("name", "")
            driver = net.get("Driver") or net.get("driver", "")
            scope = net.get("Scope") or net.get("scope", "")
            rows.append([nid, name, driver, scope])
        _print_table(headers, rows)
    except Exception as e:
        _print_error(str(e))
        sys.exit(1)


def _cmd_docker_volume_ls(args: argparse.Namespace) -> None:
    ds = _get_docker_service()
    alias = _get_account_alias(args)
    try:
        volumes = ds.list_volumes(alias)
        if not volumes:
            _print_info("无卷")
            return
        headers = ["卷名", "驱动", "挂载点"]
        rows = []
        for vol in volumes:
            name = vol.get("Name") or vol.get("name", "")
            driver = vol.get("Driver") or vol.get("driver", "")
            mountpoint = vol.get("Mountpoint") or vol.get("mountpoint", "")
            rows.append([name, driver, mountpoint])
        _print_table(headers, rows)
    except Exception as e:
        _print_error(str(e))
        sys.exit(1)


def _cmd_compose_up(args: argparse.Namespace) -> None:
    ds = _get_docker_service()
    alias = _get_account_alias(args)
    project_path = args.project_path or "."
    detach = getattr(args, "detach", False)
    _print_info(f"Compose up: {project_path}")
    try:
        result = ds.compose_up(alias, project_path, detach=detach)
        if result:
            print(result)
        _print_success("Compose 已启动")
    except Exception as e:
        _print_error(str(e))
        sys.exit(1)


def _cmd_compose_down(args: argparse.Namespace) -> None:
    ds = _get_docker_service()
    alias = _get_account_alias(args)
    project_path = args.project_path or "."
    _print_info(f"Compose down: {project_path}")
    try:
        result = ds.compose_down(alias, project_path)
        if result:
            print(result)
        _print_success("Compose 已停止")
    except Exception as e:
        _print_error(str(e))
        sys.exit(1)


def _cmd_compose_ps(args: argparse.Namespace) -> None:
    ds = _get_docker_service()
    alias = _get_account_alias(args)
    project_path = args.project_path or "."
    try:
        services = ds.compose_ps(alias, project_path)
        if not services:
            _print_info("无服务")
            return
        headers = ["名称", "状态", "端口"]
        rows = []
        for svc in services:
            name = svc.get("Name") or svc.get("name", "")
            status = svc.get("Status") or svc.get("status", "")
            ports = svc.get("Ports") or svc.get("ports", "")
            rows.append([name, status, ports])
        _print_table(headers, rows)
    except Exception as e:
        _print_error(str(e))
        sys.exit(1)


def _cmd_compose_logs(args: argparse.Namespace) -> None:
    ds = _get_docker_service()
    alias = _get_account_alias(args)
    project_path = args.project_path or "."
    try:
        logs = ds.compose_logs(alias, project_path)
        print(logs)
    except Exception as e:
        _print_error(str(e))
        sys.exit(1)


def _cmd_ssh(args: argparse.Namespace) -> None:
    WebSSHConnectRequest = _lazy("app.models.webssh_session").WebSSHConnectRequest
    webssh_service = _lazy("app.services.webssh_service").webssh_service

    if args.subcmd == "sessions":
        sessions = webssh_service.list_sessions()
        if not sessions:
            _print_info("无活跃会话")
            return
        headers = ["会话ID", "账户", "主机", "用户", "状态"]
        rows = []
        for s in sessions:
            rows.append([
                s.session_id[:8],
                s.account_alias or "",
                s.host,
                s.username,
                s.status.value,
            ])
        _print_table(headers, rows)
        return

    if args.subcmd == "close":
        sid = args.session_id
        session = webssh_service.get_session(sid)
        if session is None:
            _print_error(f"会话 '{sid}' 不存在")
            sys.exit(1)
        webssh_service.close_session(sid)
        _print_success(f"会话 '{sid}' 已关闭")
        return

    if getattr(args, "browser", False):
        url = "http://localhost:8000/webssh"
        _print_info(f"在浏览器中打开: {url}")
        webbrowser.open(url)
        return

    if not args.subcmd and not args.host and not args.alias:
        url = "http://localhost:8000/webssh"
        _print_info(f"WebSSH 地址: {url}")
        _print_info("请确保后端服务已启动 (uvicorn app.main:app)")
        return

    host = args.host
    port = args.port or 22
    username = args.user
    alias = args.alias

    try:
        if alias:
            req = WebSSHConnectRequest(account_alias=alias)
            _print_info(f"使用账户 '{alias}' 连接...")
        elif host and username:
            req = WebSSHConnectRequest(
                host=host,
                port=port,
                username=username,
                password=args.password,
                auth_type=args.auth_type or "password",
            )
            _print_info(f"连接: {username}@{host}:{port}")
        else:
            _print_error("请指定 --alias 或 --host/--user 参数")
            _print_info("提示: opsv-kits ssh --alias <alias>")
            _print_info("       opsv-kits ssh --host <host> --user <username>")
            sys.exit(1)

        session = webssh_service.create_session(req)
        _print_success(f"SSH 会话已建立 (ID: {session.session_id})")
        _print_info(f"WebSSH 终端地址: http://localhost:8000/webssh?session={session.session_id}")
        if getattr(args, "browser", False):
            webbrowser.open(f"http://localhost:8000/webssh?session={session.session_id}")
    except Exception as e:
        _print_error(f"SSH 连接失败: {e}")
        sys.exit(1)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="opsv-kits",
        description="OpsV-Kits - 远程文件同步、编译运行与运维工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            使用示例:
              opsv-kits init                    初始化配置文件
              opsv-kits run                     执行完整流程
              opsv-kits sync                    仅同步文件
              opsv-kits account list            列出SSH账户
              opsv-kits remote ls /path         列出远程目录
              opsv-kits docker ps -a            列出所有容器
              opsv-kits docker-compose up -d    启动Compose项目
              opsv-kits ssh --alias 生产环境    打开SSH连接
        """),
    )
    parser.add_argument(
        "--version", action="version", version=f"OpsV-Kits {VERSION}"
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    p_init = subparsers.add_parser("init", help="初始化配置文件")
    p_init.set_defaults(func=_cmd_init)
    p_run = subparsers.add_parser("run", help="完整流程：同步→检查→编译→运行")
    _add_common_args(p_run)
    p_run.set_defaults(func=_cmd_run)
    p_sync = subparsers.add_parser("sync", help="仅同步文件")
    _add_common_args(p_sync)
    p_sync.add_argument("--force", action="store_true", help="强制全量同步")
    p_sync.add_argument("--only", action="store_true", help="仅同步不执行后续步骤")
    p_sync.set_defaults(func=_cmd_sync)
    p_setup = subparsers.add_parser("setup", help="仅检查并安装环境")
    _add_common_args(p_setup)
    p_setup.set_defaults(func=_cmd_setup)
    p_build = subparsers.add_parser("build", help="仅编译项目")
    _add_common_args(p_build)
    p_build.set_defaults(func=_cmd_build)
    p_start = subparsers.add_parser("start", help="仅运行项目")
    _add_common_args(p_start)
    p_start.set_defaults(func=_cmd_start)
    p_account = subparsers.add_parser("account", help="SSH 账户管理")
    p_account_sub = p_account.add_subparsers(dest="subcmd", help="账户管理命令")
    p_acct_add = p_account_sub.add_parser("add", help="添加 SSH 账户")
    p_acct_add.set_defaults(func=_cmd_account_add)
    p_acct_list = p_account_sub.add_parser("list", help="列出所有账户")
    p_acct_list.set_defaults(func=_cmd_account_list)
    p_acct_test = p_account_sub.add_parser("test", help="测试账户连接")
    p_acct_test.add_argument("alias", help="账户别名")
    p_acct_test.set_defaults(func=_cmd_account_test)
    p_acct_remove = p_account_sub.add_parser("remove", help="删除账户")
    p_acct_remove.add_argument("alias", help="账户别名")
    p_acct_remove.set_defaults(func=_cmd_account_remove)
    p_acct_default = p_account_sub.add_parser("default", help="设为默认账户")
    p_acct_default.add_argument("alias", help="账户别名")
    p_acct_default.set_defaults(func=_cmd_account_default)
    p_acct_edit = p_account_sub.add_parser("edit", help="编辑账户")
    p_acct_edit.add_argument("alias", help="账户别名")
    p_acct_edit.set_defaults(func=_cmd_account_edit)
    p_remote = subparsers.add_parser("remote", help="远程文件管理")
    _add_alias_arg(p_remote)
    _add_config_arg(p_remote)
    p_remote_sub = p_remote.add_subparsers(dest="subcmd", help="远程文件管理命令")
    p_rmt_ls = p_remote_sub.add_parser("ls", help="列出远程目录")
    p_rmt_ls.add_argument("path", nargs="?", default="/", help="远程路径")
    p_rmt_ls.set_defaults(func=_cmd_remote_ls)
    p_rmt_cat = p_remote_sub.add_parser("cat", help="查看文件内容")
    p_rmt_cat.add_argument("path", help="远程文件路径")
    p_rmt_cat.set_defaults(func=_cmd_remote_cat)
    p_rmt_upload = p_remote_sub.add_parser("upload", help="上传文件")
    p_rmt_upload.add_argument("local", help="本地路径")
    p_rmt_upload.add_argument("remote", help="远程路径")
    p_rmt_upload.set_defaults(func=_cmd_remote_upload)
    p_rmt_download = p_remote_sub.add_parser("download", help="下载文件")
    p_rmt_download.add_argument("remote", help="远程路径")
    p_rmt_download.add_argument("local", nargs="?", default=None, help="本地路径（可选）")
    p_rmt_download.set_defaults(func=_cmd_remote_download)
    p_rmt_rm = p_remote_sub.add_parser("rm", help="删除文件/目录")
    p_rmt_rm.add_argument("path", help="远程路径")
    p_rmt_rm.set_defaults(func=_cmd_remote_rm)
    p_rmt_mkdir = p_remote_sub.add_parser("mkdir", help="创建目录")
    p_rmt_mkdir.add_argument("path", help="远程路径")
    p_rmt_mkdir.set_defaults(func=_cmd_remote_mkdir)
    p_rmt_mv = p_remote_sub.add_parser("mv", help="移动/重命名")
    p_rmt_mv.add_argument("src", help="源路径")
    p_rmt_mv.add_argument("dst", help="目标路径")
    p_rmt_mv.set_defaults(func=_cmd_remote_mv)
    p_rmt_cp = p_remote_sub.add_parser("cp", help="复制")
    p_rmt_cp.add_argument("src", help="源路径")
    p_rmt_cp.add_argument("dst", help="目标路径")
    p_rmt_cp.set_defaults(func=_cmd_remote_cp)
    p_rmt_chmod = p_remote_sub.add_parser("chmod", help="修改权限")
    p_rmt_chmod.add_argument("mode", help="权限模式（如 755）")
    p_rmt_chmod.add_argument("path", help="远程路径")
    p_rmt_chmod.set_defaults(func=_cmd_remote_chmod)
    p_rmt_exec = p_remote_sub.add_parser("exec", help="执行命令")
    p_rmt_exec.add_argument("command", help="要执行的命令")
    p_rmt_exec.set_defaults(func=_cmd_remote_exec)
    p_rmt_find = p_remote_sub.add_parser("find", help="搜索文件")
    p_rmt_find.add_argument("path", help="搜索路径")
    p_rmt_find.add_argument("-name", required=True, help="文件名模式")
    p_rmt_find.set_defaults(func=_cmd_remote_find)
    p_docker = subparsers.add_parser("docker", help="Docker 容器管理")
    _add_alias_arg(p_docker)
    _add_config_arg(p_docker)
    p_docker_sub = p_docker.add_subparsers(dest="subcmd", help="Docker 管理命令")
    p_dk_info = p_docker_sub.add_parser("info", help="Docker 环境信息")
    p_dk_info.set_defaults(func=_cmd_docker_info)
    p_dk_install = p_docker_sub.add_parser("install", help="安装 Docker")
    p_dk_install.set_defaults(func=_cmd_docker_install)
    p_dk_ps = p_docker_sub.add_parser("ps", help="容器列表")
    p_dk_ps.add_argument("-a", "--all", action="store_true", dest="all", help="显示所有容器，包括已停止的")
    p_dk_ps.set_defaults(func=_cmd_docker_ps)
    p_dk_start = p_docker_sub.add_parser("start", help="启动容器")
    p_dk_start.add_argument("container_id", help="容器ID或名称")
    p_dk_start.set_defaults(func=_cmd_docker_start)
    p_dk_stop = p_docker_sub.add_parser("stop", help="停止容器")
    p_dk_stop.add_argument("container_id", help="容器ID或名称")
    p_dk_stop.add_argument("-t", "--timeout", type=int, default=None, help="超时时间(秒)")
    p_dk_stop.set_defaults(func=_cmd_docker_stop)
    p_dk_restart = p_docker_sub.add_parser("restart", help="重启容器")
    p_dk_restart.add_argument("container_id", help="容器ID或名称")
    p_dk_restart.set_defaults(func=_cmd_docker_restart)
    p_dk_kill = p_docker_sub.add_parser("kill", help="强制停止容器")
    p_dk_kill.add_argument("container_id", help="容器ID或名称")
    p_dk_kill.set_defaults(func=_cmd_docker_kill)
    p_dk_rm = p_docker_sub.add_parser("rm", help="删除容器")
    p_dk_rm.add_argument("container_id", help="容器ID或名称")
    p_dk_rm.add_argument("-f", "--force", action="store_true", help="强制删除运行中的容器")
    p_dk_rm.set_defaults(func=_cmd_docker_rm)
    p_dk_logs = p_docker_sub.add_parser("logs", help="查看容器日志")
    p_dk_logs.add_argument("container_id", help="容器ID或名称")
    p_dk_logs.add_argument("-n", type=int, default=100, help="显示最后N行 (默认100)")
    p_dk_logs.add_argument("-f", "--follow", action="store_true", help="实时跟踪日志")
    p_dk_logs.set_defaults(func=_cmd_docker_logs)
    p_dk_exec = p_docker_sub.add_parser("exec", help="在容器中执行命令")
    p_dk_exec.add_argument("container_id", help="容器ID或名称")
    p_dk_exec.add_argument("command", nargs="?", default="/bin/bash", help="要执行的命令 (默认 /bin/bash)")
    p_dk_exec.set_defaults(func=_cmd_docker_exec)
    p_dk_images = p_docker_sub.add_parser("images", help="镜像列表")
    p_dk_images.set_defaults(func=_cmd_docker_images)
    p_dk_pull = p_docker_sub.add_parser("pull", help="拉取镜像")
    p_dk_pull.add_argument("image", help="镜像名称[:tag]")
    p_dk_pull.set_defaults(func=_cmd_docker_pull)
    p_dk_rmi = p_docker_sub.add_parser("rmi", help="删除镜像")
    p_dk_rmi.add_argument("image_id", help="镜像ID或名称")
    p_dk_rmi.set_defaults(func=_cmd_docker_rmi)
    p_dk_prune = p_docker_sub.add_parser("prune", help="清理悬空镜像")
    p_dk_prune.set_defaults(func=_cmd_docker_prune)
    p_dk_build = p_docker_sub.add_parser("build", help="构建镜像")
    p_dk_build.add_argument("-t", "--tag", required=True, help="镜像标签")
    p_dk_build.add_argument("-f", "--dockerfile", default=None, help="Dockerfile 路径")
    p_dk_build.add_argument("path", help="构建上下文路径")
    p_dk_build.set_defaults(func=_cmd_docker_build)
    p_dk_network = p_docker_sub.add_parser("network", help="网络管理")
    p_dk_network_sub = p_dk_network.add_subparsers(dest="net_subcmd")
    p_dk_net_ls = p_dk_network_sub.add_parser("ls", help="列出网络")
    p_dk_net_ls.set_defaults(func=_cmd_docker_network_ls)
    p_dk_volume = p_docker_sub.add_parser("volume", help="卷管理")
    p_dk_volume_sub = p_dk_volume.add_subparsers(dest="vol_subcmd")
    p_dk_vol_ls = p_dk_volume_sub.add_parser("ls", help="列出卷")
    p_dk_vol_ls.set_defaults(func=_cmd_docker_volume_ls)
    p_compose = subparsers.add_parser("docker-compose", help="Docker Compose 管理")
    _add_alias_arg(p_compose)
    _add_config_arg(p_compose)
    p_compose.add_argument("project_path", nargs="?", default=".", help="Compose 项目路径")
    p_compose_sub = p_compose.add_subparsers(dest="subcmd", help="Compose 命令")
    p_cp_up = p_compose_sub.add_parser("up", help="启动 Compose 项目")
    p_cp_up.add_argument("-d", "--detach", action="store_true", help="后台运行")
    p_cp_up.set_defaults(func=_cmd_compose_up)
    p_cp_down = p_compose_sub.add_parser("down", help="停止 Compose 项目")
    p_cp_down.set_defaults(func=_cmd_compose_down)
    p_cp_ps = p_compose_sub.add_parser("ps", help="列出 Compose 服务状态")
    p_cp_ps.set_defaults(func=_cmd_compose_ps)
    p_cp_logs = p_compose_sub.add_parser("logs", help="查看 Compose 日志")
    p_cp_logs.set_defaults(func=_cmd_compose_logs)
    p_ssh = subparsers.add_parser("ssh", help="SSH 终端（WebSSH）")
    p_ssh.add_argument("alias", nargs="?", default=None, help="SSH 账户别名")
    p_ssh.add_argument("--host", default=None, help="主机地址")
    p_ssh.add_argument("--port", type=int, default=None, help="SSH 端口")
    p_ssh.add_argument("--user", default=None, help="用户名")
    p_ssh.add_argument("--password", default=None, help="密码")
    p_ssh.add_argument("--auth-type", default=None, choices=["password", "key", "agent"], help="认证方式")
    p_ssh.add_argument("--key", dest="private_key", default=None, help="私钥路径")
    p_ssh.add_argument("--browser", action="store_true", help="在浏览器中打开")
    p_ssh.add_argument("subcmd", nargs="?", default=None,
                       choices=["sessions", "close"],
                       help="子命令: sessions (会话列表) / close (关闭会话)")
    p_ssh.add_argument("session_id", nargs="?", default=None, help="会话ID（用于 close）")
    p_ssh.set_defaults(func=_cmd_ssh)
    return parser


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-c", "--config", default=None, help="配置文件路径")
    parser.add_argument("-l", "--local", default=None, help="本地路径")
    parser.add_argument("-r", "--remote", default=None, help="远程路径")
    _add_alias_arg(parser)


def _add_alias_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--alias", default=None, help="SSH 账户别名")


def _add_config_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-c", "--config", default=None, help="配置文件路径")


def main(argv: Optional[list[str]] = None) -> None:
    _enable_vt_mode()
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(0)

    try:
        args.func(args)
    except KeyboardInterrupt:
        print()
        _print_info("已取消")
        sys.exit(0)
    except Exception as e:
        _print_error(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
