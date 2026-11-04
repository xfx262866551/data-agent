
from dataclasses import asdict

from app.entities.column_info import ColumnInfo
from app.models.column_info import ColumnInfoMySQL


class ColumnInfoMapper:
    """ColumnInfo 映射器：业务实体 ↔ ORM 模型的双向转换"""
    
    def to_entity( column_info_mysql: ColumnInfoMySQL) -> ColumnInfo:
        """将 ORM 模型转换为业务实体"""
        return ColumnInfo(
            id=column_info_mysql.id,
            name =column_info_mysql.name,
            type=column_info_mysql.type,
            role=column_info_mysql.role,
            examples =column_info_mysql.examples,
            description=column_info_mysql.description,
            alias =column_info_mysql.alias,
            table_id=column_info_mysql.table_id,
        )
        
    @staticmethod
    def to_model( column_info: ColumnInfo) -> ColumnInfoMySQL:
        """把业务实体转成 ORM 模型（字段同名，asdict + 展开）"""
        return ColumnInfoMySQL(**asdict(column_info))