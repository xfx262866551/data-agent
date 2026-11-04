from openai import AsyncOpenAI

from app.conf.app_config import EmbeddingConfig, app_config
from langchain_openai import OpenAIEmbeddings



class EmbeddingClientManager:
    """管理 embedding 客户端的生命周期"""

    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self.client: OpenAIEmbeddings | None = None  # 类型注解同步换

    def init(self):
        """显式初始化：建客户端（不发起任何网络请求）"""
        self.client = OpenAIEmbeddings(
            model=self.config.model,
            base_url=self.config.base_url,
            api_key=self.config.api_key,
        )

    async def embed_texts(self, text: list[str]) -> list[list[float]]:
        """对文本进行嵌入"""
        return await self.client.aembed_documents(text)  # langchain 的异步批量接口


# 模块级单例：外部客户端全局一份，由 lifespan 负责 init/close
embedding_client_manager = EmbeddingClientManager(app_config.embedding)

if __name__ == "__main__":
    import asyncio

    async def main():
        embedding_client_manager.init()
        vectors = await embedding_client_manager.embed_texts(
            ["地区维度表，用于描述订单发生的地理区域信息。", "客户名称"]
        )
        print("几段文本：", len(vectors))
        print("每段多少维：", len(vectors[0]))

    asyncio.run(main())
