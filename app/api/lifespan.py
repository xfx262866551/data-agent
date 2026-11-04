"""FastAPI 应用生命周期管理

服务启动时初始化外部客户端，关闭时释放连接。
这些是应用级资源：创建一次、全程复用，而不是每个请求重复初始化。
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.mysql_client_manager import (
    dw_mysql_client_manager,
    meta_mysql_client_manager,
    biz_mysql_client_manager,
)
from app.clients.qdrant_client_manager import qdrant_client_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：外部客户端初始化一次，全程复用
    qdrant_client_manager.init()
    embedding_client_manager.init()
    es_client_manager.init()
    meta_mysql_client_manager.init()
    dw_mysql_client_manager.init()
    biz_mysql_client_manager.init() 

    yield  # 中间是服务运行期

    # 关闭：统一释放连接
    await qdrant_client_manager.close()
    await es_client_manager.close()
    await meta_mysql_client_manager.close()
    await dw_mysql_client_manager.close()
    await biz_mysql_client_manager.close() 