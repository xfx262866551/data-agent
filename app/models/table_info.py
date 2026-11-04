"""table_info ORM 模型：元数据里"表"的映射"""
from sqlalchemy import String, Text

from app.models.base import Base
from sqlalchemy.orm import Mapped, mapped_column

class TableInfoMySQL(Base):
    """表信息"""
    __tablename__  = "table_info"
     # id 直接使用表名：既是主键，也是字段归属关系里的表标识
    id:Mapped[str] = mapped_column(String(64), primary_key=True,comment="表编号")
    name:Mapped[str | None] = mapped_column(String(128), comment="表名称")
    role:Mapped[str | None] = mapped_column(String(32), comment="表类型(fact/dim)")
    description:Mapped[str | None] = mapped_column(Text, comment="表描述")
