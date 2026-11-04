"""字段取值 ES 仓储

把字段真实取值组织成全文索引，提供索引创建、批量写入和关键词检索。
Service 层决定哪些字段需要同步；Repository 只关心索引存在、写入与召回。
"""
from dataclasses import asdict
from elasticsearch import AsyncElasticsearch
from app.entities.value_info import ValueInfo


class ValueESRepository:
    """负责字段取值全文索引的创建、写入和检索"""
    index_name = "value_index"
    # value 用 IK 分词，地区/会员等级/品类等中文值才能按全文检索
    index_mappings = {
        "dynamic":False,
        "properties":{
            "id":{"type":"keyword"},
            "value":{
                "type":"text",
                "analyzer":"ik_max_word",
                "search_analyzer":"ik_max_word"
            },
            "column_id":{"type":"keyword"},
        },
    }
    
    def __init__(self, client: AsyncElasticsearch):
        self.client = client
        
    async def ensure_index(self):
        """确保索引已创建（不存在才建）"""
        if not await self.client.indices.exists(index=self.index_name):
            await self.client.indices.create(
                index=self.index_name, mappings=self.index_mappings
            )
    
    async def index(self, value_infos: list[ValueInfo], batch_size: int = 20):
        """分批 bulk 写入字段取值"""
        if not value_infos:
            return

        for i in range(0, len(value_infos), batch_size):
            batch = value_infos[i : i + batch_size]
            operations = []
            for value_info in batch:
                # 用业务 id 当文档 id：重复构建时覆盖同一条（幂等）
                operations.append(
                    {"index": {"_index": self.index_name, "_id": value_info.id}}
                )
                operations.append(asdict(value_info))
            await self.client.bulk(operations=operations)
        await self.client.indices.refresh(index=self.index_name)
    
    async def search(
        self, keyword: str, score_threshold: float = 0.6, limit: int = 20
    ) -> list[ValueInfo]:
        """按关键词全文检索字段取值，还原为 ValueInfo"""
        resp = await self.client.search(
            index=self.index_name,
            query={"match": {"value": keyword}},
            size=limit,
            min_score=score_threshold,   # 过滤相关度过低的命中
        )
        return [ValueInfo(**hit["_source"]) for hit in resp["hits"]["hits"]]