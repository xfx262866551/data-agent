"""任务接口的请求/响应模型"""

from pydantic import BaseModel


class CreateTaskRequest(BaseModel):
    question: str | None = None


class RenameTaskRequest(BaseModel):
    title: str


class TaskItem(BaseModel):
    id: str
    title: str
    last_query: str | None = None
    turn_count: int = 0
    updated_at: str | None = None
