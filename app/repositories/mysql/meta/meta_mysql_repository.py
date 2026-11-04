from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.entities.column_info import ColumnInfo
from app.entities.column_metric import ColumnMetric
from app.entities.metric_info import MetricInfo
from app.entities.table_info import TableInfo
from app.models.column_info import ColumnInfoMySQL
from app.models.table_info import TableInfoMySQL
from app.repositories.mysql.meta.mappers.column_info_mapper import ColumnInfoMapper
from app.repositories.mysql.meta.mappers.column_metric_mapper import ColumnMetricMapper
from app.repositories.mysql.meta.mappers.metric_info_mapper import MetricInfoMapper
from app.repositories.mysql.meta.mappers.table_info_mapper import TableInfoMapper


class MetaMySQLRepository:
    """负责把元数据业务实体持久化到 Meta MySQL"""

    def __init__(self, session: AsyncSession):
        # session 由外部传入：Repository 不建连接、不管事务边界
        self.session = session

    def save_table_infos(self, table_infos: list[TableInfo]):
        """批量保存表元数据（只入队，不发 SQL，所以不是 async）"""
        self.session.add_all(
            [TableInfoMapper.to_model(table_info) for table_info in table_infos]
        )

    def save_column_infos(self, column_infos: list[ColumnInfo]):
        """批量保存字段元数据"""
        self.session.add_all(
            [ColumnInfoMapper.to_model(column_info) for column_info in column_infos]
        )

    def save_metric_infos(self, metric_infos: list[MetricInfo]):
        """批量保存指标元数据"""
        self.session.add_all(
            [MetricInfoMapper.to_model(metric_info) for metric_info in metric_infos]
        )

    def save_column_metrics(self, column_metrics: list[ColumnMetric]):
        """批量保存字段与指标的关联关系"""
        self.session.add_all(
            [
                ColumnMetricMapper.to_model(column_metric)
                for column_metric in column_metrics
            ]
        )

    async def get_column_info_by_id(self, id: str) -> ColumnInfo | None:
        """按字段 id 查字段元数据，供召回信息合并阶段补齐上下文"""
        column_info: ColumnInfoMySQL | None = await self.session.get(ColumnInfoMySQL, id)
        if column_info:
            return ColumnInfoMapper.to_entity(column_info)
        return None

    async def get_table_info_by_id(self, id: str) -> TableInfo | None:
        """按表 id 查表元数据，最终组装成提示词里的表结构信息"""
        table_info: TableInfoMySQL | None = await self.session.get(TableInfoMySQL, id)
        if table_info:
            return TableInfoMapper.to_entity(table_info)
        return None

    async def get_key_columns_by_table_id(self, table_id: str) -> list[ColumnInfo]:
        """查指定表的主外键字段——Join 关键字段不能只靠向量召回命中"""
        # :table_id 是参数占位符，实际值通过第二个参数传入（绝不拼进 SQL 字符串）
        sql = "select * from column_info where table_id = :table_id and role in ('primary_key','foreign_key')"
        result = await self.session.execute(text(sql), {"table_id": table_id})
        # mappings() 的结果行可以按列名取值，dict(row) 后正好匹配 ColumnInfo 字段
        return [ColumnInfo(**dict(row)) for row in result.mappings().fetchall()]