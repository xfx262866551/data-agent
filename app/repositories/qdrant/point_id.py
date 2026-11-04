import uuid


def to_point_id(business_id: str) -> str:
    """把业务 id 转成确定性 UUID"""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, business_id))
