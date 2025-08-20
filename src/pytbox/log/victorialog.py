
 
from typing import Literal
import requests
import time
from ..utils.response import ReturnResponse
from ..utils.timeutils import TimeUtils



class Victorialog:
    '''
    _summary_
    '''
    def __init__(self, url: str=None, timeout: int=3):
        self.url = url
        self.timeout = timeout

    def send_program_log(self, 
             stream: str='inbox',
             date: str = None,
             level: Literal['INFO', 'DEBUG', 'WARNING', 'ERROR', 'CRITICAL', 'SUCCESS'] = 'INFO',
             message: str = "test",
             app_name: str = "test",
             file_name: str = None,
             line_number: int = None,
             function_name: str = None
        ) -> ReturnResponse:
        
        # 如果没有提供timestamp，自动生成ISO 8601格式的UTC时间
        if date is None:
            date = TimeUtils.get_utc_time()
        
        if not isinstance(message, str):
            try:
                message = str(message)
            except Exception:
                message = "message 无法转换为字符串"
        
        r = requests.post(
            url=self.url + '/insert/jsonline?_stream_fields=stream&_time_field=date&_msg_field=log.message',
            headers={'Content-Type': 'application/stream+json'},
            json={
                "log": {
                    "level": level, 
                    "message": message,
                    "app": app_name,
                    "file": file_name,
                    "line": line_number,
                    "function": function_name
                },
                "date": date, 
                "stream": stream
            },
            timeout=self.timeout
        )
        if r.status_code == 200:
            return ReturnResponse(code=0, msg=f"{message} 发送成功", data=r.text)
        else:
            return ReturnResponse(code=1, msg=f"{message} 发送失败")
    
    def send_syslog(self, stream, hostname, ip, level, message, date):

        # 如果没有提供timestamp，自动生成ISO 8601格式的UTC时间
        if date is None:
            date = TimeUtils.get_utc_time()
        
        r = requests.post(
            url=self.url,
            headers={'Content-Type': 'application/stream+json'},
            json={
                "log": {
                    "hostname": hostname,
                    "ip": ip,
                    "level": level, 
                    "message": message,
                },
                "date": date, 
                "stream": stream
            },
            timeout=self.timeout
        )
        if r.status_code == 200:
            return ReturnResponse(code=0, msg=f"{message} 发送成功", data=r.text)
        else:
            return ReturnResponse(code=1, msg=f"{message} 发送失败")

    def query(self, query: str=None, delay: int=0) -> ReturnResponse:
        """
        查询日志数据
        
        Args:
            query: 查询语句
            limit: 限制返回结果数量
            **kwargs: 其他表单参数，如 start_time, end_time 等
            
        Returns:
            dict: 响应数据
        """
        
        # 构建查询URL
        query_url = f"{self.url}/select/logsql/query"
        
        # 构建表单数据
        form_data = {'query': query}
        if delay > 0:
            time.sleep(delay)
        # 发送POST请求，data参数传递多个表单数据
        response = requests.post(
            url=query_url,
            # headers={'Content-Type': 'application/stream+json'},
            data=form_data,  # 使用data参数传递多个表单数据
            timeout=self.timeout
        )
        if response.status_code == 200:
            if len(response.text) > 0:
                return ReturnResponse(code=0, message=f"{form_data} 查询成功", data=response.text)
            else:
                return ReturnResponse(code=2, message=f"{form_data} 查询成功, 但没有数据")
        else:
            return ReturnResponse(code=1, message=f"{form_data} 查询失败")

if __name__ == "__main__":
    victorialog = Victorialog()
    pass