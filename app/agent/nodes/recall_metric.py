"""指标召回节点

关键词扩展（LLM）→ 逐词向量化 → Qdrant 相似度检索 → 按指标 id 去重。
解决“用户问题可能对应哪些业务指标”。
"""
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.entities.metric_info import MetricInfo
from app.prompt.prompt_loader import load_prompt



async def recall_metric(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """召回和用户问题语义相关的字段元数据"""

    writer = runtime.stream_writer
    step = "召回字段信息"
    writer({"type": "progress", "step": step, "status": "running"})

    try:
        keywords = state["keywords"]
        query = state["query"]
        # 连接类对象从 context 取，不放 State（避免进 checkpoint 反复序列化）
        metric_qdrant_repository = runtime.context["metric_qdrant_repository"]
        embedding_client = runtime.context["embedding_client"]

        # LLM 把用户问法扩展成字段语义列表，弥补用户说法与字段名不一致
        prompt = PromptTemplate(
            template=load_prompt("extend_keywords_for_metric_recall"),
            input_variables=["query"],
        )
        chain = prompt | llm | JsonOutputParser()
        extended = await chain.ainvoke({"query": query})

        # 原始关键词 + 扩展词一起参与召回；set 去重避免同一词查两遍
        keywords = set(keywords + extended)

        # 逐词检索 + 按 id 去重
        metric_info_map: dict[str, MetricInfo] = {}
        for keyword in keywords:
            embedding = await embedding_client.aembed_query(keyword)
            current = await metric_qdrant_repository.search(embedding)
            for metric_info in current:
                if metric_info.id not in metric_info_map:
                    metric_info_map[metric_info.id] = metric_info

        retrieved = list(metric_info_map.values())

        writer({"type": "progress", "step": step, "status": "success"})
        logger.info(f"召回字段 {len(retrieved)} 个", list(metric_info_map.keys()))
        return {"retrieved_metric_infos": retrieved}
    except Exception as e:
        logger.error(f"{step} 失败: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        raise