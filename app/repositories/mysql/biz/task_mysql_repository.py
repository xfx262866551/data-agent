"""任务仓储：业务库里任务的增删改查"""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import TaskMySQL


class TaskMySQLRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, task: TaskMySQL) -> TaskMySQL:
        """新建任务（id 由调用方生成）"""
        self.session.add(task)
        await self.session.commit()
        return task

    async def list_by_user(
        self, user_id: str = "demo", limit: int = 50
    ) -> list[TaskMySQL]:
        """任务列表：按更新时间倒序（工作台左侧栏）"""
        stmt = (
            select(TaskMySQL)
            .where(TaskMySQL.user_id == user_id)
            .order_by(TaskMySQL.updated_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_by_id(self, task_id: str) -> TaskMySQL | None:
        return await self.session.get(TaskMySQL, task_id)

    async def rename(self, task_id: str, title: str) -> TaskMySQL | None:
        task = await self.session.get(TaskMySQL, task_id)
        if task:
            task.title = title
            await self.session.commit()
        return task

    async def touch(self, task_id: str, last_query: str):
        """每轮提问后更新：最后问题 + 轮数 + 更新时间"""
        task = await self.session.get(TaskMySQL, task_id)
        if task:
            task.last_query = last_query
            task.turn_count += 1
            await self.session.commit()

    async def delete(self, task_id: str) -> None:
        await self.session.execute(delete(TaskMySQL).where(TaskMySQL.id == task_id))
        await self.session.commit()
