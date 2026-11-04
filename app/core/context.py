"""请求级上下文：request_id 的 ContextVar，用于全链路日志追踪"""

from contextvars import ContextVar

request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="-")
