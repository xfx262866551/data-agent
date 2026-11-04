from dataclasses import asdict
from app.entities.metric_info import MetricInfo
from app.models.metric_info import MetricInfoMySQL


class MetricInfoMapper:
    """MetricInfo 映射器：业务实体 ↔ ORM 模型的双向转换"""
    
    @staticmethod
    def to_entity( metric_info_mysql: MetricInfoMySQL) -> MetricInfo:
        """将 ORM 模型转换为业务实体"""
        return MetricInfo(
            id=metric_info_mysql.id,
            name=metric_info_mysql.name,
            description=metric_info_mysql.description,
            relevant_columns =metric_info_mysql.relevant_columns,
            alias =metric_info_mysql.alias,
        )
        
    @staticmethod
    def to_model( metric_info: MetricInfo) -> MetricInfoMySQL:
        """把业务实体转成 ORM 模型（字段同名，asdict + 展开）"""
        return MetricInfoMySQL(**asdict(metric_info))