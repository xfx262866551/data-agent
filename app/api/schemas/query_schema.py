# app/api/schemas/query_schema.py
"""问数接口请求体定义"""

from pydantic import BaseModel


class QuerySchema(BaseModel):
    """/api/query 请求体：{"query": "统计华北地区销售额"}"""

    query: str

class TaskQuerySchema(BaseModel):
    """任务内提问：在某个任务（会话）里继续问"""
    query: str