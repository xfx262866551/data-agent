from dataclasses import asdict
from app.entities.column_metric import ColumnMetric
from app.models.column_metric import ColumnMetricMySQL



class ColumnMetricMapper:
    """ColumnMetric 映射器：业务实体 ↔ ORM 模型的双向转换"""
    
    @staticmethod
    def to_entity( column_metric_mysql: ColumnMetricMySQL) -> ColumnMetric:
        """将 ORM 模型转换为业务实体"""
        return ColumnMetric(
            column_id=column_metric_mysql.column_id,
            metric_id=column_metric_mysql.metric_id,
        )
        
    @staticmethod
    def to_model( column_metric: ColumnMetric) -> ColumnMetricMySQL:
        """把业务实体转成 ORM 模型（字段同名，asdict + 展开）"""
        return ColumnMetricMySQL(**asdict(column_metric))