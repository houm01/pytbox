#!/usr/bin/env python3


from typing import Literal
from rich.console import Console
from rich.theme import Theme


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