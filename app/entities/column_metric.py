

from dataclasses import dataclass

@dataclass
class ColumnMetric:
    """字段，指标之间关联"""
    column_id: str
    metric_id: str
    
