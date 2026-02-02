from dataclasses import dataclass
from typing import Optional


@dataclass
class EcsInstance:
    """
    EcsInstance 类。

    用于 Ecs Instance 相关能力的封装。
    """
    instance_id: str
    name: str
    status: str
    private_ip: Optional[str] = None
    public_ip: Optional[str] = None
    zone_id: Optional[str] = None
    vpc_id: Optional[str] = None


@dataclass
class MetricPoint:
    """
    MetricPoint 类。

    用于 Metric Point 相关能力的封装。
    """
    ts: int  # unix seconds
    value: float
