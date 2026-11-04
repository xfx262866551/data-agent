from dataclasses import dataclass

@dataclass
class MetricInfo:
    """指标信息"""
    id: str
    name: str
    description: str
    relevant_columns: list[str]
    alias: list[str]