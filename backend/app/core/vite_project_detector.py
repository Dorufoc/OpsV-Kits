from __future__ import annotations

import json
from typing import Optional

from app.core.remote_executor import RemoteExecutor, RemoteExecutorError


class ViteProjectDetectorError(Exception):
    pass


class ViteProjectDetector:
    def __init__(self, account_alias: str):
        self._account_alias = account_alias
        self._executor = RemoteExecutor(account_alias)

    def is_vite_project(
        self, account_alias: str | None = None, project_path: str = ""
    ) -> dict:
        executor = self._executor
        if account_alias and account_alias != self._account_alias:
            executor = RemoteExecutor(account_alias)

        if not project_path:
            raise ViteProjectDetectorError("项目路径不能为空")

        resolved_path = executor.resolve_path(project_path)
        result = {
            "is_vite": False,
            "has_vite_config": False,
            "has_vite_dependency": False,
            "vite_config_file": "",
            "vite_version": "",
        }

        config_check = executor.exec_command(
            f"bash -c 'for f in vite.config.js vite.config.ts vite.config.mjs vite.config.cjs vite.config.mts; do "
            f"if [ -f \"{resolved_path}/$f\" ]; then echo \"$f\"; break; fi; done'"
        )
        if config_check.success and config_check.stdout.strip():
            result["has_vite_config"] = True
            result["vite_config_file"] = config_check.stdout.strip().split("\n")[0].strip()

        package_json_path = f"{resolved_path}/package.json"
        pkg_check = executor.exec_command(f"cat '{package_json_path}' 2>/dev/null || true")
        if pkg_check.success and pkg_check.stdout.strip():
            try:
                pkg_data = json.loads(pkg_check.stdout.strip())
                deps = pkg_data.get("dependencies", {})
                dev_deps = pkg_data.get("devDependencies", {})

                vite_in_deps = "vite" in deps
                vite_in_dev_deps = "vite" in dev_deps

                if vite_in_deps or vite_in_dev_deps:
                    result["has_vite_dependency"] = True
                    result["vite_version"] = deps.get("vite", dev_deps.get("vite", ""))
            except json.JSONDecodeError:
                pass

        result["is_vite"] = result["has_vite_config"] or result["has_vite_dependency"]
        return result

    def detect_framework(
        self, account_alias: str | None = None, project_path: str = ""
    ) -> dict:
        executor = self._executor
        if account_alias and account_alias != self._account_alias:
            executor = RemoteExecutor(account_alias)

        if not project_path:
            raise ViteProjectDetectorError("项目路径不能为空")

        resolved_path = executor.resolve_path(project_path)
        framework_result = {
            "framework": "unknown",
            "has_react": False,
            "has_vue": False,
            "has_svelte": False,
            "has_preact": False,
            "has_solid": False,
            "has_lit": False,
        }

        pkg_check = executor.exec_command(
            f"cat '{resolved_path}/package.json' 2>/dev/null || true"
        )
        if not pkg_check.success or not pkg_check.stdout.strip():
            return framework_result

        try:
            pkg_data = json.loads(pkg_check.stdout.strip())
            deps = pkg_data.get("dependencies", {})
            dev_deps = pkg_data.get("devDependencies", {})
            all_deps = {**deps, **dev_deps}

            if "@vitejs/plugin-react" in dev_deps or "react" in deps:
                framework_result["has_react"] = True
                framework_result["framework"] = "react"
            elif "@vitejs/plugin-vue" in dev_deps or "vue" in deps:
                framework_result["has_vue"] = True
                framework_result["framework"] = "vue"
            elif "@vitejs/plugin-svelte" in dev_deps or "svelte" in deps:
                framework_result["has_svelte"] = True
                framework_result["framework"] = "svelte"
            elif "@vitejs/plugin-preact" in dev_deps or "preact" in deps:
                framework_result["has_preact"] = True
                framework_result["framework"] = "preact"
            elif "@vitejs/plugin-solid" in dev_deps or "solid-js" in deps:
                framework_result["has_solid"] = True
                framework_result["framework"] = "solid"
            elif "@vitejs/plugin-lit" in dev_deps or "lit" in deps:
                framework_result["has_lit"] = True
                framework_result["framework"] = "lit"
        except json.JSONDecodeError:
            pass

        return framework_result
