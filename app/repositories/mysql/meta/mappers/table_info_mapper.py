"""TableInfo 映射器：业务实体 ↔ ORM 模型的双向转换"""
from dataclasses import asdict

from app.entities.table_info import TableInfo
from app.models.table_info import TableInfoMySQL



class TableInfoMapper:
    """TableInfo 映射器：业务实体 ↔ ORM 模型的双向转换"""
    
    @staticmethod
    def to_entity( table_info_mysql: TableInfoMySQL) -> TableInfo:
        """将 ORM 模型转换为业务实体"""
        return TableInfo(
            id=table_info_mysql.id,
            name=table_info_mysql.name,
            role=table_info_mysql.role,
            description=table_info_mysql.description,
        )
        
    @staticmethod
    def to_model( table_info: TableInfo) -> TableInfoMySQL:
        """把业务实体转成 ORM 模型（字段同名，asdict + 展开）"""
        return TableInfoMySQL(**asdict(table_info))
        
   