from __future__ import annotations

from typing import Optional

from app.core.remote_executor import RemoteExecutor, RemoteExecutorError


class PackageManagerError(Exception):
    pass


class PackageManager:
    def __init__(self, account_alias: str):
        self._account_alias = account_alias
        self._executor = RemoteExecutor(account_alias)
        self._manager: Optional[str] = None
        self._install_command: Optional[str] = None

    def detect(
        self, account_alias: str | None = None, project_path: str = ""
    ) -> str:
        executor = self._executor
        if account_alias and account_alias != self._account_alias:
            executor = RemoteExecutor(account_alias)

        if not project_path:
            raise PackageManagerError("项目路径不能为空")

        resolved_path = executor.resolve_path(project_path)

        lock_files = [
            ("pnpm-lock.yaml", "pnpm"),
            ("yarn.lock", "yarn"),
            ("package-lock.json", "npm"),
            ("npm-shrinkwrap.json", "npm"),
        ]

        for lock_file, manager in lock_files:
            check = executor.exec_command(
                f"test -f '{resolved_path}/{lock_file}' && echo 'yes' || echo 'no'"
            )
            if check.success and check.stdout.strip() == "yes":
                self._manager = manager
                self._install_command = self._build_install_command(manager)
                return manager

        if executor.exec_command("which pnpm 2>/dev/null").success:
            self._manager = "pnpm"
        elif executor.exec_command("which yarn 2>/dev/null").success:
            self._manager = "yarn"
        elif executor.exec_command("which npm 2>/dev/null").success:
            self._manager = "npm"
        else:
            self._manager = "npm"

        self._install_command = self._build_install_command(self._manager)
        return self._manager

    def _build_install_command(self, manager: str) -> str:
        commands = {
            "npm": "npm install",
            "yarn": "yarn install",
            "pnpm": "pnpm install",
        }
        return commands.get(manager, "npm install")

    def get_install_command(self) -> str:
        if self._install_command is None:
            raise PackageManagerError("请先调用 detect() 方法检测包管理器")
        return self._install_command

    def get_manager(self) -> str:
        if self._manager is None:
            raise PackageManagerError("请先调用 detect() 方法检测包管理器")
        return self._manager

    def get_run_command(self, script: str) -> str:
        if self._manager is None:
            raise PackageManagerError("请先调用 detect() 方法检测包管理器")
        if self._manager == "npm":
            return f"npm run {script}"
        if self._manager == "yarn":
            return f"yarn {script}"
        if self._manager == "pnpm":
            return f"pnpm {script}"
        return f"npm run {script}"

    def get_build_command(self) -> str:
        return self.get_run_command("build")

    def get_dev_command(self) -> str:
        return self.get_run_command("dev")
