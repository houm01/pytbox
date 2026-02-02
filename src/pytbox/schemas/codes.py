from enum import IntEnum



class RespCode(IntEnum):
    """
    RespCode 类。

    用于 Resp Code 相关能力的封装。
    """
    OK = 0
    
    # 3xxx: victoriametics
    VM_REQUEST_FAILED = 3001
    VM_QUERY_FAILED = 3002
    VM_BAD_PAYLOAD = 3003
    PING_UNHEALTHY = 3101
    
    # 4xxx: internal
    INTERNAL_ERROR = 4001
    
    # 5xxx: business non-error states
    NO_DATA = 5001

