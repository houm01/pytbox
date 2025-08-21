"""
输出格式化器 - 支持多种格式和 rich 美化
"""

import json
from typing import Any, Dict, Union
from ..common.utils import logger


class OutputFormatter:
    """输出格式化器"""
    
    @staticmethod
    def format_data(data: Union[Dict[str, Any], list], format_type: str = 'toml') -> str:
        """格式化数据
        
        Args:
            data: 要格式化的数据
            format_type: 输出格式 ('toml', 'json', 'yaml')
            
        Returns:
            str: 格式化后的字符串
            
        Raises:
            ImportError: 缺少必要的依赖
            ValueError: 不支持的格式
        """
        logger.debug(f"格式化数据为 {format_type} 格式")
        
        if format_type == 'json':
            return OutputFormatter._format_json(data)
        elif format_type == 'yaml':
            return OutputFormatter._format_yaml(data)
        elif format_type == 'toml':
            return OutputFormatter._format_toml(data)
        else:
            raise ValueError(f"不支持的格式: {format_type}")
    
    @staticmethod
    def _format_json(data: Any) -> str:
        """格式化为 JSON"""
        try:
            result = json.dumps(data, indent=2, ensure_ascii=False)
            logger.debug(f"JSON 格式化完成，长度: {len(result)} 字符")
            return result
        except Exception as e:
            logger.error(f"JSON 格式化失败: {e}")
            raise
    
    @staticmethod
    def _format_yaml(data: Any) -> str:
        """格式化为 YAML"""
        try:
            import yaml
            result = yaml.dump(
                data, 
                default_flow_style=False, 
                allow_unicode=True,
                sort_keys=False,
                indent=2
            )
            logger.debug(f"YAML 格式化完成，长度: {len(result)} 字符")
            return result
        except ImportError:
            error_msg = "需要安装 pyyaml: pip install pyyaml"
            logger.error(error_msg)
            raise ImportError(error_msg)
        except Exception as e:
            logger.error(f"YAML 格式化失败: {e}")
            raise
    
    @staticmethod
    def _format_toml(data: Any) -> str:
        """格式化为 TOML"""
        try:
            import toml
            result = toml.dumps(data)
            logger.debug(f"TOML 格式化完成，长度: {len(result)} 字符")
            return result
        except ImportError:
            try:
                # Python 3.11+ 的 tomllib 只能读取，不能写入
                import tomllib
                error_msg = "需要安装 toml 库来支持 TOML 输出: pip install toml"
                logger.error(error_msg)
                raise ImportError(error_msg)
            except ImportError:
                error_msg = "需要安装 toml: pip install toml"
                logger.error(error_msg)
                raise ImportError(error_msg)
        except Exception as e:
            logger.error(f"TOML 格式化失败: {e}")
            raise
    
    @staticmethod
    def format_template_list(templates: list) -> str:
        """格式化模板列表"""
        if not templates:
            return "未找到模板文件"
        
        logger.debug(f"格式化 {len(templates)} 个模板")
        
        # 按文件类型分组
        groups = {}
        for template in templates:
            if '.' in template:
                ext = template.split('.')[-1]
                if ext not in groups:
                    groups[ext] = []
                groups[ext].append(template)
            else:
                if 'other' not in groups:
                    groups['other'] = []
                groups['other'].append(template)
        
        result = []
        result.append("可用模板:")
        
        for ext, files in sorted(groups.items()):
            result.append(f"\n{ext.upper()} 模板:")
            for template in sorted(files):
                result.append(f"  - {template}")
        
        return "\n".join(result)
    
    @staticmethod
    def format_config_summary(config: Dict[str, Any]) -> str:
        """格式化配置摘要"""
        logger.debug("生成配置摘要")
        
        result = []
        result.append("配置摘要:")
        
        for service, service_config in config.items():
            result.append(f"\n📊 {service.upper()} 服务:")
            
            if isinstance(service_config, dict):
                for key, value in service_config.items():
                    if isinstance(value, list):
                        result.append(f"  {key}: {len(value)} 项")
                        # 显示前几个项目
                        for i, item in enumerate(value[:3]):
                            if isinstance(item, dict):
                                item_keys = list(item.keys())[:2]  # 只显示前两个键
                                result.append(f"    - 项目 {i+1}: {item_keys}")
                            else:
                                result.append(f"    - {item}")
                        if len(value) > 3:
                            result.append(f"    ... 还有 {len(value) - 3} 项")
                    else:
                        result.append(f"  {key}: {value}")
            else:
                result.append(f"  值: {service_config}")
        
        return "\n".join(result)
