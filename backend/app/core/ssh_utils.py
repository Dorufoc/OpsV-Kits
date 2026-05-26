from __future__ import annotations

import logging
from typing import Optional

import paramiko

logger = logging.getLogger(__name__)


def resolve_remote_path(
    ssh: paramiko.SSHClient,
    path: str,
    username: Optional[str] = None,
) -> str:
    if not path.startswith("~"):
        return path
    try:
        _, stdout, _ = ssh.exec_command("echo $HOME", timeout=5.0)
        home = stdout.read().decode("utf-8", errors="replace").strip()
        if home:
            resolved = path.replace("~", home, 1)
            logger.info(f"展开远程路径: {path} → {resolved}")
            return resolved
    except Exception:
        pass
    fallback = f"/home/{username}" if username else "/root"
    resolved = path.replace("~", fallback, 1)
    logger.warning(f"展开远程路径(备用): {path} → {resolved}")
    return resolved
