from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Dict, List, Optional, Union

NumberLike = Union[int, float, str]


class VMInstantSeries(BaseModel):
    labels: Dict[str, str]
    value: List[NumberLike] = Field(min_length=2, max_length=2)
    
    # 兼容原始返回: metric -> labels
    @model_validator(mode='before')
    @classmethod
    def _accept_metric_as_labels(cls, data):
        if isinstance(data, dict):
            if 'labels' not in data and 'metric' in data:
                data = dict(data)
                data['labels'] = data.pop('metric')
        return data
    
    @field_validator('value')
    @classmethod
    def _validate_value(cls, v):
        if len(v) != 2:
            raise ValueError('value must be a list of two elements')
        return v
    
    @property
    def ts(self) -> int:
        return int(float(self.value[0]))
    
    @property
    def v(self) -> float:
        """value 统一转 float（VM 经常给字符串）"""
        return float(self.value[1])
    
    def label(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return self.labels.get(key, default)


from .response import ReturnResponse

class VMInstantQueryResponse(ReturnResponse):
    data: List[VMInstantSeries] = Field(default_factory=list, description='instant query 的序列列表')
    
