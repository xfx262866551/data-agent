
"""问数查询接口路由

路由层只处理请求体、依赖声明和响应类型，不直接创建 Repository 或执行图节点。
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from starlette.responses import StreamingResponse

from app.api.dependencies import get_query_service
from app.api.schemas.query_schema import QuerySchema, TaskQuerySchema
from app.services.query_service import QueryService

query_router = APIRouter()


@query_router.post("/api/query")
async def query_handler(
    query: QuerySchema,
    query_service: Annotated[QueryService, Depends(get_query_service)],
):
    """接收自然语言问题，以 SSE 流式返回工作流输出"""

    return StreamingResponse(
        # 无状态单轮：每次开一个一次性 thread，不继承任何历史
        query_service.query(query.query, thread_id=str(uuid.uuid4())),
        media_type="text/event-stream",  # SSE 媒体类型
    )
    
# app/api/routers/query_router.py 追加一个路由
@query_router.post("/api/tasks/{task_id}/query")
async def task_query_handler(
    task_id: str,
    query: TaskQuerySchema,
    query_service: Annotated[QueryService, Depends(get_query_service)],
):
    """在指定任务下提问——同一个 task_id 自动带上该任务的历史"""

    return StreamingResponse(
        query_service.query(query.query, thread_id=task_id),
        media_type="text/event-stream",
    )
