"""
CLI 通用工具函数 - 集成 rich 支持
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any, Union

try:
    from rich.console import Console

    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import track
    from rich.syntax import Syntax
    from rich.tree import Tree
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# 如果 rich 不可用，使用标准输出
import click


class Logger:
    """增强的日志器，支持 rich 格式化输出"""
    
    def __init__(self, verbose: bool = False, quiet: bool = False):
        self.verbose = verbose
        self.quiet = quiet
        
        if RICH_AVAILABLE:
            self.console = Console()
        else:
            self.console = None
    
    def info(self, message: str, style: str = "info"):
        """信息日志"""
        if self.quiet:
            return
            
        if RICH_AVAILABLE:
            if style == "success":
                self.console.print(f"✅ {message}", style="bold green")
            elif style == "warning":
                self.console.print(f"⚠️  {message}", style="bold yellow")
            elif style == "error":
                self.console.print(f"❌ {message}", style="bold red")
            else:
                self.console.print(f"ℹ️  {message}", style="bold blue")
        else:
            click.echo(message)
    
    def success(self, message: str):
        """成功日志"""
        self.info(message, "success")
    
    def warning(self, message: str):
        """警告日志"""
        self.info(message, "warning")
    
    def error(self, message: str):
        """错误日志"""
        if RICH_AVAILABLE:
            self.console.print(f"❌ {message}", style="bold red", err=True)
        else:
            click.echo(f"错误: {message}", err=True)
    
    def debug(self, message: str):
        """调试日志"""
        if self.verbose:
            if RICH_AVAILABLE:
                self.console.print(f"🔍 {message}", style="dim")
            else:
                click.echo(f"DEBUG: {message}")
    
    def print_panel(self, content: str, title: str = "", style: str = "info"):
        """打印面板"""
        if self.quiet:
            return
            
        if RICH_AVAILABLE:
            if style == "success":
                panel_style = "green"
            elif style == "warning":
                panel_style = "yellow"
            elif style == "error":
                panel_style = "red"
            else:
                panel_style = "blue"
                
            panel = Panel(content, title=title, border_style=panel_style)
            self.console.print(panel)
        else:
            if title:
                click.echo(f"=== {title} ===")
            click.echo(content)
    
    def print_table(self, data: list, headers: list, title: str = ""):
        """打印表格"""
        if self.quiet:
            return
            
        if RICH_AVAILABLE:
            table = Table(title=title, show_header=True, header_style="bold magenta")
            
            for header in headers:
                table.add_column(header)
            
            for row in data:
                table.add_row(*[str(cell) for cell in row])
            
            self.console.print(table)
        else:
            if title:
                click.echo(f"=== {title} ===")
            click.echo("\t".join(headers))
            for row in data:
                click.echo("\t".join(str(cell) for cell in row))
    
    def print_syntax(self, code: str, language: str = "toml", title: str = ""):
        """打印语法高亮的代码"""
        if self.quiet:
            return
            
        if RICH_AVAILABLE:
            syntax = Syntax(code, language, theme="monokai", line_numbers=True)
            if title:
                panel = Panel(syntax, title=title, border_style="blue")
                self.console.print(panel)
            else:
                self.console.print(syntax)
        else:
            if title:
                click.echo(f"=== {title} ===")
            click.echo(code)


# 全局日志器实例
logger = Logger()


def set_logger_config(verbose: bool = False, quiet: bool = False):
    """设置日志器配置"""
    global logger
    logger = Logger(verbose=verbose, quiet=quiet)


def handle_error(error: Exception):
    """统一的错误处理"""
    logger.error(str(error))


def write_output(content: str, output_path: Optional[str] = None, content_type: str = "text"):
    """统一的输出处理"""
    if output_path:
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.success(f"内容已保存到: {output_path}")
            logger.debug(f"文件大小: {len(content)} 字符")
            
        except Exception as e:
            logger.error(f"保存文件失败: {e}")
            raise
    else:
        # 根据内容类型选择合适的显示方式
        if content_type == "json":
            logger.print_syntax(content, "json", "JSON 内容")
        elif content_type == "yaml":
            logger.print_syntax(content, "yaml", "YAML 内容")
        elif content_type == "toml":
            logger.print_syntax(content, "toml", "TOML 内容")
        elif content_type == "template":
            logger.print_syntax(content, "jinja2", "模板内容")
        else:
            logger.print_panel(content, "输出内容")


def load_template_vars(data_str: Optional[str] = None, data_file: Optional[str] = None) -> Dict[str, Any]:
    """加载模板变量"""
    template_vars = {}
    
    try:
        if data_file:
            logger.debug(f"从文件加载变量: {data_file}")
            with open(data_file, 'r', encoding='utf-8') as f:
                file_vars = json.load(f)
                template_vars.update(file_vars)
                logger.debug(f"从文件加载了 {len(file_vars)} 个变量")
        
        if data_str:
            logger.debug("从命令行加载变量")
            cli_vars = json.loads(data_str)
            template_vars.update(cli_vars)
            logger.debug(f"从命令行加载了 {len(cli_vars)} 个变量")
        
        if template_vars:
            logger.debug(f"总计加载变量: {list(template_vars.keys())}")
        
        return template_vars
        
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 格式错误: {e}")
    except FileNotFoundError as e:
        raise FileNotFoundError(f"数据文件不存在: {e}")
    except Exception as e:
        raise Exception(f"加载模板变量失败: {e}")


def show_progress(items, description: str = "处理中..."):
    """显示进度条"""
    if RICH_AVAILABLE and not logger.quiet:
        return track(items, description=description)
    else:
        return items


def create_tree_view(data: dict, title: str = "数据结构") -> None:
    """创建树形视图显示数据"""
    if logger.quiet:
        return
        
    if RICH_AVAILABLE:
        tree = Tree(title)
        
        def add_dict_to_tree(node, data_dict):
            for key, value in data_dict.items():
                if isinstance(value, dict):
                    child = node.add(f"[bold blue]{key}[/bold blue]")
                    add_dict_to_tree(child, value)
                elif isinstance(value, list):
                    child = node.add(f"[bold green]{key}[/bold green] ({len(value)} items)")
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            item_node = child.add(f"[dim]Item {i}[/dim]")
                            add_dict_to_tree(item_node, item)
                        else:
                            child.add(f"[dim]{item}[/dim]")
                else:
                    node.add(f"[yellow]{key}[/yellow]: [white]{value}[/white]")
        
        add_dict_to_tree(tree, data)
        logger.console.print(tree)
    else:
        # 简单的文本输出
        logger.info(f"=== {title} ===")
        
        def print_dict(data_dict, indent=0):
            for key, value in data_dict.items():
                prefix = "  " * indent
                if isinstance(value, dict):
                    click.echo(f"{prefix}{key}:")
                    print_dict(value, indent + 1)
                elif isinstance(value, list):
                    click.echo(f"{prefix}{key}: ({len(value)} items)")
                    for item in value:
                        if isinstance(item, dict):
                            print_dict(item, indent + 1)
                        else:
                            click.echo(f"{prefix}  - {item}")
                else:
                    click.echo(f"{prefix}{key}: {value}")
        
        print_dict(data)
