
from dataclasses import dataclass
from typing import Any

@dataclass
class ColumnInfo:
    """列信息"""
    id: str
    name: str
    type: str
    role: str
    examples: list[Any]
    description: str
    alias: list[str]
    table_id: str
