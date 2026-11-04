from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TaskMySQL(Base):
    """问数任务表对应的 ORM 模型"""

    __tablename__ = "task"

    # id 就是 LangGraph 的 thread_id：一个任务 = 一个会话
    id: Mapped[str] = mapped_column(String(36), primary_key=True, comment="任务ID")
    title: Mapped[str] = mapped_column(String(200), comment="任务标题")
    user_id: Mapped[str] = mapped_column(String(64), default="demo", comment="用户标识")
    last_query: Mapped[str | None] = mapped_column(Text, comment="最后一次提问")
    turn_count: Mapped[int] = mapped_column(Integer, default=0, comment="对话轮数")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )