"""指标信息过滤节点

从合并后的候选指标里筛出当前问题真正需要的指标。
模型只返回“保留哪些指标名”（JSON 数组），裁剪由程序完成。
"""

import yaml
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState, MetricInfoState
from app.core.log import logger
from app.prompt.prompt_loader import load_prompt


async def filter_metric(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """根据用户问题裁剪候选指标上下文"""

    writer = runtime.stream_writer
    step = "过滤指标信息"
    writer({"type": "progress", "step": step, "status": "running"})

    try:
        query = state["query"]
        metric_infos: list[MetricInfoState] = state["metric_infos"]

        prompt = PromptTemplate(
            template=load_prompt("filter_metric_info"),
            input_variables=["query", "metric_infos"],
        )
        chain = prompt | llm | JsonOutputParser()

        result = await chain.ainvoke(
            {
                "query": query,
                "metric_infos": yaml.dump(
                    metric_infos, allow_unicode=True, sort_keys=False
                ),
            }
        )

        # 模型返回指标名数组，按名字过滤（保留完整上下文：描述/依赖字段/别名）
        filtered = [m for m in metric_infos if m["name"] in result]

        logger.info(f"过滤后保留指标：{[m['name'] for m in filtered]}")
        writer({"type": "progress", "step": step, "status": "success"})
        return {"metric_infos": filtered}
    except Exception as e:
        logger.error(f"{step} 失败: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        raise
