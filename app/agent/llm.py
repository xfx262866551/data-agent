"""问数 Agent 使用的大模型实例

集中初始化一个 OpenAI 兼容的 Chat Model 供所有节点复用；换模型只改这一处。
"""

from langchain.chat_models import init_chat_model

from app.conf.app_config import app_config

llm = init_chat_model(
    model=app_config.llm.model_name,
    # 硅基流动等服务兼容 OpenAI 协议，用 openai provider 接入
    model_provider="openai",
    base_url=app_config.llm.base_url,
    api_key=app_config.llm.api_key,
    # 字段扩展和 SQL 生成看重稳定性，关闭随机发散
    temperature=0,
    request_timeout=60,
    max_retries=5,
)

if __name__ == "__main__":
    import asyncio

    async def main():
        # langchain 的异步调用是 ainvoke，返回 AIMessage，文本在 .content
        resp = await llm.ainvoke("用一句话介绍你自己")
        print(resp.content)

    asyncio.run(main())