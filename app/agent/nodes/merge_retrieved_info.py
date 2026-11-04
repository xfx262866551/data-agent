"""召回信息合并节点

把字段/取值/指标三路召回结果聚合成统一上下文：补齐指标依赖字段、
字段真实取值、主外键和表信息，输出 SQL 生成前的候选表结构和指标结构。
"""

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import (
    ColumnInfoState,
    DataAgentState,
    MetricInfoState,
    TableInfoState,
)
from app.entities.column_info import ColumnInfo
from app.entities.metric_info import MetricInfo
from app.entities.table_info import TableInfo
from app.entities.value_info import ValueInfo
from app.core.log import logger


async def merge_retrieved_info(
    state: DataAgentState, runtime: Runtime[DataAgentContext]
):
    """合并召回结果，输出 SQL 生成前的候选表信息和指标信息"""

    writer = runtime.stream_writer
    step = "合并召回信息"
    writer({"type": "progress", "step": step, "status": "running"})

    try:
        retrieved_column_infos = state["retrieved_column_infos"]
        retrieved_metric_infos = state["retrieved_metric_infos"]
        retrieved_value_infos = state["retrieved_value_infos"]
        meta_mysql_repository = runtime.context["meta_mysql_repository"]

        # 以 column_id 为 key 合并字段（三路可能命中同一字段，dict 天然去重）
        column_map: dict[str, ColumnInfo] = {c.id: c for c in retrieved_column_infos}

        # 补齐指标依赖字段：指标说“怎么算”，SQL 还需要真实字段
        for metric in retrieved_metric_infos:
            for column_id in metric.relevant_columns:
                if column_id not in column_map:
                    column_map[column_id] = (
                        await meta_mysql_repository.get_column_info_by_id(column_id)
                    )

        # 把召回到的真实取值回填进字段 examples（帮模型写对 where 条件）
        for value_info in retrieved_value_infos:
            column_id = value_info.column_id
            if column_id not in column_map:
                column_map[column_id] = (
                    await meta_mysql_repository.get_column_info_by_id(column_id)
                )
            if value_info.value not in column_map[column_id].examples:
                column_map[column_id].examples.append(value_info.value)

        # 按表归组字段（SQL 提示词按“表 → 字段列表”描述结构）
        table_to_columns: dict[str, list[ColumnInfo]] = {}
        for column_info in column_map.values():
            table_to_columns.setdefault(column_info.table_id, []).append(column_info)

        # ⑤ 补齐主外键：Join 路径全靠它，向量召回容易漏，主动兜底
        for table_id in table_to_columns:
            existing_ids = [c.id for c in table_to_columns[table_id]]
            key_columns = await meta_mysql_repository.get_key_columns_by_table_id(
                table_id
            )
            for key_column in key_columns:
                if key_column.id not in existing_ids:
                    table_to_columns[table_id].append(key_column)

        # ⑥ 生成表结构上下文（entity → 提示词友好的 State 结构）
        table_infos: list[TableInfoState] = []
        for table_id, column_infos in table_to_columns.items():
            table_info: TableInfo = await meta_mysql_repository.get_table_info_by_id(
                table_id
            )
            table_infos.append(
                TableInfoState(
                    name=table_info.name,
                    role=table_info.role,
                    description=table_info.description,
                    columns=[
                        ColumnInfoState(
                            name=c.name,
                            type=c.type,
                            role=c.role,
                            examples=c.examples,
                            description=c.description,
                            alias=c.alias,
                        )
                        for c in column_infos
                    ],
                )
            )

        # ⑦ 生成指标上下文（保留口径：名称/描述/别名/依赖字段）
        metric_infos: list[MetricInfoState] = [
            MetricInfoState(
                name=m.name,
                description=m.description,
                relevant_columns=m.relevant_columns,
                alias=m.alias,
            )
            for m in retrieved_metric_infos
        ]

        logger.info(f"合并后表：{[t['name'] for t in table_infos]}")
        logger.info(f"合并后指标：{[m['name'] for m in metric_infos]}")
        writer({"type": "progress", "step": step, "status": "success"})
        return {"table_infos": table_infos, "metric_infos": metric_infos}
    except Exception as e:
        logger.error(f"{step} 失败: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        raise
