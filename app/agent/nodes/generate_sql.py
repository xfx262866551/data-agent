"""SQL 生成节点

根据用户问题和前置节点整理出的表结构/指标/日期/数据库环境生成候选 SQL。
只生成、不校验不执行——后续交给 validate_sql 和 run_sql。
"""

import yaml
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.prompt.prompt_loader import load_prompt


async def generate_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """基于已检索和过滤的上下文生成 SQL"""

    writer = runtime.stream_writer
    step = "生成SQL"
    writer({"type": "progress", "step": step, "status": "running"})

    try:
        # 五份上下文全部来自前置节点，本节点只负责组装 prompt
        prompt = PromptTemplate(
            template=load_prompt("generate_sql"),
            input_variables=[
                "table_infos",
                "metric_infos",
                "date_info",
                "db_info",
                "query",
            ],
        )
        # SQL 是纯文本：StrOutputParser，且 prompt 已禁止 Markdown 代码块
        chain = prompt | llm | StrOutputParser()

        result = await chain.ainvoke(
            {
                "table_infos": yaml.dump(
                    state["table_infos"], allow_unicode=True, sort_keys=False
                ),
                "metric_infos": yaml.dump(
                    state["metric_infos"], allow_unicode=True, sort_keys=False
                ),
                "date_info": yaml.dump(
                    state["date_info"], allow_unicode=True, sort_keys=False
                ),
                "db_info": yaml.dump(
                    state["db_info"], allow_unicode=True, sort_keys=False
                ),
                "query": state["query"],
            }
        )

        logger.info(f"生成的SQL：{result}")
        writer({"type": "progress", "step": step, "status": "success"})
        return {"sql": result}
    except Exception as e:
        logger.error(f"{step} 失败: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        raise
