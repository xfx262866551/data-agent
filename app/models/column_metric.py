from sqlalchemy import String
from app.models.base import Base
from sqlalchemy.orm import Mapped, mapped_column



class ColumnMetricMySQL(Base):
    """字段指标关联"""
    __tablename__  = "column_metric"
    
     # 联合主键：同一对（字段, 指标）关系只允许出现一次
    column_id:Mapped[str | None] = mapped_column(String(64), primary_key=True, comment="列编号")
    metric_id:Mapped[str | None] = mapped_column(String(64), primary_key=True, comment="指标编号")
