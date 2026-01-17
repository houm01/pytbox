from dataclasses import dataclass
from typing import Optional


@dataclass
class EcsInstance:
    instance_id: str
    name: str
    status: str
    private_ip: Optional[str] = None
    public_ip: Optional[str] = None
    zone_id: Optional[str] = None
    vpc_id: Optional[str] = None


@dataclass
class MetricPoint:
    ts: int  # unix seconds
    value: float
