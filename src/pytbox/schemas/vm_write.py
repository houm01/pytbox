from pydantic import BaseModel, Field, field_validator
from typing import Any, Dict, Optional, Union
import math

Number = Union[int, float]

class VMWriteItem(BaseModel):
    labels: Dict[str, Any] = Field(default_factory=dict)
    value: Optional[Number] = None
    timestamp: Optional[int] = None  # ms

    @field_validator("timestamp")
    @classmethod
    def _ts_ms_valid(cls, v):
        if v is None:
            return v
        if v < 0:
            raise ValueError("timestamp(ms) 必须 >= 0")
        return v

    @field_validator("value")
    @classmethod
    def _value_valid(cls, v):
        if v is None:
            return v
        # 防 NaN/inf
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            raise ValueError("value 不能是 NaN/inf")
        return v
