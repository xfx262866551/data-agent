"""问数查询服务

把自然语言问题转换成一次 LangGraph 工作流执行：
创建初始 State、组装 Context、消费 astream 的流式输出，包装成 SSE 文本。
"""

import json

from app.agent.graph import graph
from app.agent.state import DataAgentState
from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository
from app.clients.mysql_client_manager import biz_mysql_client_manager

class QueryService:
    """封装一次问数查询所需的业务编排逻辑"""

    def __init__(
        self,
        meta_mysql_repository: MetaMySQLRepository,
        embedding_client,
        dw_mysql_repository: DWMySQLRepository,
        column_qdrant_repository: ColumnQdrantRepository,
        metric_qdrant_repository: MetricQdrantRepository,
        value_es_repository: ValueESRepository,
    ):
        self.meta_mysql_repository = meta_mysql_repository
        self.dw_mysql_repository = dw_mysql_repository
        self.embedding_client = embedding_client
        self.column_qdrant_repository = column_qdrant_repository
        self.metric_qdrant_repository = metric_qdrant_repository
        self.value_es_repository = value_es_repository

    async def query(self, query: str,thread_id: str):
        """执行一次问数工作流，逐段产出 SSE 消息（异步生成器）"""

        # State 只放业务数据；连接类对象走 context
        state = DataAgentState(query=query)
        # Context 放外部依赖，节点通过 runtime.context 读取
        context = {
            "column_qdrant_repository": self.column_qdrant_repository,
            "embedding_client": self.embedding_client,
            "metric_qdrant_repository": self.metric_qdrant_repository,
            "value_es_repository": self.value_es_repository,
            "meta_mysql_repository": self.meta_mysql_repository,
            "dw_mysql_repository": self.dw_mysql_repository,
        }

        try:
            # stream_mode="custom"：只流节点 writer(...) 写的进度消息
            async for chunk in graph.astream(
                input=state, 
                context=context,
                config={"configurable": {"thread_id": thread_id}}, 
                stream_mode="custom"
            ):
                # SSE 格式：data: 开头、两个换行结尾
                # ensure_ascii=False 保留中文；default=str 兜底日期等非 JSON 类型
                yield f"data: {json.dumps(chunk, ensure_ascii=False, default=str)}\n\n"
        except Exception as e:
            # 流已开始就不能改 HTTP 状态码，把异常也包装成一条 SSE 消息
            error = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error, ensure_ascii=False, default=str)}\n\n"
        finally:
            # 每轮结束后更新任务的预览信息和轮数，失败不影响问答本身
            try:
                async with biz_mysql_client_manager.session_factory() as s:
                    from app.repositories.mysql.biz.task_mysql_repository import (
                        TaskMySQLRepository,
                    )
                    await TaskMySQLRepository(s).touch(thread_id, query)
            except Exception:
                pass   # 任务统计失败不该影响问答本身
