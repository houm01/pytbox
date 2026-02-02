

class Parse:
    
    """
    Parse 类。

    用于 Parse 相关能力的封装。
    """
    @staticmethod
    def remove_dict_none_value(data: dict) -> dict:
        """
        执行 remove dict none value 相关逻辑。

        Args:
            data: data 参数。

        Returns:
            Any: 返回值。
        """
        return {k: v for k, v in data.items() if v is not None}
    
