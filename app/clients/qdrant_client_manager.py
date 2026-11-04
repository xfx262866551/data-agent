from qdrant_client import AsyncQdrantClient,models
from typing import Optional
from app.conf.app_config import QdrantConfig,app_config


class QdrantClientManager:
    """管理 Qdrant 客户端的初始化与关闭"""

    def __init__(self, qdrant_config: QdrantConfig):
        self.qdrant_config = qdrant_config
        self.client: Optional[AsyncQdrantClient] = None

    def _get_url(self) -> str:
        """拼接 Qdrant 服务地址"""
        return f"http://{self.qdrant_config.host}:{self.qdrant_config.port}"

    def init(self):
        """显式初始化 Qdrant 客户端"""
        self.client = AsyncQdrantClient(url=self._get_url())

    async def close(self):
        """关闭 Qdrant 客户端连接"""
        await self.client.close()


qdrant_client_manager = QdrantClientManager(app_config.qdrant)

if __name__ == "__main__":
    import asyncio

    async def main():
        qdrant_client_manager.init()
        client  =  qdrant_client_manager.client

         # 建集合（不存在才建）：向量维度 10（测试用）、余弦相似度
        if not await client.collection_exists("my_collection"):
            await client.create_collection(
                collection_name ="my_collection",
                vectors_config=models.VectorParams(size = 10,distance=models.Distance.COSINE),
            )

        # 写 10 条固定向量（自测数据用确定性值，不用随机）
        await client.upsert(
            collection_name="my_collection",
            points=[
                models.PointStruct(id=i, vector=[0.1 * (i + 1)] * 10)
                for i in range(10)
            ],
        )

        # 相似度检索：最多 3 条，且相似度不低于 0.8
        res = await client.query_points(
            collection_name="my_collection",
            query = [0.1] * 10,
            limit=3,
            score_threshold=0.8,
        )
        print(f"检索结果: {len(res.points)}条")

    asyncio.run(main())
        