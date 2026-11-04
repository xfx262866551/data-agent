"""元数据知识库构建脚本入口

只负责接线：解析参数 → 初始化客户端 → 组装仓储和服务 → 触发构建 → 关闭连接。
真正的构建逻辑在 MetaKnowledgeService。
"""

import argparse
import asyncio
from pathlib import Path

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
from app.services.meta_knowledge_service import MetaKnowledgeService
from langchain_openai import OpenAIEmbeddings

async def build(config_path: Path):
    """初始化依赖并执行一次元数据知识构建"""

    # 五个客户端全部显式初始化（连接型资源，用前先 init）
    embedding_client_manager.init()
    es_client_manager.init()
    dw_mysql_client_manager.init()
    meta_mysql_client_manager.init()
    qdrant_client_manager.init()
    
    # 两个 MySQL session 用同一个 async with 管理（进出自动关）
    async with (
        dw_mysql_client_manager.session_factory() as dw_session,
        meta_mysql_client_manager.session_factory() as meta_session,
    ):
        # 仓储对象：每个 Repository 拿自己需要的 session/client
        dw_mysql_repository = DWMySQLRepository(dw_session)
        meta_mysql_repository = MetaMySQLRepository(meta_session)
        column_qdrant_repository = ColumnQdrantRepository(qdrant_client_manager.client)
        metric_qdrant_repository = MetricQdrantRepository(qdrant_client_manager.client)
        value_es_repository = ValueESRepository(es_client_manager.client)
        
        meta_knowledge_service = MetaKnowledgeService(
            meta_mysql_repository = meta_mysql_repository,
            dw_mysql_repository = dw_mysql_repository,
            column_qdrant_repository = column_qdrant_repository,
            metric_qdrant_repository = metric_qdrant_repository,
            value_es_repository = value_es_repository,
            embedding_client = embedding_client_manager.client,
        )
        # 正式进入构建
        await meta_knowledge_service.build(config_path)
        
    # 收尾：五个客户端全部关闭（连接池/连接释放）
    await es_client_manager.close()
    await dw_mysql_client_manager.close()
    await meta_mysql_client_manager.close()
    await qdrant_client_manager.close()
    
    
if __name__ == "__main__":
    # 配置路径由外部决定：-c/--conf 必填
    parser = argparse.ArgumentParser(description="元数据知识库构建脚本")
    parser.add_argument("-c", "--conf",  required=True, help="meta_config.yaml 路径")
    args = parser.parse_args()
    
    asyncio.run(build(args.conf))

    
    
