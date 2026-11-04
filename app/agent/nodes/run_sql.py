"""SQL 执行节点

执行最终 SQL 并产出结果。这是 SQL 闭环的结束节点，完成后流程进入 END。
"""

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.log import logger


async def run_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """执行 SQL 并产出最终问数结果"""

    writer = runtime.stream_writer
    step = "执行SQL"
    writer({"type": "progress", "step": step, "status": "running"})

    try:
        sql = state["sql"]
        dw_mysql_repository = runtime.context["dw_mysql_repository"]

        # 真实数据库访问封装在仓储层，节点只负责触发
        result = await dw_mysql_repository.run(sql)
        logger.info(f"SQL执行结果（前 3 行）：{result[:3]}")
        writer({"type": "progress", "step": step, "status": "success"})
        writer({"type": "result", "data": result})
    except Exception as e:
        logger.error(f"{step} 失败: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        raise