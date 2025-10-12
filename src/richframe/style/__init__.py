"""Style primitives and theme registry for richframe."""
from .model import CellStyle, RowStyle, TableStyle
from .registry import StyleRegistry
from .theme import Theme, compose_theme, get_theme, list_themes, register_theme, resolve_theme

__all__ = [
    "CellStyle",
    "RowStyle",
    "TableStyle",
    "StyleRegistry",
    "Theme",
    "compose_theme",
    "get_theme",
    "list_themes",
    "register_theme",
    "resolve_theme",
]
