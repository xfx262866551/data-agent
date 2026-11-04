"""多轮评估脚本：同一任务里连问两轮，判第 2 轮有没有继承第 1 轮的条件。

数据文件：data/eval_set_multi_turn.json
运行：py -m app.scripts.run_multi_turn_eval
判分：只提取第 2 轮结果里的数值；期望数字全部出现（容差 0.01）即通过。
"""

import asyncio
import json
import re
import uuid
from decimal import Decimal
from pathlib import Path

from langchain_openai.chat_models.base import OpenAIRateLimitError

from app.agent.graph import graph
from app.agent.state import DataAgentState
from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.mysql_client_manager import (
    dw_mysql_client_manager,
    meta_mysql_client_manager,
)
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository

EVAL_PATH = Path(__file__).parents[2] / "data" / "eval_set_multi_turn.json"


def extract_numbers(obj) -> list[float]:
    """递归提取结果里的所有数值（Decimal/int/float/数字字符串统一转 float）"""
    nums: list[float] = []

    def walk(x):
        if isinstance(x, bool):
            return
        if isinstance(x, Decimal):
            nums.append(float(x))
        elif isinstance(x, (int, float)):
            nums.append(float(x))
        elif isinstance(x, str):
            nums.extend(float(m) for m in re.findall(r"-?\d+(?:\.\d+)?", x))
        elif isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, (list, tuple)):
            for v in x:
                walk(v)

    walk(obj)
    return nums


async def run_turn(query: str, thread_id: str, context: dict):
    """跑一轮，返回该轮的 result 数据行"""
    rows = None
    async for chunk in graph.astream(
        DataAgentState(query=query),
        context=context,
        config={"configurable": {"thread_id": thread_id}},
        stream_mode="custom",
    ):
        if chunk.get("type") == "result":
            rows = chunk["data"]
    return rows


async def judge_case(case: dict, context: dict) -> dict:
    """一个用例 = 一条独立会话 + 连问两轮，只判第 2 轮"""
    thread_id = str(uuid.uuid4())  # 每个用例独立，避免用例之间串历史
    rows1 = await run_turn(case["turn1"], thread_id, context)
    rows2 = await run_turn(case["turn2"], thread_id, context)

    got = extract_numbers(rows2)
    ok = all(any(abs(n - e) < 0.01 for n in got) for e in case["expect_numbers"])
    return {
        "turn2": case["turn2"],
        "passed": ok,
        "rows2": rows2,
        "turn1_row_count": len(rows1 or []),
    }


async def main():
    meta_mysql_client_manager.init()
    dw_mysql_client_manager.init()
    qdrant_client_manager.init()
    embedding_client_manager.init()
    es_client_manager.init()

    cases = json.loads(EVAL_PATH.read_text(encoding="utf-8"))

    async with (
        meta_mysql_client_manager.session_factory() as meta_session,
        dw_mysql_client_manager.session_factory() as dw_session,
    ):
        context = {
            "column_qdrant_repository": ColumnQdrantRepository(
                qdrant_client_manager.client
            ),
            "metric_qdrant_repository": MetricQdrantRepository(
                qdrant_client_manager.client
            ),
            "value_es_repository": ValueESRepository(es_client_manager.client),
            "embedding_client": embedding_client_manager.client,
            "meta_mysql_repository": MetaMySQLRepository(meta_session),
            "dw_mysql_repository": DWMySQLRepository(dw_session),
        }
        await asyncio.sleep(10)
        results = []
        for case in cases:
            r = None
            for attempt in range(3):
                try:
                    r = await judge_case(case, context)
                    break
                except OpenAIRateLimitError as e:  # 只有限流才重试
                    print(f"  第 {attempt + 1} 次被限流，等待后重试：{e}")
                    await asyncio.sleep(20)
                except Exception as e:  # 其它错误不重试
                    print(f"  不可重试的错误，跳过这例：{e}")
                    break
            if r is None:
                r = {
                    "turn2": case["turn2"],
                    "passed": False,
                    "rows2": None,
                    "turn1_row_count": 0,
                }
            results.append(r)
            print(("✅" if r["passed"] else "❌"), f'{case["turn2"]} -> {r["rows2"]}')
            await asyncio.sleep(2)

    passed = sum(1 for r in results if r["passed"])
    print(
        f"\n=== 多轮正确率：{passed}/{len(results)} = {passed / len(results) * 100:.0f}% ==="
    )

    await meta_mysql_client_manager.close()
    await dw_mysql_client_manager.close()
    await qdrant_client_manager.close()
    await es_client_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
