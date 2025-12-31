

class Parse:
    
    @staticmethod
    def remove_dict_none_value(data: dict) -> dict:
        return {k: v for k, v in data.items() if v is not None}
    
