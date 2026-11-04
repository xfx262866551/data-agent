"""问数 Agent 图编排

用 LangGraph 把 12 个节点串成可观测的执行链路：
抽词 → 三路并行召回 → 合并 → 双线过滤 → 补上下文 → 生成 SQL → 校验 →（修正）→ 执行。
"""

from langgraph.constants import END, START
from langgraph.graph import StateGraph

from app.agent.context import DataAgentContext
from app.agent.nodes.add_extra_context import add_extra_context
from app.agent.nodes.correct_sql import correct_sql
from app.agent.nodes.extract_keywords import extract_keywords
from app.agent.nodes.filter_metric import filter_metric
from app.agent.nodes.filter_table import filter_table
from app.agent.nodes.generate_sql import generate_sql
from app.agent.nodes.merge_retrieved_info import merge_retrieved_info
from app.agent.nodes.recall_column import recall_column
from app.agent.nodes.recall_metric import recall_metric
from app.agent.nodes.recall_value import recall_value
from app.agent.nodes.run_sql import run_sql
from app.agent.nodes.validate_sql import validate_sql
from app.agent.state import DataAgentState
from langgraph.types import RetryPolicy
from langgraph.checkpoint.memory import InMemorySaver
from app.agent.nodes.rewrite_query import rewrite_query
# state_schema 管节点间数据，context_schema 管外部依赖（连接类对象走 context，不进 State）
graph_builder = StateGraph(state_schema=DataAgentState, context_schema=DataAgentContext)
NODE_RETRY = RetryPolicy(max_attempts=3, initial_interval=2)

graph_builder.add_node("rewrite_query", rewrite_query, retry_policy=NODE_RETRY)

# 注册 12 个节点
graph_builder.add_node("extract_keywords", extract_keywords, retry_policy=NODE_RETRY)
graph_builder.add_node("recall_column", recall_column, retry_policy=NODE_RETRY)
graph_builder.add_node("recall_value", recall_value, retry_policy=NODE_RETRY)
graph_builder.add_node("recall_metric", recall_metric, retry_policy=NODE_RETRY)
graph_builder.add_node("merge_retrieved_info", merge_retrieved_info, retry_policy=NODE_RETRY)
graph_builder.add_node("filter_table", filter_table, retry_policy=NODE_RETRY)
graph_builder.add_node("filter_metric", filter_metric, retry_policy=NODE_RETRY)
graph_builder.add_node("add_extra_context", add_extra_context, retry_policy=NODE_RETRY)
graph_builder.add_node("generate_sql", generate_sql, retry_policy=NODE_RETRY)
graph_builder.add_node("validate_sql", validate_sql, retry_policy=NODE_RETRY)
graph_builder.add_node("correct_sql", correct_sql, retry_policy=NODE_RETRY)
graph_builder.add_node("run_sql", run_sql, retry_policy=NODE_RETRY)

# 入口：先抽词
graph_builder.add_edge(START, "rewrite_query")
graph_builder.add_edge("rewrite_query", "extract_keywords")

# 扇出：三路召回并行（一个节点连多条边 = 并行）
graph_builder.add_edge("extract_keywords", "recall_column")
graph_builder.add_edge("extract_keywords", "recall_value")
graph_builder.add_edge("extract_keywords", "recall_metric")

# 扇入：三路都完成才合并
graph_builder.add_edge("recall_column", "merge_retrieved_info")
graph_builder.add_edge("recall_value", "merge_retrieved_info")
graph_builder.add_edge("recall_metric", "merge_retrieved_info")

# 双线过滤
graph_builder.add_edge("merge_retrieved_info", "filter_table")
graph_builder.add_edge("merge_retrieved_info", "filter_metric")

# 过滤完成 → 补上下文 → 生成 → 校验
graph_builder.add_edge("filter_table", "add_extra_context")
graph_builder.add_edge("filter_metric", "add_extra_context")
graph_builder.add_edge("add_extra_context", "generate_sql")
graph_builder.add_edge("generate_sql", "validate_sql")


# 条件边：校验通过直接执行，失败先修正再执行（自纠循环）
graph_builder.add_conditional_edges(
    source="validate_sql",
    path=lambda state: "run_sql" if state["error"] is None else "correct_sql",
    path_map={"run_sql": "run_sql", "correct_sql": "correct_sql"},
)
graph_builder.add_edge("correct_sql", "run_sql")
graph_builder.add_edge("run_sql", END)

# 编译后的 graph 是对外使用的 Agent 执行入口
graph = graph_builder.compile(checkpointer=InMemorySaver())