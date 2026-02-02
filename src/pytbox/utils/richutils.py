#!/usr/bin/env python3


from typing import Literal
from rich.console import Console
from rich.theme import Theme
from rich.prompt import Prompt
from rich.logging import RichHandler




class RichUtils:
  
    """
    RichUtils 类。

    用于 Rich Utils 相关能力的封装。
    """
    def __init__(self):
        """
        初始化对象。
        """
        self.theme = Theme({
            "info": "bold blue",
            "warning": "bold yellow",
            "danger": "bold red",
        })
        self.console = Console(theme=self.theme)

    
    def print(self, msg: str, style: Literal['info', 'warning', 'danger']='info'):
        """
        打印。

        Args:
            msg: msg 参数。
            style: style 参数。

        Returns:
            Any: 返回值。
        """
        self.console.print(msg, style=style)
    
    def ask(self, msg: str="是否继续操作？", choices: list[str]=["Y", "N", "CANCEL"], default: str='N', show_choices: bool=True):
        """
        询问。

        Args:
            msg: msg 参数。
            choices: choices 参数。
            default: default 参数。
            show_choices: show_choices 参数。

        Returns:
            Any: 返回值。
        """
        choice = Prompt.ask(
            f"[bold cyan]{msg}[/bold cyan]",
            choices=choices,
            default=default,
            show_choices=show_choices,
        )
        return choice
    
    def log(self, msg: str, style: Literal['info', 'warning', 'danger']='info'):
        """
        记录。

        Args:
            msg: msg 参数。
            style: style 参数。

        Returns:
            Any: 返回值。
        """
        self.console.log(msg, style=style)
