from dataclasses import dataclass

@dataclass
class ValueInfo:
    """值信息"""
    id: str
    value: str
    column_id: str