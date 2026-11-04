"""额外上下文补全节点

补齐不来自召回、但 SQL 生成必须知道的运行环境：当前日期和数据库方言/版本。
（date_info / db_info 两个占位符的填充处，供 SQL 生成节点使用）
"""

from datetime import date

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState, DateInfoState, DBInfoState
from app.core.log import logger


async def add_extra_context(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """补齐 SQL 生成所需的日期和数据库环境信息"""

    writer = runtime.stream_writer
    step = "添加额外上下文"
    writer({"type": "progress", "step": step, "status": "running"})

    try:
        dw_mysql_repository = runtime.context["dw_mysql_repository"]

        # 当前日期：帮模型处理“本月/本季度/最近 N 天”这类相对时间
        today = date.today()
        date_info = DateInfoState(
            date=today.strftime("%Y-%m-%d"),
            weekday=today.strftime("%A"),
            quarter=f"Q{(today.month - 1) // 3 + 1}",
        )

        # 数据库方言和版本：影响函数名、日期运算、limit 语法
        db = await dw_mysql_repository.get_db_info()
        db_info = DBInfoState(**db)

        logger.info(
            f"日期：{date_info['date']} {date_info['quarter']} | 数据库：{db_info['dialect']} {db_info['version']}"
        )
        writer({"type": "progress", "step": step, "status": "success"})
        return {"date_info": date_info, "db_info": db_info}
    except Exception as e:
        logger.error(f"{step} 失败: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        raise
