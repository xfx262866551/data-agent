
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from app.conf.app_config import DBConfig, app_config

class MySQLClientManager:
    """管理 MySQL 客户端的初始化与关闭"""

    def __init__(self, config: DBConfig):
        self.engine: AsyncEngine | None = None
        self.session_factory = None
        self.config = config
    
    def _get_url(self) -> str:
        """拼接异步连接地址：mysql+asyncmy 表示用 asyncmy 作异步驱动"""
        return (f"mysql+asyncmy://{self.config.user}:{self.config.password}"
                f"@{self.config.host}:{self.config.port}/{self.config.database}"
                f"?charset=utf8mb4")
    
    def init(self):
         """初始化 Engine 和 Session 工厂"""
         self.engine  = create_async_engine(self._get_url(), pool_size=10, pool_pre_ping=True)
         self.session_factory = async_sessionmaker(self.engine, autoflush=True, expire_on_commit=False)
            
    async def close(self):
        """关闭数据库连接"""
        await self.engine.dispose()
        
# 元数据库与数仓分两个实例：知识库可重建，业务数据不可动
meta_mysql_client_manager = MySQLClientManager(app_config.db_meta)
dw_mysql_client_manager = MySQLClientManager(app_config.db_dw)
biz_mysql_client_manager = MySQLClientManager(app_config.db_biz)

if __name__ == "__main__":
    import asyncio
    dw_mysql_client_manager.init()
    
    async def main():
        async with dw_mysql_client_manager.session_factory() as session:
            sql = "select * from fact_order limit 10"
            result = await session.execute(text(sql))
            # mappings().fetchall() 把结果转成"按列名访问"的行对象
            rows = result.mappings().fetchall()
            
            print("行类型：", type(rows[0]).__name__)
            print("第一条 order_id：", rows[0]["order_id"])
            print("共查出：", len(rows), "行")
            
    asyncio.run(main())
