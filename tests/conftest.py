import sys
import threading
from pathlib import Path

backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

_original_thread_init = threading.Thread.__init__
_blocked_thread_names = {
    "_reap",
    "webssh-reaper",
}


def _patched_thread_init(self, *args, **kwargs):
    target = kwargs.get("target") or (args[1] if len(args) > 1 else None)
    name = kwargs.get("name") or (args[2] if len(args) > 2 else None)
    if name in _blocked_thread_names:
        kwargs["target"] = lambda: None
        kwargs["name"] = f"{name}-blocked"
    elif name and isinstance(name, str) and (name.startswith("webssh-reader-") or name.startswith("ssh-reader-") or name.startswith("ssh-keepalive-")):
        kwargs["target"] = lambda: None
        kwargs["name"] = f"{name}-blocked"
    elif target is not None:
        try:
            qualname = getattr(target, "__qualname__", "") or ""
            if "_reap" in qualname or "_start_metric_watcher" in qualname or "_reader_loop" in qualname:
                kwargs["target"] = lambda: None
                kwargs["name"] = f"blocked-{qualname}"
        except Exception:
            pass
    _original_thread_init(self, *args, **kwargs)


threading.Thread.__init__ = _patched_thread_init


def pytest_configure(config):
    try:
        import app.core.ssh_pool as ssh_pool_mod
        if hasattr(ssh_pool_mod, "SSHPool"):
            ssh_pool_mod.SSHPool._start_reaper = lambda self: None
    except Exception:
        pass
    try:
        import app.services.webssh_service as webssh_mod
        if hasattr(webssh_mod, "WebSSHService"):
            webssh_mod.WebSSHService._start_reaper = lambda self: None
    except Exception:
        pass
