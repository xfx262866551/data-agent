"""日志初始化：统一格式 + request_id 注入 + 按配置输出控制台/文件"""

import sys
from pathlib import Path

from loguru import logger

from app.conf.app_config import app_config
from app.core.context import request_id_ctx_var

log_format = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
    "{level: <8} | "
    "request_id - {extra[request_id]} | "
    "{name}:{function}:{line} - "
    "{message}"
)


def inject_request_id(record):
    """把上下文里的 request_id 注入每条日志"""
    record["extra"]["request_id"] = request_id_ctx_var.get()


logger.remove()                      # 去掉默认输出，避免重复
logger = logger.patch(inject_request_id)

if app_config.logging.console.enable:
    logger.add(sink=sys.stdout, level=app_config.logging.console.level, format=log_format)

if app_config.logging.file.enable:
    path = Path(app_config.logging.file.path)
    path.mkdir(parents=True, exist_ok=True)
    logger.add(
        sink=path / "app.log",
        level=app_config.logging.file.level,
        format=log_format,
        rotation=app_config.logging.file.rotation,
        retention=app_config.logging.file.retention,
        encoding="utf-8",
    )