from elasticsearch import AsyncElasticsearch
from typing import Optional
from app.conf.app_config import ESConfig,app_config



class ESClientManager:
    """管理 Elasticsearch 客户端的生命周期"""

    def __init__(self, es_config: ESConfig):
        self.es_config = es_config
        self.client: Optional[AsyncElasticsearch]  = None
        
    def _get_url(self):
        return f"http://{self.es_config.host}:{self.es_config.port}"
    
    def init(self):
        """显式初始化：建客户端（不发起任何网络请求）"""
        self.client = AsyncElasticsearch(hosts=[self._get_url()])
        
    async def close(self):
        """关闭客户端"""
        await self.client.close()
        
es_client_manager = ESClientManager(app_config.es)

if __name__ == "__main__":
    import asyncio
    
    async def main():
        es_client_manager.init()
        info = await es_client_manager.client.info()
        print("ES版本信息:", info["version"]["number"])
    
    asyncio.run(main())
       
