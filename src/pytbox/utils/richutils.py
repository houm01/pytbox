#!/usr/bin/env python3


from typing import Literal
from rich.console import Console
from rich.theme import Theme
from rich.prompt import Prompt
from rich.logging import RichHandler




class RichUtils:
  
    def __init__(self):
        self.theme = Theme({
            "info": "bold blue",
            "warning": "bold yellow",
            "danger": "bold red",
        })
        self.console = Console(theme=self.theme)

    
    def print(self, msg: str, style: Literal['info', 'warning', 'danger']='info'):
        self.console.print(msg, style=style)
    
    def ask(self, msg: str="是否继续操作？", choices: list[str]=["Y", "N", "CANCEL"], default: str='N', show_choices: bool=True):
        choice = Prompt.ask(
            f"[bold cyan]{msg}[/bold cyan]",
            choices=choices,
            default=default,
            show_choices=show_choices,
        )
        return choice
    
    def log(self, msg: str, style: Literal['info', 'warning', 'danger']='info'):
        self.console.log(msg, style=style)