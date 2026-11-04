"""SQL 校验节点

执行前用 EXPLAIN 让数据库解析一次生成的 SQL。
校验结果不决定流程走向，而是通过 state["error"] 交给图的条件边判断。
"""

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.log import logger


async def validate_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """校验 SQL，返回 error 字段控制后续条件分支"""

    writer = runtime.stream_writer
    step = "校验SQL"
    writer({"type": "progress", "step": step, "status": "running"})

    try:
        sql = state["sql"]
        dw_mysql_repository = runtime.context["dw_mysql_repository"]

        try:
            # validate 内部是 explain ：只关心数据库能否成功解析
            await dw_mysql_repository.validate(sql)
            logger.info("SQL语法正确")
            return {"error": None}
        except Exception as e:
            # 关键：不抛异常中断图，把错误写进 state，让条件边走 correct_sql
            logger.warning(f"SQL语法错误：{e}")
            return {"error": str(e)}
    except Exception as e:
        logger.error(f"{step} 失败: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        raise
