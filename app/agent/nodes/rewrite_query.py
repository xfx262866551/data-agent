"""查询改写节点

多轮追问常是省略句（"那华南区呢"），直接抽词会丢掉上一轮的时间/指标条件。
本节点用最近几轮原始提问把本轮追问改写成一句独立可执行的问题。
"""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.prompt.prompt_loader import load_prompt

# 只带最近 3 轮原始提问：token 可控；更长的历史要走摘要策略
MAX_HISTORY_TURNS = 3


async def rewrite_query(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """把省略的追问改写成独立问题，并维护最近 N 轮原始提问"""

    step = "改写问题"
    writer = runtime.stream_writer
    writer({"type": "progress", "step": step, "status": "running"})

    try:
        history = state.get("query_history") or []
        raw_query = state["query"]

        prompt = PromptTemplate(
            template=load_prompt("rewrite_query"),
            input_variables=["history", "query"],
        )
        # 输出是一句话：StrOutputParser，不用 JSON
        chain = prompt | llm | StrOutputParser()

        rewritten = await chain.ainvoke(
            {
                "history": "\n".join(history) if history else "（无，这是本任务第一轮）",
                "query": raw_query,
            }
        )
        rewritten = rewritten.strip()

        logger.info(f"问题改写：{raw_query} -> {rewritten}")
        writer({"type": "progress", "step": step, "status": "success"})

        # 存用户原话（不是改写结果），且只留最近 3 轮
        return {
            "query": rewritten,
            "query_history": (history + [raw_query])[-MAX_HISTORY_TURNS:],
        }
    except Exception as e:
        logger.error(f"{step} 失败: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        raise