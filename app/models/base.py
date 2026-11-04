"""ORM 基类

所有 SQLAlchemy ORM 模型共享的声明式基类。
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """ORM 基类"""
    pass
    