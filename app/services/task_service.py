import uuid

from app.clients.mysql_client_manager import biz_mysql_client_manager
from app.repositories.mysql.biz.task_mysql_repository import TaskMySQLRepository


class TaskService:
    async def create(self, question: str | None = None) -> dict:
        """新建任务：没有标题就用问题前 20 字，否则"新任务" """
        async with biz_mysql_client_manager.session_factory() as session:
            repo = TaskMySQLRepository(session)
            from app.models.task import TaskMySQL

            title = (question or "新任务")[:20]
            task = await repo.create(
                TaskMySQL(id=str(uuid.uuid4()), title=title, user_id="demo")
            )
            return {
                "id": task.id,
                "title": task.title,
                "turn_count": task.turn_count,
            }

    async def list(self) -> list[dict]:
        async with biz_mysql_client_manager.session_factory() as session:
            repo = TaskMySQLRepository(session)
            rows = await repo.list_by_user()
            return [
                {
                    "id": r.id,
                    "title": r.title,
                    "last_query": r.last_query,
                    "turn_count": r.turn_count,
                    "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                }
                for r in rows
            ]

    async def rename(self, task_id: str, title: str) -> bool:
        async with biz_mysql_client_manager.session_factory() as session:
            repo = TaskMySQLRepository(session)
            return await repo.rename(task_id, title) is not None

    async def delete(self, task_id: str) -> None:
        async with biz_mysql_client_manager.session_factory() as session:
            repo = TaskMySQLRepository(session)
            await repo.delete(task_id)
