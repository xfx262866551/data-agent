"""FastAPI 应用入口"""

import uuid

from fastapi import FastAPI, Request

from app.api.lifespan import lifespan
from app.api.routers.query_router import query_router
from app.core.context import request_id_ctx_var
from app.api.routers.task_router import task_router

app = FastAPI(lifespan=lifespan)
app.include_router(query_router)
app.include_router(task_router)

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """每个请求生成一个 request_id 塞进上下文（日志链路追踪用）"""
    request_id_ctx_var.set(uuid.uuid4())
    return await call_next(request)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
