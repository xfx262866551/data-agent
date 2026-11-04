"""数仓 MySQL 仓储

职责：到真实数仓补齐配置里没有的信息（字段真实类型、示例值），
以及 SQL 生成闭环里的环境读取、SQL 校验与最终执行。
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

def _quote_identifier(name: str) -> str:
    """对 MySQL 识别符进行引号处理"""
    if not name.replace("_", "").isalnum():
        return ValueError(f"非法标识符：{name!r}")
    return f"{name}"

class DWMySQLRepository:
    """数仓 MySQL 仓储"""
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_column_types(self, table_name: str) -> dict[str,str]:
         """查询整张表的字段类型，作为 ColumnInfo.type 的真实来源"""
         sql = f"show columns from {_quote_identifier(table_name)}"
         result = await self.session.execute(text(sql))
         rows = result.mappings().fetchall()
         return {row["Field"]: row["Type"] for row in rows}
     
    async def get_column_values(
        self, table_name: str, column_name: str, limit: int = 10
    ) -> list:
        """抽样查询字段示例值（distinct 去重），供元数据入库和检索复用"""
        sql = (
            f"select distinct {_quote_identifier(column_name)} "
            f"from {_quote_identifier(table_name)} limit {int(limit)}"
        )
        result = await self.session.execute(text(sql))
        return [row[0] for row in result.fetchall()]

    async def get_db_info(self) -> dict:
        """读取数库的方言和版本，供 SQL 生成提示词使用"""
        result = await self.session.execute(text("select version()"))
        version = result.scalar()
        # dialect 来自 SQLAlchemy 绑定的方言，例如 mysql
        dialect = self.session.bind.dialect.name
        return {"dialect": dialect, "version": version}

    async def validate(self, sql: str):
        """用 EXPLAIN 让数据库提前解析 SQL，发现语法/表名/字段名错误"""
        await self.session.execute(text(f"explain {sql}"))

    async def run(self, sql: str) -> list[dict]:
        """执行最终 SQL，并把行对象转成字典列表（前端易消费）"""
        result = await self.session.execute(text(sql))
        return [dict(row) for row in result.mappings().fetchall()]
