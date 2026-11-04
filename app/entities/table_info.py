from dataclasses import dataclass

@dataclass
class TableInfo:
    """表信息"""
    id: str
    name: str
    role: str
    description: str
    