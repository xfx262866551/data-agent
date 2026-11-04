"""任务接口路由：工作台的数据源"""

from fastapi import APIRouter, HTTPException

from app.api.schemas.task_schema import (
    CreateTaskRequest,
    RenameTaskRequest,
    TaskItem,
)
from app.services.task_service import TaskService

task_router = APIRouter(prefix="/api")
_service = TaskService()


@task_router.post("/tasks", response_model=TaskItem)
async def create_task(req: CreateTaskRequest):
    """新建任务（工作台"新建"按钮）"""
    return await _service.create(req.question)


@task_router.get("/tasks", response_model=list[TaskItem])
async def list_tasks():
    """任务列表（左侧栏，按更新时间倒序）"""
    return await _service.list()


@task_router.patch("/tasks/{task_id}", response_model=TaskItem)
async def rename_task(task_id: str, req: RenameTaskRequest):
    """重命名任务"""
    ok = await _service.rename(task_id, req.title)
    if not ok:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"id": task_id, "title": req.title}


@task_router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(task_id: str):
    """删除任务"""
    await _service.delete(task_id)
