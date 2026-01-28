from pydantic import BaseModel, Field
from typing import Any, Optional
from .codes import RespCode


class ReturnResponse(BaseModel):
    '''
    _summary_

    Args:
        BaseModel (_type_): _description_

    Returns:
        _type_: _description_
    '''
    code: int = Field(..., description='业务状态码，0=成功，其它=失败或特殊状态')
    msg: str = Field(..., description='状态消息描述')
    data: Optional[Any] = Field(default=None, description='返回的数据')
    
    @classmethod
    def ok(cls, data: Any = None, msg: str = "OK"):
        return cls(code=int(RespCode.OK), msg=msg, data=data)
    
    @classmethod
    def fail(cls, code: RespCode, msg: str, data: Any = None):
        return cls(code=code, msg=msg, data=data)
    
    @classmethod
    def no_data(cls, msg: str = "No data", data: Any = None):
        return cls(code=int(RespCode.NO_DATA), msg=msg, data=data)