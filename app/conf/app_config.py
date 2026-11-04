from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from omegaconf import OmegaConf



@dataclass
class File:
    """文件日志配置"""

    enable: bool
    level: str
    path: str
    rotation: str
    retention: str


@dataclass
class Console:
    """控制台日志配置"""

    enable: bool
    level: str


@dataclass
class LoggingConfig:
    """日志总配置"""

    file: File
    console: Console


@dataclass
class DBConfig:
    """MySQL 连接配置（meta 和 dw 两个库共用一个类）"""

    host: str
    port: int
    user: str
    password: str
    database: str


@dataclass
class QdrantConfig:
    """Qdrant 连接与向量维度"""

    host: str
    port: int
    embedding_size: int


@dataclass
class EmbeddingConfig:
    """Embedding 服务配置（我们用 API，不是本地服务）"""

    model: str
    api_key: str
    base_url: str


@dataclass
class ESConfig:
    """Elasticsearch 配置"""

    host: str
    port: int
    index_name: str


@dataclass
class LLMConfig:
    """大模型调用配置"""

    model_name: str
    api_key: str
    base_url: str


@dataclass
class AppConfig:
    """项目级总配置入口"""

    logging: LoggingConfig
    db_meta: DBConfig
    db_dw: DBConfig
    qdrant: QdrantConfig
    embedding: EmbeddingConfig
    es: ESConfig
    llm: LLMConfig
    db_biz: DBConfig


# 从当前文件位置回到项目根目录，再定位 yaml
project_root = Path(__file__).parents[2]
config_file = project_root / "conf" / "app_config.yaml"

# 先读 .env，让 yaml 里的 ${oc.env:...} 能解析到敏感配置
load_dotenv(project_root / ".env")

context = OmegaConf.load(config_file)
schema = OmegaConf.structured(AppConfig)
app_config: AppConfig = OmegaConf.to_object(OmegaConf.merge(schema, context))

if __name__ == "__main__":
    print(app_config.es.host)
    print(app_config.db_meta.database, app_config.db_dw.database,
      app_config.qdrant.embedding_size, app_config.llm.model_name)
