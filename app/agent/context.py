"""问数 Agent 运行上下文

Context 保存一次图执行中不参与状态合并的外部依赖；
节点通过 runtime.context 复用工具，不需要把连接类对象塞进 State。
"""

from typing import TypedDict

from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository


class DataAgentContext(TypedDict):
    """LangGraph Runtime 中传递的上下文对象"""

    # 字段向量仓储：按向量从 Qdrant 检索候选字段
    column_qdrant_repository: ColumnQdrantRepository
    # Embedding 客户端：把关键词变成 query vector
    embedding_client: object  # OpenAIEmbeddings 实例，由 lifespan 创建后注入
    # 指标向量仓储：按向量检索候选指标
    metric_qdrant_repository: MetricQdrantRepository
    # 字段取值全文检索仓储：从 ES 检索真实字段值
    value_es_repository: ValueESRepository
    # 元数据仓储：召回合并时按 id 补齐结构信息
    meta_mysql_repository: MetaMySQLRepository
    # 数仓仓储：补全阶段读数据库方言和版本
    dw_mysql_repository: DWMySQLRepository
