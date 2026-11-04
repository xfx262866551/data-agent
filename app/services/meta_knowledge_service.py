"""元数据知识构建服务（上）

组织“表/字段 → Meta MySQL + Qdrant 向量”这条链路；
字段取值 ES 索引与指标链路见本文件下半部分。
"""

import uuid
from dataclasses import asdict
from pathlib import Path
from app.conf.app_config import app_config
from omegaconf import OmegaConf
from sqlalchemy import delete
from app.models.column_info import ColumnInfoMySQL
from app.models.table_info import TableInfoMySQL
from app.conf.meta_config import MetaConfig
from app.entities.column_info import ColumnInfo
from app.entities.table_info import TableInfo
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.point_id import to_point_id
from app.entities.metric_info import MetricInfo
from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository
from app.entities.column_metric import ColumnMetric
from app.entities.column_info import ColumnInfo
from app.entities.metric_info import MetricInfo
from app.entities.table_info import TableInfo
from app.entities.value_info import ValueInfo
from app.models.column_info import ColumnInfoMySQL
from app.models.column_metric import ColumnMetricMySQL
from app.models.metric_info import MetricInfoMySQL
from app.models.table_info import TableInfoMySQL
from langchain_openai import OpenAIEmbeddings
from app.core.log import logger

class MetaKnowledgeService:
    """串联元数据知识库构建流程的应用服务"""

    def __init__(
        self,
        meta_mysql_repository: MetaMySQLRepository,
        dw_mysql_repository: DWMySQLRepository,
        column_qdrant_repository: ColumnQdrantRepository,
        embedding_client: OpenAIEmbeddings,           # 向量化客户端，由调用方注入
        value_es_repository: ValueESRepository,
        metric_qdrant_repository: MetricQdrantRepository,
    ):
        self.meta_mysql_repository = meta_mysql_repository
        self.dw_mysql_repository = dw_mysql_repository
        self.column_qdrant_repository = column_qdrant_repository
        self.embedding_client = embedding_client
        self.value_es_repository = value_es_repository
        self.metric_qdrant_repository = metric_qdrant_repository

    async def _embed(self, texts: list[str]) -> list[list[float]]:
        """向量化（包一层：以后换 embedding 实现只改这里）"""
        return await self.embedding_client.aembed_documents(texts)

    async def _save_tables_to_meta_db(self, meta_config: MetaConfig) -> list[ColumnInfo]:
        """把配置里的表/字段信息补齐真实类型后写入 Meta MySQL"""
        table_infos: list[TableInfo] = []
        column_infos: list[ColumnInfo] = []

        for table in meta_config.tables:
            table_infos.append(
                TableInfo(
                    id=table.name,
                    name=table.name,
                    role=table.role,
                    description=table.description,
                )
            )

            # 字段真实类型只有数仓知道，回 dw 查
            column_types = await self.dw_mysql_repository.get_column_types(table.name)

            for column in table.columns:
                # 示例值只取少量，供模型判断字段语义与枚举取值
                column_values = await self.dw_mysql_repository.get_column_values(
                    table.name, column.name
                )
                column_infos.append(
                    ColumnInfo(
                        id=f"{table.name}.{column.name}",
                        name=column.name,
                        type=column_types[column.name],
                        role=column.role,
                        examples=column_values,
                        description=column.description,
                        alias=column.alias,
                        table_id=table.name,
                    )
                )

        # 事务边界在这：表 + 字段要么全写进去，要么全不回滚
        # 先删后插（重建语义）：脚本重复跑也幂等，且配置里删掉的字段会同步消失
        async with self.meta_mysql_repository.session.begin():
            await self.meta_mysql_repository.session.execute(delete(TableInfoMySQL))
            await self.meta_mysql_repository.session.execute(delete(ColumnInfoMySQL))
            self.meta_mysql_repository.save_table_infos(table_infos)
            self.meta_mysql_repository.save_column_infos(column_infos)

        return column_infos

    async def _save_column_info_to_qdrant(self, column_infos: list[ColumnInfo]):
        """把字段元数据拆成多个语义入口，建成 Qdrant 向量点"""
        await self.column_qdrant_repository.ensure_collection()

        points: list[dict] = []
        for column_info in column_infos:
            # 一个字段拆 3 类语义入口：名字、描述、每个别名各一个点
            # payload 都是完整 ColumnInfo——搜到任何一条都能还原整个字段
            entries = [("name", column_info.name), ("desc", column_info.description)]
            entries += [("alias", alia) for alia in column_info.alias]

            for kind, text in entries:
                points.append(
                    {
                        # 确定性 id：重跑覆盖同一批点，不会越堆越多
                        "id": to_point_id(f"{column_info.id}.{kind}.{text}"),
                        "embedding_text": text,
                        "payload": asdict(column_info),
                    }
                )

        # 先集中向量化（分批 20），再一次性 upsert，避免逐条请求
        embeddings: list[list[float]] = []
        embedding_texts = [point["embedding_text"] for point in points]
        batch_size = 20
        for i in range(0, len(embedding_texts), batch_size):
            batch = await self._embed(embedding_texts[i : i + batch_size])
            embeddings.extend(batch)

        await self.column_qdrant_repository.upsert(
            ids=[point["id"] for point in points],
            embeddings=embeddings,
            payloads=[point["payload"] for point in points],
        )
    
    async def _save_value_info_to_es(
        self, meta_config: MetaConfig, column_infos: list[ColumnInfo]
    ):
        """把允许同步的字段真实取值写入 ES 全文索引"""
        await self.value_es_repository.ensure_index()

        # 配置里显式声明哪些字段同步取值：表.字段 → bool
        column2sync: dict[str, bool] = {}
        for table in meta_config.tables:
            for column in table.columns:
                column2sync[f"{table.name}.{column.name}"] = column.sync

        value_infos: list[ValueInfo] = []
        for column_info in column_infos:
            if not column2sync[column_info.id]:
                continue
            # 全量取值（不是少量示例）：供关键词检索用
            current_values = await self.dw_mysql_repository.get_column_values(
                column_info.table_id, column_info.name, 100000
            )
            value_infos.extend(
                ValueInfo(
                    id=f"{column_info.id}.{value}",
                    value=value,
                    column_id=column_info.id,
                )
                for value in current_values
            )

        await self.value_es_repository.index(value_infos)
        
    async def _save_metrics_to_meta_db(self, meta_config: MetaConfig) -> list[MetricInfo]:
        """把指标信息和字段依赖关系写入 Meta MySQL"""
        metric_infos: list[MetricInfo] = []
        column_metrics: list[ColumnMetric] = []

        for metric in meta_config.metrics:
            metric_infos.append(
                MetricInfo(
                    id=metric.name,               # 指标名直接当稳定业务 id
                    name=metric.name,
                    description=metric.description,
                    relevant_columns=metric.relevant_columns,
                    alias=metric.alias,
                )
            )
            for column in metric.relevant_columns:
                # ColumnMetric 单独表达"某指标依赖某字段"
                column_metrics.append(
                    ColumnMetric(column_id=column, metric_id=metric.name)
                )

        # 指标和关系同一笔事务；先删后插保幂等（重复构建不报错）
        async with self.meta_mysql_repository.session.begin():
            await self.meta_mysql_repository.session.execute(delete(MetricInfoMySQL))
            await self.meta_mysql_repository.session.execute(delete(ColumnMetricMySQL))
            self.meta_mysql_repository.save_metric_infos(metric_infos)
            self.meta_mysql_repository.save_column_metrics(column_metrics)

        return metric_infos
    
    async def _save_metrics_to_qdrant(self, metric_infos: list[MetricInfo]):
        """把指标元数据拆成多个语义入口，建成 Qdrant 向量点"""
        await self.metric_qdrant_repository.ensure_collection()

        points: list[dict] = []
        for metric_info in metric_infos:
            entries = [("name", metric_info.name), ("desc", metric_info.description)]
            entries += [("alias", alia) for alia in metric_info.alias]
            for kind, text in entries:
                points.append(
                    {
                        "id": to_point_id(f"{metric_info.id}.{kind}.{text}"),
                        "embedding_text": text,
                        "payload": asdict(metric_info),
                    }
                )

        embeddings: list[list[float]] = []
        embedding_texts = [point["embedding_text"] for point in points]
        batch_size = 20
        for i in range(0, len(embedding_texts), batch_size):
            embeddings.extend(await self._embed(embedding_texts[i : i + batch_size]))

        await self.metric_qdrant_repository.upsert(
            ids=[point["id"] for point in points],
            embeddings=embeddings,
            payloads=[point["payload"] for point in points],
        )

    async def build(self, config_path: Path):
        """读取配置并依次构建 Meta MySQL / Qdrant / ES 中的元数据索引"""
        context = OmegaConf.load(config_path)
        schema = OmegaConf.structured(MetaConfig)
        meta_config: MetaConfig = OmegaConf.to_object(OmegaConf.merge(schema, context))

        # 配置里有表才建表链路，有指标才建指标链路（Optional 分阶段构建）
        if meta_config.tables:
            column_infos = await self._save_tables_to_meta_db(meta_config)
            logger.info("保存表信息和字段信息到 Meta MySQL：", len(column_infos), "个字段")
            await self._save_column_info_to_qdrant(column_infos)
            logger.info("为字段信息建立向量索引")
            await self._save_value_info_to_es(meta_config, column_infos)
            logger.info("为字段取值建立全文索引")

        if meta_config.metrics:
            metric_infos = await self._save_metrics_to_meta_db(meta_config)
            logger.info("保存指标信息到 Meta MySQL：", len(metric_infos), "个指标")
            await self._save_metrics_to_qdrant(metric_infos)
            logger.info("为指标信息建立向量索引")