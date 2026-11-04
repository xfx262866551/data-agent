"""评估脚本：跑 10 道题，比对期望数字，输出正确率。

数据文件：data/eval_set.json
运行：py -m app.scripts.run_eval
判分：结果里提取所有数值，期望数字全部出现（容差 0.01）即通过；
      无数据题要求结果为空或全 null。
"""

import asyncio
import json
import re
from decimal import Decimal
from pathlib import Path
import uuid
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
from langchain_openai.chat_models.base import OpenAIRateLimitError

EVAL_PATH = Path(__file__).parents[2] / "data" / "eval_set.json"


def extract_numbers(obj) -> list[float]:
    """递归提取结果里的所有数值（Decimal/int/float/数字字符串都算）"""
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


async def judge(item: dict, context: dict) -> dict:
    """跑一道题并判分"""
    rows = None
    async for chunk in graph.astream(
         DataAgentState(query=item["question"]),
        context=context,
        # 每题一条独立会话：不给 thread_id 会直接报错；共用一条会被上一题历史污染
        config={"configurable": {"thread_id": str(uuid.uuid4())}},
        stream_mode="custom",
    ):
        if chunk.get("type") == "result":
            rows = chunk["data"]

    if item.get("expect_empty"):
        ok = not rows or all(v is None for r in rows for v in r.values())
    else:
        got = extract_numbers(rows)
        ok = all(any(abs(n - e) < 0.01 for n in got) for e in item["expect_numbers"])
    return {"question": item["question"], "passed": ok, "rows": rows}


async def main():
    meta_mysql_client_manager.init()
    dw_mysql_client_manager.init()
    qdrant_client_manager.init()
    embedding_client_manager.init()
    es_client_manager.init()

    items = json.loads(EVAL_PATH.read_text(encoding="utf-8"))

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
        for item in items:
            r = None
            for attempt in range(3):
                try:
                    r = await judge(item, context)
                    break
                except OpenAIRateLimitError as e:
                    print(f"  第 {attempt + 1} 次被限流，等待后重试：{e}")
                    await asyncio.sleep(20)
                except Exception as e:
                    print(f"  不可重试的错误，跳过这题：{e}")
                    break
            if r is None:
                r = {"question": item["question"], "passed": False, "rows": None}
            results.append(r)
            print(("✅" if r["passed"] else "❌"), r["question"])
            await asyncio.sleep(2)

    passed = sum(1 for r in results if r["passed"])
    print(
        f"\n=== 总正确率：{passed}/{len(results)} = {passed / len(results) * 100:.0f}% ==="
    )

    await meta_mysql_client_manager.close()
    await dw_mysql_client_manager.close()
    await qdrant_client_manager.close()
    await es_client_manager.close()


asyncio.run(main())
