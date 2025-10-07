"""Style primitives and theme registry for richframe."""
from .model import CellStyle, RowStyle, TableStyle
from .registry import StyleRegistry
from .theme import Theme, get_theme, list_themes, resolve_theme

__all__ = [
    "CellStyle",
    "RowStyle",
    "TableStyle",
    "StyleRegistry",
    "Theme",
    "get_theme",
    "list_themes",
    "resolve_theme",
]
