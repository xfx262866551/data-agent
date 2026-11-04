"""表信息过滤节点

在合并后的候选表里筛出当前问题真正需要的表和字段。
模型只返回“保留哪些”，真正的裁剪由程序完成。
"""

import yaml
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState, TableInfoState
from app.core.log import logger
from app.prompt.prompt_loader import load_prompt


async def filter_table(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """根据用户问题裁剪候选表结构上下文"""

    writer = runtime.stream_writer
    step = "过滤表信息"
    writer({"type": "progress", "step": step, "status": "running"})

    try:
        query = state["query"]
        table_infos: list[TableInfoState] = state["table_infos"]

        # 嵌套结构转 YAML 进提示词：比 JSON 紧凑、中文可读
        prompt = PromptTemplate(
            template=load_prompt("filter_table_info"),
            input_variables=["query", "table_infos"],
        )
        chain = prompt | llm | JsonOutputParser()

        result = await chain.ainvoke(
            {
                "query": query,
                "table_infos": yaml.dump(table_infos, allow_unicode=True, sort_keys=False),
            }
        )

        # 模型只做选择（{表名: [字段名]}），程序按选择从原始结构裁剪
        filtered: list[TableInfoState] = []
        for table_info in table_infos:
            if table_info["name"] in result:
                table_info["columns"] = [
                    c for c in table_info["columns"] if c["name"] in result[table_info["name"]]
                ]
                filtered.append(table_info)

        logger.info(f"过滤后保留表：{[t['name'] for t in filtered]}")
        writer({"type": "progress", "step": step, "status": "success"})
        return {"table_infos": filtered}
    except Exception as e:
        logger.error(f"{step} 失败: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        raise