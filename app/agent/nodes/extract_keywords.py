"""关键词抽取节点

从用户自然语言问题中识别检索线索；后续三路召回都基于这些关键词展开。
用 jieba 而不是 LLM：机械切词零成本、确定性、毫秒级。
"""

import jieba.analyse
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.log import logger


async def extract_keywords(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """抽取用户问题中的关键词，并通过流式输出反馈进度"""

    step = "抽取关键词"
    writer = runtime.stream_writer
    writer({"type": "progress", "step": step, "status": "running"})

    try:
        query = state["query"]

        # 只保留可能承载业务含义的词性（名词/地名/机构/动词/英文等），滤掉“的、帮我、一下”这类噪声
        allow_pos = ("n", "nr", "ns", "nt", "nz", "v", "vn", "a", "an", "eng", "i", "l")

        # TF-IDF 抽词 + 词性过滤
        keywords = jieba.analyse.extract_tags(query, allowPOS=allow_pos)

        # 原始问题兜底进关键词：切分不准时不丢完整语义；set 去重
        keywords = list(set(keywords + [query]))

        writer({"type": "progress", "step": step, "status": "success"})
        logger.info(f"抽取关键词成功: {keywords}")
        return {"keywords": keywords}
    except Exception as e:
        logger.error(f"抽取关键词失败: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        raise
