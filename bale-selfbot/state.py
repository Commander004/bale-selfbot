# state.py
from dataclasses import dataclass


@dataclass
class AppState:
    afk_enabled: bool = False
    afk_text: str = "سلام نیستم، بعداً پیام بده."

    name_clock_enabled: bool = False
    name_format: str = "commander04 time"
    waiting_for_format: bool = False

    bold_enabled: bool = False
    italic_enabled: bool = False


state = AppState()