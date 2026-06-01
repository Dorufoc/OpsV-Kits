import logging


def patch_uvicorn_logging() -> None:
    """将 uvicorn 的日志器接入项目的日志配置，避免 uvicorn 覆盖 logging.basicConfig 的设置"""
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
